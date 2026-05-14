"""Tests for fcm_admin_service singleton."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level singleton between tests."""
    import app.services.fcm_admin_service as svc

    svc._app = None
    yield
    svc._app = None


def test_get_app_returns_none_when_credentials_missing(tmp_path, monkeypatch):
    from app.services import fcm_admin_service as svc

    missing = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(svc.settings, "firebase_credentials_path", missing)

    assert svc.get_app() is None


@patch("firebase_admin.initialize_app")
@patch("firebase_admin.credentials.Certificate")
def test_get_app_initializes_once(mock_cert, mock_init, tmp_path, monkeypatch):
    from app.services import fcm_admin_service as svc

    cred_path = tmp_path / "fake.json"
    cred_path.write_text('{"type": "service_account"}')
    monkeypatch.setattr(svc.settings, "firebase_credentials_path", cred_path)
    mock_init.return_value = MagicMock(name="firebase_app")

    a = svc.get_app()
    b = svc.get_app()

    assert a is b
    assert mock_init.call_count == 1


@patch("firebase_admin.initialize_app")
@patch("firebase_admin.credentials.Certificate")
def test_get_app_returns_none_when_sdk_unavailable(
    mock_cert,
    mock_init,
    tmp_path,
    monkeypatch,
):
    from app.services import fcm_admin_service as svc

    cred_path = tmp_path / "fake.json"
    cred_path.write_text('{"type": "service_account"}')
    monkeypatch.setattr(svc.settings, "firebase_credentials_path", cred_path)
    monkeypatch.setattr(
        svc,
        "_firebase_import_error",
        ImportError("missing"),
        raising=False,
    )

    assert svc.get_app() is None
    mock_cert.assert_not_called()
    mock_init.assert_not_called()


@patch("app.services.fcm_admin_service.messaging.send")
@patch("app.services.fcm_admin_service.get_app")
def test_publish_to_topic_forwards_args(mock_get_app, mock_send):
    from app.services import fcm_admin_service as svc

    mock_app = MagicMock(name="firebase_app")
    mock_get_app.return_value = mock_app
    mock_send.return_value = "msg-id-123"

    msg_id = svc.publish_to_topic("qld-health-alerts", "Title", "Body")

    assert msg_id == "msg-id-123"
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    sent_message = args[0]
    assert sent_message.topic == "qld-health-alerts"
    assert sent_message.notification.title == "Title"
    assert sent_message.notification.body == "Body"
    assert kwargs.get("app") is mock_app


@patch("app.services.fcm_admin_service.get_app")
def test_publish_to_topic_raises_when_app_unavailable(mock_get_app):
    from app.services import fcm_admin_service as svc

    mock_get_app.return_value = None

    with pytest.raises(RuntimeError, match="Firebase Admin SDK not initialized"):
        svc.publish_to_topic("t", "x", "y")
