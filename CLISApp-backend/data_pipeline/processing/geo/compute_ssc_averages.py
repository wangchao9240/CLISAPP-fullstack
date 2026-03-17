"""Compute per-SSC climate averages from the latest processed GeoTIFF rasters."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

from data_pipeline.processing.geo.process_boundaries import (
    SSC_SHP,
    load_shapefile,
    prepare_ssc_records,
    resolve_field_mapping,
)

LOGGER = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = (
    BACKEND_ROOT / "data_pipeline" / "data" / "processed" / "geo" / "ssc_climate_values.json"
)


@dataclass(frozen=True)
class LayerSpec:
    name: str
    raster_path: Path
    unit: str
    precision: int = 1


@dataclass(frozen=True)
class SscRegion:
    ssc_id: str
    name: str
    group_id: str
    geometry: dict[str, Any]


LAYER_SPECS: dict[str, LayerSpec] = {
    "temperature": LayerSpec(
        name="temperature",
        raster_path=BACKEND_ROOT / "data" / "processing" / "temp" / "temperature_latest.tif",
        unit="C",
    ),
    "humidity": LayerSpec(
        name="humidity",
        raster_path=BACKEND_ROOT / "data" / "processing" / "humidity" / "humidity_latest.tif",
        unit="%",
    ),
    "precipitation": LayerSpec(
        name="precipitation",
        raster_path=BACKEND_ROOT / "data" / "processing" / "precipitation" / "precipitation_latest.tif",
        unit="mm/day",
    ),
    "uv": LayerSpec(
        name="uv",
        raster_path=BACKEND_ROOT / "data" / "processing" / "uv" / "uv_latest.tif",
        unit="UVI",
    ),
    "pm25": LayerSpec(
        name="pm25",
        raster_path=BACKEND_ROOT / "data" / "processing" / "pm25" / "pm25_latest.tif",
        unit="ug/m3",
    ),
}


def _parse_timestamp(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_ssc_regions(shapefile_path: Path) -> list[SscRegion]:
    ssc_gdf = load_shapefile(shapefile_path)
    field_mapping = resolve_field_mapping(ssc_gdf.columns)
    prepared = prepare_ssc_records(ssc_gdf, field_mapping).sort_values(
        ["_group_id", "_ssc_code"]
    )

    return [
        SscRegion(
            ssc_id=str(row["_ssc_id"]),
            name=str(row["_name"]),
            group_id=str(row["_group_id"]),
            geometry=mapping(row["geometry"]),
        )
        for row in prepared.to_dict("records")
    ]


def _build_region_payload(regions: list[SscRegion]) -> dict[str, dict[str, Any]]:
    return {
        region.ssc_id: {
            "name": region.name,
            "group_id": region.group_id,
        }
        for region in regions
    }


def _extract_dataset_timestamp(dataset: rasterio.io.DatasetReader, raster_path: Path) -> datetime:
    tags = dataset.tags()
    for key in ("creation_time", "generated_at", "timestamp"):
        parsed = _parse_timestamp(tags.get(key))
        if parsed is not None:
            return parsed

    file_mtime = datetime.fromtimestamp(raster_path.stat().st_mtime, tz=UTC)
    return file_mtime


def _mean_value_for_region(
    dataset: rasterio.io.DatasetReader,
    region: SscRegion,
) -> float | None:
    try:
        data, _ = mask(dataset, [region.geometry], crop=True, filled=False, indexes=1)
    except ValueError:
        return None
    except Exception as exc:
        LOGGER.warning(
            "Failed to mask %s for %s: %s",
            region.ssc_id,
            dataset.name,
            exc,
        )
        return None

    values = (
        data.compressed()
        if np.ma.isMaskedArray(data)
        else np.asarray(data, dtype=np.float32).ravel()
    )
    finite_values = np.asarray(values, dtype=np.float32)
    finite_values = finite_values[np.isfinite(finite_values)]
    if finite_values.size == 0:
        return None

    return float(np.mean(finite_values))


def _compute_layer_averages(
    regions: list[SscRegion],
    spec: LayerSpec,
) -> tuple[dict[str, float | None], dict[str, Any]]:
    if not spec.raster_path.exists():
        LOGGER.warning("GeoTIFF for %s not found at %s; skipping layer", spec.name, spec.raster_path)
        return {}, {
            "available": False,
            "valid_ssc_count": 0,
            "coverage_pct": 0.0,
            "raster_path": str(spec.raster_path),
        }

    values: dict[str, float | None] = {}
    valid_count = 0
    missing_regions: list[str] = []

    with rasterio.open(spec.raster_path) as dataset:
        layer_timestamp = _extract_dataset_timestamp(dataset, spec.raster_path)
        for region in regions:
            mean_value = _mean_value_for_region(dataset, region)
            if mean_value is None:
                values[region.ssc_id] = None
                missing_regions.append(f"{region.ssc_id} ({region.name})")
                continue

            values[region.ssc_id] = round(mean_value, spec.precision)
            valid_count += 1

    if missing_regions:
        LOGGER.warning(
            "%s had %d SSCs with 0 valid pixels; examples: %s",
            spec.name,
            len(missing_regions),
            ", ".join(missing_regions[:5]),
        )

    total_regions = len(regions)
    coverage_pct = round((valid_count / total_regions) * 100.0, 1) if total_regions else 0.0
    return values, {
        "available": True,
        "valid_ssc_count": valid_count,
        "coverage_pct": coverage_pct,
        "raster_path": str(spec.raster_path),
        "timestamp": layer_timestamp,
    }


def compute_ssc_climate_averages(
    shapefile_path: Path = SSC_SHP,
    output_path: Path = OUTPUT_PATH,
    layer_specs: Mapping[str, LayerSpec] | None = None,
) -> dict[str, Any]:
    """Compute per-SSC mean climate values from the latest rasters."""

    start_time = time.perf_counter()
    target_layer_specs = dict(layer_specs or LAYER_SPECS)
    regions = _load_ssc_regions(shapefile_path)
    region_payload = _build_region_payload(regions)

    layer_coverage: dict[str, dict[str, Any]] = {}
    dataset_timestamps: list[datetime] = []

    for layer_name, spec in target_layer_specs.items():
        layer_values, coverage = _compute_layer_averages(regions, spec)
        layer_timestamp = coverage.pop("timestamp", None)
        if isinstance(layer_timestamp, datetime):
            dataset_timestamps.append(layer_timestamp)

        if coverage.get("available"):
            region_payload = {
                region_id: {
                    **payload,
                    layer_name: {
                        "value": layer_values.get(region_id),
                        "unit": spec.unit,
                    },
                }
                for region_id, payload in region_payload.items()
            }

        layer_coverage[layer_name] = coverage

    output_timestamp = _format_timestamp(
        max(dataset_timestamps) if dataset_timestamps else datetime.now(UTC)
    )
    payload = {
        "timestamp": output_timestamp,
        "source": "Open-Meteo",
        "ssc_count": len(regions),
        "regions": region_payload,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload), encoding="utf-8")

    elapsed_seconds = time.perf_counter() - start_time
    LOGGER.info("Processed %d SSC regions", len(regions))
    for layer_name, coverage in layer_coverage.items():
        LOGGER.info(
            "%s valid coverage: %s/%s SSCs (%.1f%%)",
            layer_name,
            coverage.get("valid_ssc_count", 0),
            len(regions),
            coverage.get("coverage_pct", 0.0),
        )
    LOGGER.info("SSC climate averaging completed in %.2f seconds", elapsed_seconds)

    return {
        "output_path": str(output_path),
        "ssc_count": len(regions),
        "layer_coverage": layer_coverage,
        "elapsed_seconds": round(elapsed_seconds, 2),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = compute_ssc_climate_averages()
    LOGGER.info("SSC climate averages written: %s", result)


if __name__ == "__main__":
    main()
