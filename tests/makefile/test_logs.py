"""
Black-box tests for `make logs`.

These tests validate:
- AC1: `make logs` shows log locations, provides quick viewing commands, exits successfully
"""

import os
import subprocess
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for logs command
LOGS_TIMEOUT = 5


class TestLogsBasics:
    """AC1: `make logs` shows log locations and viewing commands."""

    def test_logs_exits_zero_when_no_services_running(self):
        """AC1: `make logs` should exit 0 even when no services running."""
        # Ensure services are stopped
        subprocess.run(
            ["make", "down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )

        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        # Should exit 0 even when no services running
        assert result.returncode == 0, \
            f"make logs should exit 0\nOutput: {result.stdout + result.stderr}"

    def test_logs_mentions_api_log_path(self):
        """AC1: `make logs` should mention API log path."""
        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention canonical stable log path (per story contract)
        assert "CLISApp-backend/logs/api/api.log" in output, "Should mention API stable log path"

    def test_logs_mentions_tiles_log_path(self):
        """AC1: `make logs` should mention tiles log path."""
        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention canonical stable log path (per story contract)
        assert "CLISApp-backend/logs/tiles/tiles.log" in output, "Should mention tiles stable log path"

    def test_logs_provides_tail_command_for_api(self):
        """AC1: `make logs` should provide copy/paste-ready tail command for API."""
        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should provide tail command for API
        assert "tail" in output.lower(), "Should mention tail command"
        # The command should reference API logs
        assert "tail -n 200 -f CLISApp-backend/logs/api/api.log" in output, \
            "Should provide stable API tail command"

    def test_logs_provides_tail_command_for_tiles(self):
        """AC1: `make logs` should provide copy/paste-ready tail command for tiles."""
        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should provide tail command for tiles
        assert "tail -n 200 -f CLISApp-backend/logs/tiles/tiles.log" in output, \
            "Should provide stable tiles tail command"

    def test_logs_suggests_starting_services_when_logs_missing(self):
        """AC1: `make logs` should suggest starting services when logs are missing."""
        # Ensure services are stopped
        subprocess.run(
            ["make", "down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=10,
        )

        # Clean up log files to simulate missing logs
        api_latest = REPO_ROOT / "CLISApp-backend" / "logs" / "api" / "api-latest.log"
        api_stable = REPO_ROOT / "CLISApp-backend" / "logs" / "api" / "api.log"
        tiles_latest = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles" / "tiles-latest.log"
        tiles_stable = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles" / "tiles.log"

        for path in (api_latest, api_stable, tiles_latest, tiles_stable):
            if path.exists() or path.is_symlink():
                path.unlink()

        result = subprocess.run(
            ["make", "logs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=LOGS_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should suggest make api-up
        assert "api-up" in output or "make api-up" in output, \
            "Should suggest make api-up"

        # Should suggest make tiles-up
        assert "tiles-up" in output or "make tiles-up" in output, \
            "Should suggest make tiles-up"
