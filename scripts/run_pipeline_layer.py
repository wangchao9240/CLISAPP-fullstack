#!/usr/bin/env python3
"""
Pipeline Layer Runner Wrapper

Wraps one-click pipeline scripts with test mode support.
"""

import os
import subprocess
import sys
from pathlib import Path

from pipeline_prereqs import validate_prerequisites
from pipeline_locations import LAYER_OUTPUTS, LAYER_ALIASES, normalize_layer, supported_layers
from pipeline_logging import BACKEND_DIR, get_log_file, tee_stdio_to_file, update_latest_symlink


LAYER_MODULES: dict[str, str] = {
    "pm25": "data_pipeline.pipeline_scripts.run_pipeline_pm25",
    "precipitation": "data_pipeline.pipeline_scripts.run_pipeline_precip",
    "temperature": "data_pipeline.pipeline_scripts.run_pipeline_temp",
    "humidity": "data_pipeline.pipeline_scripts.run_pipeline_humidity",
    "uv": "data_pipeline.pipeline_scripts.run_pipeline_uv",
}


def _guess_stage(command_line: str) -> str | None:
    lower = command_line.lower()
    if "downloads" in lower or "download_" in lower or "download" in lower:
        return "download"
    if "generate_" in lower or "generate_tiles" in lower or "upsample" in lower:
        return "tiles"
    if "process_" in lower or "processing" in lower or "process" in lower:
        return "process"
    return None


def main():
    """Main entry point - run pipeline for specified layer."""

    if len(sys.argv) < 2:
        print("Usage: run_pipeline_layer.py <layer>")
        print(f"  Supported layers: {', '.join(supported_layers())}")
        sys.exit(1)

    raw_layer = sys.argv[1]
    layer = normalize_layer(raw_layer)

    if layer not in LAYER_MODULES:
        print(f"Error: Unknown layer '{raw_layer}'")
        print(f"Supported layers: {', '.join(supported_layers())}")
        if LAYER_ALIASES:
            aliases = ", ".join(f"{k}→{v}" for k, v in sorted(LAYER_ALIASES.items()))
            print(f"Aliases: {aliases}")
        sys.exit(1)

    module = LAYER_MODULES[layer]
    raw_dir = LAYER_OUTPUTS[layer]["raw_dir"]
    processed_dir = LAYER_OUTPUTS[layer]["processed_dir"]
    tiles_dir = LAYER_OUTPUTS[layer]["tiles_dir"]

    prereq_rc = validate_prerequisites(layer, "full")
    if prereq_rc != 0:
        return prereq_rc

    # Check if running in test mode
    test_mode = os.environ.get("PIPELINE_TEST_MODE", "0") == "1"

    log_file, latest_symlink = get_log_file(test_mode=test_mode)
    update_latest_symlink(log_file, latest_symlink)
    log_label = str(log_file) if log_file is not None else "no log file (PIPELINE_TEST_MODE=1)"

    import time
    with tee_stdio_to_file(log_file):
        print()
        print("=" * 70)
        print(f"PIPELINE: {layer.upper()}")
        print("=" * 70)
        print()
        print("Stages: download → process → tiles")
        print(f"Module:   {module}")
        print(f"Log file: {log_label}")
        print()
        print("Output Locations:")
        print(f"  Raw data:       CLISApp-backend/{raw_dir}/")
        print(f"  Processed data: CLISApp-backend/{processed_dir}/")
        print(f"  Tiles:          CLISApp-backend/{tiles_dir}/")
        print()

        stage_durations = {"download": 0.0, "process": 0.0, "tiles": 0.0}
        overall_start = time.monotonic()

        if test_mode:
            print()
            for stage in ("download", "process", "tiles"):
                print(f"== {stage} ==")
                print("  [TEST MODE] skipped")
                print()
            print("PIPELINE SUMMARY")
            print(f"  download: skipped")
            print(f"  process:  skipped")
            print(f"  tiles:    skipped")
            print(f"  total:    skipped")
            print()
            return 0

        # Run the actual pipeline module and derive per-stage timings from runner output ("➤ ...")
        try:
            proc = subprocess.Popen(
                ["python3", "-m", module],
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

            total = end - overall_start
            print()
            print("PIPELINE SUMMARY")
            for stage in ("download", "process", "tiles"):
                print(f"  {stage:8} {stage_durations[stage]:6.2f}s")
            print(f"  total     {total:6.2f}s")
            print()
            return rc
        except Exception as e:
            print(f"Error running pipeline: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
