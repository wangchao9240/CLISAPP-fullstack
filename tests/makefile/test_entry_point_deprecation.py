"""
Entry point guardrails for Makefile-first workflow.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_backend_readme_makefile_first():
    content = _read("CLISApp-backend/README.md").lower()
    assert "quick start" in content
    assert "make up" in content


def test_frontend_guide_references_makefile():
    content = _read("docs/development-guide-frontend.md").lower()
    assert "make up" in content


def test_deprecated_scripts_marked():
    content = _read("CLISApp-backend/README.md")
    if "dev_server.py" in content or "start_all_services.py" in content or "start.sh" in content:
        assert "DEPRECATED" in content or "deprecated" in content


def test_root_readme_makefile_first():
    content = _read("README.md").lower()
    assert "make help" in content
    assert "make preflight" in content
    assert "make up" in content
