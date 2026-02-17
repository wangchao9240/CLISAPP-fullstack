#!/usr/bin/env python3
"""
Phase 0 validator for Open-Meteo full-grid data coverage.

Validates one full cycle for Queensland grid points against migration gates:
- Weather API coverage for temperature/humidity/precipitation/uv_index
- Air Quality API coverage for pm2_5
- End-to-end runtime and rate-limit behavior
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.config.grid_config import GRID_POINTS  # noqa: E402


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEZONE = "Australia/Brisbane"
WEATHER_FIELDS = ("temperature", "humidity", "precipitation", "uv_index")


def estimate_call_budget(
    point_count: int,
    batch_size: int,
    apis_per_batch: int = 2,
    updates_per_day: int = 24,
) -> Dict[str, int]:
    batches = math.ceil(point_count / batch_size)
    requests_per_cycle = batches * apis_per_batch
    requests_per_day = requests_per_cycle * updates_per_day
    return {
        "point_count": point_count,
        "batch_size": batch_size,
        "batches": batches,
        "apis_per_batch": apis_per_batch,
        "requests_per_cycle": requests_per_cycle,
        "updates_per_day": updates_per_day,
        "requests_per_day": requests_per_day,
    }


def evaluate_gate(
    weather_coverage: Dict[str, float],
    pm25_coverage: float,
    total_minutes: float,
    rate_limit_ratio: float,
    weather_target: float = 90.0,
    pm25_target: float = 80.0,
    max_minutes: float = 30.0,
    max_rate_limit_ratio: float = 0.05,
) -> Dict[str, Any]:
    fail_reasons: List[str] = []

    for field_name, value in weather_coverage.items():
        if value < weather_target:
            fail_reasons.append(f"weather_{field_name}")
    if pm25_coverage < pm25_target:
        fail_reasons.append("pm25_coverage")
    if total_minutes > max_minutes:
        fail_reasons.append("total_runtime_minutes")
    if rate_limit_ratio > max_rate_limit_ratio:
        fail_reasons.append("rate_limit_ratio")

    return {
        "pass": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "thresholds": {
            "weather_target": weather_target,
            "pm25_target": pm25_target,
            "max_minutes": max_minutes,
            "max_rate_limit_ratio": max_rate_limit_ratio,
        },
    }


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    rank = (len(values) - 1) * percentile
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(values[low])
    weight = rank - low
    return float(values[low] * (1 - weight) + values[high] * weight)


def _to_location_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


@dataclass
class Metrics:
    weather_request_total: int = 0
    weather_request_success: int = 0
    air_request_total: int = 0
    air_request_success: int = 0
    weather_status_counts: Dict[int, int] = field(default_factory=dict)
    air_status_counts: Dict[int, int] = field(default_factory=dict)
    weather_429: int = 0
    air_429: int = 0
    weather_latencies: List[float] = field(default_factory=list)
    air_latencies: List[float] = field(default_factory=list)
    batch_latencies: List[float] = field(default_factory=list)
    weather_errors: List[str] = field(default_factory=list)
    air_errors: List[str] = field(default_factory=list)


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    params: Dict[str, str],
    api_kind: str,
    metrics: Metrics,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> Optional[Any]:
    for attempt in range(1, max_attempts + 1):
        if api_kind == "weather":
            metrics.weather_request_total += 1
        else:
            metrics.air_request_total += 1

        t0 = time.perf_counter()
        try:
            response = await client.get(url, params=params)
            elapsed = time.perf_counter() - t0
        except Exception as exc:  # pragma: no cover - network path
            message = f"{api_kind} request failed (attempt {attempt}/{max_attempts}): {exc}"
            if api_kind == "weather":
                metrics.weather_errors.append(message)
            else:
                metrics.air_errors.append(message)
            if attempt < max_attempts:
                await asyncio.sleep(retry_backoff_seconds * attempt)
                continue
            return None

        if api_kind == "weather":
            metrics.weather_latencies.append(elapsed)
            metrics.weather_status_counts[response.status_code] = (
                metrics.weather_status_counts.get(response.status_code, 0) + 1
            )
        else:
            metrics.air_latencies.append(elapsed)
            metrics.air_status_counts[response.status_code] = (
                metrics.air_status_counts.get(response.status_code, 0) + 1
            )

        if response.status_code == 429:
            if api_kind == "weather":
                metrics.weather_429 += 1
            else:
                metrics.air_429 += 1
            if attempt < max_attempts:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_seconds = max(float(retry_after), 1.0)
                    except ValueError:
                        sleep_seconds = max(retry_backoff_seconds * attempt * 5.0, 5.0)
                else:
                    # 429 responses often need a larger cool-down than generic retries.
                    sleep_seconds = max(retry_backoff_seconds * attempt * 5.0, 5.0)
                await asyncio.sleep(sleep_seconds)
                continue

        if 200 <= response.status_code < 300:
            if api_kind == "weather":
                metrics.weather_request_success += 1
            else:
                metrics.air_request_success += 1
            try:
                return response.json()
            except Exception as exc:  # pragma: no cover - malformed json
                message = f"{api_kind} JSON parse failed: {exc}"
                if api_kind == "weather":
                    metrics.weather_errors.append(message)
                else:
                    metrics.air_errors.append(message)
                return None

        message = f"{api_kind} status={response.status_code} body={response.text[:180]}"
        if api_kind == "weather":
            metrics.weather_errors.append(message)
        else:
            metrics.air_errors.append(message)

        if response.status_code >= 500 and attempt < max_attempts:
            await asyncio.sleep(retry_backoff_seconds * attempt)
            continue
        return None

    return None


async def run_validation(args: argparse.Namespace) -> Dict[str, Any]:
    points = GRID_POINTS[: args.max_points] if args.max_points > 0 else GRID_POINTS
    coverage_counts = {
        "temperature": 0,
        "humidity": 0,
        "precipitation": 0,
        "uv_index": 0,
        "pm25": 0,
    }
    metrics = Metrics()

    total_batches = math.ceil(len(points) / args.batch_size)
    start_cycle = time.perf_counter()

    async with httpx.AsyncClient(timeout=args.request_timeout) as client:
        for idx in range(total_batches):
            batch_start = time.perf_counter()
            batch = points[idx * args.batch_size : (idx + 1) * args.batch_size]
            lats = ",".join(str(p["latitude"]) for p in batch)
            lons = ",".join(str(p["longitude"]) for p in batch)

            weather_params = {
                "latitude": lats,
                "longitude": lons,
                "current": "temperature_2m,relative_humidity_2m,precipitation,uv_index",
                "timezone": TIMEZONE,
                "forecast_days": "1",
            }
            air_params = {
                "latitude": lats,
                "longitude": lons,
                "current": "pm2_5",
                "timezone": TIMEZONE,
                "domains": args.air_domains,
            }

            weather_payload, air_payload = await asyncio.gather(
                _request_with_retries(
                    client=client,
                    url=WEATHER_URL,
                    params=weather_params,
                    api_kind="weather",
                    metrics=metrics,
                    max_attempts=args.max_attempts,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                ),
                _request_with_retries(
                    client=client,
                    url=AIR_QUALITY_URL,
                    params=air_params,
                    api_kind="air",
                    metrics=metrics,
                    max_attempts=args.max_attempts,
                    retry_backoff_seconds=args.retry_backoff_seconds,
                ),
            )

            weather_items = _to_location_list(weather_payload)
            air_items = _to_location_list(air_payload)

            for pidx in range(len(batch)):
                weather_current = {}
                if pidx < len(weather_items):
                    weather_current = weather_items[pidx].get("current", {}) or {}
                air_current = {}
                if pidx < len(air_items):
                    air_current = air_items[pidx].get("current", {}) or {}

                if weather_current.get("temperature_2m") is not None:
                    coverage_counts["temperature"] += 1
                if weather_current.get("relative_humidity_2m") is not None:
                    coverage_counts["humidity"] += 1
                if weather_current.get("precipitation") is not None:
                    coverage_counts["precipitation"] += 1
                if weather_current.get("uv_index") is not None:
                    coverage_counts["uv_index"] += 1
                if air_current.get("pm2_5") is not None:
                    coverage_counts["pm25"] += 1

            metrics.batch_latencies.append(time.perf_counter() - batch_start)
            if args.sleep_between_batches > 0:
                await asyncio.sleep(args.sleep_between_batches)

    total_seconds = time.perf_counter() - start_cycle
    total_minutes = total_seconds / 60.0

    weather_coverage = {
        "temperature": 100.0 * coverage_counts["temperature"] / len(points),
        "humidity": 100.0 * coverage_counts["humidity"] / len(points),
        "precipitation": 100.0 * coverage_counts["precipitation"] / len(points),
        "uv_index": 100.0 * coverage_counts["uv_index"] / len(points),
    }
    pm25_coverage = 100.0 * coverage_counts["pm25"] / len(points)

    total_429 = metrics.weather_429 + metrics.air_429
    total_requests = metrics.weather_request_total + metrics.air_request_total
    rate_limit_ratio = (total_429 / total_requests) if total_requests > 0 else 0.0

    gate = evaluate_gate(
        weather_coverage=weather_coverage,
        pm25_coverage=pm25_coverage,
        total_minutes=total_minutes,
        rate_limit_ratio=rate_limit_ratio,
        weather_target=args.weather_target,
        pm25_target=args.pm25_target,
        max_minutes=args.max_minutes,
        max_rate_limit_ratio=args.max_rate_limit_ratio,
    )

    budget = estimate_call_budget(
        point_count=len(points),
        batch_size=args.batch_size,
        apis_per_batch=2,
        updates_per_day=24,
    )
    full_grid_budget = estimate_call_budget(
        point_count=len(GRID_POINTS),
        batch_size=args.batch_size,
        apis_per_batch=2,
        updates_per_day=24,
    )
    estimated_full_grid_minutes = total_minutes * (len(GRID_POINTS) / len(points))

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "points_tested": len(points),
            "points_total_grid": len(GRID_POINTS),
            "batch_size": args.batch_size,
            "total_batches": total_batches,
            "air_domains": args.air_domains,
        },
        "coverage_percent": {
            **weather_coverage,
            "pm25": pm25_coverage,
        },
        "request_metrics": {
            "weather": {
                "total": metrics.weather_request_total,
                "success": metrics.weather_request_success,
                "success_rate_percent": (
                    100.0 * metrics.weather_request_success / metrics.weather_request_total
                    if metrics.weather_request_total > 0
                    else 0.0
                ),
                "status_counts": metrics.weather_status_counts,
                "latency_seconds": {
                    "avg": statistics.mean(metrics.weather_latencies) if metrics.weather_latencies else 0.0,
                    "p95": _percentile(sorted(metrics.weather_latencies), 0.95) if metrics.weather_latencies else 0.0,
                    "max": max(metrics.weather_latencies) if metrics.weather_latencies else 0.0,
                },
                "rate_limit_429": metrics.weather_429,
            },
            "air_quality": {
                "total": metrics.air_request_total,
                "success": metrics.air_request_success,
                "success_rate_percent": (
                    100.0 * metrics.air_request_success / metrics.air_request_total
                    if metrics.air_request_total > 0
                    else 0.0
                ),
                "status_counts": metrics.air_status_counts,
                "latency_seconds": {
                    "avg": statistics.mean(metrics.air_latencies) if metrics.air_latencies else 0.0,
                    "p95": _percentile(sorted(metrics.air_latencies), 0.95) if metrics.air_latencies else 0.0,
                    "max": max(metrics.air_latencies) if metrics.air_latencies else 0.0,
                },
                "rate_limit_429": metrics.air_429,
            },
            "combined": {
                "total_requests": total_requests,
                "total_429": total_429,
                "rate_limit_ratio": rate_limit_ratio,
            },
        },
        "timing": {
            "total_seconds": total_seconds,
            "total_minutes": total_minutes,
            "batch_latency_seconds": {
                "avg": statistics.mean(metrics.batch_latencies) if metrics.batch_latencies else 0.0,
                "p95": _percentile(sorted(metrics.batch_latencies), 0.95) if metrics.batch_latencies else 0.0,
                "max": max(metrics.batch_latencies) if metrics.batch_latencies else 0.0,
            },
            "estimated_full_grid_minutes": estimated_full_grid_minutes,
        },
        "call_budget": {
            "tested_scope": budget,
            "full_grid_scope": full_grid_budget,
        },
        "gate": gate,
        "errors": {
            "weather": metrics.weather_errors[-20:],
            "air_quality": metrics.air_errors[-20:],
        },
    }

    return report


def print_report(report: Dict[str, Any]) -> None:
    scope = report["scope"]
    cov = report["coverage_percent"]
    req = report["request_metrics"]
    timing = report["timing"]
    gate = report["gate"]
    budget = report["call_budget"]["full_grid_scope"]

    print("\n=== Open-Meteo Phase 0 Validation Report ===")
    print(f"Timestamp (UTC): {report['timestamp_utc']}")
    print(
        f"Grid tested: {scope['points_tested']}/{scope['points_total_grid']} points "
        f"in {scope['total_batches']} batches (size={scope['batch_size']})"
    )
    print(f"Air domains: {scope['air_domains']}")

    print("\nCoverage (%):")
    for field_name in WEATHER_FIELDS:
        print(f"  {field_name:13}: {cov[field_name]:6.2f}")
    print(f"  {'pm25':13}: {cov['pm25']:6.2f}")

    print("\nRequests:")
    print(
        f"  Weather API   : total={req['weather']['total']} success={req['weather']['success']} "
        f"429={req['weather']['rate_limit_429']} success_rate={req['weather']['success_rate_percent']:.2f}%"
    )
    print(
        f"  Air Quality   : total={req['air_quality']['total']} success={req['air_quality']['success']} "
        f"429={req['air_quality']['rate_limit_429']} success_rate={req['air_quality']['success_rate_percent']:.2f}%"
    )
    print(
        f"  Combined      : total={req['combined']['total_requests']} "
        f"429={req['combined']['total_429']} ratio={req['combined']['rate_limit_ratio']:.4f}"
    )

    print("\nTiming:")
    print(
        f"  Total cycle   : {timing['total_seconds']:.2f}s ({timing['total_minutes']:.2f} min), "
        f"estimated full-grid={timing['estimated_full_grid_minutes']:.2f} min"
    )
    print(
        f"  Weather latency (avg/p95/max): "
        f"{req['weather']['latency_seconds']['avg']:.3f}/"
        f"{req['weather']['latency_seconds']['p95']:.3f}/"
        f"{req['weather']['latency_seconds']['max']:.3f}s"
    )
    print(
        f"  Air latency     (avg/p95/max): "
        f"{req['air_quality']['latency_seconds']['avg']:.3f}/"
        f"{req['air_quality']['latency_seconds']['p95']:.3f}/"
        f"{req['air_quality']['latency_seconds']['max']:.3f}s"
    )

    print("\nCall budget (full grid):")
    print(
        f"  batches={budget['batches']} requests/cycle={budget['requests_per_cycle']} "
        f"requests/day={budget['requests_per_day']}"
    )

    print("\nGate:")
    print(f"  pass={gate['pass']}")
    if gate["fail_reasons"]:
        print(f"  fail_reasons={', '.join(gate['fail_reasons'])}")
    else:
        print("  fail_reasons=none")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Open-Meteo APIs for Queensland full-grid migration.")
    parser.add_argument("--max-points", type=int, default=0, help="Number of grid points to test (0 = full grid).")
    parser.add_argument("--batch-size", type=int, default=100, help="Coordinate batch size per request.")
    parser.add_argument("--request-timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument("--max-attempts", type=int, default=5, help="Retry attempts per request.")
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0, help="Backoff base for retries.")
    parser.add_argument(
        "--sleep-between-batches",
        type=float,
        default=1.0,
        help="Pause between batches to reduce rate-limit collisions.",
    )
    parser.add_argument("--air-domains", type=str, default="auto", help="Open-Meteo Air Quality domain selection.")
    parser.add_argument("--weather-target", type=float, default=90.0, help="Weather coverage threshold percent.")
    parser.add_argument("--pm25-target", type=float, default=80.0, help="PM2.5 coverage threshold percent.")
    parser.add_argument("--max-minutes", type=float, default=30.0, help="Max end-to-end cycle time in minutes.")
    parser.add_argument(
        "--max-rate-limit-ratio",
        type=float,
        default=0.05,
        help="Max allowed 429 ratio over all requests.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="",
        help="Optional path for report JSON (default: CLISApp-backend/logs/validation/openmeteo_validation_*.json).",
    )
    return parser.parse_args()


async def _main_async() -> int:
    args = parse_args()
    report = await run_validation(args)
    print_report(report)

    if args.output_json:
        output_path = Path(args.output_json)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PROJECT_ROOT / "logs" / "validation" / f"openmeteo_validation_{stamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport JSON: {output_path}")

    return 0 if report["gate"]["pass"] else 1


def main() -> None:
    exit_code = asyncio.run(_main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
