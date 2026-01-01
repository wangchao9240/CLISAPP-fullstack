"""
Guard against deprecated tile-serving surfaces in scripts.

Story 4.3: Deprecate Legacy Tile-Serving Topology Safely
"""

from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent

FILES_TO_SCAN = [
    "CLISApp-backend/quick-docker-test.sh",
    "scripts/verify_backend.py",
    "scripts/status.py",
]

DEPRECATED_PATTERNS = [
    "http://localhost:8080/tiles",
    "https://clisapp-api.qut.edu.au/tiles",
    ":8080/tiles/",
]


def test_scripts_do_not_use_deprecated_static_mount():
    for rel_path in FILES_TO_SCAN:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for pattern in DEPRECATED_PATTERNS:
            assert pattern not in content, f"{rel_path} contains deprecated tile surface: {pattern}"
