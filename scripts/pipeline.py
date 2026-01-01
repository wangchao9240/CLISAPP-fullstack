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

from pipeline_prereqs import validate_prerequisites
from pipeline_locations import LAYER_OUTPUTS, normalize_layer
from pipeline_logging import get_log_file, tee_stdio_to_file, update_latest_symlink


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# Test mode flag
TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"

# Optional failure simulation (for deterministic testing of AC3)
SIMULATED_FAILURES = {
    key.strip()
    for key in os.environ.get("PIPELINE_SIMULATE_FAILURES", "").split(",")
    if key.strip()
}

# Layer configurations in execution order
LAYERS = [
    {
        "name": "PM2.5",
        "key": "pm25",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_pm25",
    },
    {
        "name": "Precipitation",
        "key": "precipitation",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_precip",
    },
    {
        "name": "Temperature",
        "key": "temperature",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_temp",
    },
    {
        "name": "Humidity",
        "key": "humidity",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_humidity",
    },
    {
        "name": "UV",
        "key": "uv",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_uv",
    },
]

for layer in LAYERS:
    outputs = LAYER_OUTPUTS[layer["key"]]
    layer["raw_dir"] = outputs["raw_dir"]
    layer["processed_dir"] = outputs["processed_dir"]
    layer["tiles_dir"] = outputs["tiles_dir"]


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
    print(f"Stages: download → process → tiles")
    print()
    print("Output Locations:")
    print(f"  Raw data:       CLISApp-backend/{layer['raw_dir']}/")
    print(f"  Processed data: CLISApp-backend/{layer['processed_dir']}/")
    print(f"  Tiles:          CLISApp-backend/{layer['tiles_dir']}/")
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
    print("Layer Results (durations):")
    for result in results:
        status = "✓ SUCCESS" if result["exit_code"] == 0 else "✗ FAILED"
        if result.get("durations_skipped"):
            timing = "download=skipped process=skipped tiles=skipped total=skipped"
        else:
            d = result.get("stage_durations", {})
            timing = (
                f"download={d.get('download', 0.0):.2f}s "
                f"process={d.get('process', 0.0):.2f}s "
                f"tiles={d.get('tiles', 0.0):.2f}s "
                f"total={result.get('elapsed', 0.0):.2f}s"
            )
        print(f"  {status:12} {result['name']:15} → {timing}")

    print()
    print(f"Log file: {log_file}")
    print()
    print("=" * 70)
    print()

def _guess_stage(command_line: str) -> str | None:
    lower = command_line.lower()
    if "downloads" in lower or "download_" in lower or "download" in lower:
        return "download"
    if "generate_" in lower or "generate_tiles" in lower or "upsample" in lower:
        return "tiles"
    if "process_" in lower or "processing" in lower or "process" in lower:
        return "process"
    return None


def run_layer(layer):
    """
    Run a single layer pipeline.

    Returns (exit_code, stage_durations, elapsed, durations_skipped).
    """
    import time

    stage_durations = {"download": 0.0, "process": 0.0, "tiles": 0.0}
    elapsed = 0.0

    if TEST_MODE:
        print()
        for stage in ("download", "process", "tiles"):
            print(f"== {stage} ==")
            print("  [TEST MODE] skipped")
            print()

        sim = {normalize_layer(k) for k in SIMULATED_FAILURES}
        if layer["key"] in sim:
            print(f"  [TEST MODE] SIMULATED FAIL for {layer['key']}")
            return 1, stage_durations, elapsed, True
        return 0, stage_durations, elapsed, True

    # Run the pipeline module
    try:
        start = time.monotonic()
        proc = subprocess.Popen(
            [PYTHON_CMD, "-m", layer["module"]],
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        current_stage: str | None = None
        stage_start: float | None = None
        for line in proc.stdout:
            if line.startswith("➤"):
                now = time.monotonic()
                if current_stage and stage_start is not None:
                    stage_durations[current_stage] += now - stage_start
                next_stage = _guess_stage(line)
                if next_stage and next_stage != current_stage:
                    print()
                    print(f"== {next_stage} ==")
                    print()
                    current_stage = next_stage
                stage_start = now
            print(line, end="")
        rc = proc.wait()
        end = time.monotonic()
        if current_stage and stage_start is not None:
            stage_durations[current_stage] += end - stage_start
        elapsed = end - start
        return rc, stage_durations, elapsed, False
    except Exception as e:
        print(f"Error running layer {layer['name']}: {e}")
        return 1, stage_durations, elapsed, False


def main():
    """Main pipeline orchestrator."""

    # Always create a log file, even in test mode, for reproducible verification.
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

        results = []

        for layer in LAYERS:
            print_layer_start(layer)
            prereq_rc = validate_prerequisites(layer["key"], "full")
            if prereq_rc != 0:
                exit_code, stage_durations, elapsed, durations_skipped = prereq_rc, {"download": 0.0, "process": 0.0, "tiles": 0.0}, 0.0, True
            else:
                exit_code, stage_durations, elapsed, durations_skipped = run_layer(layer)

            results.append({
                "name": layer["name"],
                "key": layer["key"],
                "module": layer["module"],
                "raw_dir": layer["raw_dir"],
                "processed_dir": layer["processed_dir"],
                "tiles_dir": layer["tiles_dir"],
                "exit_code": exit_code,
                "stage_durations": stage_durations,
                "elapsed": elapsed,
                "durations_skipped": durations_skipped,
            })

            if exit_code == 0:
                print(f"\n✓ {layer['name']} completed successfully\n")
            else:
                print(f"\n✗ {layer['name']} failed with exit code {exit_code}\n")

        print_summary(results, log_label)

        failed_count = sum(1 for r in results if r["exit_code"] != 0)
        return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
