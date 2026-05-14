"""Endpoint tests for /api/v1/debug/fcm-test."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_debug_defaults_false_without_environment(monkeypatch):
    """Debug endpoints must be explicitly enabled for local demo use."""
    monkeypatch.delenv("DEBUG", raising=False)

    from app.core.config import Settings

    assert Settings(_env_file=None).debug is False


def test_endpoint_not_mounted_when_debug_false(monkeypatch):
    """With DEBUG=false, the router is not registered and returns 404."""
    from app.core.config import settings
    from app.main import create_application

    monkeypatch.setattr(settings, "debug", False)

    client = TestClient(create_application())
    response = client.post("/api/v1/debug/fcm-test", json={"title": "x", "body": "y"})

    assert response.status_code == 404


def test_422_on_missing_title(debug_client):
    response = debug_client.post("/api/v1/debug/fcm-test", json={"body": "y"})

    assert response.status_code == 422


def test_422_on_oversized_body(debug_client):
    response = debug_client.post(
        "/api/v1/debug/fcm-test",
        json={"title": "x", "body": "y" * 201},
    )

    assert response.status_code == 422


def test_503_when_credentials_missing(debug_client, tmp_path, monkeypatch):
    from app.core.config import settings
    import app.services.fcm_admin_service as svc

    monkeypatch.setattr(
        settings,
        "firebase_credentials_path",
        tmp_path / "missing.json",
    )
    svc._app = None

    response = debug_client.post(
        "/api/v1/debug/fcm-test",
        json={"title": "x", "body": "y"},
    )

    assert response.status_code == 503
    assert "not initialized" in response.json()["detail"].lower()


@patch("app.services.fcm_admin_service.publish_to_topic")
def test_503_when_sdk_unavailable(mock_publish, debug_client):
    mock_publish.side_effect = RuntimeError("Firebase Admin SDK unavailable")

    response = debug_client.post(
        "/api/v1/debug/fcm-test",
        json={"title": "x", "body": "y"},
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


@patch("app.services.fcm_admin_service.publish_to_topic")
def test_200_publishes_with_correct_args(mock_publish, debug_client):
    mock_publish.return_value = "msg-id-abc"

    response = debug_client.post(
        "/api/v1/debug/fcm-test",
        json={"title": "Heat", "body": "Stay indoors"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["message_id"] == "msg-id-abc"
    mock_publish.assert_called_once_with("qld-health-alerts", "Heat", "Stay indoors")


@patch("app.services.fcm_admin_service.publish_to_topic")
def test_500_when_publish_fails(mock_publish, debug_client):
    mock_publish.side_effect = ValueError("send failed")

    response = debug_client.post(
        "/api/v1/debug/fcm-test",
        json={"title": "Heat", "body": "Stay indoors"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "FCM publish failed"
