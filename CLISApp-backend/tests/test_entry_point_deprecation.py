"""
Entry Point Deprecation Tests

Ensures deprecated entry points are properly marked and not promoted in docs.
"""

import pytest
from pathlib import Path


class TestDeprecatedScripts:
    """Verify deprecated scripts have proper deprecation notices"""

    def test_start_sh_has_deprecation_notice(self):
        """start.sh should contain deprecation warning"""
        script_path = Path(__file__).parent.parent / "start.sh"
        assert script_path.exists(), "start.sh should exist for backward compatibility"

        content = script_path.read_text()
        assert "DEPRECATED" in content, "start.sh should have DEPRECATED notice"
        assert "Phase 2" in content, "start.sh should mention Phase 2 removal"
        assert "make up" in content, "start.sh should reference make up"

    def test_start_all_services_has_deprecation_notice(self):
        """start_all_services.py should contain deprecation warning"""
        script_path = Path(__file__).parent.parent / "start_all_services.py"
        assert script_path.exists(), "start_all_services.py should exist for backward compatibility"

        content = script_path.read_text()
        assert "DEPRECATED" in content, "start_all_services.py should have DEPRECATED notice"
        assert "Phase 2" in content, "start_all_services.py should mention Phase 2 removal"
        assert "make up" in content, "start_all_services.py should reference make up"

    def test_dev_server_has_deprecation_notice(self):
        """dev_server.py should contain deprecation warning"""
        script_path = Path(__file__).parent.parent / "dev_server.py"
        assert script_path.exists(), "dev_server.py should exist for backward compatibility"

        content = script_path.read_text()
        assert "DEPRECATED" in content, "dev_server.py should have DEPRECATED notice"
        assert "Phase 2" in content, "dev_server.py should mention Phase 2 removal"
        assert "make api-up" in content, "dev_server.py should reference make api-up"


class TestDocumentationEntryPoints:
    """Verify documentation promotes Makefile as primary entry point"""

    def test_backend_readme_promotes_makefile(self):
        """CLISApp-backend/README.md should promote Makefile first"""
        readme_path = Path(__file__).parent.parent / "README.md"
        assert readme_path.exists(), "CLISApp-backend/README.md should exist"

        content = readme_path.read_text()

        # Check that Quick Start section exists
        assert "Quick Start" in content, "README should have Quick Start section"

        # Check that Makefile is mentioned in Quick Start
        quick_start_index = content.find("Quick Start")
        deprecated_index = content.find("Alternative:", quick_start_index)

        # Ensure "make up" appears before deprecated scripts section
        make_up_index = content.find("make up", quick_start_index)
        assert make_up_index > 0, "README should mention 'make up'"
        assert make_up_index < deprecated_index, "'make up' should appear before deprecated scripts"

        # Ensure deprecated scripts are marked as such
        assert "DEPRECATED" in content or "deprecated" in content, "README should mark deprecated scripts"

    def test_development_guide_backend_promotes_makefile(self):
        """docs/development-guide-backend.md should promote Makefile first"""
        guide_path = Path(__file__).parent.parent.parent / "docs" / "development-guide-backend.md"
        assert guide_path.exists(), "development-guide-backend.md should exist"

        content = guide_path.read_text()

        # Check that Makefile approach is mentioned
        assert "make up" in content.lower(), "Development guide should mention 'make up'"
        assert "make api-up" in content.lower() or "make tiles-up" in content.lower(), \
            "Development guide should mention individual service start commands"

        # Ensure deprecated scripts are marked if mentioned
        if "start.sh" in content or "start_all_services.py" in content or "dev_server.py" in content:
            assert "deprecated" in content.lower() or "DEPRECATED" in content, \
                "If deprecated scripts are mentioned, they should be marked as deprecated"

    def test_root_readme_is_makefile_first(self):
        """Root README.md should be Makefile-first"""
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        assert readme_path.exists(), "Root README.md should exist"

        content = readme_path.read_text()

        # Check for Getting Started section
        assert "Getting Started" in content, "Root README should have Getting Started section"

        # Verify it mentions make help/preflight/up
        assert "make help" in content, "Root README should mention 'make help'"
        assert "make preflight" in content, "Root README should mention 'make preflight'"
        assert "make up" in content, "Root README should mention 'make up'"

    def test_no_backend_scripts_in_root_readme_getting_started(self):
        """Root README.md Getting Started should not mention backend-local scripts"""
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        content = readme_path.read_text()

        # Find Getting Started section
        getting_started_index = content.find("## Getting Started")
        assert getting_started_index > 0, "Root README should have Getting Started section"

        # Find end of Getting Started (next ## heading or end of file)
        next_section = content.find("\n## ", getting_started_index + 1)
        if next_section == -1:
            next_section = len(content)

        getting_started_section = content[getting_started_index:next_section]

        # Ensure backend-local scripts are not mentioned in Getting Started
        assert "start.sh" not in getting_started_section, \
            "Getting Started should not mention start.sh"
        assert "start_all_services.py" not in getting_started_section, \
            "Getting Started should not mention start_all_services.py"
        assert "dev_server.py" not in getting_started_section, \
            "Getting Started should not mention dev_server.py"


class TestMakefileConsistency:
    """Verify Makefile remains the single source of truth"""

    def test_makefile_exists(self):
        """Root Makefile should exist"""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        assert makefile_path.exists(), "Root Makefile should exist"

    def test_makefile_has_help_target(self):
        """Makefile should have a help target"""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        content = makefile_path.read_text()

        assert "help:" in content, "Makefile should have help target"
        assert ".PHONY:" in content, "Makefile should declare PHONY targets"

    def test_makefile_has_core_targets(self):
        """Makefile should have core lifecycle targets"""
        makefile_path = Path(__file__).parent.parent.parent / "Makefile"
        content = makefile_path.read_text()

        required_targets = ["preflight", "up", "down", "api-up", "tiles-up", "status", "logs"]

        for target in required_targets:
            assert f"{target}:" in content, f"Makefile should have {target} target"
