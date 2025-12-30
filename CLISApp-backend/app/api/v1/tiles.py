"""
Tile Service API Endpoints
Serves climate data tiles for map visualization
Implements the tile server for frontend map consumption
"""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pathlib import Path
import os
from typing import Literal

from app.core.config import settings
from app.services.tile_service import TileService

router = APIRouter()
tile_service = TileService()


@router.get("/tiles/{layer}/{level}/{z}/{x}/{y}.{format}")
async def get_tile(
    layer: Literal["pm25", "precipitation", "uv", "humidity", "temperature"],
    level: Literal["lga", "suburb"],
    z: int,
    x: int,
    y: int,
    format: Literal["png", "jpg", "webp"] = "png"
):
    """
    Get a map tile for the specified layer, level, and coordinates
    
    Args:
        layer: Climate data layer (pm25, precipitation, uv, humidity, temperature)
        level: Geographic level (lga or suburb)
        z: Zoom level (6-12)
        x: Tile X coordinate
        y: Tile Y coordinate
        format: Image format (png, jpg, webp)
    
    Returns:
        Image tile as file response
    """
    
    # Validate zoom level
    if not (settings.min_zoom <= z <= settings.max_zoom):
        raise HTTPException(
            status_code=400,
            detail=f"Zoom level must be between {settings.min_zoom} and {settings.max_zoom}"
        )
    
    # Construct tile file path
    tile_path = settings.tiles_path / layer / level / str(z) / str(x) / f"{y}.{format}"
    
    # Check if tile exists
    if not tile_path.exists():
        # Try to generate tile on demand
        try:
            generated_tile = await tile_service.generate_tile(layer, level, z, x, y, format)
            if generated_tile:
                tile_path = generated_tile
            else:
                raise HTTPException(status_code=404, detail="Tile not found and cannot be generated")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")
    
    # Return tile file
    return FileResponse(
        tile_path,
        media_type=f"image/{format}",
        headers={
            "Cache-Control": f"public, max-age={settings.tile_cache_ttl}",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/tiles/{layer}/{level}/metadata")
async def get_layer_metadata(
    layer: Literal["pm25", "precipitation", "uv", "humidity", "temperature"],
    level: Literal["lga", "suburb"]
):
    """
    Get metadata for a specific layer and level combination
    
    Args:
        layer: Climate data layer
        level: Geographic level
        
    Returns:
        Layer metadata including bounds, zoom levels, and data info
    """
    
    metadata = await tile_service.get_layer_metadata(layer, level)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Layer metadata not found")
    
    return metadata


@router.post("/tiles/{layer}/{level}/generate")
async def generate_tiles(
    layer: Literal["pm25", "precipitation", "uv", "humidity", "temperature"],
    level: Literal["lga", "suburb"],
    min_zoom: int = None,
    max_zoom: int = None
):
    """
    Generate tiles for a specific layer and level
    
    Args:
        layer: Climate data layer
        level: Geographic level
        min_zoom: Minimum zoom level to generate (optional)
        max_zoom: Maximum zoom level to generate (optional)
        
    Returns:
        Generation status and summary
    """
    
    # Use default zoom levels if not specified
    min_z = min_zoom or settings.min_zoom
    max_z = max_zoom or settings.max_zoom
    
    # Validate zoom levels
    if not (settings.min_zoom <= min_z <= max_z <= settings.max_zoom):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid zoom range. Must be within {settings.min_zoom}-{settings.max_zoom}"
        )
    
    try:
        result = await tile_service.generate_tile_set(layer, level, min_z, max_z)
        return {
            "status": "success",
            "layer": layer,
            "level": level,
            "zoom_range": f"{min_z}-{max_z}",
            "tiles_generated": result.get("tiles_generated", 0),
            "generation_time": result.get("generation_time", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tiles: {str(e)}")


@router.get("/tiles/status")
async def get_tiles_status():
    """
    Get status of all available tiles
    
    Returns:
        Summary of available tiles by layer and level
    """
    
    status = await tile_service.get_tiles_status()
    return {
        "tile_directory": str(settings.tiles_path),
        "total_size_mb": status.get("total_size_mb", 0),
        "layers": status.get("layers", {}),
        "last_updated": status.get("last_updated")
    }
