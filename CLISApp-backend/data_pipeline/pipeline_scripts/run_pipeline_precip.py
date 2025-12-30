#!/usr/bin/env python3
"""End-to-end pipeline for GPM precipitation tiles."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(PACKAGE_ROOT))
    from pipeline_scripts.runner_utils import ROOT, python, run  # type: ignore
else:
    from .runner_utils import ROOT, python, run


DL_GPM = ROOT / "data_pipeline" / "downloads" / "gpm"
PROC_GPM = ROOT / "data_pipeline" / "processing" / "gpm"
PROC_COMMON = ROOT / "data_pipeline" / "processing" / "common"
DATA_RAW = ROOT / "data_pipeline" / "data" / "raw" / "gpm"
DATA_PROCESSED = ROOT / "data_pipeline" / "data" / "processed" / "gpm"
TILES_DIR = ROOT / "tiles" / "precipitation"


def main(mode: str = "daily") -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    run(python(DL_GPM / "download_gpm_imerg.py", "--mode", mode))

    geotiff = DATA_PROCESSED / "imerg_daily_precip_qld.tif"
    run(python(PROC_GPM / "process_imerg_daily_to_tif.py"))

    run(python(PROC_GPM / "generate_precip_tiles.py", "6-12"))

    if not (TILES_DIR / "13").exists():
        run(python(PROC_COMMON / "upsample_zoom11_to_12.py", "--min-zoom", "12", "--max-zoom", "13", "precipitation"))

    print("\n✅ Precipitation 数据流水线完成!")
    print(f"📁 瓦片目录: {TILES_DIR}")


if __name__ == "__main__":
    main()


