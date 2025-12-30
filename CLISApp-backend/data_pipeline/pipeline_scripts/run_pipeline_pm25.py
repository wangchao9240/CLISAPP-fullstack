#!/usr/bin/env python3
"""End-to-end pipeline for CAMS PM2.5: download → process → tiles."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(PACKAGE_ROOT))
    from pipeline_scripts.runner_utils import ROOT, python, run  # type: ignore
else:
    from .runner_utils import ROOT, python, run


DL_PM25 = ROOT / "data_pipeline" / "downloads" / "pm25"
PROC_PM25 = ROOT / "data_pipeline" / "processing" / "pm25"
PROC_COMMON = ROOT / "data_pipeline" / "processing" / "common"
DATA_RAW = ROOT / "data_pipeline" / "data" / "raw" / "pm25"
DATA_PROCESSED = ROOT / "data_pipeline" / "data" / "processed" / "pm25"
TILES_DIR = ROOT / "tiles" / "pm25"


def main(use_legacy_thresholds: bool = False):
    ROOT.mkdir(parents=True, exist_ok=True)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # 1) Download CAMS PM2.5 GRIB
    run(python(DL_PM25 / "download_pm25.py"))

    # 2) Process GRIB → NetCDF + GeoTIFF
    run(python(PROC_PM25 / "process_grib_data.py"))

    # 3.1 生成 z6-13
    args = [str(PROC_COMMON / 'generate_tiles.py'), str(DATA_PROCESSED / 'pm25_qld_cams_processed.tif')]
    if use_legacy_thresholds:
        args.append('--legacy-thresholds')
    run([sys.executable, *args])

    # Upsample highest generated zoom to reach z13 if missing
    if not (TILES_DIR / "13").exists():
        run(python(PROC_COMMON / "upsample_zoom11_to_12.py", "--min-zoom", "11", "--max-zoom", "13", "pm25"))

    print("\n✅ PM2.5 数据流水线完成!")
    print(f"📁 瓦片目录: {TILES_DIR}")
    print("📝 下一步: python data_pipeline/servers/tile_server.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run PM2.5 data pipeline")
    parser.add_argument('--legacy-thresholds', action='store_true', help='Use WHO default thresholds instead of dynamic breaks')
    args = parser.parse_args()

    main(use_legacy_thresholds=args.legacy_thresholds)


