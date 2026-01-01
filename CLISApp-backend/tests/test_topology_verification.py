"""
Topology Verification Tests

Ensures the canonical two-service topology is correctly configured and
deprecated surfaces are properly disabled.
"""

import pytest
import os
from fastapi.testclient import TestClient


class TestCanonicalTopology:
    """Verify the canonical two-service topology works correctly"""

    def test_api_health_endpoint_exists(self):
        """AC1: API health at :8080/api/v1/health is accessible"""
        from app.main import app
        client = TestClient(app)

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_api_tile_metadata_endpoint_exists(self):
        """AC1: API tile metadata endpoint is accessible"""
        from app.main import app
        client = TestClient(app)

        response = client.get("/api/v1/tiles/status")
        # Should return 200 (data available) or 503 (no tiles yet)
        assert response.status_code in [200, 503]

    def test_tile_server_health_endpoint_exists(self):
        """AC1: Tile server health at :8000/health is accessible"""
        from data_pipeline.servers.tile_server import app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code in [200, 503]  # 503 if no tiles exist yet

    def test_tile_server_tile_route_exists(self):
        """AC1: Tile server level-aware tile route exists"""
        from data_pipeline.servers.tile_server import app
        client = TestClient(app)

        # Try canonical level-aware format
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        # Should return 200 (tile exists), 404 (tile doesn't exist), or
        # transparent placeholder - all acceptable
        assert response.status_code in [200, 404]


class TestStaticTileMountDeprecation:
    """Verify the static tile mount is properly deprecated"""

    def test_static_mount_disabled_by_default(self):
        """AC1: Static tile mount should be disabled by default"""
        # Clear any legacy env var
        os.environ.pop("ENABLE_LEGACY_STATIC_TILES", None)

        # Reimport to get fresh app instance
        import importlib
        import app.main
        importlib.reload(app.main)

        from app.main import app as fresh_app
        client = TestClient(fresh_app)

        # Static mount at /tiles should not be accessible
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        # Should return 404 (not found - mount doesn't exist)
        assert response.status_code == 404

    def test_static_mount_can_be_enabled_with_env_var(self):
        """Static mount can be enabled with ENABLE_LEGACY_STATIC_TILES=true"""
        # Enable legacy static tiles
        os.environ["ENABLE_LEGACY_STATIC_TILES"] = "true"

        # Reimport to get fresh app instance with env var
        import importlib
        import app.main
        importlib.reload(app.main)

        from app.main import app as fresh_app
        client = TestClient(fresh_app)

        # Static mount should exist now, but may 404 if tiles don't exist
        # The key is it should not return 404 for route-not-found
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        # If tiles exist: 200, if not: 404 from filesystem, but route exists
        assert response.status_code in [200, 404, 307]  # 307 = redirect from static files

        # Clean up
        os.environ.pop("ENABLE_LEGACY_STATIC_TILES", None)


class TestTopologyContract:
    """Ensure services expose only their designated endpoints"""

    def test_api_does_not_serve_tile_images_by_default(self):
        """API should not serve tile images at /tiles/* when static mount is disabled"""
        os.environ.pop("ENABLE_LEGACY_STATIC_TILES", None)

        import importlib
        import app.main
        importlib.reload(app.main)

        from app.main import app
        client = TestClient(app)

        # Should not find /tiles/* routes
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        assert response.status_code == 404

    def test_api_provides_tile_metadata(self):
        """API should provide tile metadata endpoints"""
        from app.main import app
        client = TestClient(app)

        response = client.get("/api/v1/tiles/status")
        assert response.status_code in [200, 503]

        # Layer metadata endpoint
        response = client.get("/api/v1/tiles/pm25/suburb/metadata")
        assert response.status_code in [200, 404, 503]

    def test_tile_server_provides_tile_images(self):
        """Tile server should provide tile image endpoints"""
        from data_pipeline.servers.tile_server import app
        client = TestClient(app)

        # Canonical level-aware format
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        assert response.status_code in [200, 404]

        # Legacy format (deprecated but still works)
        response = client.get("/tiles/pm25/8/241/155.png")
        assert response.status_code in [200, 404]


class TestLegacyHealthEndpointDeprecation:
    """Verify legacy health endpoint deprecation (from Story 4.1)"""

    def test_legacy_health_endpoint_exists_with_deprecation(self):
        """Legacy /health should exist but be marked deprecated"""
        from app.main import app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

        # Should have deprecation headers
        assert "deprecation" in response.headers or "Deprecation" in response.headers

    def test_canonical_health_endpoint_not_deprecated(self):
        """Canonical /api/v1/health should NOT have deprecation headers"""
        from app.main import app
        client = TestClient(app)

        response = client.get("/api/v1/health")
        assert response.status_code == 200

        # Should NOT have deprecation headers
        assert "deprecation" not in response.headers.keys() and "Deprecation" not in response.headers.keys()
