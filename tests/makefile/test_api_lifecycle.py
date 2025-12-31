"""
Black-box tests for `make api-up`, `make api-down`, and `make api` targets.

Tests verify:
- AC1: `make api-up` starts API on :8080, prints health URL and docs URL, writes logs to CLISApp-backend/logs/api/
- AC2: Running `make api-up` twice should not start duplicates, should report already running
- AC3: `make api-down` stops the service, exits successfully if already stopped
- AC4: `make api` alias behaves same as `make api-up`

Per Story 1.3, these tests run in test mode using a dummy process instead of actual uvicorn.
"""
import subprocess
import time
import os
from pathlib import Path

import pytest


# Repository root is 2 levels up from this test file
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Timeout for api lifecycle operations (seconds)
API_TIMEOUT = 10


def build_api_test_env(tmp_path: Path) -> dict[str, str]:
    state_dir = tmp_path / "api_state"
    log_dir = REPO_ROOT / "CLISApp-backend" / "logs" / "api"
    env = os.environ.copy()
    env["API_TEST_MODE"] = "1"
    env["API_STATE_DIR"] = str(state_dir)
    env["API_LOG_DIR"] = str(log_dir)
    return env


@pytest.fixture
def api_test_env(tmp_path: Path) -> dict[str, str]:
    return build_api_test_env(tmp_path)


def run_make(target: str, env: dict[str, str], timeout: int = API_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["make", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


class TestApiUpBasics:
    """Basic tests for `make api-up` target (AC1)."""

    def test_api_up_starts_and_prints_urls(self, api_test_env):
        """AC1: `make api-up` starts API and prints health URL and docs URL."""
        # Clean up any existing test process
        run_make("api-down", api_test_env)

        result = run_make("api-up", api_test_env)

        output = result.stdout + result.stderr
        assert result.returncode == 0, f"api-up should succeed, output: {output}"

        # Should print health URL
        assert "http://localhost:8080/api/v1/health" in output, \
            "api-up should print health URL"

        # Should print docs URL
        assert "http://localhost:8080/docs" in output, \
            "api-up should print docs URL"

        # Clean up
        run_make("api-down", api_test_env)

    def test_api_up_creates_log_file(self, api_test_env):
        """AC1: `make api-up` writes logs to CLISApp-backend/logs/api/."""
        # Clean up any existing test process
        run_make("api-down", api_test_env)

        result = run_make("api-up", api_test_env)

        assert result.returncode == 0

        # Check log directory exists
        log_dir = REPO_ROOT / "CLISApp-backend" / "logs" / "api"
        assert log_dir.exists(), "Log directory should be created"

        # Should mention log file path in output
        output = result.stdout + result.stderr
        assert "log" in output.lower() or "CLISApp-backend/logs/api" in output, \
            "api-up should mention log file location"

        # Clean up
        run_make("api-down", api_test_env)


class TestApiUpIdempotency:
    """Idempotency tests for `make api-up` (AC2)."""

    def test_api_up_twice_reports_already_running(self, api_test_env):
        """AC2: Running `make api-up` twice should not start duplicates."""
        # Clean up any existing test process
        run_make("api-down", api_test_env)

        # First call - should start process
        result1 = run_make("api-up", api_test_env)
        assert result1.returncode == 0, "First api-up should succeed"

        # Give process time to start
        time.sleep(1)

        # Second call - should report already running
        result2 = run_make("api-up", api_test_env)

        output2 = result2.stdout + result2.stderr
        assert "already running" in output2.lower() or "already started" in output2.lower(), \
            "Second api-up should report already running"

        # Clean up
        run_make("api-down", api_test_env)

    def test_api_up_twice_does_not_create_duplicate_processes(self, api_test_env):
        """AC2: Running `make api-up` twice should not start duplicate processes."""
        # Clean up any existing test process
        run_make("api-down", api_test_env)

        # First call
        result1 = run_make("api-up", api_test_env)
        assert result1.returncode == 0

        # Read PID file
        pid_file = Path(api_test_env["API_STATE_DIR"]) / "api.pid"
        assert pid_file.exists(), "PID file should exist after first api-up"
        pid1 = pid_file.read_text().strip()

        time.sleep(1)

        # Second call
        run_make("api-up", api_test_env)

        # PID should be the same (no duplicate process)
        pid2 = pid_file.read_text().strip()
        assert pid1 == pid2, "PID should not change on second api-up"

        # Clean up
        run_make("api-down", api_test_env)


class TestApiDown:
    """Tests for `make api-down` (AC3)."""

    def test_api_down_stops_running_service(self, api_test_env):
        """AC3: `make api-down` stops the service started by api-up."""
        # Clean up first
        run_make("api-down", api_test_env)

        # Start service
        result_up = run_make("api-up", api_test_env)
        assert result_up.returncode == 0

        # Get PID
        pid_file = Path(api_test_env["API_STATE_DIR"]) / "api.pid"
        assert pid_file.exists()
        pid = int(pid_file.read_text().strip())

        time.sleep(1)

        # Stop service
        result_down = run_make("api-down", api_test_env)
        assert result_down.returncode == 0, "api-down should succeed"

        # Process should be terminated
        time.sleep(1)
        try:
            os.kill(pid, 0)  # Check if process exists
            pytest.fail(f"Process {pid} should be terminated after api-down")
        except ProcessLookupError:
            pass  # Process doesn't exist - good

        # PID file should be removed
        assert not pid_file.exists(), "PID file should be removed after api-down"

    def test_api_down_when_nothing_running_exits_successfully(self, api_test_env):
        """AC3: `make api-down` exits successfully if service already stopped."""
        # Make sure nothing is running
        run_make("api-down", api_test_env)

        # Call api-down when nothing running
        result = run_make("api-down", api_test_env)

        assert result.returncode == 0, "api-down should exit 0 when nothing running"


class TestApiAlias:
    """Tests for `make api` alias (AC4)."""

    def test_api_alias_behaves_like_api_up(self, api_test_env):
        """AC4: `make api` behaves same as `make api-up`."""
        # Clean up
        run_make("api-down", api_test_env)

        # Run make api
        result_api = subprocess.run(
            ["make", "api"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=API_TIMEOUT,
            env=api_test_env,
        )

        output = result_api.stdout + result_api.stderr

        # Should have same behavior as api-up
        assert result_api.returncode == 0, "make api should succeed"
        assert "http://localhost:8080/api/v1/health" in output, \
            "make api should print health URL like api-up"
        assert "http://localhost:8080/docs" in output, \
            "make api should print docs URL like api-up"

        # Clean up
        run_make("api-down", api_test_env)

    def test_api_alias_exit_code_matches_api_up(self, api_test_env):
        """AC4: `make api` exit code matches `make api-up`."""
        # Clean up
        run_make("api-down", api_test_env)

        # Run both and compare exit codes
        result_api_up = subprocess.run(
            ["make", "api-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=API_TIMEOUT,
            env=api_test_env,
        )

        # Clean up and restart with api alias
        run_make("api-down", api_test_env)

        result_api = subprocess.run(
            ["make", "api"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=API_TIMEOUT,
            env=api_test_env,
        )

        assert result_api_up.returncode == result_api.returncode, \
            "make api and make api-up should have same exit code"

        # Clean up
        run_make("api-down", api_test_env)
