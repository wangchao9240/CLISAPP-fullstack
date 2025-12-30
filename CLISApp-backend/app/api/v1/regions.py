"""
Regions API Endpoints
Handles geographic region data and search functionality
Supports FR-003 (Search) and FR-004 (Region Info) requirements
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Literal
from app.services.region_service import RegionService
from app.models.region import RegionResponse, RegionSearchResult

router = APIRouter()
region_service = RegionService()


@router.get("/regions/search", response_model=List[RegionSearchResult])
async def search_regions(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    type: Optional[Literal["lga", "suburb"]] = Query(None, description="Filter by region type"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """
    Search for regions by name (FR-003)
    
    Args:
        q: Search query string
        type: Optional filter by region type
        limit: Maximum number of results to return
        
    Returns:
        List of matching regions
    """
    
    try:
        results = await region_service.search_regions(q, type, limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/regions/by-coordinates", response_model=RegionResponse)
async def get_region_by_coordinates(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    include_climate_data: bool = Query(True, description="Include current climate data"),
):
    """
    Get the region that contains the provided coordinate (FR-004)
    """

    try:
        region = await region_service.get_region_by_coordinates(lat, lng, include_climate_data)
        if not region:
            raise HTTPException(status_code=404, detail="Region not found for coordinate")
        return region
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get region info: {str(e)}")


@router.get("/regions/{region_id}", response_model=RegionResponse)
async def get_region_info(
    region_id: str,
    include_climate_data: bool = Query(True, description="Include current climate data")
):
    """
    Get detailed information about a specific region (FR-004)
    """

    try:
        region = await region_service.get_region_by_id(region_id, include_climate_data)

        if not region:
            raise HTTPException(status_code=404, detail="Region not found")

        return region
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get region info: {str(e)}")


@router.get("/regions/{region_id}/climate", response_model=dict)
async def get_region_climate_data(
    region_id: str,
    layers: Optional[List[str]] = Query(None, alias="layers", description="Specific climate layers to include")
):
    """
    Get current climate data for a specific region
    """

    try:
        climate_data = await region_service.get_region_climate_data(region_id, layers)

        if not climate_data:
            raise HTTPException(status_code=404, detail="Region or climate data not found")

        return climate_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get climate data: {str(e)}")


@router.get("/regions/bounds/{level}")
async def get_level_bounds(
    level: Literal["lga", "suburb"],
    state: str = Query("QLD", description="State abbreviation (default: QLD)")
):
    """
    Get geographic bounds for all regions at a specific level
    
    Args:
        level: Geographic level (lga or suburb)
        state: State abbreviation
        
    Returns:
        List of region boundaries
    """
    
    try:
        bounds = await region_service.get_level_bounds(level, state)
        return {
            "level": level,
            "state": state,
            "count": len(bounds),
            "regions": bounds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bounds: {str(e)}")


@router.get("/regions/nearby")
async def get_nearby_regions(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    level: Literal["lga", "suburb"] = Query("lga", description="Geographic level"),
    radius_km: float = Query(10.0, ge=0.1, le=100, description="Search radius in kilometers")
):
    """
    Find regions near a specific coordinate
    
    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate
        level: Geographic level to search
        radius_km: Search radius in kilometers
        
    Returns:
        List of nearby regions
    """
    
    try:
        nearby = await region_service.get_nearby_regions(lat, lng, level, radius_km)
        return {
            "query_point": {"latitude": lat, "longitude": lng},
            "level": level,
            "radius_km": radius_km,
            "count": len(nearby),
            "regions": nearby
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find nearby regions: {str(e)}")


@router.get("/regions/{region_id}/boundary")
async def get_region_boundary(region_id: str):
    """
    Get the geographic boundary (GeoJSON) for a specific region
    
    Args:
        region_id: Unique region identifier
        
    Returns:
        GeoJSON Feature with the region's boundary geometry
    """
    
    try:
        boundary = await region_service.get_region_boundary(region_id)
        if not boundary:
            raise HTTPException(status_code=404, detail="Region boundary not found")
        return boundary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get region boundary: {str(e)}")
