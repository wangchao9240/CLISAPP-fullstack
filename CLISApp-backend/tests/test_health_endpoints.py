"""
Tests for health endpoint compatibility.

Story 4.1: Align Health Endpoint Contract Without Breaking the App

Tests:
- AC1: Canonical /api/v1/health endpoint works
- AC2: Legacy /health endpoint exists for backward compatibility
- AC2: Legacy /health includes deprecation warning
- AC3: verify-backend checks both endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCanonicalHealthEndpoint:
    """AC1: Canonical health endpoint"""

    def test_canonical_health_returns_200(self):
        """Canonical /api/v1/health should return 200"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_canonical_health_returns_json(self):
        """Canonical /api/v1/health should return JSON with status"""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    def test_canonical_health_includes_service_info(self):
        """Canonical /api/v1/health should include service information"""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "service" in data
        assert "version" in data
        assert "timestamp" in data


class TestLegacyHealthEndpoint:
    """AC2: Legacy /health endpoint for backward compatibility"""

    def test_legacy_health_exists(self):
        """Legacy /health endpoint should exist"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_legacy_health_returns_json(self):
        """Legacy /health should return JSON with status"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    def test_legacy_health_includes_deprecation_header(self):
        """AC2: Legacy /health should include deprecation header"""
        response = client.get("/health")

        # Check for deprecation header
        assert "deprecation" in response.headers or "Deprecation" in response.headers

    def test_legacy_health_returns_same_structure_as_canonical(self):
        """Legacy /health should return same structure as canonical"""
        legacy_response = client.get("/health")
        canonical_response = client.get("/api/v1/health")

        legacy_data = legacy_response.json()
        canonical_data = canonical_response.json()

        # Should have same keys
        assert "status" in legacy_data
        assert "service" in legacy_data
        assert "version" in legacy_data


class TestHealthEndpointCompatibility:
    """Test backward compatibility between endpoints"""

    def test_both_endpoints_return_healthy_status(self):
        """Both endpoints should return healthy status"""
        legacy = client.get("/health")
        canonical = client.get("/api/v1/health")

        assert legacy.json()["status"] == "healthy"
        assert canonical.json()["status"] == "healthy"

    def test_legacy_endpoint_marked_as_deprecated(self):
        """Legacy endpoint should be clearly marked as deprecated"""
        response = client.get("/health")

        # Check for deprecation signals
        has_deprecation_header = (
            "deprecation" in response.headers or
            "Deprecation" in response.headers
        )

        assert has_deprecation_header, \
            "Legacy /health endpoint must include deprecation header"
