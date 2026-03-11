"""
Unified Open-Meteo processor for all climate layers.

This module fetches all supported climate dimensions from Open-Meteo in one pass,
exports per-layer GeoTIFF files, and generates map tiles for each layer.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Literal

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from data_pipeline.config.grid_config import GRID_POINTS, LAYER_CONFIG, QLD_BOUNDS
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.pipeline_logger import (
    LayerResult,
    PipelineExecutionLog,
    configure_pipeline_logging,
    log_layer_result,
)

logger = logging.getLogger(__name__)

LAYER_FIELD_MAP: Dict[str, str] = {
    "temperature": "temperature",
    "humidity": "humidity",
    "precipitation": "precipitation",
    "uv": "uv_index",
    "pm25": "pm25",
}

OUTPUT_DIR_MAP: Dict[str, Path] = {
    "temperature": Path("data/processing/temp"),
    "humidity": Path("data/processing/humidity"),
    "precipitation": Path("data/processing/precipitation"),
    "uv": Path("data/processing/uv"),
    "pm25": Path("data/processing/pm25"),
}

OUTPUT_BASENAME_MAP: Dict[str, str] = {
    "temperature": "temperature",
    "humidity": "humidity",
    "precipitation": "precipitation",
    "uv": "uv",
    "pm25": "pm25",
}


def _build_layer_arrays(
    climate_data: Dict[str, Dict[str, Any]]
) -> Dict[str, np.ndarray]:
    """Split pointwise climate data into 2D arrays for each layer."""
    unique_lats = sorted({point["latitude"] for point in GRID_POINTS}, reverse=True)
    unique_lons = sorted({point["longitude"] for point in GRID_POINTS})

    lat_to_row = {lat: idx for idx, lat in enumerate(unique_lats)}
    lon_to_col = {lon: idx for idx, lon in enumerate(unique_lons)}

    arrays = {
        layer: np.full((len(unique_lats), len(unique_lons)), np.nan, dtype=np.float32)
        for layer in LAYER_FIELD_MAP
    }

    for point in GRID_POINTS:
        key = f"{point['latitude']}:{point['longitude']}"
        values = climate_data.get(key)
        if not values:
            continue

        row = lat_to_row[point["latitude"]]
        col = lon_to_col[point["longitude"]]

        for layer, source_field in LAYER_FIELD_MAP.items():
            raw_value = values.get(source_field)
            if raw_value is None:
                continue

            try:
                arrays[layer][row, col] = float(raw_value)
            except (TypeError, ValueError):
                continue

    return arrays


def _extract_representative_values(arrays: dict[str, Any]) -> dict[str, float]:
    """Extract conservative Queensland-wide values for health alert checks."""
    representative_values: dict[str, float] = {}

    for layer, raw_array in arrays.items():
        array = np.asarray(raw_array, dtype=np.float32)
        if array.size == 0 or np.isnan(array).all():
            continue

        representative_values[layer] = float(np.nanmax(array))

    return representative_values


def _write_geotiff(layer: str, data: np.ndarray, timestamp: str) -> Path:
    """Write one layer array to a GeoTIFF file and update latest symlink."""
    out_dir = OUTPUT_DIR_MAP[layer]
    out_dir.mkdir(parents=True, exist_ok=True)

    basename = OUTPUT_BASENAME_MAP[layer]
    tif_path = out_dir / f"{basename}_openmeteo_{timestamp}.tif"
    latest_link = out_dir / f"{basename}_latest.tif"

    transform = from_bounds(
        QLD_BOUNDS["west"],
        QLD_BOUNDS["south"],
        QLD_BOUNDS["east"],
        QLD_BOUNDS["north"],
        data.shape[1],
        data.shape[0],
    )

    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        dtype=np.float32,
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=np.nan,
        compress="lzw",
    ) as dst:
        dst.write(data.astype(np.float32), 1)
        layer_cfg = LAYER_CONFIG.get(layer if layer != "uv" else "uv_index", {})
        dst.update_tags(
            variable=LAYER_FIELD_MAP[layer],
            units=layer_cfg.get("unit", ""),
            source="Open-Meteo",
            creation_time=_utcnow().isoformat(),
        )

    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(tif_path.name)
    old_files = [
        p
        for p in out_dir.glob(f"{basename}_openmeteo_*.tif")
        if p.name != tif_path.name
    ]
    for old_file in old_files:
        old_file.unlink()
    logger.info("Removed %d old %s GeoTIFF files", len(old_files), layer)

    return tif_path


def _generate_tiles(layer: str, tif_path: Path) -> None:
    """Generate PNG tiles for a layer GeoTIFF."""
    cmd = [
        sys.executable,
        "-m",
        "data_pipeline.processing.common.generate_tiles",
        str(tif_path),
        layer,
    ]
    logger.info("Generating %s tiles from %s", layer, tif_path)
    subprocess.run(cmd, check=True)


def _normalize_trigger_type(raw_value: str | None) -> Literal["scheduled", "manual"]:
    if (raw_value or "").strip().lower() == "scheduled":
        return "scheduled"
    return "manual"


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime (no tzinfo).

    Uses datetime.now(UTC) to avoid deprecated utcnow(), then strips
    tzinfo to stay consistent with naive-UTC convention used throughout
    the pipeline codebase.
    """
    return datetime.now(UTC).replace(tzinfo=None)


async def process_all_layers(
    skip_tiles: bool = False,
    trigger_type: Literal["scheduled", "manual"] = "manual",
) -> tuple[Dict[str, Path], PipelineExecutionLog]:
    """Fetch all layers from Open-Meteo and generate per-layer GeoTIFF + tiles."""
    run_id = str(uuid.uuid4())
    run_start = _utcnow()
    logger.info("Fetching Open-Meteo climate data for %d grid points", len(GRID_POINTS))

    async with OpenMeteoFetcher() as fetcher:
        climate_data = await fetcher.fetch_all_data(GRID_POINTS)

    if not climate_data:
        raise RuntimeError("Open-Meteo fetch returned no data")

    arrays = _build_layer_arrays(climate_data)
    timestamp = _utcnow().strftime("%Y%m%d_%H%M%S")

    outputs: Dict[str, Path] = {}
    layer_results: dict[str, LayerResult] = {}
    for layer, array in arrays.items():
        layer_start = _utcnow()

        try:
            coverage = (
                float(np.count_nonzero(~np.isnan(array))) / float(array.size) * 100.0
            )
            logger.info("%s coverage: %.1f%%", layer, coverage)

            tif_path = _write_geotiff(layer, array, timestamp)
            if not skip_tiles:
                _generate_tiles(layer, tif_path)
            else:
                logger.info("Skipping tile generation (geotiff-only mode)")
            outputs[layer] = tif_path

            layer_end = _utcnow()
            layer_result = LayerResult(
                layer_name=layer,
                status="success",
                start_time=layer_start,
                end_time=layer_end,
                duration_seconds=(layer_end - layer_start).total_seconds(),
            )
            layer_results[layer] = layer_result
            log_layer_result(logger, run_id, layer_result, data_timestamp=timestamp)
        except Exception as exc:
            layer_end = _utcnow()
            layer_result = LayerResult(
                layer_name=layer,
                status="failed",
                start_time=layer_start,
                end_time=layer_end,
                duration_seconds=(layer_end - layer_start).total_seconds(),
                error_message=str(exc),
                error_traceback=traceback.format_exc(),
            )
            layer_results[layer] = layer_result
            log_layer_result(logger, run_id, layer_result, data_timestamp=timestamp)
            continue

    execution_log = PipelineExecutionLog(
        run_id=run_id,
        start_time=run_start,
        end_time=_utcnow(),
        trigger_type=trigger_type,
        layer_results=layer_results,
    )
    logger.info(execution_log.format_summary(data_timestamp=timestamp))

    try:
        from app.core.config import settings
        from app.services.notification_service import NotificationService

        representative_values = _extract_representative_values(arrays)
        notification_service = NotificationService(
            credentials_path=settings.firebase_credentials_path,
            thresholds_path=settings.health_thresholds_path,
        )
        notification_result = notification_service.check_and_notify(
            representative_values
        )
        logger.info("Notification check result: %s", notification_result)
    except Exception as exc:
        logger.warning("Notification check failed (non-fatal): %s", exc, exc_info=True)

    return outputs, execution_log


def main() -> int:
    configure_pipeline_logging()

    try:
        skip = (
            os.environ.get("SKIP_TILES", "").strip().lower() in ("1", "true", "yes")
            or "--geotiff-only" in sys.argv
        )
        trigger_type = _normalize_trigger_type(os.environ.get("PIPELINE_TRIGGER"))
        outputs, execution_log = asyncio.run(
            process_all_layers(skip_tiles=skip, trigger_type=trigger_type)
        )
        logger.info("Pipeline run id: %s", execution_log.run_id)
        logger.info("Generated layers: %s", ", ".join(sorted(outputs.keys())))
        for layer, path in outputs.items():
            logger.info("%s GeoTIFF: %s", layer, path)
        return 0
    except Exception as exc:
        # Log structured summary even on early failure (e.g. fetch stage)
        run_id = str(uuid.uuid4())
        fail_log = PipelineExecutionLog(
            run_id=run_id,
            start_time=_utcnow(),
            end_time=_utcnow(),
            trigger_type=trigger_type,
            layer_results={},
        )
        logger.error(fail_log.format_summary())
        logger.error("Open-Meteo all-layers processing failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
