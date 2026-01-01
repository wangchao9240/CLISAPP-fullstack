"""
Black-box tests for `make verify-mobile`.

These tests validate:
- AC1: Step-by-step checklist for iOS and Android
- AC2: Queensland-only coverage validation instructions
- AC3: Canonical evidence directory creation
- AC4: Exit 0 with evidence reminder

This is a manual checklist generator, not automated testing.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime

import pytest

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# Test timeout
VERIFY_TIMEOUT = 30


class TestVerifyMobileExecution:
    """AC4: Exit code and basic execution"""

    def test_verify_mobile_exits_zero(self):
        """AC4: Should always exit 0 (manual checklist)"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should always exit 0 (manual checklist)
        assert result.returncode == 0, \
            f"verify-mobile should exit 0\\nOutput: {output}"


class TestVerifyMobileChecklist:
    """AC1: Step-by-step checklist content"""

    def test_verify_mobile_mentions_ios_and_android(self):
        """AC1: Should include checklist for both iOS and Android"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention both platforms
        assert "ios" in output.lower(), \
            f"Should mention iOS platform\\nOutput: {output}"
        assert "android" in output.lower(), \
            f"Should mention Android platform\\nOutput: {output}"

    def test_verify_mobile_mentions_all_five_layers(self):
        """AC1: Should mention all five layers for switching verification"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention all five layers
        layers = ["pm2.5", "uv", "precipitation", "temperature", "humidity"]
        for layer in layers:
            assert layer.lower() in output.lower() or layer.replace(".", "") in output.lower(), \
                f"Should mention layer: {layer}\\nOutput: {output}"

    def test_verify_mobile_mentions_app_launch_and_map(self):
        """AC1: Should verify app launch and map load"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention app launch
        assert "launch" in output.lower() or "start" in output.lower(), \
            f"Should mention app launch\\nOutput: {output}"

        # Should mention map
        assert "map" in output.lower(), \
            f"Should mention map load\\nOutput: {output}"

    def test_verify_mobile_mentions_pipeline_per_layer(self):
        """AC1: Should mention per-layer pipeline commands"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention per-layer pipeline commands
        assert "pipeline-" in output.lower() or "per-layer" in output.lower(), \
            f"Should mention per-layer pipeline commands\\nOutput: {output}"


class TestVerifyMobileQueenslandBoundary:
    """AC2: Queensland-only coverage validation"""

    def test_verify_mobile_mentions_queensland_boundary(self):
        """AC2: Should instruct Queensland boundary validation"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention Queensland
        assert "queensland" in output.lower() or "qld" in output.lower(), \
            f"Should mention Queensland boundary\\nOutput: {output}"

    def test_verify_mobile_mentions_boundary_screenshots(self):
        """AC2: Should instruct taking boundary screenshots"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention screenshots or evidence
        assert "screenshot" in output.lower() or "capture" in output.lower() or "image" in output.lower(), \
            f"Should mention screenshots\\nOutput: {output}"

        # Should mention boundary or outside
        assert "boundary" in output.lower() or "outside" in output.lower() or "inside" in output.lower(), \
            f"Should mention boundary validation\\nOutput: {output}"


class TestVerifyMobileEvidenceDirectories:
    """AC3: Canonical evidence directory creation"""

    def test_verify_mobile_prints_evidence_directory_paths(self):
        """AC3: Should print canonical evidence directory paths"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should mention evidence directories
        assert "_bmad-output/verification-evidence" in output or "verification-evidence" in output, \
            f"Should mention verification-evidence path\\nOutput: {output}"

        # Should mention both platforms
        assert "ios" in output.lower() and "android" in output.lower(), \
            f"Should mention both iOS and Android paths\\nOutput: {output}"

    def test_verify_mobile_creates_evidence_directories(self):
        """AC3: Should create evidence directories"""
        # Clean up any existing evidence directories for today
        today = datetime.now().strftime("%Y-%m-%d")
        evidence_base = REPO_ROOT / "_bmad-output" / "verification-evidence" / today / "mobile"

        # Run verify-mobile
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Evidence directories should exist
        ios_dir = evidence_base / "ios"
        android_dir = evidence_base / "android"

        assert ios_dir.exists() and ios_dir.is_dir(), \
            f"iOS evidence directory should exist: {ios_dir}\\nOutput: {output}"
        assert android_dir.exists() and android_dir.is_dir(), \
            f"Android evidence directory should exist: {android_dir}\\nOutput: {output}"


class TestVerifyMobileEvidenceReminder:
    """AC4: Evidence reminder"""

    def test_verify_mobile_prints_evidence_reminder(self):
        """AC4: Should print reminder about evidence capture"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        # Should remind about evidence
        assert "evidence" in output.lower() or "screenshot" in output.lower() or "capture" in output.lower(), \
            f"Should remind about evidence capture\\nOutput: {output}"


class TestVerifyMobileAdditionalArtifacts:
    """AC3: Additional artifacts guidance"""

    def test_verify_mobile_mentions_logs_and_notes(self):
        """AC3: Should mention logs and notes storage"""
        result = subprocess.run(
            ["make", "verify-mobile"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
        )

        output = result.stdout + result.stderr

        assert "notes.md" in output.lower() or "notes" in output.lower(), \
            f"Should mention notes.md\\nOutput: {output}"
        assert "logs" in output.lower() or "logs.txt" in output.lower(), \
            f"Should mention logs\\nOutput: {output}"


class TestVerifyMobileHelp:
    """Make help integration"""

    def test_make_help_lists_verify_mobile_target(self):
        """verify-mobile should appear in make help"""
        result = subprocess.run(
            ["make", "help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout + result.stderr

        # Should list verify-mobile target
        assert "verify-mobile" in output.lower() or "verify mobile" in output.lower(), \
            f"make help should list verify-mobile target\\nOutput: {output}"
