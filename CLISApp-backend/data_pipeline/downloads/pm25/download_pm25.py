#!/usr/bin/env python3
"""Download CAMS PM2.5 forecasts for Queensland with metadata."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cdsapi

from data_pipeline.downloads.common import build_lead_hours, ensure_directory, write_metadata

LOGGER = logging.getLogger(__name__)
QLD_BOUNDS = [-9.0, 138.0, -29.0, 154.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download CAMS PM2.5 forecasts for Queensland (GRIB)"
    )
    parser.add_argument("--days-back", type=int, default=1, help="Days back from today (UTC)")
    parser.add_argument(
        "--run-time", default="00:00", choices=["00:00", "12:00"], help="Forecast run (UTC)"
    )
    parser.add_argument(
        "--lead-hours", type=int, default=48, help="Forecast horizon (inclusive, <=120)"
    )
    parser.add_argument(
        "--output-dir", default="data_pipeline/data/raw/pm25", help="Directory for GRIB output"
    )
    return parser.parse_args()


def build_request(date_str: str, run_time: str, lead_hours: list[str]) -> dict:
    return {
        "variable": "particulate_matter_2.5um",
        "model_level": "60",
        "date": date_str,
        "time": run_time,
        "leadtime_hour": lead_hours,
        "area": QLD_BOUNDS,
        "format": "grib",
        "type": "forecast",
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    if args.lead_hours < 0 or args.lead_hours > 120:
        raise SystemExit("--lead-hours must be between 0 and 120")

    forecast_date = (datetime.now(timezone.utc) - timedelta(days=args.days_back)).strftime("%Y-%m-%d")
    lead_hours = build_lead_hours(args.lead_hours)
    output_dir = ensure_directory(Path(args.output_dir))
    outfile = output_dir / f"cams_pm25_qld_{forecast_date.replace('-', '')}.grib"

    LOGGER.info(
        "Requesting CAMS PM2.5 run %s UTC for %s (lead hours 0-%s)",
        args.run_time,
        forecast_date,
        args.lead_hours,
    )
    client = cdsapi.Client()
    client.retrieve(
        "cams-global-atmospheric-composition-forecasts",
        build_request(forecast_date, args.run_time, lead_hours),
        str(outfile),
    )
    LOGGER.info("Saved: %s", outfile)

    metadata = {
        "source": "CAMS Global Atmospheric Composition Forecasts",
        "dataset": "cams-global-atmospheric-composition-forecasts",
        "variable": "particulate_matter_2.5um",
        "request_date": forecast_date,
        "run_time": args.run_time,
        "lead_hours": [int(h) for h in lead_hours],
        "area": QLD_BOUNDS,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "output_file": str(outfile),
    }
    write_metadata(outfile, metadata)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        LOGGER.error("PM2.5 download failed: %s", exc)
        sys.exit(1)
