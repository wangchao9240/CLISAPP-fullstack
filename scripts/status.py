#!/usr/bin/env python3
"""
Service Status Check Script

Checks health of API and tile server services and provides actionable guidance.
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Configuration from environment
API_PORT = int(os.environ.get("API_PORT", "8080"))
TILES_PORT = int(os.environ.get("TILES_PORT", "8000"))

API_HEALTH_URL = f"http://localhost:{API_PORT}/api/v1/health"
TILES_HEALTH_URL = f"http://localhost:{TILES_PORT}/health"

# Timeout for health checks (seconds)
HEALTH_TIMEOUT = 5

# Deterministic test mode (no network / no sockets)
# STATUS_TEST_MODE=1
#   STATUS_TEST_API=healthy|down
#   STATUS_TEST_TILES=healthy|down|no_data
TEST_MODE = os.environ.get("STATUS_TEST_MODE") == "1"


def _parse_json_payload(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return None


def check_health(url, *, interpret_status=False, require_tiles_data=False):
    """
    Check if a service is healthy by requesting its health endpoint.

    interpret_status: if response is JSON with a 'status' field, use it to determine health.
    require_tiles_data: if JSON indicates tiles are unavailable (status=no_data or tiles_available=false),
                        treat as unhealthy even if HTTP 200.

    Returns: (is_healthy: bool, status_msg: str)
    """
    try:
        with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as response:
            body = response.read(10_000)
            payload = _parse_json_payload(body)

            if response.status != 200:
                return False, f"FAIL (HTTP {response.status})"

            if interpret_status and isinstance(payload, dict):
                status = str(payload.get("status", "")).strip().lower()
                tiles_available = payload.get("tiles_available")

                if require_tiles_data:
                    if status in {"no_data", "missing", "unavailable"}:
                        return False, f"FAIL ({status})"
                    if tiles_available is False:
                        return False, "FAIL (no_data)"

                if status:
                    if status in {"healthy", "ok", "pass"}:
                        return True, "PASS"
                    return False, f"FAIL ({status})"

            return True, "PASS"
    except urllib.error.URLError as e:
        return False, f"FAIL (Connection error: {e.reason})"
    except Exception as e:
        return False, f"FAIL ({e})"


def _print_free_port_action(port: int):
    print(f"    → If port {port} is busy, free it:")
    print(f"       lsof -nP -iTCP:{port} -sTCP:LISTEN")
    print("       # then stop/kill that process (or change API_PORT/TILES_PORT)")


def main():
    """Main entry point - check status of all services."""

    print()
    print("Service Status Check")
    print("=" * 60)
    print()

    # Check API health
    if TEST_MODE:
        api_mode = os.environ.get("STATUS_TEST_API", "healthy").strip().lower()
        api_healthy = api_mode in {"healthy", "ok", "pass"}
        api_status = "PASS" if api_healthy else f"FAIL ({api_mode})"
    else:
        api_healthy, api_status = check_health(API_HEALTH_URL, interpret_status=True)

    print(f"  API Service ({API_HEALTH_URL})")
    if api_healthy:
        print(f"    ✓ {api_status}")
    else:
        print(f"    ✗ {api_status}")

    print()

    # Check tiles health
    if TEST_MODE:
        tiles_mode = os.environ.get("STATUS_TEST_TILES", "healthy").strip().lower()
        tiles_healthy = tiles_mode in {"healthy", "ok", "pass"}
        tiles_status = "PASS" if tiles_healthy else f"FAIL ({tiles_mode})"
    else:
        tiles_healthy, tiles_status = check_health(
            TILES_HEALTH_URL, interpret_status=True, require_tiles_data=True
        )

    print(f"  Tile Server ({TILES_HEALTH_URL})")
    if tiles_healthy:
        print(f"    ✓ {tiles_status}")
    else:
        print(f"    ✗ {tiles_status}")

    print()

    # Provide actionable guidance if any service is down
    if not api_healthy or not tiles_healthy:
        print("Next Actions:")
        print("-" * 60)

        if not api_healthy:
            print("  API Service is down:")
            print("    → Run: make api-up")
            print("    → If that fails, run: make preflight")
            _print_free_port_action(API_PORT)
            print()

        if not tiles_healthy:
            print("  Tile Server is down:")
            print("    → Run: make tiles-up")
            _print_free_port_action(TILES_PORT)
            print("    → If tiles are missing, generate them:")
            print("       make pipeline")
            print("       make pipeline-pm25")
            print("       make pipeline-precip")
            print("       make pipeline-temp")
            print("       make pipeline-humidity")
            print("       make pipeline-uv")
            print()

        print()

        # Exit with non-zero status
        return 1

    # All services healthy
    print("✓ All services healthy")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
