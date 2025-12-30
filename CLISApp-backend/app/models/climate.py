"""
Climate Data Models
Pydantic models for climate data structures
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime
from enum import Enum


class ClimateLayer(str, Enum):
    """Available climate data layers"""
    PM25 = "pm25"
    PRECIPITATION = "precipitation"
    UV = "uv" 
    HUMIDITY = "humidity"
    TEMPERATURE = "temperature"


class MapLevel(str, Enum):
    """Geographic resolution levels"""
    LGA = "lga"
    SUBURB = "suburb"


class ClimateDataPoint(BaseModel):
    """Single climate data measurement"""
    layer: ClimateLayer
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    quality: Optional[str] = Field(None, description="Data quality indicator")
    category: Optional[str] = Field(None, description="Qualitative level or label")


class ClimateDataConfig(BaseModel):
    """Configuration for climate data layer"""
    name: str = Field(..., description="Human-readable layer name")
    description: str = Field(..., description="Layer description")
    unit: str = Field(..., description="Unit of measurement")
    color_scale: List[str] = Field(..., description="Hex color codes for visualization")
    thresholds: List[float] = Field(..., description="Value thresholds for color mapping")
    min_value: Optional[float] = Field(None, description="Minimum possible value")
    max_value: Optional[float] = Field(None, description="Maximum possible value")
    data_source: str = Field(..., description="Original data source")
    update_frequency: str = Field(..., description="How often data is updated")


class TileMetadata(BaseModel):
    """Metadata for tile layer"""
    layer: ClimateLayer
    level: MapLevel
    bounds: Dict[str, float] = Field(..., description="Geographic bounds (north, south, east, west)")
    zoom_levels: Dict[str, int] = Field(..., description="Available zoom levels (min, max)")
    tile_count: int = Field(..., description="Total number of tiles")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    data_date: Optional[datetime] = Field(None, description="Date of source data")
    file_size_mb: Optional[float] = Field(None, description="Total size in MB")


# Climate layer configurations
CLIMATE_LAYER_CONFIGS = {
    ClimateLayer.PM25: ClimateDataConfig(
        name="PM2.5 Concentration",
        description="Particulate matter smaller than 2.5 micrometers",
        unit="µg/m³",
        color_scale=["#00ff00", "#ffff00", "#ff6600", "#ff0000", "#800080"],
        thresholds=[0, 12, 35, 55, 150],
        min_value=0,
        max_value=500,
        data_source="Copernicus CAMS",
        update_frequency="Daily"
    ),
    ClimateLayer.PRECIPITATION: ClimateDataConfig(
        name="Precipitation",
        description="Hourly precipitation rate",
        unit="mm/hour",
        color_scale=["#ffffff", "#87ceeb", "#4169e1", "#0000ff", "#00008b"],
        thresholds=[0, 0.5, 2, 10, 50],
        min_value=0,
        max_value=100,
        data_source="NASA GPM",
        update_frequency="Daily"
    ),
    ClimateLayer.UV: ClimateDataConfig(
        name="UV Index",
        description="Ultraviolet radiation index",
        unit="UVI",
        color_scale=["#289500", "#f7e400", "#f85900", "#d8001d", "#6b49c8"],
        thresholds=[0, 3, 6, 8, 11],
        min_value=0,
        max_value=15,
        data_source="Copernicus CAMS",
        update_frequency="Daily"
    ),
    ClimateLayer.HUMIDITY: ClimateDataConfig(
        name="Relative Humidity",
        description="Relative humidity percentage",
        unit="%",
        color_scale=["#8B4513", "#DAA520", "#FFD700", "#87CEEB", "#4169E1"],
        thresholds=[0, 30, 50, 70, 90],
        min_value=0,
        max_value=100,
        data_source="NASA MERRA-2",
        update_frequency="Daily"
    ),
    ClimateLayer.TEMPERATURE: ClimateDataConfig(
        name="2m Temperature",
        description="Air temperature at 2 meters above ground",
        unit="°C",
        color_scale=["#0000ff", "#87ceeb", "#ffff00", "#ff6600", "#ff0000"],
        thresholds=[0, 10, 20, 30, 40],
        min_value=-20,
        max_value=50,
        data_source="NASA MERRA-2",
        update_frequency="Daily"
    )
}
