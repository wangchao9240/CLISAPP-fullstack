from fastapi import APIRouter, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.models.telemetry import TelemetryEvent, TelemetryResponse
from app.services.telemetry_service import is_rate_limited, insert_event

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    """Extract a single client IP, guarding against missing request.client."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Only trust the first (leftmost) IP — set by the nearest trusted proxy
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


@router.post("/telemetry", response_model=TelemetryResponse, status_code=201)
async def record_event(event: TelemetryEvent, request: Request):
    client_id = _get_client_ip(request)

    if is_rate_limited(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    event_id = await run_in_threadpool(insert_event, event)
    return TelemetryResponse(status="ok", event_id=event_id)
