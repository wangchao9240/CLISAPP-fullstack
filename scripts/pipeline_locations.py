#!/usr/bin/env python3
"""
Single source of truth for pipeline output locations and layer naming.

This is used by:
- scripts/run_pipeline_layer.py (per-layer wrappers)
- scripts/pipeline.py (full pipeline)
- scripts/pipeline_stage.py (stage runner)
- scripts/pipeline_prereqs.py (layer normalization)
"""

from __future__ import annotations


LAYER_ALIASES: dict[str, str] = {
    # Make target names
    "precip": "precipitation",
    "temp": "temperature",
}


def normalize_layer(layer: str) -> str:
    return LAYER_ALIASES.get(layer, layer)


LAYER_OUTPUTS: dict[str, dict[str, str]] = {
    "pm25": {
        "raw_dir": "data_pipeline/data/raw/pm25",
        "processed_dir": "data_pipeline/data/processed/pm25",
        "tiles_dir": "tiles/pm25",
    },
    "precipitation": {
        "raw_dir": "data_pipeline/data/raw/gpm/imerg_daily",
        "processed_dir": "data_pipeline/data/processed/gpm",
        "tiles_dir": "tiles/precipitation",
    },
    "uv": {
        "raw_dir": "data_pipeline/data/raw/cams/uv",
        "processed_dir": "data_pipeline/data/processed/uv",
        "tiles_dir": "tiles/uv",
    },
    "temperature": {
        "raw_dir": "N/A (Open-Meteo API)",
        "processed_dir": "data/processing/temp",
        "tiles_dir": "tiles/temperature",
    },
    "humidity": {
        "raw_dir": "N/A (Open-Meteo API)",
        "processed_dir": "data/processing/humidity",
        "tiles_dir": "tiles/humidity",
    },
}


def supported_layers() -> list[str]:
    return list(LAYER_OUTPUTS.keys())

