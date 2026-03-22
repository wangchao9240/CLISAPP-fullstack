from fastapi import APIRouter, Request, HTTPException
from app.models.telemetry import TelemetryEvent, TelemetryResponse
from app.services.telemetry_service import is_rate_limited, insert_event

router = APIRouter()


@router.post("/telemetry", response_model=TelemetryResponse, status_code=201)
async def record_event(event: TelemetryEvent, request: Request):
    client_id = request.headers.get("X-Forwarded-For") or request.client.host or "unknown"

    if is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    event_id = insert_event(event)
    return TelemetryResponse(status="ok", event_id=event_id)
