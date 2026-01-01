"""
Black-box tests for `make verify-backend`.

These tests validate:
- AC1: Health checks for API and tile server
- AC2: Sample tile URL verification (canonical + legacy)
- AC3: Exits non-zero when tiles unavailable
- AC4: Actionable next steps on failure
- AC5: Custom port support (API_PORT, TILES_PORT)

Uses HTTP mock servers for deterministic testing.
"""

import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# Test timeout
VERIFY_TIMEOUT = 15

# Test ports (non-conflicting with default services)
TEST_API_PORT = 28080
TEST_TILES_PORT = 28000


class MockAPIServer:
    """Mock API server for testing"""

    def __init__(self, port, healthy=True):
        self.port = port
        self.healthy = healthy
        self.server = None
        self.thread = None

    def start(self):
        handler = self._create_handler()
        self.server = http.server.HTTPServer(("localhost", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)  # Allow server to start

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _create_handler(self):
        healthy = self.healthy

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/v1/health":
                    if healthy:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "healthy"}).encode())
                    else:
                        self.send_response(503)
                        self.end_headers()
                elif self.path == "/health":
                    if healthy:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Deprecation", "true")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "healthy"}).encode())
                    else:
                        self.send_response(503)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logs

        return Handler


class MockTileServer:
    """Mock tile server for testing"""

    def __init__(self, port, tiles_available=True, canonical_ok=True, legacy_ok=True):
        self.port = port
        self.tiles_available = tiles_available
        self.canonical_ok = canonical_ok
        self.legacy_ok = legacy_ok
        self.server = None
        self.thread = None

    def start(self):
        handler = self._create_handler()
        self.server = http.server.HTTPServer(("localhost", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)  # Allow server to start

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def _create_handler(self):
        tiles_available = self.tiles_available
        canonical_ok = self.canonical_ok
        legacy_ok = self.legacy_ok

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    health_data = {
                        "status": "healthy" if tiles_available else "no_data",
                        "tiles_available": tiles_available,
                    }
                    self.wfile.write(json.dumps(health_data).encode())
                elif self.path == "/tiles/pm25/suburb/8/241/155.png":
                    if canonical_ok:
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.end_headers()
                        # Send minimal PNG (1x1 transparent pixel)
                        self.wfile.write(
                            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                        )
                    else:
                        self.send_response(404)
                        self.end_headers()
                elif self.path == "/tiles/pm25/8/241/155.png":
                    if legacy_ok:
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.end_headers()
                        # Send minimal PNG (1x1 transparent pixel)
                        self.wfile.write(
                            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                            b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                        )
                    else:
                        self.send_response(404)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logs

        return Handler


def _run_verify_backend(api_server=None, tiles_server=None):
    """Run make verify-backend with mock servers"""
    env = os.environ.copy()
    env["API_PORT"] = str(TEST_API_PORT)
    env["TILES_PORT"] = str(TEST_TILES_PORT)

    # Start mock servers if provided
    if api_server:
        api_server.start()
    if tiles_server:
        tiles_server.start()

    try:
        result = subprocess.run(
            ["make", "verify-backend"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT,
            env=env,
        )
        return result
    finally:
        if api_server:
            api_server.stop()
        if tiles_server:
            tiles_server.stop()


class TestHealthChecks:
    """AC1: Health checks for API and tile server"""

    def test_verify_backend_checks_api_health(self):
        """AC1: Should check API health endpoint"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should mention API health URL
        assert f"localhost:{TEST_API_PORT}" in output or "/api/v1/health" in output
        assert "PASS" in output or "✓" in output

    def test_verify_backend_checks_tile_health(self):
        """AC1: Should check tile server health endpoint"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should mention tiles health URL
        assert f"localhost:{TEST_TILES_PORT}" in output or "/health" in output
        assert "PASS" in output or "✓" in output

    def test_verify_backend_reports_legacy_deprecation(self):
        """AC3: Should report legacy /health as deprecated when present"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        assert "deprecat" in output.lower(), \
            f"verify-backend should report legacy /health as deprecated\nOutput: {output}"


class TestTileURLVerification:
    """AC2: Sample tile URL verification"""

    def test_verify_backend_checks_canonical_tile_url(self):
        """AC2: Should verify canonical tile URL with {level}"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should check canonical tile URL (with level: suburb)
        assert (
            "tiles/pm25/suburb/8/241/155.png" in output
            or "suburb/8/241/155" in output
        )

    def test_verify_backend_allows_canonical_missing_when_route_exists(self):
        """AC3: Canonical 404 is acceptable if route shape is correct"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=False, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        assert result.returncode == 0
        assert "404" in output or "tile missing" in output.lower()

    def test_verify_backend_checks_legacy_tile_url_if_supported(self):
        """AC2: Should check legacy tile URL without {level}"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should check legacy tile URL (without level)
        # AND mark as deprecated
        if "tiles/pm25/8/241/155.png" in output or "8/241/155" in output:
            assert "deprecat" in output.lower() or "legacy" in output.lower()


class TestTilesUnavailable:
    """AC3: Exit non-zero when tiles unavailable"""

    def test_verify_backend_exits_nonzero_when_no_tiles(self):
        """AC3: Should exit non-zero when tiles unavailable"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=False, canonical_ok=False, legacy_ok=False)

        result = _run_verify_backend(api, tiles)

        # Should exit non-zero
        assert result.returncode != 0

    def test_verify_backend_prints_pipeline_guidance_when_no_tiles(self):
        """AC3: Should suggest pipeline commands when no tiles"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=False, canonical_ok=False, legacy_ok=False)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should suggest pipeline generation
        assert "pipeline" in output.lower()
        assert "make" in output.lower()


class TestFailureGuidance:
    """AC4: Actionable next steps on failure"""

    def test_verify_backend_suggests_api_up_when_api_down(self):
        """AC4: Should suggest 'make api-up' when API is down"""
        # Don't start API server (simulate API down)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api_server=None, tiles_server=tiles)
        output = result.stdout + result.stderr

        # Should exit non-zero
        assert result.returncode != 0

        # Should suggest make api-up
        assert "make api-up" in output or "api-up" in output

    def test_verify_backend_suggests_tiles_up_when_tiles_down(self):
        """AC4: Should suggest 'make tiles-up' when tiles are down"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        # Don't start tiles server (simulate tiles down)

        result = _run_verify_backend(api_server=api, tiles_server=None)
        output = result.stdout + result.stderr

        # Should exit non-zero
        assert result.returncode != 0

        # Should suggest make tiles-up
        assert "make tiles-up" in output or "tiles-up" in output

    def test_verify_backend_suggests_make_logs_on_failure(self):
        """AC4: Should suggest 'make logs' to troubleshoot"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=False, canonical_ok=False, legacy_ok=False)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should mention logs
        assert "log" in output.lower()


class TestCustomPorts:
    """AC5: Custom port support"""

    def test_verify_backend_uses_custom_api_port(self):
        """AC5: Should use API_PORT environment variable"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should print custom port
        assert str(TEST_API_PORT) in output

    def test_verify_backend_uses_custom_tiles_port(self):
        """AC5: Should use TILES_PORT environment variable"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)
        output = result.stdout + result.stderr

        # Should print custom port
        assert str(TEST_TILES_PORT) in output


class TestSuccessCase:
    """Integration test: all healthy"""

    def test_verify_backend_exits_zero_when_all_healthy(self):
        """Should exit 0 when all checks pass"""
        api = MockAPIServer(TEST_API_PORT, healthy=True)
        tiles = MockTileServer(TEST_TILES_PORT, tiles_available=True, canonical_ok=True, legacy_ok=True)

        result = _run_verify_backend(api, tiles)

        # Should exit 0
        assert result.returncode == 0

        # Should show positive status
        output = result.stdout + result.stderr
        assert "PASS" in output or "✓" in output or "healthy" in output.lower()
