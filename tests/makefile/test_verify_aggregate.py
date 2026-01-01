"""
Black-box tests for `make verify` (aggregated verification).

These tests validate:
- AC1: Runs verify-backend and verify-pipeline, creates report, exits non-zero on failure
- AC2: Report includes manual section for verify-mobile
- AC3: Works in CI/restricted environments (smoke mode)

Uses PIPELINE_TEST_MODE=1 for deterministic testing.
"""

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

import pytest

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# Test timeout
VERIFY_TIMEOUT = 180  # Aggregated verification may take longer


def _report_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"


@pytest.fixture(autouse=True)
def _clean_report():
    report_file = _report_path()
    if report_file.exists():
        report_file.unlink()
    yield


class TestVerifyAggregation:
    """AC1: Aggregated verification execution"""

    def test_verify_exits_zero_when_all_checks_pass(self):
        """AC1: Should exit 0 when all automated checks pass"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"  # Use smoke mode for deterministic testing

        # Start services for backend verification
        subprocess.run(["make", "up"], cwd=REPO_ROOT, capture_output=True, timeout=30)
        time.sleep(3)  # Wait for services to initialize

        try:
            result = subprocess.run(
                ["make", "verify"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=VERIFY_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            # Should exit 0 when all checks pass
            assert result.returncode == 0, \
                f"verify should exit 0 when all checks pass\nOutput: {output}"
        finally:
            # Clean up services
            subprocess.run(["make", "down"], cwd=REPO_ROOT, capture_output=True, timeout=30)

    def test_verify_runs_verify_backend(self):
        """AC1: Should run verify-backend"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention backend verification
        assert "backend" in output.lower() or "api" in output.lower(), \
            f"Should run verify-backend\nOutput: {output}"

    def test_verify_runs_verify_pipeline(self):
        """AC1: Should run verify-pipeline"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        result = subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        output = result.stdout + result.stderr

        # Should mention pipeline verification
        assert "pipeline" in output.lower() or "tiles" in output.lower(), \
            f"Should run verify-pipeline\nOutput: {output}"


class TestVerifyReport:
    """AC1: Report generation"""

    def test_verify_creates_report_file(self):
        """AC1: Should create verification report file"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        result = subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Check for report file
        today = datetime.now().strftime("%Y-%m-%d")
        report_dir = REPO_ROOT / "_bmad-output" / "verification-reports"
        report_file = report_dir / f"verify-{today}.md"

        assert report_file.exists(), \
            f"Report file should exist: {report_file}"

    def test_verify_report_includes_pass_fail_status(self):
        """AC1: Report should include pass/fail status per check"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"

        assert report_file.exists(), "Report file should exist"

        report_content = report_file.read_text()

        # Should include status indicators
        assert "pass" in report_content.lower() or "fail" in report_content.lower() or "✓" in report_content or "✗" in report_content, \
            f"Report should include pass/fail status\nReport: {report_content}"

    def test_verify_report_includes_backend_check(self):
        """AC1: Report should mention backend verification"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"
        report_content = report_file.read_text()

        # Should mention backend
        assert "backend" in report_content.lower() or "api" in report_content.lower(), \
            f"Report should mention backend verification\nReport: {report_content}"

    def test_verify_report_includes_pipeline_check(self):
        """AC1: Report should mention pipeline verification"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"
        report_content = report_file.read_text()

        # Should mention pipeline
        assert "pipeline" in report_content.lower() or "tiles" in report_content.lower(), \
            f"Report should mention pipeline verification\nReport: {report_content}"


class TestVerifyMobileManualSection:
    """AC2: Manual verification section"""

    def test_verify_report_includes_mobile_section(self):
        """AC2: Report should include manual section for verify-mobile"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"
        report_content = report_file.read_text()

        # Should mention mobile or manual
        assert "mobile" in report_content.lower() or "manual" in report_content.lower(), \
            f"Report should mention mobile verification\nReport: {report_content}"

    def test_verify_report_includes_verify_mobile_command(self):
        """AC2: Report should include make verify-mobile command"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"
        report_content = report_file.read_text()

        # Should mention verify-mobile command
        assert "verify-mobile" in report_content or "make verify-mobile" in report_content, \
            f"Report should mention verify-mobile command\nReport: {report_content}"

    def test_verify_report_includes_evidence_folder_path(self):
        """AC2: Report should include evidence folder path convention"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Read report
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"
        report_content = report_file.read_text()

        # Should mention evidence path
        assert "verification-evidence" in report_content or "evidence" in report_content.lower(), \
            f"Report should mention evidence folder\nReport: {report_content}"


class TestVerifyCIMode:
    """AC3: CI/restricted environment support"""

    def test_verify_works_with_pipeline_test_mode(self):
        """AC3: Should work in CI with PIPELINE_TEST_MODE=1"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Start services for backend verification
        subprocess.run(["make", "up"], cwd=REPO_ROOT, capture_output=True, timeout=30)
        time.sleep(3)  # Wait for services to initialize

        try:
            result = subprocess.run(
                ["make", "verify"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=VERIFY_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            # Should complete successfully in test mode
            assert result.returncode == 0, \
                f"verify should work in test mode\nOutput: {output}"
        finally:
            # Clean up services
            subprocess.run(["make", "down"], cwd=REPO_ROOT, capture_output=True, timeout=30)

    def test_verify_report_created_in_test_mode(self):
        """AC3: Should create report even in test mode"""
        env = os.environ.copy()
        env["PIPELINE_TEST_MODE"] = "1"

        # Run verify
        subprocess.run(
            ["make", "verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )

        # Check for report file
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = REPO_ROOT / "_bmad-output" / "verification-reports" / f"verify-{today}.md"

        assert report_file.exists(), \
            f"Report should be created in test mode: {report_file}"


class TestVerifyHelp:
    """Make help integration"""

    def test_make_help_lists_verify_target(self):
        """verify should appear in make help"""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should list verify target
        assert "verify" in output.lower(), \
            f"make help should list verify target\nOutput: {output}"
