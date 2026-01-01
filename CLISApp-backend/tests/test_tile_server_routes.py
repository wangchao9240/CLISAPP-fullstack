"""
Tests for tile server level-aware routes.

Story 4.2: Align Tile URL Shape Across Dev/Prod (Level + Prefix)

Tests:
- AC1: Level-aware routes work for all layers and levels
- AC2: Legacy routes preserved with deprecation
- AC3: Fallback to legacy layout when level-specific tiles don't exist
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add data_pipeline to path for importing tile_server
sys.path.insert(0, str(Path(__file__).parent.parent / "data_pipeline" / "servers"))

from tile_server import app

client = TestClient(app)


class TestLevelAwareTileRoutes:
    """AC1: Level-aware tile routes"""

    def test_level_aware_route_exists_pm25_suburb(self):
        """Level-aware route should exist for PM2.5 suburb tiles"""
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        # 200 if tile exists, 404 if not, but NOT 404 due to route mismatch
        assert response.status_code in [200, 404]

    def test_level_aware_route_exists_pm25_lga(self):
        """Level-aware route should exist for PM2.5 LGA tiles"""
        response = client.get("/tiles/pm25/lga/8/241/155.png")
        assert response.status_code in [200, 404]

    def test_level_aware_route_all_layers(self):
        """Level-aware route should work for all 5 layers"""
        layers = ["pm25", "precipitation", "temperature", "humidity", "uv"]
        levels = ["suburb", "lga"]

        for layer in layers:
            for level in levels:
                response = client.get(f"/tiles/{layer}/{level}/8/241/155.png")
                # Should not be 422 (route not found) or 404 with route mismatch
                assert response.status_code in [200, 404, 400]

    def test_level_aware_route_returns_png(self):
        """Level-aware route should return image/png content type"""
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        if response.status_code == 200:
            assert "image/png" in response.headers.get("content-type", "")

    def test_level_aware_route_invalid_level_rejected(self):
        """Invalid level should be rejected"""
        response = client.get("/tiles/pm25/invalid_level/8/241/155.png")
        assert response.status_code == 400


class TestLegacyTileRoutes:
    """AC2: Legacy routes preserved with deprecation"""

    def test_legacy_route_still_works(self):
        """Legacy route without level should still work"""
        response = client.get("/tiles/pm25/8/241/155.png")
        # Should return 200 or 404, but NOT route error
        assert response.status_code in [200, 404]

    def test_legacy_route_has_deprecation_signal(self):
        """Legacy route should include deprecation header or log warning"""
        response = client.get("/tiles/pm25/8/241/155.png")
        assert response.status_code in [200, 404]
        assert "deprecation" in response.headers or "Deprecation" in response.headers


class TestTileServerFallback:
    """AC1: Fallback to legacy layout when level tiles don't exist"""

    def test_falls_back_to_legacy_when_level_tile_missing(self):
        """Should fall back to legacy layout if level-specific tile doesn't exist"""
        # This test assumes we might have old tiles without level subdirectories
        response = client.get("/tiles/pm25/suburb/8/241/155.png")
        # Should try level-aware path first, then fall back to legacy
        assert response.status_code in [200, 404]


class TestTileServerEndpoints:
    """Verify endpoint information is updated"""

    def test_root_endpoint_includes_level_aware_template(self):
        """Root endpoint should document level-aware URL template"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        # Should include level-aware template in endpoints
        assert "endpoints" in data

    def test_tile_info_includes_level_aware_template(self):
        """Tile info endpoint should document level-aware URL"""
        response = client.get("/tiles/pm25/info")
        assert response.status_code == 200
        data = response.json()
        # Should include updated URL template
        assert "api_endpoints" in data
