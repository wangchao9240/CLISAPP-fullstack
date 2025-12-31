#!/usr/bin/env python3
"""
Pipeline Orchestrator Script

Runs all climate data layer pipelines sequentially:
- PM2.5
- Precipitation
- Temperature
- Humidity
- UV

Produces a final summary of success/failure and writes logs to a predictable location.
Supports PIPELINE_TEST_MODE=1 for deterministic testing (dry-run).
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).parent.parent.absolute()
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

# Log directory
LOG_DIR = BACKEND_DIR / "logs" / "pipeline"

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# Test mode flag
TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"

# Layer configurations in execution order
LAYERS = [
    {
        "name": "PM2.5",
        "key": "pm25",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_pm25",
        "output_dir": "tiles/pm25",
    },
    {
        "name": "Precipitation",
        "key": "precip",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_precip",
        "output_dir": "tiles/precipitation",
    },
    {
        "name": "Temperature",
        "key": "temp",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_temp",
        "output_dir": "tiles/temperature",
    },
    {
        "name": "Humidity",
        "key": "humidity",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_humidity",
        "output_dir": "tiles/humidity",
    },
    {
        "name": "UV",
        "key": "uv",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_uv",
        "output_dir": "tiles/uv",
    },
]


def ensure_log_dir():
    """Ensure log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file():
    """Get log file path with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"pipeline-{timestamp}.log"
    latest_symlink = LOG_DIR / "pipeline-latest.log"
    return log_file, latest_symlink


def create_log_symlink(log_file, symlink_path):
    """Create or update symlink to latest log file."""
    try:
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(log_file.name)
    except Exception:
        # Best effort - don't fail if symlink creation fails
        pass


def print_header():
    """Print pipeline start header."""
    print()
    print("=" * 70)
    print("CLISAPP PIPELINE - FULL LAYER RUN")
    print("=" * 70)
    print()


def print_layer_start(layer):
    """Print layer start marker."""
    print()
    print("-" * 70)
    print(f"LAYER: {layer['name']}")
    print(f"Module: {layer['module']}")
    print(f"Output: CLISApp-backend/{layer['output_dir']}/")
    print("-" * 70)
    print()


def print_summary(results, log_file):
    """Print final summary of pipeline execution."""
    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print()

    # Count successes and failures
    succeeded = [r for r in results if r["exit_code"] == 0]
    failed = [r for r in results if r["exit_code"] != 0]

    print(f"Total layers: {len(results)}")
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed: {len(failed)}")
    print()

    # Print details
    print("Layer Results:")
    for result in results:
        status = "✓ SUCCESS" if result["exit_code"] == 0 else "✗ FAILED"
        print(f"  {status:12} {result['name']:15} → CLISApp-backend/{result['output_dir']}/")

    print()
    print(f"Log file: {log_file}")
    print()
    print("=" * 70)
    print()


def run_layer(layer):
    """
    Run a single layer pipeline.

    Returns exit code (0 for success, non-zero for failure).
    """
    if TEST_MODE:
        # In test mode, just print what would run
        return 0

    # Run the pipeline module
    try:
        result = subprocess.run(
            [PYTHON_CMD, "-m", layer["module"]],
            cwd=BACKEND_DIR,
            check=False,
        )
        return result.returncode
    except Exception as e:
        print(f"Error running layer {layer['name']}: {e}")
        return 1


def main():
    """Main pipeline orchestrator."""

    if TEST_MODE:
        print()
        print("=" * 70)
        print("PIPELINE TEST MODE (PIPELINE_TEST_MODE=1)")
        print("=" * 70)
        print()
        print("The following layers would be executed:")
        print()

        for layer in LAYERS:
            print(f"  Layer: {layer['name']}")
            print(f"    Module: {layer['module']}")
            print(f"    Output: CLISApp-backend/{layer['output_dir']}/")
            print()

        print("=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        print()
        print("Test mode - no data processed")
        print("All layers would execute sequentially")
        print()
        return 0

    # Real execution
    ensure_log_dir()
    log_file, latest_symlink = get_log_file()

    print_header()
    print(f"Log file: {log_file}")
    print()

    # Track results
    results = []

    # Run each layer sequentially
    for layer in LAYERS:
        print_layer_start(layer)
        exit_code = run_layer(layer)

        results.append({
            "name": layer["name"],
            "key": layer["key"],
            "module": layer["module"],
            "output_dir": layer["output_dir"],
            "exit_code": exit_code,
        })

        if exit_code == 0:
            print(f"\n✓ {layer['name']} completed successfully\n")
        else:
            print(f"\n✗ {layer['name']} failed with exit code {exit_code}\n")

    # Create symlink to latest log
    create_log_symlink(log_file, latest_symlink)

    # Print final summary
    print_summary(results, log_file)

    # Exit non-zero if any layer failed
    failed_count = sum(1 for r in results if r["exit_code"] != 0)
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
