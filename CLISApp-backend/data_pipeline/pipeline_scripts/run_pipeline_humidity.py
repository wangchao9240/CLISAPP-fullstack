#!/usr/bin/env python3
"""
End-to-end pipeline for humidity tiles.

Uses Open-Meteo API with BOM ACCESS-G model for Queensland humidity data.
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
PROC_HUMIDITY = ROOT / "data_pipeline" / "processing" / "humidity"
PROC_COMMON = ROOT / "data_pipeline" / "processing" / "common"
DATA_PROCESSED = ROOT / "data" / "processing" / "humidity"
TILES_DIR = ROOT / "tiles" / "humidity"


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch + Process Open-Meteo data
    print("📡 Fetching and processing Open-Meteo humidity data...")
    run([sys.executable, "-m", "data_pipeline.processing.humidity.process_openmeteo_humidity_to_tif"])

    # Step 2: Generate tiles
    print("🗺️  Generating humidity tiles...")
    run([sys.executable, "-m", "data_pipeline.processing.humidity.generate_humidity_tiles"])

    # Step 3: Upsample high zoom levels if needed
    if not (TILES_DIR / "13").exists():
        print("🔍 Upsampling to higher zoom levels...")
        run([sys.executable, "-m", "data_pipeline.processing.common.upsample_zoom11_to_12", "--min-zoom", "11", "--max-zoom", "13", "humidity"])

    print("\n✅ Humidity 数据流水线完成! (Open-Meteo)")
    print(f"📁 瓦片目录: {TILES_DIR}")
    print("📊 数据源: Open-Meteo API (BOM ACCESS-G model)")
    print("⏱️  数据延迟: Real-time")
    print("💧 数据类型: Relative humidity at 2m")


if __name__ == "__main__":
    main()


