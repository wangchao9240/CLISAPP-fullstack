#!/usr/bin/env python3
"""End-to-end pipeline for CAMS UV tiles."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(PACKAGE_ROOT))
    from pipeline_scripts.runner_utils import ROOT, python, run  # type: ignore
else:
    from .runner_utils import ROOT, python, run


DL_CAMS = ROOT / "data_pipeline" / "downloads" / "cams"
PROC_UV = ROOT / "data_pipeline" / "processing" / "uv"
DATA_PROCESSED = ROOT / "data_pipeline" / "data" / "processed" / "uv"
TILES_DIR = ROOT / "tiles" / "uv"


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    run(python(DL_CAMS / "download_cams_uv.py"))

    run(python(PROC_UV / "process_cams_uv_to_tif.py"))

    run(python(PROC_UV / "generate_uv_tiles.py"))

    print("\n✅ UV 数据流水线完成!")
    print(f"📁 瓦片目录: {TILES_DIR}")


if __name__ == "__main__":
    main()


