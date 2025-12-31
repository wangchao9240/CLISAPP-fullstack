"""
Black-box tests for repo-root README.md onboarding document.

These tests validate:
- AC1: README.md exists and contains all required onboarding content
"""

from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent
README_PATH = REPO_ROOT / "README.md"


class TestOnboardingDoc:
    """AC1: README.md provides single onboarding path with all required content."""

    def test_readme_exists_at_repo_root(self):
        """AC1: README.md should exist at repository root."""
        assert README_PATH.exists(), \
            f"README.md should exist at {REPO_ROOT}"
        assert README_PATH.is_file(), \
            f"README.md should be a file, not a directory"

    def test_readme_mentions_make_help(self):
        """AC1: README.md should mention 'make help' target."""
        content = README_PATH.read_text()
        assert "make help" in content, \
            "README.md should mention 'make help'"

    def test_readme_mentions_make_preflight(self):
        """AC1: README.md should mention 'make preflight' target."""
        content = README_PATH.read_text()
        assert "make preflight" in content, \
            "README.md should mention 'make preflight'"

    def test_readme_mentions_make_up(self):
        """AC1: README.md should mention 'make up' target."""
        content = README_PATH.read_text()
        assert "make up" in content, \
            "README.md should mention 'make up'"

    def test_readme_mentions_make_status(self):
        """AC1: README.md should mention 'make status' target."""
        content = README_PATH.read_text()
        assert "make status" in content, \
            "README.md should mention 'make status'"

    def test_readme_mentions_make_logs(self):
        """AC1: README.md should mention 'make logs' target."""
        content = README_PATH.read_text()
        assert "make logs" in content, \
            "README.md should mention 'make logs'"

    def test_readme_mentions_make_verify(self):
        """AC1: README.md should mention 'make verify' target."""
        content = README_PATH.read_text()
        assert "make verify" in content, \
            "README.md should mention 'make verify'"

    def test_readme_mentions_module_boundaries(self):
        """AC1: README.md should describe module boundaries."""
        content = README_PATH.read_text()
        # Should mention all three main modules
        assert "CLISApp-backend" in content, \
            "README.md should mention CLISApp-backend module"
        assert "CLISApp-frontend" in content, \
            "README.md should mention CLISApp-frontend module"
        # Should mention the key components
        assert "API" in content or "api" in content, \
            "README.md should mention API service"
        assert "tile" in content.lower(), \
            "README.md should mention tile server"
        assert "pipeline" in content.lower(), \
            "README.md should mention data pipeline"

    def test_readme_mentions_ios_simulator_localhost(self):
        """AC1: README.md should mention iOS simulator uses localhost."""
        content = README_PATH.read_text()
        assert "localhost" in content, \
            "README.md should mention localhost for iOS simulator"
        assert "iOS" in content or "ios" in content, \
            "README.md should mention iOS simulator"

    def test_readme_mentions_android_emulator_ip(self):
        """AC1: README.md should mention Android emulator IP (10.0.2.2)."""
        content = README_PATH.read_text()
        assert "10.0.2.2" in content, \
            "README.md should mention 10.0.2.2 for Android emulator"
        assert "Android" in content or "android" in content, \
            "README.md should mention Android emulator"

    def test_readme_mentions_verification_evidence_folder(self):
        """AC1: README.md should mention verification evidence folder convention."""
        content = README_PATH.read_text()
        assert "_bmad-output/verification-evidence" in content, \
            "README.md should mention _bmad-output/verification-evidence folder"
        # Should mention mobile verification
        assert "mobile" in content.lower(), \
            "README.md should mention mobile verification"
