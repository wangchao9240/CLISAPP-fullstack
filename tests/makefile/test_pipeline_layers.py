"""
Black-box tests for `make pipeline-<layer>` targets.

These tests validate:
- AC1: `make pipeline-pm25` runs the PM2.5 pipeline
- AC2: All layer targets run corresponding modules and print output locations
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for pipeline commands
PIPELINE_TIMEOUT = 10

# Layer configurations
LAYERS = {
    "pm25": {
        "target": "pipeline-pm25",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_pm25",
        "output_dir": "CLISApp-backend/tiles/pm25/",
    },
    "precip": {
        "target": "pipeline-precip",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_precip",
        "output_dir": "CLISApp-backend/tiles/precipitation/",
    },
    "temp": {
        "target": "pipeline-temp",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_temp",
        "output_dir": "CLISApp-backend/tiles/temperature/",
    },
    "humidity": {
        "target": "pipeline-humidity",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_humidity",
        "output_dir": "CLISApp-backend/tiles/humidity/",
    },
    "uv": {
        "target": "pipeline-uv",
        "module": "data_pipeline.pipeline_scripts.run_pipeline_uv",
        "output_dir": "CLISApp-backend/tiles/uv/",
    },
}


class TestPipelinePM25:
    """AC1: `make pipeline-pm25` runs PM2.5 pipeline module."""

    def test_pipeline_pm25_runs_in_test_mode(self):
        """AC1: `make pipeline-pm25` should run in test mode without errors."""
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

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline-pm25 should succeed in test mode\\nOutput: {result.stdout + result.stderr}"

    def test_pipeline_pm25_mentions_module(self):
        """AC1: `make pipeline-pm25` should mention the module being run."""
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

        # Should mention the module
        assert "run_pipeline_pm25" in output or "data_pipeline.pipeline_scripts.run_pipeline_pm25" in output, \
            f"Output should mention the pipeline module\\nOutput: {output}"

    def test_pipeline_pm25_prints_output_location(self):
        """AC1: `make pipeline-pm25` should print expected output location."""
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

        # Should mention the output directory
        assert "tiles/pm25" in output, \
            f"Output should mention tiles/pm25 directory\\nOutput: {output}"


class TestAllPipelineLayers:
    """AC2: All layer targets run corresponding modules and print output locations."""

    @pytest.mark.parametrize("layer_name,layer_config", LAYERS.items())
    def test_layer_target_exits_zero_in_test_mode(self, layer_name, layer_config):
        """AC2: Each pipeline target should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", layer_config["target"]],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"{layer_config['target']} should succeed in test mode\\nOutput: {result.stdout + result.stderr}"

    @pytest.mark.parametrize("layer_name,layer_config", LAYERS.items())
    def test_layer_target_mentions_module(self, layer_name, layer_config):
        """AC2: Each pipeline target should mention its module."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", layer_config["target"]],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention the module (check for key part of module name)
        module_key = f"run_pipeline_{layer_name}"
        assert module_key in output or layer_config["module"] in output, \
            f"Output should mention {module_key}\\nOutput: {output}"

    @pytest.mark.parametrize("layer_name,layer_config", LAYERS.items())
    def test_layer_target_prints_output_location(self, layer_name, layer_config):
        """AC2: Each pipeline target should print expected output location."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", layer_config["target"]],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention the output directory (exact canonical output path)
        assert layer_config["output_dir"] in output, \
            f"Output should mention {layer_config['output_dir']}\\nOutput: {output}"
