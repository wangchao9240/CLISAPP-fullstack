"""
Black-box tests for `make tiles-up`, `make tiles-down`, and `make tiles` targets.

Tests verify:
- AC1: `make tiles-up` starts tile server on :8000, prints health URL and demo URL, writes logs to CLISApp-backend/logs/tiles/
- AC2: Running `make tiles-up` twice should not start duplicates, should report already running
- AC3: `make tiles-down` stops the service, exits successfully if already stopped
- AC4: `make tiles` alias behaves same as `make tiles-up`

Per Story 1.4, these tests run in test mode using a dummy process instead of actual uvicorn.
"""
import subprocess
import time
import os
import signal
import re
from pathlib import Path

import pytest


# Repository root is 2 levels up from this test file
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Timeout for tiles lifecycle operations (seconds)
TILES_TIMEOUT = 10


def extract_log_path(output: str) -> str | None:
    for line in output.splitlines():
        if line.strip().lower().startswith("log:"):
            return line.split(":", 1)[1].strip()
    return None


class TestTilesUpBasics:
    """Basic tests for `make tiles-up` target (AC1)."""

    def test_tiles_up_starts_and_prints_urls(self):
        """AC1: `make tiles-up` starts tile server and prints health URL and demo URL."""
        # Clean up any existing test process
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        # Set test mode to use dummy process
        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, f"tiles-up should succeed, output: {output}"

        # Should print health URL
        assert "http://localhost:8000/health" in output, \
            "tiles-up should print health URL"

        # Should print demo URL
        assert "http://localhost:8000/tiles/pm25/demo" in output, \
            "tiles-up should print demo URL"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

    def test_tiles_up_creates_log_file(self):
        """AC1: `make tiles-up` writes logs to CLISApp-backend/logs/tiles/."""
        # Clean up any existing test process
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        assert result.returncode == 0

        # Check log directory exists
        log_dir = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles"
        assert log_dir.exists(), "Log directory should be created"

        # Should mention log file path in output
        output = result.stdout + result.stderr
        log_path = extract_log_path(output)
        assert log_path, f"tiles-up should print Log path\\nOutput: {output}"
        assert "CLISApp-backend/logs/tiles" in log_path, "Log path should be repo-local tiles log dir"
        assert re.search(r"tiles-\d{8}-\d{6}\.log$", log_path), "Log file should be timestamped"
        assert Path(log_path).exists(), "Log file should exist"

        # Should maintain a stable 'latest' pointer for make logs UX
        latest_log = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles" / "tiles-latest.log"
        assert latest_log.exists(), "tiles-latest.log should exist after tiles-up"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )


class TestTilesUpIdempotency:
    """Idempotency tests for `make tiles-up` (AC2)."""

    def test_tiles_up_twice_reports_already_running(self):
        """AC2: Running `make tiles-up` twice should not start duplicates."""
        # Clean up any existing test process
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # First call - should start process
        result1 = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )
        assert result1.returncode == 0, "First tiles-up should succeed"

        # Give process time to start
        time.sleep(1)

        # Second call - should report already running
        result2 = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        output2 = result2.stdout + result2.stderr
        assert "already running" in output2.lower() or "already started" in output2.lower(), \
            "Second tiles-up should report already running"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

    def test_tiles_up_twice_does_not_create_duplicate_processes(self):
        """AC2: Running `make tiles-up` twice should not start duplicate processes."""
        # Clean up any existing test process
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # First call
        result1 = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )
        assert result1.returncode == 0

        # Read PID file
        pid_file = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles" / "tiles.pid"
        assert pid_file.exists(), "PID file should exist after first tiles-up"
        pid1 = pid_file.read_text().strip()

        time.sleep(1)

        # Second call
        subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        # PID should be the same (no duplicate process)
        pid2 = pid_file.read_text().strip()
        assert pid1 == pid2, "PID should not change on second tiles-up"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )


class TestTilesDown:
    """Tests for `make tiles-down` (AC3)."""

    def test_tiles_down_stops_running_service(self):
        """AC3: `make tiles-down` stops the service started by tiles-up."""
        # Clean up first
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # Start service
        result_up = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )
        assert result_up.returncode == 0

        # Get PID
        pid_file = REPO_ROOT / "CLISApp-backend" / "logs" / "tiles" / "tiles.pid"
        assert pid_file.exists()
        pid = int(pid_file.read_text().strip())

        time.sleep(1)

        # Stop service
        result_down = subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )
        assert result_down.returncode == 0, "tiles-down should succeed"

        # Process should be terminated
        time.sleep(1)
        try:
            os.kill(pid, 0)  # Check if process exists
            pytest.fail(f"Process {pid} should be terminated after tiles-down")
        except ProcessLookupError:
            pass  # Process doesn't exist - good

        # PID file should be removed
        assert not pid_file.exists(), "PID file should be removed after tiles-down"

    def test_tiles_down_when_nothing_running_exits_successfully(self):
        """AC3: `make tiles-down` exits successfully if service already stopped."""
        # Make sure nothing is running
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # Call tiles-down when nothing running
        result = subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        assert result.returncode == 0, "tiles-down should exit 0 when nothing running"


class TestTilesAlias:
    """Tests for `make tiles` alias (AC4)."""

    def test_tiles_alias_behaves_like_tiles_up(self):
        """AC4: `make tiles` behaves same as `make tiles-up`."""
        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # Run make tiles
        result_tiles = subprocess.run(
            ["make", "tiles"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        output = result_tiles.stdout + result_tiles.stderr

        # Should have same behavior as tiles-up
        assert result_tiles.returncode == 0, "make tiles should succeed"
        assert "http://localhost:8000/health" in output, \
            "make tiles should print health URL like tiles-up"
        assert "http://localhost:8000/tiles/pm25/demo" in output, \
            "make tiles should print demo URL like tiles-up"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

    def test_tiles_alias_exit_code_matches_tiles_up(self):
        """AC4: `make tiles` exit code matches `make tiles-up`."""
        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
        )

        env = os.environ.copy()
        env["TILES_TEST_MODE"] = "1"

        # Run both and compare exit codes
        result_tiles_up = subprocess.run(
            ["make", "tiles-up"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        # Clean up and restart with tiles alias
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        result_tiles = subprocess.run(
            ["make", "tiles"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )

        assert result_tiles_up.returncode == result_tiles.returncode, \
            "make tiles and make tiles-up should have same exit code"

        # Clean up
        subprocess.run(
            ["make", "tiles-down"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=TILES_TIMEOUT,
            env=env,
        )
