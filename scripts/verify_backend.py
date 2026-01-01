#!/usr/bin/env python3
"""
Backend Verification Script

Runs fast smoke checks for backend services:
- API health endpoint
- Tile server health endpoint
- Sample tile URL validation (canonical + legacy)

Provides actionable next steps on failure.
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Configuration from environment
API_PORT = int(os.environ.get("API_PORT", "8080"))
TILES_PORT = int(os.environ.get("TILES_PORT", "8000"))
BACKEND_TEST_MODE = (
    os.environ.get("VERIFY_BACKEND_TEST_MODE") == "1"
    or os.environ.get("PIPELINE_TEST_MODE") == "1"
)

API_HEALTH_URL = f"http://localhost:{API_PORT}/api/v1/health"
API_LEGACY_HEALTH_URL = f"http://localhost:{API_PORT}/health"  # Legacy endpoint for backward compatibility
TILES_HEALTH_URL = f"http://localhost:{TILES_PORT}/health"

# Sample tile URLs for testing
# Canonical format (Phase 1 target): /tiles/{layer}/{level}/{z}/{x}/{y}.png
# Legacy format (Phase 0): /tiles/{layer}/{z}/{x}/{y}.png
CANONICAL_TILE_URL = f"http://localhost:{TILES_PORT}/tiles/pm25/suburb/8/241/155.png"
LEGACY_TILE_URL = f"http://localhost:{TILES_PORT}/tiles/pm25/8/241/155.png"

# Timeout for health checks (seconds)
HEALTH_TIMEOUT = 5


def _parse_json_payload(raw: bytes):
    """Parse JSON payload from HTTP response"""
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return None


def check_health(url):
    """
    Check if a service is healthy by requesting its health endpoint.

    Returns: (is_healthy: bool, status_msg: str, response_data: dict|None, headers: dict)
    """
    try:
        with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as response:
            body = response.read(10_000)
            payload = _parse_json_payload(body)
            headers = dict(response.headers)

            if response.status != 200:
                return False, f"FAIL (HTTP {response.status})", None, headers

            return True, "PASS", payload, headers
    except urllib.error.URLError as e:
        return False, f"FAIL (Connection error: {e.reason})", None, {}
    except Exception as e:
        return False, f"FAIL ({e})", None, {}


def check_tile_url(url, *, allow_404: bool = False):
    """
    Check if a tile URL can be fetched.

    Returns: (is_valid: bool, status_msg: str)
    """
    try:
        with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as response:
            if response.status == 404 and allow_404:
                return True, "PASS (HTTP 404 - tile missing)"
            if response.status != 200:
                return False, f"FAIL (HTTP {response.status})"

            # Check Content-Type
            content_type = response.headers.get("Content-Type", "")
            if "image/png" not in content_type:
                return False, f"FAIL (invalid Content-Type: {content_type})"

            # Check body is non-empty
            body = response.read(1024)  # Read first 1KB
            if not body:
                return False, "FAIL (empty response)"

            return True, "PASS"
    except urllib.error.HTTPError as e:
        if e.code == 404 and allow_404:
            return True, "PASS (HTTP 404 - tile missing)"
        return False, f"FAIL (HTTP {e.code})"
    except urllib.error.URLError as e:
        return False, f"FAIL (Connection error: {e.reason})"
    except Exception as e:
        return False, f"FAIL ({e})"


def main():
    """Main entry point - verify backend services"""

    print()
    print("Backend Verification")
    print("=" * 60)
    print()

    if BACKEND_TEST_MODE:
        print("✓ Test mode enabled (skipping live service checks)")
        print()
        return 0

    all_healthy = True
    tiles_data = None
    tile_checks_failed = False

    # Check API health (canonical endpoint)
    api_healthy, api_status, _, _ = check_health(API_HEALTH_URL)
    print(f"  API Service ({API_HEALTH_URL})")
    if api_healthy:
        print(f"    ✓ {api_status}")
    else:
        print(f"    ✗ {api_status}")
        all_healthy = False

    print()

    # Check legacy API health endpoint (Phase 1 backward compatibility)
    legacy_healthy, legacy_status, _, legacy_headers = check_health(API_LEGACY_HEALTH_URL)
    print(f"  API Service - Legacy Endpoint ({API_LEGACY_HEALTH_URL})")
    if legacy_healthy:
        # Check if endpoint includes deprecation header
        is_deprecated = (
            "deprecation" in legacy_headers or
            "Deprecation" in legacy_headers
        )
        if is_deprecated:
            print(f"    ✓ {legacy_status} (DEPRECATED - backward compatibility only)")
            print(f"       → Endpoint will be removed in Phase 2")
            print(f"       → Use {API_HEALTH_URL} instead")
        else:
            print(f"    ✓ {legacy_status}")
    else:
        # Legacy endpoint not required, but report if it exists
        print(f"    ℹ️  Not available (legacy endpoint, not required)")

    print()

    # Check tiles health
    tiles_healthy, tiles_status, tiles_data, _ = check_health(TILES_HEALTH_URL)
    print(f"  Tile Server ({TILES_HEALTH_URL})")
    if tiles_healthy:
        # Check if tiles are actually available
        if tiles_data and isinstance(tiles_data, dict):
            status = str(tiles_data.get("status", "")).strip().lower()
            tiles_available = tiles_data.get("tiles_available")

            if status in {"no_data", "missing", "unavailable"} or tiles_available is False:
                print(f"    ✗ FAIL (no_data)")
                tiles_healthy = False
                all_healthy = False
            else:
                print(f"    ✓ {tiles_status}")
        else:
            print(f"    ✓ {tiles_status}")
    else:
        print(f"    ✗ {tiles_status}")
        all_healthy = False

    print()

    # Check sample tile URLs (only if tile server is healthy)
    if tiles_healthy:
        # Try canonical URL first (Phase 1 target)
        canonical_valid, canonical_status = check_tile_url(CANONICAL_TILE_URL, allow_404=True)
        print(f"  Sample Tile (Canonical)")
        print(f"    URL: {CANONICAL_TILE_URL}")
        if canonical_valid:
            print(f"    ✓ {canonical_status}")
        else:
            print(f"    ✗ {canonical_status}")
            tile_checks_failed = True
            all_healthy = False

        print()

        # Try legacy URL as fallback
        legacy_valid, legacy_status = check_tile_url(LEGACY_TILE_URL)
        print(f"  Sample Tile (Legacy)")
        print(f"    URL: {LEGACY_TILE_URL}")
        if legacy_valid:
            print(f"    ✓ {legacy_status}")
            print(f"    ⚠  DEPRECATED but supported (migrate to canonical URL shape)")
        else:
            print(f"    ✗ {legacy_status}")
            if not canonical_valid:
                tile_checks_failed = True
                all_healthy = False
            else:
                print("    ℹ️  Legacy URL not available (deprecated path removed)")

        print()

    # Provide actionable guidance if any check failed
    if not all_healthy:
        print("Next Actions:")
        print("-" * 60)

        if not api_healthy:
            print("  API Service is down:")
            print("    → Run: make api-up")
            print("    → If that fails, run: make preflight")
            print(f"    → If port {API_PORT} is busy, free it:")
            print(f"       lsof -nP -iTCP:{API_PORT} -sTCP:LISTEN")
            print()

        if not tiles_healthy or tile_checks_failed:
            print("  Tile checks failed:")
            print("    → Run: make tiles-up")
            print(f"    → If port {TILES_PORT} is busy, free it:")
            print(f"       lsof -nP -iTCP:{TILES_PORT} -sTCP:LISTEN")
            print()

            # Check if it's a "no tiles" issue
            if tiles_data and isinstance(tiles_data, dict):
                status = str(tiles_data.get("status", "")).strip().lower()
                tiles_available = tiles_data.get("tiles_available")
                if status in {"no_data", "missing", "unavailable"} or tiles_available is False:
                    print("  Tiles are missing - generate them:")
                    print("    → Run: make pipeline")
                    print("    → Or run per-layer: make pipeline-pm25, make pipeline-precip, etc.")
                    print()
            elif tile_checks_failed:
                print("  Tiles failed to load - regenerate tiles and verify URL shape:")
                print("    → Run: make pipeline")
                print("    → Confirm tile URL shape includes /{level}/ (e.g., suburb)")
                print()

        print("  View logs for troubleshooting:")
        print("    → Run: make logs")
        print()

        # Exit with non-zero status
        return 1

    # All checks passed
    print("✓ All backend verifications passed")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
