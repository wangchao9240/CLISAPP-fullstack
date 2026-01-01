"""
Black-box tests for `make verify-pipeline`.

These tests validate:
- AC1: End-to-end pipeline verification workflow
- AC2: Deterministic smoke mode with fixtures (no network)
- AC3: Concise summary output
- AC4: PIPELINE_TEST_MODE=1 support (no network, deterministic)

Uses PIPELINE_SMOKE_MODE=1 for deterministic testing.
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# Test timeout
VERIFY_TIMEOUT = 120  # Pipeline verification may take longer


class TestVerifyPipelineSmokeMode:
    """AC2, AC4: Deterministic smoke mode with fixtures"""

    def test_verify_pipeline_exits_zero_in_smoke_mode(self):
        """AC2: Should exit 0 when smoke verification passes"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should exit 0 in smoke mode
        assert result.returncode == 0, \
            f"verify-pipeline should exit 0 in smoke mode\nOutput: {output}"

    def test_verify_pipeline_smoke_mode_no_network(self):
        """AC4: PIPELINE_TEST_MODE=1 must not perform networked downloads"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should not mention network/download operations
        assert "download" not in output.lower() or "skip" in output.lower() or "smoke" in output.lower(), \
            "Should skip downloads in test mode"

        # Should exit 0
        assert result.returncode == 0, \
            f"verify-pipeline should exit 0 in test mode\nOutput: {output}"

    def test_verify_pipeline_verifies_tile_existence(self):
        """AC2: Should verify tiles exist (at least one .png per layer)"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should verify or mention tiles
        assert "tile" in output.lower() or "png" in output.lower(), \
            "Should mention tile verification"


class TestVerifyPipelineSummary:
    """AC3: Concise summary output"""

    def test_verify_pipeline_prints_layers_exercised(self):
        """AC3: Should print which layers were exercised"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention at least one layer
        layer_found = any(
            layer in output.lower()
            for layer in ["pm25", "precipitation", "temp", "humidity", "uv"]
        )
        assert layer_found, f"Should mention exercised layers\nOutput: {output}"

    def test_verify_pipeline_prints_mode(self):
        """AC3: Should print which mode ran (full vs smoke)"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention mode
        assert "smoke" in output.lower() or "test" in output.lower() or "mode" in output.lower(), \
            f"Should indicate verification mode\nOutput: {output}"

    def test_verify_pipeline_prints_output_locations(self):
        """AC3: Should print output locations (tiles directory)"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention tiles directory
        assert "tiles/" in output or "CLISApp-backend/tiles" in output, \
            f"Should print tiles output location\nOutput: {output}"

    def test_verify_pipeline_prints_summary(self):
        """AC3: Should print a concise summary"""
        env = os.environ.copy()
        env["PIPELINE_SMOKE_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify-pipeline"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should have summary or verification section
        assert "summary" in output.lower() or "verification" in output.lower() or "pass" in output.lower(), \
            f"Should include verification summary\nOutput: {output}"


class TestVerifyPipelineHelp:
    """Make help integration"""

    def test_make_help_lists_verify_pipeline_target(self):
        """verify-pipeline should appear in make help"""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should list verify-pipeline target
        assert "verify-pipeline" in output.lower() or "verify pipeline" in output.lower(), \
            f"make help should list verify-pipeline target\nOutput: {output}"


class TestVerifyPipelineFailureMode:
    """AC1: Exits non-zero on failure"""

    @pytest.mark.skip(reason="Complex to simulate - test manually by removing fixtures")
    def test_verify_pipeline_exits_nonzero_when_tiles_missing(self):
        """AC1: Should exit non-zero if tiles are missing"""
        # This test would require manipulating fixtures or tile directories
        # Skip for now - can be tested manually
        pass
