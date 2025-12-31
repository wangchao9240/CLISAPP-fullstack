#!/usr/bin/env python3
"""
Boundary Checker Script

Enforces architectural boundaries between API service and data pipeline:
- app/ MUST NOT import from data_pipeline/
- data_pipeline/ MUST NOT import from app/
- Both MAY import from shared/
 - shared/ MUST NOT import from app/ or data_pipeline/ (prevents transitive coupling)

Exit codes:
- 0: No boundary violations
- 1: Boundary violations detected
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple


# Get repository root (support testing with custom repo root)
REPO_ROOT = Path(
    os.environ.get(
        "CHECK_BOUNDARIES_REPO_ROOT",
        str(Path(__file__).resolve().parent.parent),
    )
).resolve()

BACKEND_DIR = REPO_ROOT / "CLISApp-backend"
APP_DIR = BACKEND_DIR / "app"
DATA_PIPELINE_DIR = BACKEND_DIR / "data_pipeline"
SHARED_DIR = BACKEND_DIR / "shared"


def extract_imports(python_file: Path) -> List[str]:
    """
    Extract all import statements from a Python file using AST.

    Returns list of imported module names (e.g., ['data_pipeline.something', 'app.services'])
    """
    try:
        content = python_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(python_file))
    except SyntaxError:
        # Skip files with syntax errors (they'll fail elsewhere)
        return []
    except Exception:
        # Skip files that can't be read or parsed
        return []

    imports = []

    for node in ast.walk(tree):
        # Handle: import foo, import foo.bar
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        # Handle: from foo import bar, from foo.bar import baz
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
            else:
                # Handle: from . import foo, from .. import app
                for alias in node.names:
                    if alias.name != "*":
                        imports.append(alias.name)

    return imports


def check_directory(directory: Path, forbidden_prefixes: List[str]) -> List[Tuple[Path, str]]:
    """
    Check all Python files in a directory for forbidden imports.

    Returns list of (file_path, forbidden_import) tuples.
    """
    violations = []

    if not directory.exists():
        return violations

    # Find all Python files recursively
    for python_file in directory.rglob("*.py"):
        imports = extract_imports(python_file)

        for imported_module in imports:
            # Check if this import starts with any forbidden prefix
            for forbidden_prefix in forbidden_prefixes:
                if imported_module.startswith(forbidden_prefix):
                    violations.append((python_file, imported_module))

    return violations


def main():
    """Main entry point - check boundaries and report violations."""

    violations_found = False

    # Check app/ for imports from data_pipeline/
    print()
    print("Checking app/ for forbidden data_pipeline/ imports...")
    app_violations = check_directory(APP_DIR, ["data_pipeline"])

    if app_violations:
        violations_found = True
        print()
        print("  FAIL: app/ imports from data_pipeline/")
        print()
        for file_path, forbidden_import in app_violations:
            # Make path relative for readability
            rel_path = file_path.relative_to(REPO_ROOT)
            print(f"    File: {rel_path}")
            print(f"    Import: {forbidden_import}")
            print()
        print("  How to fix:")
        print("    - Move shared code to CLISApp-backend/shared/")
        print("    - Or use filesystem/API boundaries (read tiles/artifacts from disk)")
        print()
    else:
        print("  PASS")

    # Check data_pipeline/ for imports from app/
    print()
    print("Checking data_pipeline/ for forbidden app/ imports...")
    pipeline_violations = check_directory(DATA_PIPELINE_DIR, ["app"])

    if pipeline_violations:
        violations_found = True
        print()
        print("  FAIL: data_pipeline/ imports from app/")
        print()
        for file_path, forbidden_import in pipeline_violations:
            # Make path relative for readability
            rel_path = file_path.relative_to(REPO_ROOT)
            print(f"    File: {rel_path}")
            print(f"    Import: {forbidden_import}")
            print()
        print("  How to fix:")
        print("    - Move shared code to CLISApp-backend/shared/")
        print("    - Or use filesystem/API boundaries (call API endpoints, don't import app code)")
        print()
    else:
        print("  PASS")

    # Check shared/ is pure (prevents app <-> data_pipeline transitive coupling via shared)
    print()
    print("Checking shared/ for forbidden app/ and data_pipeline/ imports...")
    shared_violations = check_directory(SHARED_DIR, ["app", "data_pipeline"])

    if shared_violations:
        violations_found = True
        print()
        print("  FAIL: shared/ imports from app/ or data_pipeline/")
        print()
        for file_path, forbidden_import in shared_violations:
            rel_path = file_path.relative_to(REPO_ROOT)
            print(f"    File: {rel_path}")
            print(f"    Import: {forbidden_import}")
            print()
        print("  How to fix:")
        print("    - Keep shared/ dependency-free of app/ and data_pipeline/")
        print("    - Move shared types/helpers into shared/, not runtime modules")
        print()
    else:
        print("  PASS")

    print()

    if violations_found:
        print("Boundary check FAILED: Fix violations above")
        print()
        return 1
    else:
        print("Boundary check PASSED: No violations found")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
