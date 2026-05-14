"""Debug-only endpoints for A5 demo support."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
import app.services.fcm_admin_service as fcm_admin_service

logger = logging.getLogger(__name__)
router = APIRouter()

HEALTH_ALERTS_TOPIC = "qld-health-alerts"


class FcmTestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=200)


class FcmTestResponse(BaseModel):
    status: str
    message_id: str


@router.post("/fcm-test", response_model=FcmTestResponse)
def fcm_test(req: FcmTestRequest) -> FcmTestResponse:
    """Publish a single FCM notification to the demo health-alerts topic."""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Debug endpoints disabled")

    try:
        message_id = fcm_admin_service.publish_to_topic(
            HEALTH_ALERTS_TOPIC,
            req.title,
            req.body,
        )
    except RuntimeError as exc:
        message = str(exc).lower()
        if "not initialized" in message or "unavailable" in message:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        logger.exception("debug-fcm publish failed")
        raise HTTPException(status_code=500, detail="FCM publish failed") from exc
    except Exception as exc:
        logger.exception("debug-fcm publish failed")
        raise HTTPException(status_code=500, detail="FCM publish failed") from exc

    logger.info(
        "debug-fcm published message_id=%s topic=%s",
        message_id,
        HEALTH_ALERTS_TOPIC,
    )
    return FcmTestResponse(status="ok", message_id=message_id)
