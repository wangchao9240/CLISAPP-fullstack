#!/usr/bin/env python3
"""
Pipeline Layer Runner Wrapper

Wraps one-click pipeline scripts with test mode support.
"""

import os
import subprocess
import sys
from pathlib import Path


# Get repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

# Layer configurations
LAYERS = {
    "pm25": {
        "module": "data_pipeline.pipeline_scripts.run_pipeline_pm25",
        "output_dir": "tiles/pm25",
    },
    "precip": {
        "module": "data_pipeline.pipeline_scripts.run_pipeline_precip",
        "output_dir": "tiles/precipitation",
    },
    "temp": {
        "module": "data_pipeline.pipeline_scripts.run_pipeline_temp",
        "output_dir": "tiles/temperature",
    },
    "humidity": {
        "module": "data_pipeline.pipeline_scripts.run_pipeline_humidity",
        "output_dir": "tiles/humidity",
    },
    "uv": {
        "module": "data_pipeline.pipeline_scripts.run_pipeline_uv",
        "output_dir": "tiles/uv",
    },
}


def main():
    """Main entry point - run pipeline for specified layer."""

    if len(sys.argv) < 2:
        print("Usage: run_pipeline_layer.py <layer>")
        print(f"  Supported layers: {', '.join(LAYERS.keys())}")
        sys.exit(1)

    layer = sys.argv[1]

    if layer not in LAYERS:
        print(f"Error: Unknown layer '{layer}'")
        print(f"Supported layers: {', '.join(LAYERS.keys())}")
        sys.exit(1)

    config = LAYERS[layer]
    module = config["module"]
    output_dir = config["output_dir"]

    # Check if running in test mode
    test_mode = os.environ.get("PIPELINE_TEST_MODE", "0") == "1"

    print()
    print(f"Pipeline: {layer.upper()}")
    print(f"Module:   {module}")
    print(f"Output:   CLISApp-backend/{output_dir}/")
    print()

    if test_mode:
        print("  [TEST MODE] Pipeline not executed (PIPELINE_TEST_MODE=1)")
        print()
        return 0

    # Run the actual pipeline module
    try:
        result = subprocess.run(
            ["python3", "-m", module],
            cwd=BACKEND_DIR,
            check=False,
        )
        return result.returncode
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
