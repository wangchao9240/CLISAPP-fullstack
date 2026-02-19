#!/usr/bin/env python3
"""Run UV pipeline via unified Open-Meteo processor."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    sys.path.append(str(PACKAGE_ROOT))
    from pipeline_scripts.runner_utils import ROOT, run  # type: ignore
else:
    from .runner_utils import ROOT, run


TILES_DIR = ROOT / "tiles" / "uv"


def main() -> None:
    run([sys.executable, "-m", "data_pipeline.processing.openmeteo.process_all_layers"])

    print("\n✅ UV pipeline completed (Open-Meteo)")
    print(f"📁 Tiles directory: {TILES_DIR}")


if __name__ == "__main__":
    main()
