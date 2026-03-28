from __future__ import annotations

import re
from datetime import date, time

from pydantic import BaseModel, Field, field_validator

from app.models.response import ApiError, ApiResponse

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}$")


class TelemetryCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=128)
    event_date: str
    time_of_day: str
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("device_id must be non-empty")
        return normalized

    @field_validator("event_date")
    @classmethod
    def validate_event_date(cls, value: str) -> str:
        if not DATE_PATTERN.match(value):
            raise ValueError("event_date must be YYYY-MM-DD format")
        date.fromisoformat(value)
        return value

    @field_validator("time_of_day")
    @classmethod
    def validate_time_of_day(cls, value: str) -> str:
        if not TIME_PATTERN.match(value):
            raise ValueError("time_of_day must be HH:MM:SS format")
        time.fromisoformat(value)
        return value


class TelemetryCreatedData(BaseModel):
    id: int
    created_at: str


class TelemetryResponse(ApiResponse[TelemetryCreatedData]):
    data: TelemetryCreatedData
    error: None = None


class TelemetryErrorResponse(ApiResponse[None]):
    data: None = None
    error: ApiError
