"""
Black-box tests for `make check-boundaries`.

These tests validate:
- AC3: `make check-boundaries` fails fast on disallowed imports between app/ and data_pipeline/
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Repository root (two levels up from this test file)
REPO_ROOT = Path(__file__).parent.parent.parent

# Timeout for boundary check command
BOUNDARIES_TIMEOUT = 10


class TestCheckBoundariesBasics:
    """AC3: `make check-boundaries` enforces architectural boundaries."""

    def test_check_boundaries_exits_zero_on_current_repo(self):
        """AC3: `make check-boundaries` should pass on current repo state."""
        result = subprocess.run(
            ["make", "check-boundaries"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=BOUNDARIES_TIMEOUT,
        )

        # Should exit 0 if no boundary violations
        assert result.returncode == 0, \
            f"check-boundaries should pass on current repo\\nOutput: {result.stdout + result.stderr}"

    def test_check_boundaries_completes_quickly(self):
        """AC3: `make check-boundaries` should complete quickly (no network, no service starts)."""
        import time
        start = time.time()

        result = subprocess.run(
            ["make", "check-boundaries"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=BOUNDARIES_TIMEOUT,
        )

        elapsed = time.time() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0, \
            f"check-boundaries should complete quickly (took {elapsed:.2f}s)"


class TestCheckBoundariesViolations:
    """AC3: `make check-boundaries` detects and reports boundary violations."""

    def test_check_boundaries_detects_app_importing_data_pipeline(self):
        """AC3: Should detect when app/ imports from data_pipeline/."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal structure
            backend_dir = tmpdir / "CLISApp-backend"
            app_dir = backend_dir / "app"
            data_pipeline_dir = backend_dir / "data_pipeline"

            app_dir.mkdir(parents=True)
            data_pipeline_dir.mkdir(parents=True)

            # Create a file in app/ that imports from data_pipeline/
            violating_file = app_dir / "violating_module.py"
            violating_file.write_text(
                "from data_pipeline.something import foo\n"
                "\n"
                "def bar():\n"
                "    return foo()\n"
            )

            # Create a dummy module in data_pipeline/
            dummy_module = data_pipeline_dir / "something.py"
            dummy_module.write_text("def foo():\n    return 42\n")

            # Run check-boundaries with custom repo root
            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            # Should fail (non-zero exit code)
            assert result.returncode != 0, \
                "check-boundaries should fail on app/ importing data_pipeline/"

            # Should mention the violation
            assert "data_pipeline" in output, \
                "Output should mention the forbidden import"

            # Should provide actionable guidance
            assert "shared" in output.lower() or "fix" in output.lower(), \
                "Output should provide actionable fix guidance"

    def test_check_boundaries_detects_app_relative_importing_data_pipeline(self):
        """AC3: Should detect when app/ uses relative imports to pull in data_pipeline/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            backend_dir = tmpdir / "CLISApp-backend"
            app_dir = backend_dir / "app"
            data_pipeline_dir = backend_dir / "data_pipeline"

            app_dir.mkdir(parents=True)
            data_pipeline_dir.mkdir(parents=True)

            # Use a relative import form that previously bypassed detection:
            # `from .. import data_pipeline`
            violating_file = app_dir / "violating_relative_import.py"
            violating_file.write_text("from .. import data_pipeline\n")

            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            assert result.returncode != 0, \
                "check-boundaries should fail on relative import of data_pipeline from app/"
            assert "data_pipeline" in output, \
                "Output should mention the forbidden import (data_pipeline)"
            assert "how to fix" in output.lower(), \
                "Output should provide actionable fix guidance"

    def test_check_boundaries_detects_data_pipeline_importing_app(self):
        """AC3: Should detect when data_pipeline/ imports from app/."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal structure
            backend_dir = tmpdir / "CLISApp-backend"
            app_dir = backend_dir / "app"
            data_pipeline_dir = backend_dir / "data_pipeline"

            app_dir.mkdir(parents=True)
            data_pipeline_dir.mkdir(parents=True)

            # Create a file in data_pipeline/ that imports from app/
            violating_file = data_pipeline_dir / "violating_module.py"
            violating_file.write_text(
                "from app.services.something import Service\n"
                "\n"
                "def process():\n"
                "    return Service()\n"
            )

            # Create a dummy module in app/
            app_services_dir = app_dir / "services"
            app_services_dir.mkdir()
            dummy_module = app_services_dir / "something.py"
            dummy_module.write_text("class Service:\n    pass\n")

            # Run check-boundaries with custom repo root
            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            # Should fail (non-zero exit code)
            assert result.returncode != 0, \
                "check-boundaries should fail on data_pipeline/ importing app/"

            # Should mention the violation
            assert "app" in output, \
                "Output should mention the forbidden import"

            # Should provide actionable guidance
            assert "shared" in output.lower() or "fix" in output.lower(), \
                "Output should provide actionable fix guidance"

    def test_check_boundaries_detects_data_pipeline_relative_importing_app(self):
        """AC3: Should detect when data_pipeline/ uses relative imports to pull in app/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            backend_dir = tmpdir / "CLISApp-backend"
            app_dir = backend_dir / "app"
            data_pipeline_dir = backend_dir / "data_pipeline"

            app_dir.mkdir(parents=True)
            data_pipeline_dir.mkdir(parents=True)

            violating_file = data_pipeline_dir / "violating_relative_import.py"
            violating_file.write_text("from .. import app\n")

            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            assert result.returncode != 0, \
                "check-boundaries should fail on relative import of app from data_pipeline/"
            assert "app" in output, \
                "Output should mention the forbidden import (app)"
            assert "how to fix" in output.lower(), \
                "Output should provide actionable fix guidance"

    def test_check_boundaries_allows_shared_imports(self):
        """AC3: Should allow both app/ and data_pipeline/ to import from shared/."""
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal structure
            backend_dir = tmpdir / "CLISApp-backend"
            app_dir = backend_dir / "app"
            data_pipeline_dir = backend_dir / "data_pipeline"
            shared_dir = backend_dir / "shared"

            app_dir.mkdir(parents=True)
            data_pipeline_dir.mkdir(parents=True)
            shared_dir.mkdir(parents=True)

            # Create a shared utility
            shared_util = shared_dir / "utils.py"
            shared_util.write_text("def shared_function():\n    return 'shared'\n")

            # Create app file importing from shared
            app_file = app_dir / "app_module.py"
            app_file.write_text(
                "from shared.utils import shared_function\n"
                "\n"
                "def app_func():\n"
                "    return shared_function()\n"
            )

            # Create data_pipeline file importing from shared
            pipeline_file = data_pipeline_dir / "pipeline_module.py"
            pipeline_file.write_text(
                "from shared.utils import shared_function\n"
                "\n"
                "def pipeline_func():\n"
                "    return shared_function()\n"
            )

            # Run check-boundaries with custom repo root
            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            # Should pass (exit 0) - shared imports are allowed
            assert result.returncode == 0, \
                f"check-boundaries should allow shared/ imports\\nOutput: {result.stdout + result.stderr}"

    def test_check_boundaries_detects_shared_importing_app(self):
        """AC3: Should detect shared/ importing app/ (prevents transitive coupling)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            backend_dir = tmpdir / "CLISApp-backend"
            (backend_dir / "app").mkdir(parents=True)
            (backend_dir / "data_pipeline").mkdir(parents=True)
            shared_dir = backend_dir / "shared"
            shared_dir.mkdir(parents=True)

            violating_file = shared_dir / "violating_shared_import.py"
            violating_file.write_text("from app import api\n")

            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            assert result.returncode != 0, \
                "check-boundaries should fail on shared/ importing app/"
            assert "shared/" in output or "shared" in output.lower(), \
                "Output should reference shared/ check"
            assert "app" in output, \
                "Output should mention the forbidden import (app)"

    def test_check_boundaries_detects_shared_importing_data_pipeline(self):
        """AC3: Should detect shared/ importing data_pipeline/ (prevents transitive coupling)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            backend_dir = tmpdir / "CLISApp-backend"
            (backend_dir / "app").mkdir(parents=True)
            (backend_dir / "data_pipeline").mkdir(parents=True)
            shared_dir = backend_dir / "shared"
            shared_dir.mkdir(parents=True)

            violating_file = shared_dir / "violating_shared_import.py"
            violating_file.write_text("from data_pipeline import servers\n")

            env = os.environ.copy()
            env["CHECK_BOUNDARIES_REPO_ROOT"] = str(tmpdir)

            result = subprocess.run(
                ["make", "check-boundaries"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=BOUNDARIES_TIMEOUT,
                env=env,
            )

            output = result.stdout + result.stderr

            assert result.returncode != 0, \
                "check-boundaries should fail on shared/ importing data_pipeline/"
            assert "shared/" in output or "shared" in output.lower(), \
                "Output should reference shared/ check"
            assert "data_pipeline" in output, \
                "Output should mention the forbidden import (data_pipeline)"
