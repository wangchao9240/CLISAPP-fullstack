#!/usr/bin/env python3
"""
Log Viewing Helper Script

Shows log locations and provides quick viewing commands for API and tile server logs.
"""

import sys
from pathlib import Path

# Paths (relative to repository root)
REPO_ROOT = Path(__file__).parent.parent.absolute()
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

# Log directories (matching service scripts)
API_LOG_DIR = BACKEND_DIR / "logs" / "api"
TILES_LOG_DIR = BACKEND_DIR / "logs" / "tiles"

# Stable + latest log file symlinks (matching service scripts)
API_STABLE_LOG = API_LOG_DIR / "api.log"
API_LATEST_LOG = API_LOG_DIR / "api-latest.log"
TILES_STABLE_LOG = TILES_LOG_DIR / "tiles.log"
TILES_LATEST_LOG = TILES_LOG_DIR / "tiles-latest.log"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _has_any_log_link(stable: Path, latest: Path) -> bool:
    return stable.exists() or latest.exists()


def main():
    """Main entry point - show log locations and viewing commands."""

    print()
    print("Log Locations")
    print("=" * 60)
    print()

    # Show canonical log locations (even if missing)
    print("  API Service:")
    print(f"    Stable: {_rel(API_STABLE_LOG)}")
    print(f"    Latest: {_rel(API_LATEST_LOG)}")
    print()

    print("  Tile Server:")
    print(f"    Stable: {_rel(TILES_STABLE_LOG)}")
    print(f"    Latest: {_rel(TILES_LATEST_LOG)}")
    print()

    # Provide quick viewing commands
    print("Quick View (copy/paste)")
    print("-" * 60)
    print()
    print(f"  # API logs (last 200 lines + follow):")
    print(f"  tail -n 200 -f {_rel(API_STABLE_LOG)}")
    print()
    print(f"  # Tile server logs (last 200 lines + follow):")
    print(f"  tail -n 200 -f {_rel(TILES_STABLE_LOG)}")
    print()

    # If logs don't exist, suggest starting services
    api_missing = not _has_any_log_link(API_STABLE_LOG, API_LATEST_LOG)
    tiles_missing = not _has_any_log_link(TILES_STABLE_LOG, TILES_LATEST_LOG)
    if api_missing or tiles_missing:
        print("If logs are missing, start services first:")
        print("-" * 60)
        print()
        if api_missing:
            print("  make api-up")
        if tiles_missing:
            print("  make tiles-up")
        print()

    # Always exit 0 (per AC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
