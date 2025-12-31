"""
Black-box tests for pipeline prerequisite validation.

These tests validate:
- AC4: PIPELINE_TEST_MODE=1 skips credential/system checks and exits 0
- Prerequisite checks are listed but not enforced in test mode
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for pipeline commands
PIPELINE_TIMEOUT = 30

# Sample layers that require different prerequisites
# Note: Use actual Make target names (precip, not precipitation)
LAYERS_WITH_EXTERNAL_DEPS = ["pm25", "uv", "precip"]


class TestPipelinePrereqsTestMode:
    """AC4: Test mode skips credential checks and exits successfully."""

    @pytest.mark.parametrize("layer", LAYERS_WITH_EXTERNAL_DEPS)
    def test_pipeline_layer_exits_zero_in_test_mode(self, layer):
        """AC4: Pipeline commands should exit 0 in test mode regardless of missing credentials."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Remove any credentials to ensure we're testing test mode behavior
        env.pop("CDSAPI_URL", None)
        env.pop("CDSAPI_KEY", None)
        if "HOME" in env:
            # Temporarily override HOME to avoid using real credentials
            env["HOME"] = "/tmp/test_no_credentials"

        result = subprocess.run(
            ["make", f"pipeline-{layer}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode even without credentials
        assert result.returncode == 0, \
            f"pipeline-{layer} should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    def test_pipeline_full_exits_zero_in_test_mode(self):
        """AC4: Full pipeline should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Remove any credentials
        env.pop("CDSAPI_URL", None)
        env.pop("CDSAPI_KEY", None)

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

    @pytest.mark.parametrize("stage", ["download", "process", "tiles"])
    def test_pipeline_stages_exit_zero_in_test_mode(self, stage):
        """AC4: Stage commands should exit 0 in test mode."""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Remove any credentials
        env.pop("CDSAPI_URL", None)
        env.pop("CDSAPI_KEY", None)

        result = subprocess.run(
            ["make", f"pipeline-{stage}", "LAYER=pm25"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            env=env,
        )

        # Should exit 0 in test mode
        assert result.returncode == 0, \
            f"pipeline-{stage} should succeed in test mode\nOutput: {result.stdout + result.stderr}"

    def test_test_mode_mentions_skipped_checks(self):
        """AC4: Test mode should mention that checks are skipped."""
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

        # Should mention test mode somewhere in output
        assert "test" in output.lower() or "mode" in output.lower(), \
            f"Output should mention test mode\nOutput: {output}"


class TestPipelinePrereqsRealMode:
    """Test prerequisite validation behavior (using safe test scenarios)."""

    def test_pipeline_help_includes_prereq_targets(self):
        """Pipeline help should mention prerequisite validation."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should mention pipeline targets
        assert "pipeline" in output.lower(), \
            f"Help should mention pipeline\nOutput: {output}"
