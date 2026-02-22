#!/usr/bin/env python3
"""
Pipeline Orchestrator Script

Runs the Open-Meteo climate pipeline once for all layers:
- PM2.5
- Precipitation
- Temperature
- Humidity
- UV

Produces a final summary of success/failure and writes logs to a predictable location.
Supports PIPELINE_TEST_MODE=1 for deterministic testing (dry-run).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from pipeline_logging import get_log_file, tee_stdio_to_file, update_latest_symlink


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# Test mode flag
TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"

# Optional failure simulation (for deterministic testing)
SIMULATED_FAILURES = {
    key.strip().lower()
    for key in os.environ.get("PIPELINE_SIMULATE_FAILURES", "").split(",")
    if key.strip()
}

# Layers to verify after a single process_all_layers run
LAYER_KEYS = ["pm25", "precipitation", "temperature", "humidity", "uv"]


def print_header():
    """Print pipeline start header."""
    print()
    print("=" * 70)
    print("CLISAPP PIPELINE - FULL LAYER RUN")
    print("=" * 70)
    print()


def _run_process_all_layers():
    """Run process_all_layers once and stream output."""
    cmd = [PYTHON_CMD, "-m", "data_pipeline.processing.openmeteo.process_all_layers"]
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    exit_code = proc.wait()
    elapsed = time.monotonic() - start
    return exit_code, elapsed


def _verify_layer_tiles():
    """Check whether each layer has generated tiles metadata."""
    verification = {}
    for layer_key in LAYER_KEYS:
        meta_path = BACKEND_DIR / "tiles" / layer_key / "metadata.json"
        verification[layer_key] = meta_path.exists()
    return verification


def print_summary(run_exit_code, elapsed, verification, log_file):
    """Print final summary of pipeline execution."""
    overall_success = run_exit_code == 0 and all(verification.values())

    print()
    print("=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print()
    print("Overall run:")
    print(f"  {'✓ SUCCESS' if overall_success else '✗ FAILED'}")
    print(f"  Exit code: {run_exit_code}")
    print(f"  Total elapsed: {elapsed:.2f}s")
    print()
    print("Per-layer tile verification (metadata.json):")
    for layer_key in LAYER_KEYS:
        mark = "✓" if verification.get(layer_key, False) else "✗"
        print(f"  {mark} {layer_key}")
    print()
    print(f"Log file: {log_file}")
    print()
    print("=" * 70)
    print()


def main():
    """Main pipeline orchestrator."""
    log_file, latest_symlink = get_log_file(test_mode=False)
    update_latest_symlink(log_file, latest_symlink)
    log_label = str(log_file) if log_file is not None else "no log file (PIPELINE_TEST_MODE=1)"

    with tee_stdio_to_file(log_file):
        print_header()
        if TEST_MODE:
            print("PIPELINE TEST MODE (PIPELINE_TEST_MODE=1)")
            if SIMULATED_FAILURES:
                print(f"Simulated failures: {', '.join(sorted(SIMULATED_FAILURES))}")
            print()
        print(f"Log file: {log_label}")
        print()

        if TEST_MODE:
            print("== process_all_layers ==")
            print("  [TEST MODE] skipped")
            print()
            verification = {layer_key: True for layer_key in LAYER_KEYS}
            for layer_key in LAYER_KEYS:
                if layer_key in SIMULATED_FAILURES:
                    verification[layer_key] = False
            run_exit_code = 0
            elapsed = 0.0
        else:
            run_exit_code, elapsed = _run_process_all_layers()
            verification = _verify_layer_tiles()

        print_summary(run_exit_code, elapsed, verification, log_label)
        return 0 if run_exit_code == 0 and all(verification.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
