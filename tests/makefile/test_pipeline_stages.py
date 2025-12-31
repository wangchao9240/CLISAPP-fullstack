"""
Black-box tests for stage-level pipeline targets.

These tests validate:
- AC1: `make pipeline-download LAYER=<layer>` runs download stage only
- AC2: `make pipeline-process LAYER=<layer>` runs process stage only
- AC3: `make pipeline-tiles LAYER=<layer>` runs tiles stage only
- AC4: PIPELINE_TEST_MODE=1 dry-run support
- AC5: Missing/invalid LAYER fails fast with clear error
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for stage commands
STAGE_TIMEOUT = 30

# Supported layers
SUPPORTED_LAYERS = ["pm25", "precipitation", "uv", "temperature", "humidity"]


class TestPipelineDownload:
    """AC1 + AC4: Download stage execution."""

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_download_exits_zero_in_test_mode(self, layer):
        """AC1/AC4: Download stage should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-download", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline-download LAYER={layer} should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_download_mentions_layer(self, layer):
        """AC1/AC4: Download stage should mention the layer being processed."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-download", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention the layer
        assert layer in output.lower() or layer.replace("precipitation", "precip") in output.lower(), \
            f"Output should mention layer {layer}\nOutput: {output}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_download_prints_output_directory(self, layer):
        """AC1: Download stage should print expected output directory."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-download", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention output directory (raw data location)
        assert "data/raw" in output or "raw" in output.lower() or "download" in output.lower(), \
            f"Output should mention download/raw output directory\nOutput: {output}"


class TestPipelineProcess:
    """AC2 + AC4: Process stage execution."""

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_process_exits_zero_in_test_mode(self, layer):
        """AC2/AC4: Process stage should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-process", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline-process LAYER={layer} should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_process_mentions_layer(self, layer):
        """AC2/AC4: Process stage should mention the layer being processed."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-process", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention the layer
        assert layer in output.lower() or layer.replace("precipitation", "precip") in output.lower(), \
            f"Output should mention layer {layer}\nOutput: {output}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_process_prints_output_directory(self, layer):
        """AC2: Process stage should print expected output directory."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-process", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention output directory (processed data location)
        assert "processed" in output.lower() or "processing" in output.lower(), \
            f"Output should mention processed output directory\nOutput: {output}"


class TestPipelineTiles:
    """AC3 + AC4: Tiles stage execution."""

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_tiles_exits_zero_in_test_mode(self, layer):
        """AC3/AC4: Tiles stage should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-tiles", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline-tiles LAYER={layer} should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_tiles_mentions_layer(self, layer):
        """AC3/AC4: Tiles stage should mention the layer being processed."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-tiles", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention the layer
        assert layer in output.lower() or layer.replace("precipitation", "precip") in output.lower(), \
            f"Output should mention layer {layer}\nOutput: {output}"

    @pytest.mark.parametrize("layer", SUPPORTED_LAYERS)
    def test_pipeline_tiles_prints_output_directory(self, layer):
        """AC3: Tiles stage should print tiles output directory."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-tiles", f"LAYER={layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention tiles output directory
        assert "tiles" in output.lower() and layer in output.lower() or \
               ("tiles" in output.lower() and layer.replace("precipitation", "precip") in output.lower()), \
            f"Output should mention tiles/{layer} output directory\nOutput: {output}"


class TestMissingOrInvalidLayer:
    """AC5: Missing or invalid LAYER parameter fails fast."""

    def test_pipeline_download_without_layer_fails(self):
        """AC5: pipeline-download without LAYER should fail fast."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-download"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should fail (non-zero exit code)
        assert result.returncode != 0, \
            "pipeline-download without LAYER should fail"

        output = result.stdout + result.stderr

        # Should mention supported layers
        assert "layer" in output.lower() or "supported" in output.lower(), \
            f"Error message should mention layer requirement\nOutput: {output}"

    def test_pipeline_process_with_invalid_layer_fails(self):
        """AC5: pipeline-process with invalid LAYER should fail fast."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-process", "LAYER=invalid_layer_name"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should fail (non-zero exit code)
        assert result.returncode != 0, \
            "pipeline-process with invalid LAYER should fail"

        output = result.stdout + result.stderr

        # Should list supported layers
        for supported in ["pm25", "precipitation", "humidity"]:
            # At least some supported layers should be mentioned
            if supported in output.lower():
                break
        else:
            pytest.fail(f"Error message should list supported layers\nOutput: {output}")

    def test_pipeline_tiles_without_layer_fails(self):
        """AC5: pipeline-tiles without LAYER should fail fast."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "pipeline-tiles"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT,
            env=env,
        )

        # Should fail (non-zero exit code)
        assert result.returncode != 0, \
            "pipeline-tiles without LAYER should fail"

        output = result.stdout + result.stderr

        # Should mention layer requirement
        assert "layer" in output.lower() or "required" in output.lower(), \
            f"Error message should mention layer requirement\nOutput: {output}"
