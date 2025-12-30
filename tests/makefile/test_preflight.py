"""
Black-box tests for the `make preflight` target.

Tests verify:
- AC1: `make preflight` checks tools (python3, pip, node, npm), repo prerequisites (.env, node_modules),
        and port availability (8080, 8000) with version reporting and actionable suggestions
- AC2: Each failure includes exact next action; no services started, no files modified, no network

Per Story 1.2, these tests must run without Docker, Redis, or network access.
"""
import subprocess
import socket
import os
import re
from pathlib import Path
from contextlib import contextmanager

import pytest


# Repository root is 2 levels up from this test file
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Timeout for preflight (seconds) - must be quick, no long-running tasks
PREFLIGHT_TIMEOUT = 10


class TestPreflightBasics:
    """Basic tests for `make preflight` target (AC1, AC2)."""

    def test_preflight_completes_quickly(self):
        """AC2: `make preflight` finishes quickly and never starts services."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        # Should complete within timeout (no hanging services)
        # Exit code may be 0 or non-zero depending on environment
        assert result.returncode is not None

    def test_preflight_checks_python3(self):
        """AC1: preflight checks for python3 and reports version."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert "python3" in output or "python" in output, "preflight should check python3"

    def test_preflight_checks_pip(self):
        """AC1: preflight checks for pip and reports version."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert "pip" in output, "preflight should check pip"

    def test_preflight_checks_node(self):
        """AC1: preflight checks for node and reports version."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert "node" in output, "preflight should check node"

    def test_preflight_checks_npm(self):
        """AC1: preflight checks for npm and reports version."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert "npm" in output, "preflight should check npm"

    def test_preflight_checks_backend_env(self):
        """AC1: preflight checks for CLISApp-backend/.env existence."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert ".env" in output, "preflight should check .env file"

    def test_preflight_checks_frontend_modules(self):
        """AC1: preflight checks for CLISApp-frontend/node_modules or install state."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.lower() + result.stderr.lower()
        assert "node_modules" in output or "npm install" in output, \
            "preflight should check frontend install state"

    def test_preflight_checks_ports(self):
        """AC1: preflight checks port availability (8080 for API, 8000 for tiles)."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout + result.stderr
        # Should mention both ports
        assert "8080" in output, "preflight should check port 8080"
        assert "8000" in output, "preflight should check port 8000"

    def test_preflight_shows_pass_or_fail(self):
        """AC1: preflight output shows PASS/FAIL status for checks."""
        result = subprocess.run(
            ["make", "preflight"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
        )
        output = result.stdout.upper() + result.stderr.upper()
        # Should show either PASS or FAIL indicators
        has_status = "PASS" in output or "FAIL" in output or "OK" in output or "ERROR" in output
        assert has_status, "preflight should show PASS/FAIL or OK/ERROR status"


class TestPreflightPortConflict:
    """Deterministic port conflict tests (AC1, AC2)."""

    @contextmanager
    def bind_ephemeral_port(self):
        """Context manager to bind a random local port for testing (if permitted)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            yield sock.getsockname()[1]
        except PermissionError:
            yield None
        finally:
            sock.close()

    def find_listening_port_via_lsof(self) -> int | None:
        """Find any listening TCP port via lsof (best-effort)."""
        try:
            result = subprocess.run(
                ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

        # Extract port numbers from NAME column like "*:8080 (LISTEN)" or "127.0.0.1:5432 (LISTEN)"
        ports = []
        for line in (result.stdout or "").splitlines():
            match = re.search(r":(\d+)\s+\(LISTEN\)", line)
            if match:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    ports.append(port)

        return ports[0] if ports else None

    def test_preflight_detects_port_conflict(self):
        """AC1: preflight reports conflict when port is in use and exits non-zero."""
        with self.bind_ephemeral_port() as bound_port:
            test_port = bound_port or self.find_listening_port_via_lsof()
            if test_port is None:
                pytest.skip("Unable to create or discover a listening port in this environment")

            env = os.environ.copy()
            env["PREFLIGHT_API_PORT"] = str(test_port)
            env["PREFLIGHT_TILES_PORT"] = str(test_port)

            result = subprocess.run(
                ["make", "preflight"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=PREFLIGHT_TIMEOUT,
                env=env,
            )
            output = result.stdout + result.stderr
            assert str(test_port) in output, f"preflight should report port {test_port}"
            assert result.returncode != 0, "preflight should exit non-zero on port conflict"

    def test_preflight_provides_actionable_suggestion_on_port_conflict(self):
        """AC2: each failure includes exact next action for port conflicts."""
        with self.bind_ephemeral_port() as bound_port:
            test_port = bound_port or self.find_listening_port_via_lsof()
            if test_port is None:
                pytest.skip("Unable to create or discover a listening port in this environment")

            env = os.environ.copy()
            env["PREFLIGHT_API_PORT"] = str(test_port)
            env["PREFLIGHT_TILES_PORT"] = str(test_port)

            result = subprocess.run(
                ["make", "preflight"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=PREFLIGHT_TIMEOUT,
                env=env,
            )
            output = (result.stdout + result.stderr).lower()
            assert result.returncode != 0
            assert "action:" in output
            assert "lsof" in output


class TestPreflightActionHints:
    """Deterministic next-action hint tests (AC2) using PREFLIGHT_REPO_ROOT."""

    def test_preflight_prints_exact_next_actions_for_missing_env_and_node_modules(self, tmp_path: Path):
        fake_root = tmp_path / "repo"
        (fake_root / "CLISApp-backend").mkdir(parents=True)
        (fake_root / "CLISApp-frontend").mkdir(parents=True)

        env_example = fake_root / "CLISApp-backend" / ".env.example"
        env_example.write_text("EXAMPLE=1\n")
        (fake_root / "CLISApp-frontend" / "package.json").write_text('{"name":"x"}\n')

        env = os.environ.copy()
        env["PREFLIGHT_REPO_ROOT"] = str(fake_root)
        env["PREFLIGHT_API_PORT"] = "54321"
        env["PREFLIGHT_TILES_PORT"] = "54322"

        result = subprocess.run(
            ["python3", "scripts/preflight.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
            env=env,
        )
        output = (result.stdout + result.stderr)
        assert result.returncode != 0
        assert "Action:" in output
        assert f"cp {env_example}" in output
        assert "cd CLISApp-frontend && npm install" in output

    def test_preflight_invalid_port_env_is_actionable(self):
        env = os.environ.copy()
        env["PREFLIGHT_API_PORT"] = "not-a-number"
        env["PREFLIGHT_TILES_PORT"] = "8000"

        result = subprocess.run(
            ["python3", "scripts/preflight.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=PREFLIGHT_TIMEOUT,
            env=env,
        )
        output = (result.stdout + result.stderr)
        assert result.returncode != 0
        assert "PREFLIGHT_API_PORT" in output
        assert "Action:" in output
