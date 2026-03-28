from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute

from app.models.response import ApiError
from app.models.telemetry import (
    TelemetryCreate,
    TelemetryErrorResponse,
    TelemetryResponse,
)
from app.services import telemetry_service


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = TelemetryErrorResponse(
        error=ApiError(code=code, message=message)
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


def _format_validation_error(exc: RequestValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        if location:
            messages.append(f"{location}: {error['msg']}")
        else:
            messages.append(error["msg"])
    return "; ".join(messages)


class TelemetryValidationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Response]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except RequestValidationError as exc:
                return _error_response(
                    status_code=422,
                    code="TELEMETRY_INVALID_FORMAT",
                    message=_format_validation_error(exc),
                )

        return custom_route_handler


router = APIRouter(route_class=TelemetryValidationRoute)


@router.post(
    "/telemetry",
    response_model=TelemetryResponse,
    status_code=201,
    responses={
        422: {"model": TelemetryErrorResponse},
        429: {"model": TelemetryErrorResponse},
    },
)
async def record_event(event: TelemetryCreate):
    if telemetry_service.is_rate_limited(event.device_id):
        return _error_response(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded: max 5 requests per minute per device",
        )

    created = await run_in_threadpool(telemetry_service.insert_telemetry, event)
    return TelemetryResponse(data=created)
