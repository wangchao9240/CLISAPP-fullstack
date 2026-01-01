#!/usr/bin/env python3
"""
Pipeline Stage Runner

Runs individual pipeline stages (download, process, tiles) for a specific layer.
Allows developers to rerun only the failing stage without rerunning the entire pipeline.

Usage:
    python scripts/pipeline_stage.py download --layer pm25
    python scripts/pipeline_stage.py process --layer precipitation
    python scripts/pipeline_stage.py tiles --layer uv
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

from pipeline_prereqs import validate_prerequisites
from pipeline_locations import LAYER_ALIASES, LAYER_OUTPUTS, normalize_layer
from pipeline_logging import BACKEND_DIR, get_log_file, tee_stdio_to_file, update_latest_symlink


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# Test mode flag
TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"

# Layer configurations
LAYER_CONFIGS = {
    "pm25": {
        "download": {
            "module": "data_pipeline.downloads.pm25.download_pm25",
            "output_dir": "data_pipeline/data/raw/pm25",
        },
        "process": {
            "module": "data_pipeline.processing.pm25.process_grib_data",
            "output_dir": "data_pipeline/data/processed/pm25",
        },
        "tiles": {
            "script": "data_pipeline/processing/common/generate_tiles.py",
            "args": ["data_pipeline/data/processed/pm25/pm25_qld_cams_processed.tif"],
            "output_dir": "tiles/pm25",
        },
    },
    "precipitation": {
        "download": {
            "script": "data_pipeline/downloads/gpm/download_gpm_imerg.py",
            "args": ["--mode", "daily"],
            "output_dir": "data_pipeline/data/raw/gpm/imerg_daily",
        },
        "process": {
            "module": "data_pipeline.processing.gpm.process_imerg_daily_to_tif",
            "output_dir": "data_pipeline/data/processed/gpm",
        },
        "tiles": {
            "script": "data_pipeline/processing/gpm/generate_precip_tiles.py",
            "args": ["6-12"],
            "output_dir": "tiles/precipitation",
        },
    },
    "uv": {
        "download": {
            "module": "data_pipeline.downloads.cams.download_cams_uv",
            "output_dir": "data_pipeline/data/raw/cams/uv",
        },
        "process": {
            "module": "data_pipeline.processing.uv.process_cams_uv_to_tif",
            "output_dir": "data_pipeline/data/processed/uv",
        },
        "tiles": {
            "script": "data_pipeline/processing/common/generate_tiles.py",
            "args": ["data_pipeline/data/processed/uv/cams_uv_qld.tif", "uv"],
            "output_dir": "tiles/uv",
        },
    },
    "temperature": {
        "download": {
            "note": "Temperature uses Open-Meteo API - download is part of process stage",
            "skip": True,
            "output_dir": "data/processing/temp",
        },
        "process": {
            "module": "data_pipeline.processing.temp.process_openmeteo_temp_to_tif",
            "output_dir": "data/processing/temp",
        },
        "tiles": {
            "module": "data_pipeline.processing.temp.generate_temperature_tiles",
            "output_dir": "tiles/temperature",
        },
    },
    "humidity": {
        "download": {
            "note": "Humidity uses Open-Meteo API - download is part of process stage",
            "skip": True,
            "output_dir": "data/processing/humidity",
        },
        "process": {
            "module": "data_pipeline.processing.humidity.process_openmeteo_humidity_to_tif",
            "output_dir": "data/processing/humidity",
        },
        "tiles": {
            "module": "data_pipeline.processing.humidity.generate_humidity_tiles",
            "output_dir": "tiles/humidity",
        },
    },
}


def print_stage_header(stage, layer):
    """Print stage start header."""
    print()
    print("=" * 70)
    print(f"PIPELINE STAGE: {stage.upper()}")
    print(f"Layer: {layer}")
    print("=" * 70)
    print()


def run_stage(stage, layer):
    """
    Run a specific pipeline stage for a layer.

    Args:
        stage: One of 'download', 'process', 'tiles'
        layer: Layer name (e.g., 'pm25', 'precipitation')

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    layer = normalize_layer(layer)

    # Get layer configuration
    if layer not in LAYER_CONFIGS:
        print(f"Error: Unknown layer '{layer}'")
        print(f"Supported layers: {', '.join(LAYER_CONFIGS.keys())}")
        if LAYER_ALIASES:
            aliases = ", ".join(f"{k}→{v}" for k, v in sorted(LAYER_ALIASES.items()))
            print(f"Aliases: {aliases}")
        return 1

    layer_config = LAYER_CONFIGS[layer]

    if stage not in layer_config:
        print(f"Error: Stage '{stage}' not defined for layer '{layer}'")
        return 1

    stage_config = layer_config[stage]

    prereq_rc = validate_prerequisites(layer, stage)
    if prereq_rc != 0:
        return prereq_rc

    # Check if this stage should be skipped
    if stage_config.get("skip", False):
        note = stage_config.get("note", f"{layer} does not have a separate {stage} stage")
        print(f"Note: {note}")
        print(f"Output: CLISApp-backend/{stage_config.get('output_dir', 'N/A')}/")
        return 0

    # Print stage information
    output_dir = stage_config.get("output_dir", "N/A")
    print(f"Stage: {stage}")
    print(f"Layer: {layer}")
    print(f"Output: CLISApp-backend/{output_dir}/")
    print()

    # In test mode, just print what would run
    if TEST_MODE:
        if "module" in stage_config:
            print(f"  Would run module: {stage_config['module']}")
        elif "script" in stage_config:
            script_path = stage_config['script']
            args = stage_config.get('args', [])
            print(f"  Would run script: {script_path}")
            if args:
                print(f"  With args: {' '.join(args)}")
        print()
        print("  [TEST MODE] Stage not executed (PIPELINE_TEST_MODE=1)")
        print()
        return 0

    # Build command
    cmd = [PYTHON_CMD]

    if "module" in stage_config:
        # Run as Python module
        cmd.extend(["-m", stage_config["module"]])
    elif "script" in stage_config:
        # Run as Python script
        cmd.append(stage_config["script"])
        cmd.extend(stage_config.get("args", []))
    else:
        print(f"Error: No module or script defined for {layer}/{stage}")
        return 1

    # Run the command
    try:
        result = subprocess.run(
            cmd,
            cwd=BACKEND_DIR,
            check=False,
        )
        return result.returncode
    except Exception as e:
        print(f"Error running {layer}/{stage}: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run individual pipeline stages for specific layers"
    )
    parser.add_argument(
        "stage",
        choices=["download", "process", "tiles"],
        help="Pipeline stage to run",
    )
    parser.add_argument(
        "--layer",
        required=True,
        choices=list(LAYER_CONFIGS.keys()) + list(LAYER_ALIASES.keys()),
        help="Climate data layer",
    )

    args = parser.parse_args()

    layer = normalize_layer(args.layer)

    log_file, latest_symlink = get_log_file(test_mode=TEST_MODE)
    update_latest_symlink(log_file, latest_symlink)
    log_label = str(log_file) if log_file is not None else "no log file (PIPELINE_TEST_MODE=1)"

    import time
    with tee_stdio_to_file(log_file):
        # Print header
        print_stage_header(args.stage, layer)
        print("Stages: download → process → tiles")
        print(f"Log file: {log_label}")
        print()
        outputs = LAYER_OUTPUTS.get(layer)
        if outputs:
            print("Output Locations:")
            print(f"  Raw data:       CLISApp-backend/{outputs['raw_dir']}/")
            print(f"  Processed data: CLISApp-backend/{outputs['processed_dir']}/")
            print(f"  Tiles:          CLISApp-backend/{outputs['tiles_dir']}/")
            print()

        print(f"== {args.stage} ==")
        print()

        start = time.monotonic()
        exit_code = run_stage(args.stage, layer)
        end = time.monotonic()

        # Print completion message + duration summary
        if TEST_MODE:
            duration_str = "skipped"
        else:
            duration_str = f"{(end - start):.2f}s"

        print()
        print("STAGE SUMMARY")
        print(f"  stage:   {args.stage}")
        print(f"  layer:   {layer}")
        print(f"  rc:      {exit_code}")
        print(f"  elapsed: {duration_str}")
        print()

        if exit_code == 0:
            print(f"✓ {args.stage.capitalize()} stage completed for {layer}")
            print()
        else:
            print(f"✗ {args.stage.capitalize()} stage failed for {layer} (exit code: {exit_code})")
            print()

        return exit_code


if __name__ == "__main__":
    sys.exit(main())
