"""
Black-box tests for `make status`.

These tests validate:
- AC1: `make status` checks API and tiles health, prints PASS/FAIL, provides next actions

Uses deterministic STATUS_TEST_MODE=1 (no network / no sockets) for portability.
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for status command
STATUS_TIMEOUT = 10

# Test ports (different from default to avoid conflicts)
TEST_API_PORT = 18080
TEST_TILES_PORT = 18000


def _run_status(*, api: str, tiles: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["STATUS_TEST_MODE"] = "1"
    env["STATUS_TEST_API"] = api
    env["STATUS_TEST_TILES"] = tiles
    env["API_PORT"] = str(TEST_API_PORT)
    env["TILES_PORT"] = str(TEST_TILES_PORT)

    return subprocess.run(
        ["make", "status"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=STATUS_TIMEOUT,
        env=env,
    )


class TestStatusBothHealthy:
    """AC1: `make status` shows PASS when both services healthy."""

    def test_status_shows_pass_for_both_services(self):
        """AC1: `make status` should show PASS for both API and tiles when healthy."""
        result = _run_status(api="healthy", tiles="healthy")

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Should exit 0 when both healthy
        assert result.returncode == 0, f"make status should exit 0 when healthy\nOutput: {output}"

        # Should show PASS or similar positive indicator
        assert "pass" in output_lower or "✓" in output or "healthy" in output_lower, \
            "Should show positive status"

    def test_status_prints_urls_checked(self):
        """AC1: `make status` should print the URLs it checked."""
        result = _run_status(api="healthy", tiles="healthy")
        output = result.stdout + result.stderr

        # Should print health URLs
        assert "localhost:" + str(TEST_API_PORT) in output or "/api/v1/health" in output, \
            "Should print API health URL"

        assert "localhost:" + str(TEST_TILES_PORT) in output or "/health" in output, \
            "Should print tiles health URL"


class TestStatusApiDown:
    """AC1: `make status` shows actionable guidance when API is down."""

    def test_status_shows_fail_when_api_down(self):
        """AC1: `make status` should show FAIL when API is down."""
        result = _run_status(api="down", tiles="healthy")

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Should exit non-zero when API unhealthy
        assert result.returncode != 0, \
            f"make status should exit non-zero when API down\nOutput: {output}"

        # Should show FAIL or similar negative indicator
        assert "fail" in output_lower or "✗" in output or "unhealthy" in output_lower or "down" in output_lower, \
            "Should show negative status"

    def test_status_suggests_api_up_when_api_down(self):
        """AC1: `make status` should suggest `make api-up` when API is down."""
        result = _run_status(api="down", tiles="healthy")

        output = result.stdout + result.stderr

        # Should suggest make api-up
        assert "make api-up" in output or "api-up" in output, \
            "Should suggest 'make api-up' as next action"


class TestStatusTilesDown:
    """AC1: `make status` shows actionable guidance when tiles are down."""

    def test_status_shows_fail_when_tiles_down(self):
        """AC1: `make status` should show FAIL when tiles are down."""
        result = _run_status(api="healthy", tiles="down")

        output = result.stdout + result.stderr
        output_lower = output.lower()

        # Should exit non-zero when tiles unhealthy
        assert result.returncode != 0, \
            f"make status should exit non-zero when tiles down\nOutput: {output}"

        # Should show FAIL or similar
        assert "fail" in output_lower or "✗" in output or "unhealthy" in output_lower or "down" in output_lower, \
            "Should show negative status"

    def test_status_suggests_tiles_up_and_pipeline_when_tiles_down(self):
        """AC1: `make status` should suggest `make tiles-up` and pipeline when tiles down."""
        result = _run_status(api="healthy", tiles="down")

        output = result.stdout + result.stderr

        # Should suggest make tiles-up
        assert "make tiles-up" in output or "tiles-up" in output, \
            "Should suggest 'make tiles-up' as next action"

        # Should mention pipeline for generating tiles
        assert "pipeline" in output.lower(), \
            "Should mention pipeline for tile generation"

class TestStatusTilesNoData:
    """AC1: `make status` treats tiles 'no_data' as unhealthy and suggests pipeline."""

    def test_status_fails_when_tiles_report_no_data(self):
        result = _run_status(api="healthy", tiles="no_data")
        output = (result.stdout + result.stderr).lower()

        assert result.returncode != 0, "make status should exit non-zero when tiles are no_data"
        assert "no_data" in output or "no data" in output, "Output should indicate tiles are missing"
        assert "make tiles-up" in output or "tiles-up" in output
        assert "pipeline" in output


class TestStatusBothDown:
    """AC1: `make status` handles both services down."""

    def test_status_exits_nonzero_when_both_down(self):
        """AC1: `make status` should exit non-zero when both services down."""
        result = _run_status(api="down", tiles="down")

        # Should exit non-zero
        assert result.returncode != 0, \
            "make status should exit non-zero when both services down"

    def test_status_suggests_both_actions_when_both_down(self):
        """AC1: `make status` should suggest actions for both services when both down."""
        result = _run_status(api="down", tiles="down")

        output = result.stdout + result.stderr

        # Should suggest api-up
        assert "api-up" in output, "Should suggest api-up"

        # Should suggest tiles-up
        assert "tiles-up" in output, "Should suggest tiles-up"
