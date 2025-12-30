"""Shared helpers for atmospheric data download scripts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Tuple


LOGGER = logging.getLogger(__name__)


def build_lead_hours(max_hours: int) -> List[str]:
    """Return an inclusive list of lead hours as strings."""

    if max_hours < 0:
        raise ValueError("lead_hours must be >= 0")
    if max_hours > 120:
        raise ValueError("lead_hours above 120 exceeds CAMS retention window")
    return [str(hour) for hour in range(0, max_hours + 1)]


def format_metadata_path(data_file: Path) -> Path:
    """Return metadata path for the given data file."""

    return data_file.with_name(f"{data_file.name}.metadata.json")


def write_metadata(data_file: Path, payload: dict) -> Path:
    """Write metadata JSON next to the data file."""

    metadata_path = format_metadata_path(data_file)
    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    LOGGER.info("Metadata written: %s", metadata_path)
    return metadata_path


def ensure_directory(path: Path) -> Path:
    """Create directory if missing and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_bbox(value: str) -> List[float]:
    """Parse a comma-separated bbox string into floats."""

    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 4:
        raise ValueError("bbox must have four comma-separated values")
    return [float(p) for p in parts]


def generate_grid_points(bbox: List[float], step: float) -> List[Tuple[float, float]]:
    """Generate (lat, lon) grid covering bbox with the provided step in degrees."""

    if step <= 0:
        raise ValueError("grid step must be > 0")

    lat_north, lon_west, lat_south, lon_east = bbox
    lat_max = max(lat_north, lat_south)
    lat_min = min(lat_north, lat_south)
    lon_min = min(lon_west, lon_east)
    lon_max = max(lon_west, lon_east)

    def frange(start: float, end: float) -> List[float]:
        values: List[float] = []
        current = start
        # Use round to avoid floating point drift when stepping
        while current < end:
            values.append(round(current, 4))
            current = round(current + step, 10)
        if not values or values[-1] < end - 1e-9:
            values.append(round(end, 4))
        return values

    latitudes = frange(lat_min, lat_max)
    longitudes = frange(lon_min, lon_max)

    grid: List[Tuple[float, float]] = []
    for lat in latitudes:
        for lon in longitudes:
            grid.append((lat, lon))
    return grid
