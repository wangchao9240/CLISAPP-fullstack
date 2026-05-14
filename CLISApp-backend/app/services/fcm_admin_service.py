"""Firebase Admin SDK singleton for debug-only FCM pushes."""
from __future__ import annotations

import logging
from typing import Any, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError as exc:
    firebase_admin = None
    credentials = None
    messaging = None
    _firebase_import_error: ImportError | None = exc
else:
    _firebase_import_error = None

from app.core.config import settings

logger = logging.getLogger(__name__)

_app: Optional[Any] = None


def get_app() -> Optional[Any]:
    """Return the lazily initialized Firebase Admin app, if credentials exist."""
    global _app

    if _app is not None:
        return _app

    if _firebase_import_error is not None:
        logger.warning("Firebase Admin SDK unavailable: %s", _firebase_import_error)
        return None

    cred_path = settings.firebase_credentials_path
    if not cred_path.exists():
        logger.warning("Firebase credentials not found at %s", cred_path)
        return None

    if credentials is None or firebase_admin is None:
        return None

    cred = credentials.Certificate(str(cred_path))
    _app = firebase_admin.initialize_app(cred, name="clisapp-debug")
    logger.info("Firebase Admin SDK initialized for debug FCM")
    return _app


def publish_to_topic(topic: str, title: str, body: str) -> str:
    """Publish a notification message to an FCM topic and return its message id."""
    app = get_app()
    if app is None:
        raise RuntimeError("Firebase Admin SDK not initialized")

    if messaging is None:
        raise RuntimeError("Firebase Admin SDK not initialized")

    message = messaging.Message(
        topic=topic,
        notification=messaging.Notification(title=title, body=body),
    )
    return messaging.send(message, app=app)
