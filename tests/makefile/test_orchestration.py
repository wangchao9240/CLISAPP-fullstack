"""
Black-box tests for `make up` and `make down` orchestration.

These tests validate:
- AC1: `make up` starts both services and prints verification URLs + platform note
- AC2: `make dev-up` alias behaves the same as `make up`
- AC3: `make down` stops both services and succeeds even if already stopped

Uses test mode (via API_TEST_MODE=1 and TILES_TEST_MODE=1) to start dummy processes
instead of real services for deterministic testing.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for orchestration commands (longer than individual services)
ORCHESTRATION_TIMEOUT = 15


def build_orchestration_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["API_TEST_MODE"] = "1"
    env["TILES_TEST_MODE"] = "1"
    env["API_STATE_DIR"] = str(tmp_path / "api_state")
    env["API_LOG_DIR"] = str(tmp_path / "api_logs")
    env["TILES_STATE_DIR"] = str(tmp_path / "tiles_state")
    env["TILES_LOG_DIR"] = str(tmp_path / "tiles_logs")
    return env


def run_make(target: str, env: dict[str, str], timeout: int = ORCHESTRATION_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


class TestUpBasics:
    """AC1: `make up` starts both services and prints verification URLs."""

    def test_up_starts_both_services(self, tmp_path: Path):
        """AC1: `make up` starts both API and tile server."""
        # Clean up first
        env = build_orchestration_env(tmp_path)
        run_make("down", env)

        result = run_make("up", env)

        output = result.stdout + result.stderr

        # Should start successfully
        assert result.returncode == 0, f"make up should succeed\nOutput: {output}"

        # Should print API health URL
        assert "http://localhost:8080/api/v1/health" in output, \
            "Should print API health URL"

        # Should print tiles health URL
        assert "http://localhost:8000/health" in output, \
            "Should print tiles health URL"

        # Should print platform connectivity note
        assert "10.0.2.2" in output, \
            "Should mention Android emulator IP (10.0.2.2)"

        # Clean up
        run_make("down", env)

    def test_up_creates_pid_files_for_both_services(self, tmp_path: Path):
        """AC1: `make up` should create PID files for both services."""
        env = build_orchestration_env(tmp_path)
        run_make("down", env)

        # Start services
        result = run_make("up", env)
        assert result.returncode == 0

        # Check PID files exist
        api_pid_file = Path(env["API_STATE_DIR"]) / "api.pid"
        tiles_pid_file = Path(env["TILES_STATE_DIR"]) / "tiles.pid"

        assert api_pid_file.exists(), "API PID file should exist after up"
        assert tiles_pid_file.exists(), "Tiles PID file should exist after up"

        # Clean up
        run_make("down", env)


class TestDevUpAlias:
    """AC2: `make dev-up` alias behaves the same as `make up`."""

    def test_dev_up_alias_behaves_like_up(self, tmp_path: Path):
        """AC2: `make dev-up` should behave identically to `make up`."""
        env = build_orchestration_env(tmp_path)
        run_make("down", env)

        # Run dev-up
        result = run_make("dev-up", env)

        output = result.stdout + result.stderr

        # Should succeed
        assert result.returncode == 0, f"make dev-up should succeed\nOutput: {output}"

        # Should print both health URLs
        assert "http://localhost:8080/api/v1/health" in output
        assert "http://localhost:8000/health" in output

        # Should print platform note
        assert "10.0.2.2" in output

        # Clean up
        run_make("down", env)

    def test_dev_up_exit_code_matches_up(self, tmp_path: Path):
        """AC2: `make dev-up` should have same exit code behavior as `make up`."""
        env = build_orchestration_env(tmp_path)
        run_make("down", env)

        # Run both commands
        result_up = run_make("up", env)
        result_dev_up = run_make("dev-up", env)

        # Both should succeed (services already running is OK)
        assert result_up.returncode == 0
        assert result_dev_up.returncode == 0

        # Clean up
        run_make("down", env)


class TestDown:
    """AC3: `make down` stops both services predictably."""

    def test_down_stops_both_services(self, tmp_path: Path):
        """AC3: `make down` should stop both API and tile server."""
        # Start services first
        env = build_orchestration_env(tmp_path)
        run_make("up", env)

        # Get PIDs
        api_pid_file = Path(env["API_STATE_DIR"]) / "api.pid"
        tiles_pid_file = Path(env["TILES_STATE_DIR"]) / "tiles.pid"

        assert api_pid_file.exists(), "API should be running"
        assert tiles_pid_file.exists(), "Tiles should be running"

        api_pid = int(api_pid_file.read_text().strip())
        tiles_pid = int(tiles_pid_file.read_text().strip())

        # Stop services
        result = run_make("down", env)

        assert result.returncode == 0, "make down should succeed"

        # Processes should be terminated
        time.sleep(1)
        try:
            os.kill(api_pid, 0)
            pytest.fail(f"API process {api_pid} should be terminated")
        except ProcessLookupError:
            pass  # Expected

        try:
            os.kill(tiles_pid, 0)
            pytest.fail(f"Tiles process {tiles_pid} should be terminated")
        except ProcessLookupError:
            pass  # Expected

    def test_down_when_nothing_running_exits_successfully(self, tmp_path: Path):
        """AC3: `make down` should exit successfully even if nothing is running."""
        env = build_orchestration_env(tmp_path)
        run_make("down", env)

        # Run down again
        result = run_make("down", env)

        # Should succeed (idempotent)
        assert result.returncode == 0, "make down should succeed when nothing running"

    def test_down_succeeds_if_only_one_service_running(self, tmp_path: Path):
        """AC3: `make down` should succeed even if only one service is running."""
        env = build_orchestration_env(tmp_path)
        env.pop("TILES_TEST_MODE", None)
        run_make("down", env)

        # Start only API (not tiles)
        run_make("api-up", env)

        # Stop both (should succeed even though tiles wasn't running)
        result = run_make("down", env)

        assert result.returncode == 0, "make down should succeed with partial services"
