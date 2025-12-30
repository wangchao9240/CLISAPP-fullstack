"""
Tile Service
Handles tile generation, caching, and serving for climate data visualization
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.core.config import settings
from app.models.climate import ClimateLayer, MapLevel, TileMetadata

logger = logging.getLogger(__name__)


class TileService:
    """Service for managing map tiles"""
    
    def __init__(self):
        self.tiles_path = settings.tiles_path
        
    async def generate_tile(
        self, 
        layer: str, 
        level: str, 
        z: int, 
        x: int, 
        y: int, 
        format: str = "png"
    ) -> Optional[Path]:
        """
        Generate a single tile on demand
        
        Args:
            layer: Climate data layer
            level: Geographic level (lga/suburb)
            z: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
            format: Image format
            
        Returns:
            Path to generated tile or None if generation failed
        """
        
        # Create tile directory structure
        tile_dir = self.tiles_path / layer / level / str(z) / str(x)
        tile_dir.mkdir(parents=True, exist_ok=True)
        
        tile_path = tile_dir / f"{y}.{format}"
        
        # For now, create a placeholder tile
        # TODO: Implement actual tile generation from satellite data
        success = await self._create_placeholder_tile(tile_path, layer, z, x, y)
        
        return tile_path if success else None
    
    async def generate_tile_set(
        self, 
        layer: str, 
        level: str, 
        min_zoom: int, 
        max_zoom: int
    ) -> Dict[str, Any]:
        """
        Generate a complete set of tiles for a layer/level combination
        
        Args:
            layer: Climate data layer
            level: Geographic level
            min_zoom: Minimum zoom level
            max_zoom: Maximum zoom level
            
        Returns:
            Generation statistics
        """
        
        start_time = time.time()
        tiles_generated = 0
        
        logger.info(f"Starting tile generation for {layer}/{level}, zoom {min_zoom}-{max_zoom}")
        
        # Calculate Queensland tile bounds for each zoom level
        for z in range(min_zoom, max_zoom + 1):
            # Queensland approximate bounds at different zoom levels
            bounds = self._calculate_tile_bounds(z)
            
            for x in range(bounds['min_x'], bounds['max_x'] + 1):
                for y in range(bounds['min_y'], bounds['max_y'] + 1):
                    tile_path = await self.generate_tile(layer, level, z, x, y)
                    if tile_path:
                        tiles_generated += 1
        
        generation_time = time.time() - start_time
        
        logger.info(f"Generated {tiles_generated} tiles in {generation_time:.2f} seconds")
        
        return {
            "tiles_generated": tiles_generated,
            "generation_time": generation_time
        }
    
    async def get_layer_metadata(self, layer: str, level: str) -> Optional[TileMetadata]:
        """
        Get metadata for a specific layer/level combination
        
        Args:
            layer: Climate data layer
            level: Geographic level
            
        Returns:
            Layer metadata or None if not found
        """
        
        layer_path = self.tiles_path / layer / level
        
        if not layer_path.exists():
            return None
        
        # Count tiles and calculate size
        tile_count = 0
        total_size = 0
        last_modified = None
        
        for tile_file in layer_path.rglob("*.png"):
            tile_count += 1
            stat = tile_file.stat()
            total_size += stat.st_size
            if last_modified is None or stat.st_mtime > last_modified:
                last_modified = stat.st_mtime
        
        return TileMetadata(
            layer=ClimateLayer(layer),
            level=MapLevel(level),
            bounds=settings.queensland_bounds,
            zoom_levels={"min": settings.min_zoom, "max": settings.max_zoom},
            tile_count=tile_count,
            last_updated=datetime.fromtimestamp(last_modified) if last_modified else None,
            file_size_mb=total_size / (1024 * 1024)
        )
    
    async def get_tiles_status(self) -> Dict[str, Any]:
        """
        Get status of all available tiles
        
        Returns:
            Summary of tile availability and statistics
        """
        
        status = {
            "layers": {},
            "total_size_mb": 0,
            "last_updated": None
        }
        
        if not self.tiles_path.exists():
            return status
        
        for layer_dir in self.tiles_path.iterdir():
            if layer_dir.is_dir():
                layer_name = layer_dir.name
                status["layers"][layer_name] = {}
                
                for level_dir in layer_dir.iterdir():
                    if level_dir.is_dir():
                        level_name = level_dir.name
                        metadata = await self.get_layer_metadata(layer_name, level_name)
                        
                        if metadata:
                            status["layers"][layer_name][level_name] = {
                                "tile_count": metadata.tile_count,
                                "size_mb": metadata.file_size_mb,
                                "last_updated": metadata.last_updated
                            }
                            
                            status["total_size_mb"] += metadata.file_size_mb or 0
                            
                            if (not status["last_updated"] or 
                                (metadata.last_updated and metadata.last_updated > status["last_updated"])):
                                status["last_updated"] = metadata.last_updated
        
        return status
    
    def _calculate_tile_bounds(self, zoom: int) -> Dict[str, int]:
        """
        Calculate tile bounds for Queensland at a specific zoom level
        
        Args:
            zoom: Zoom level
            
        Returns:
            Dictionary with min/max X/Y tile coordinates
        """
        
        # Queensland bounds
        north = -10.0
        south = -29.0
        east = 154.0
        west = 138.0
        
        # Convert lat/lng to tile coordinates
        import math
        
        def deg2num(lat_deg, lng_deg, zoom):
            lat_rad = math.radians(lat_deg)
            n = 2.0 ** zoom
            x = int((lng_deg + 180.0) / 360.0 * n)
            y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
            return (x, y)
        
        min_x, max_y = deg2num(south, west, zoom)
        max_x, min_y = deg2num(north, east, zoom)
        
        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y
        }
    
    async def _create_placeholder_tile(
        self, 
        tile_path: Path, 
        layer: str, 
        z: int, 
        x: int, 
        y: int
    ) -> bool:
        """
        Create a placeholder tile for development/testing
        
        Args:
            tile_path: Path where tile should be saved
            layer: Climate layer name
            z: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
            
        Returns:
            True if tile was created successfully
        """
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a 256x256 image
            img = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw grid and tile info
            draw.rectangle([0, 0, 255, 255], outline='gray', width=1)
            
            # Add tile coordinates text
            try:
                # Try to use a basic font
                font = ImageFont.load_default()
            except:
                font = None
            
            text = f"{layer}\nZ:{z} X:{x} Y:{y}"
            draw.text((10, 10), text, fill='black', font=font)
            
            # Add some color based on layer
            layer_colors = {
                'temperature': (255, 100, 100, 100),
                'precipitation': (100, 100, 255, 100),
                'pm25': (200, 100, 200, 100),
                'uv': (255, 200, 100, 100),
                'humidity': (100, 200, 200, 100)
            }
            
            color = layer_colors.get(layer, (128, 128, 128, 100))
            draw.rectangle([50, 50, 206, 206], fill=color)
            
            # Save the tile
            img.save(tile_path, 'PNG')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create placeholder tile: {e}")
            return False
