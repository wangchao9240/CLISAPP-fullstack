from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class EventType(str, Enum):
    app_start = "app_start"
    layer_change = "layer_change"
    region_search = "region_search"
    region_select = "region_select"
    map_move = "map_move"


class TelemetryEvent(BaseModel):
    event_type: EventType
    layer: Optional[str] = Field(None, max_length=50)
    region_type: Optional[str] = Field(None, max_length=50)
    zoom_level: Optional[int] = Field(None, ge=1, le=20)
    platform: Optional[str] = Field(None, max_length=20)  # "ios" or "android"
    app_version: Optional[str] = Field(None, max_length=20)


class TelemetryResponse(BaseModel):
    status: str
    event_id: int
