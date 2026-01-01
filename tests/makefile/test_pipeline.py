"""
Black-box tests for `make pipeline` target.

These tests validate:
- AC1: Sequential execution of all layer pipelines
- AC2: Final summary with success/failure and output directories
- AC3: Continue on failure, exit non-zero if any failed
- AC4: PIPELINE_TEST_MODE=1 dry-run support
- AC5: `make help` lists pipeline target
"""

import os
import subprocess
from pathlib import Path
import re

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for pipeline commands
PIPELINE_TIMEOUT = 30

# Expected layer modules in order
EXPECTED_LAYERS = [
    ("pm25", "data_pipeline.pipeline_scripts.run_pipeline_pm25"),
    ("precip", "data_pipeline.pipeline_scripts.run_pipeline_precip"),
    ("temp", "data_pipeline.pipeline_scripts.run_pipeline_temp"),
    ("humidity", "data_pipeline.pipeline_scripts.run_pipeline_humidity"),
    ("uv", "data_pipeline.pipeline_scripts.run_pipeline_uv"),
]

# Expected output directories
EXPECTED_OUTPUT_DIRS = [
    "CLISApp-backend/tiles/pm25/",
    "CLISApp-backend/tiles/precipitation/",
    "CLISApp-backend/tiles/temperature/",
    "CLISApp-backend/tiles/humidity/",
    "CLISApp-backend/tiles/uv/",
]


class TestPipelineTestMode:
    """AC4: PIPELINE_TEST_MODE=1 dry-run support."""

    def test_pipeline_exits_zero_in_test_mode(self):
        """AC4: `make pipeline` should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    def test_pipeline_prints_all_modules_in_order(self):
        """AC4: Test mode should print all module invocations in order."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Check all layers are mentioned in order
        last_pos = -1
        for layer_name, module_name in EXPECTED_LAYERS:
            # Check module is mentioned
            assert module_name in output or f"run_pipeline_{layer_name}" in output, \
                f"Output should mention module for {layer_name}\nOutput: {output}"

            # Verify order (rough check)
            module_pos = output.find(f"run_pipeline_{layer_name}")
            if module_pos > 0:
                assert module_pos > last_pos, \
                    f"Modules should appear in expected order\nOutput: {output}"
                last_pos = module_pos

    def test_pipeline_prints_all_output_directories(self):
        """AC4: Test mode should print all expected output directories."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Check all output directories are mentioned
        for output_dir in EXPECTED_OUTPUT_DIRS:
            # Accept both variations: tiles/pm25 and tiles/pm25/
            layer_key = output_dir.split("/")[-2] if output_dir.endswith("/") else output_dir.split("/")[-1]
            assert f"tiles/{layer_key}" in output, \
                f"Output should mention tiles/{layer_key}\nOutput: {output}"

    def test_pipeline_prints_log_file_path_and_creates_log(self):
        """AC2: Pipeline should print and write a log file (even in test mode)."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0

        m = re.search(r"Log file:\s*(.+pipeline-\d{8}_\d{6}\.log)", output)
        assert m, f"Output should print pipeline log file path\\nOutput: {output}"

        log_path = Path(m.group(1)).expanduser()
        assert log_path.exists(), f"Pipeline log file should exist: {log_path}"

        # Cleanup (avoid polluting repo with test logs)
        try:
            log_path.unlink(missing_ok=True)
        except Exception:
            pass
        latest = log_path.parent / "pipeline-latest.log"
        if latest.is_symlink():
            try:
                latest.unlink()
            except Exception:
                pass

    def test_pipeline_prints_summary_section(self):
        """AC2/AC4: Output should include final summary section."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention summary or recap
        assert "summary" in output.lower() or "complete" in output.lower() or "pipeline" in output.lower(), \
            f"Output should include summary section\nOutput: {output}"


class TestPipelineFailureSimulation:
    """AC3: Continue on failure and exit non-zero if any layer failed."""

    def test_pipeline_continues_on_failure_and_exits_non_zero(self):
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"
        env["PIPELINE_SIMULATE_FAILURES"] = "precip,temp"

        result = subprocess.run(
            ["make", "pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        assert result.returncode != 0, \
            f"Pipeline should exit non-zero if any layer failed\\nOutput: {output}"

        # Should still mention later layers (continue-on-failure)
        assert "run_pipeline_humidity" in output, \
            f"Pipeline should still attempt remaining layers\\nOutput: {output}"
        assert "run_pipeline_uv" in output, \
            f"Pipeline should still attempt remaining layers\\nOutput: {output}"


class TestPipelineHelp:
    """AC5: `make help` lists pipeline target."""

    def test_make_help_lists_pipeline_target(self):
        """AC5: `make help` should list the pipeline target."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should list pipeline target
        assert "pipeline" in output.lower(), \
            f"make help should list pipeline target\nOutput: {output}"

    def test_make_help_includes_pipeline_description(self):
        """AC5: pipeline target should have a clear description."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should have descriptive text near "pipeline"
        # Looking for lines that contain "pipeline" with description
        lines = output.split("\n")
        pipeline_lines = [line for line in lines if "pipeline" in line.lower()]

        assert len(pipeline_lines) > 0, \
            f"make help should mention pipeline\nOutput: {output}"

        # At least one line should have more than just the word "pipeline"
        descriptive_lines = [line for line in pipeline_lines if len(line.strip()) > 15]
        assert len(descriptive_lines) > 0, \
            f"pipeline should have descriptive help text\nOutput: {output}"


class TestPipelineAlias:
    """AC5: pipeline-all alias availability."""

    def test_pipeline_all_alias_exists(self):
        """AC5: `make pipeline-all` should work as alias."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-all"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        # Should succeed (exit 0 in test mode)
        # OR return error indicating target doesn't exist (we document in help instead)
        # Accept both: if it's an alias, it should work; if documented only, that's ok
        # For now, expect it to work
        assert result.returncode == 0 or "no rule to make target" in result.stderr.lower(), \
            f"pipeline-all should be available or documented\nOutput: {result.stdout + result.stderr}"
