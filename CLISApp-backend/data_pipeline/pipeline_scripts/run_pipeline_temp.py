#!/usr/bin/env python3
"""
End-to-end pipeline for temperature tiles.

Uses Open-Meteo API with BOM ACCESS-G model for Queensland temperature data.
- Fast processing: ~10 minutes total
- Resolution: ~50km grid
- Free API, no authentication required
- Direct Queensland coverage
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(PACKAGE_ROOT))
    from pipeline_scripts.runner_utils import ROOT, python, run  # type: ignore
else:
    from .runner_utils import ROOT, python, run


# Updated to use Open-Meteo processors
PROC_TEMP = ROOT / "data_pipeline" / "processing" / "temp"
DATA_PROCESSED = ROOT / "data" / "processing" / "temp"
TILES_DIR = ROOT / "tiles" / "temperature"


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch + Process Open-Meteo data
    print("📡 Fetching and processing Open-Meteo temperature data...")
    run([sys.executable, "-m", "data_pipeline.processing.temp.process_openmeteo_temp_to_tif"])

    # Step 2: Generate tiles
    print("🗺️  Generating temperature tiles...")
    run([sys.executable, "-m", "data_pipeline.processing.temp.generate_temperature_tiles"])

    print("\n✅ Temperature 数据流水线完成! (Open-Meteo)")
    print(f"📁 瓦片目录: {TILES_DIR}")
    print("📊 数据源: Open-Meteo API (BOM ACCESS-G model)")
    print("⏱️  数据延迟: Real-time")


if __name__ == "__main__":
    main()


