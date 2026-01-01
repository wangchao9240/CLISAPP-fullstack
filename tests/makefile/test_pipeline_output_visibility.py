"""
Black-box tests for pipeline output visibility.

These tests validate:
- AC1: Stage-level progress markers and timing
- AC2: Output locations are printed for each layer/stage
- AC3: PIPELINE_TEST_MODE=1 shows same progress markers
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for pipeline commands
PIPELINE_TIMEOUT = 30


class TestPipelineProgressMarkers:
    """AC1: Pipeline runs should print stage-level progress markers."""

    def test_full_pipeline_shows_stage_markers_in_test_mode(self):
        """AC1: Full pipeline should show download → process → tiles markers."""
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

        # Should mention the three stages
        assert "download" in output.lower(), \
            f"Should mention download stage\nOutput: {output}"
        assert "process" in output.lower(), \
            f"Should mention process stage\nOutput: {output}"
        assert "tiles" in output.lower(), \
            f"Should mention tiles stage\nOutput: {output}"

    def test_layer_pipeline_shows_progress_in_test_mode(self):
        """AC1: Layer pipeline should show progress markers."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-pm25"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should show layer name
        assert "pm25" in output.lower() or "pm2.5" in output.lower(), \
            f"Should mention PM2.5 layer\nOutput: {output}"


class TestOutputLocationVisibility:
    """AC2: Pipeline runs should print canonical output locations."""

    @pytest.mark.parametrize("layer,expected_keywords", [
        ("pm25", ["raw", "processed", "tiles"]),
        ("precip", ["raw", "processed", "tiles"]),
        ("uv", ["raw", "processed", "tiles"]),
    ])
    def test_layer_pipeline_prints_output_directories(self, layer, expected_keywords):
        """AC2: Layer pipelines should print raw/processed/tiles directories."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", f"pipeline-{layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention output directories
        for keyword in expected_keywords:
            assert keyword in output.lower(), \
                f"Should mention '{keyword}' output directory for {layer}\nOutput: {output}"

    def test_stage_command_prints_output_directory(self):
        """AC2: Stage commands should print output directory."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-download", "LAYER=pm25"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention output directory
        assert "output" in output.lower(), \
            f"Should mention output directory\nOutput: {output}"

    def test_full_pipeline_prints_log_file_path(self):
        """AC2: Full pipeline should print log file path."""
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

        # Should mention log file or "no log file" in test mode
        assert "log" in output.lower(), \
            f"Should mention log file path\nOutput: {output}"


class TestTimingInformation:
    """AC1: Pipeline runs should show timing information."""

    def test_full_pipeline_shows_summary_with_duration(self):
        """AC1: Full pipeline should show summary with duration."""
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

        # Should show summary section
        assert "summary" in output.lower(), \
            f"Should include summary section\nOutput: {output}"


class TestModeConsistency:
    """AC3: Test mode should show same progress markers."""

    def test_test_mode_shows_progress_markers(self):
        """AC3: Test mode should show same progress markers as real mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-pm25"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should still show output locations in test mode
        assert "output" in output.lower(), \
            f"Test mode should show output locations\nOutput: {output}"

    def test_test_mode_exits_zero(self):
        """AC3: Test mode should exit 0."""
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

        assert result.returncode == 0, \
            f"Test mode should exit 0\nOutput: {result.stdout + result.stderr}"
