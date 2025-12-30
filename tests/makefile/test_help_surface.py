"""
Black-box tests for the root Makefile help surface.

Tests verify:
- AC1: `make help` exits 0, shows grouped targets with descriptions
- AC2: `make` with no target exits 0, shows help or instruction, does not start services

Per Story 1.1, these tests must run without Docker, Redis, or network access.
"""
import subprocess
import re
from pathlib import Path


# Repository root is 2 levels up from this test file
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Timeout for commands (seconds) - must be quick, no long-running tasks
MAKE_TIMEOUT = 5


class TestMakeHelp:
    """Tests for `make help` target (AC1)."""

    def test_make_help_has_expected_sections(self):
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make help failed: {result.stderr}"

        output = result.stdout
        assert "Core Targets:" in output
        assert "Service Management:" in output
        assert "Aliases (for continuity):" in output

    def test_make_help_exits_zero(self):
        """AC1: `make help` exits successfully (exit code 0)."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make help failed with: {result.stderr}"

    def test_make_help_includes_required_targets(self):
        """AC1: Help output lists required targets: help, preflight, api-up, tiles-up, up, status, logs, pipeline, verify."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make help failed: {result.stderr}"

        output = result.stdout.lower()
        required_targets = [
            "help",
            "preflight",
            "api-up",
            "tiles-up",
            "up",
            "status",
            "logs",
            "pipeline",
            "verify",
        ]

        for target in required_targets:
            assert target in output, f"Required target '{target}' not found in help output"

    def test_make_help_includes_alias_mappings(self):
        """AC1: Help output lists required aliases: dev-up -> up, api -> api-up, tiles -> tiles-up."""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make help failed: {result.stderr}"

        output = result.stdout
        assert "Aliases (for continuity):" in output

        lower = output.lower()

        # Ensure alias targets appear as distinct targets (avoid substring matches like "api" in "api-up")
        assert re.search(r"(?m)^\s+dev-up\s", lower)
        assert re.search(r"(?m)^\s+api\s", lower)
        assert re.search(r"(?m)^\s+tiles\s", lower)

        # Ensure mappings are explicit
        assert re.search(r"(?m)^\s*dev-up\s*->\s*up\b", lower)
        assert re.search(r"(?m)^\s*api\s*->\s*api-up\b", lower)
        assert re.search(r"(?m)^\s*tiles\s*->\s*tiles-up\b", lower)


class TestMakeNoTarget:
    """Tests for `make` with no target (AC2)."""

    def test_make_no_target_exits_zero(self):
        """AC2: `make` with no target exits successfully."""
        result = subprocess.run(
            ["make"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make (no target) failed with: {result.stderr}"

    def test_make_no_target_shows_help_or_instruction(self):
        """AC2: `make` with no target prints help output or instruction to run `make help`."""
        result = subprocess.run(
            ["make"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=MAKE_TIMEOUT,
        )
        assert result.returncode == 0, f"make (no target) failed: {result.stderr}"

        output = result.stdout.lower()
        # Should either show help directly or mention how to get help
        has_help_content = "help" in output or "usage" in output or "available" in output
        assert has_help_content, "make (no target) should show help or mention 'help'"

    def test_make_no_target_completes_quickly(self):
        """AC2: `make` with no target does not start services (must be quick)."""
        # This test uses the timeout inherently - if it hangs, the test fails
        # We set a very short timeout to ensure no long-running tasks
        result = subprocess.run(
            ["make"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,  # Must complete in 2 seconds
        )
        # If we get here, it completed quickly (didn't timeout)
        assert result.returncode == 0, f"make (no target) failed: {result.stderr}"
