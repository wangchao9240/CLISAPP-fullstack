"""
Region Data Models
Pydantic models for geographic region data
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime
from app.models.climate import ClimateDataPoint


class Coordinate(BaseModel):
    """Geographic coordinate"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class Bounds(BaseModel):
    """Geographic bounding box"""
    northeast: Coordinate
    southwest: Coordinate
    
    @property
    def center(self) -> Coordinate:
        """Calculate center point of bounds"""
        lat = (self.northeast.latitude + self.southwest.latitude) / 2
        lng = (self.northeast.longitude + self.southwest.longitude) / 2
        return Coordinate(latitude=lat, longitude=lng)


class RegionSearchResult(BaseModel):
    """Search result for region queries"""
    id: str = Field(..., description="Unique region identifier")
    name: str = Field(..., description="Region name")
    type: Literal["lga", "suburb"] = Field(..., description="Region type")
    state: str = Field(..., description="State/territory abbreviation")
    location: Coordinate = Field(..., description="Center coordinate")
    population: Optional[int] = Field(None, description="Population count")
    area_km2: Optional[float] = Field(None, description="Area in square kilometers")


class RegionResponse(BaseModel):
    """Detailed region information response"""
    id: str = Field(..., description="Unique region identifier")
    name: str = Field(..., description="Official region name")
    type: Literal["lga", "suburb"] = Field(..., description="Region type")
    state: str = Field(..., description="State/territory abbreviation") 
    
    # Geographic data
    location: Coordinate = Field(..., description="Center coordinate")
    bounds: Bounds = Field(..., description="Geographic bounds")
    area_km2: Optional[float] = Field(None, description="Area in square kilometers")
    
    # Administrative data
    parent_region: Optional[str] = Field(None, description="Parent region name (if suburb)")
    postcode: Optional[str] = Field(None, description="Primary postcode")
    
    # Demographics
    population: Optional[int] = Field(None, description="Population count")
    population_density: Optional[float] = Field(None, description="People per km²")
    
    # Climate data (if requested)
    current_climate: Optional[Dict[str, ClimateDataPoint]] = Field(
        None, 
        description="Current climate measurements by layer"
    )
    
    # Metadata
    last_updated: Optional[datetime] = Field(None, description="Data last updated")
    data_sources: Optional[List[str]] = Field(None, description="Data source references")


class RegionClimateData(BaseModel):
    """Climate data for a specific region"""
    region_id: str = Field(..., description="Region identifier")
    region_name: str = Field(..., description="Region name")
    measurements: Dict[str, ClimateDataPoint] = Field(
        ..., 
        description="Climate measurements by layer"
    )
    measurement_time: datetime = Field(..., description="When measurements were taken")
    location: Coordinate = Field(..., description="Measurement location")
    interpolation_method: Optional[str] = Field(
        None, 
        description="How values were calculated for this region"
    )


class RegionBoundary(BaseModel):
    """Region boundary geometry"""
    region_id: str = Field(..., description="Region identifier")
    name: str = Field(..., description="Region name")
    type: Literal["lga", "suburb"] = Field(..., description="Region type")
    geometry: Dict = Field(..., description="GeoJSON geometry")
    properties: Optional[Dict] = Field(None, description="Additional properties")
