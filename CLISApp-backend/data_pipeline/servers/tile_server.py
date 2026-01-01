#!/usr/bin/env python3
"""
Tile server - Phase 0 prototype
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
import logging
from pathlib import Path
from io import BytesIO
from PIL import Image
from fastapi.responses import Response
import rasterio
import math
import json
from itertools import islice

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CLISApp Phase 0 Tile Server",
    description="PM2.5 tile service prototype",
    version="0.1.0"
)

# Enable CORS support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tile directory configuration
TILES_DIR = Path("tiles")

TRANSPARENT_TILE = BytesIO()
Image.new('RGBA', (256, 256), (0, 0, 0, 0)).save(TRANSPARENT_TILE, format='PNG')
TRANSPARENT_TILE.seek(0)

ASSET_TILES = {
    "humidity": Path("tiles/humidity")
}

LAST_PLACEHOLDER = {}

def _first_png(root: Path) -> Path | None:
    try:
        return next(root.rglob("*.png"))
    except StopIteration:
        return None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CLISApp Tile Server (Phase 1)",
        "version": "0.2.0",
        "status": "running",
        "endpoints": {
            "tiles_level_aware": "/tiles/{layer}/{level}/{z}/{x}/{y}.png (canonical - Phase 1)",
            "tiles_legacy": "/tiles/{layer}/{z}/{x}/{y}.png (deprecated - Phase 0 compatibility)",
            "info": "/tiles/pm25/info",
            "health": "/health",
            "test": "/tiles/pm25/test"
        },
        "supported_layers": ["pm25", "precipitation", "temperature", "humidity", "uv"],
        "supported_levels": ["suburb", "lga"],
        "documentation": {
            "openapi": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check(include_stats: bool = False, max_files: int = 2000):
    """Health check compatible with frontend HealthStatus interface"""
    from datetime import datetime
    
    root = TILES_DIR
    sample_png = _first_png(root) if root.exists() else None
    tiles_exist = sample_png is not None

    total_tiles = None
    total_size_mb = None
    stats_truncated = None
    if include_stats and tiles_exist:
        total_tiles = 0
        total_size_bytes = 0
        stats_truncated = False

        for idx, png in enumerate(root.rglob("*.png")):
            if idx >= max_files:
                stats_truncated = True
                break
            total_tiles += 1
            try:
                total_size_bytes += png.stat().st_size
            except OSError:
                pass

        total_size_mb = round(total_size_bytes / 1024 / 1024, 2)
    
    # Return format expected by frontend
    return {
        "status": "healthy" if tiles_exist else "no_data",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "CLISApp Phase 0 Tile Server",
        "version": "0.1.0",
        # Phase 0 specific extra information
        "tiles_directory": str(TILES_DIR),
        "tiles_available": tiles_exist,
        "total_tiles": total_tiles,
        "total_size_mb": total_size_mb,
        "stats_truncated": stats_truncated,
        "stats_max_files": max_files if include_stats else None,
        "tile_format": "PNG with transparency",
        "supported_zoom_levels": "6-13"
    }

def build_tile_response(tile_path: Path, layer: str, z: int, x: int, y: int):
    if not tile_path.exists():
        # Return transparent placeholder tile to avoid white seams on frontend
        try:
            from io import BytesIO
            from PIL import Image
            buf = BytesIO()
            Image.new('RGBA', (256, 256), (0, 0, 0, 0)).save(buf, format='PNG')
            buf.seek(0)
            from fastapi.responses import Response
            return Response(content=buf.read(), media_type='image/png', headers={
                "Cache-Control": "public, max-age=300",
                "Access-Control-Allow-Origin": "*",
                "X-Tile-Info": f"Placeholder transparent tile for {layer} {z}/{x}/{y}"
            })
        except Exception:
            logger.debug(f"Tile not found: {layer} {z}/{x}/{y}")
            raise HTTPException(status_code=404, detail=f"Tile not found: {layer} {z}/{x}/{y}")
    return FileResponse(
        tile_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "X-Tile-Info": f"{layer} tile at zoom {z}, coordinate ({x}, {y})"
        }
    )

@app.get("/tiles/{layer}/{level}/{z}/{x}/{y}.png")
async def get_layer_tile_level_aware(layer: str, level: str, z: int, x: int, y: int):
    """
    Level-aware tile endpoint (Phase 1 canonical format)

    Supports both aggregation levels: 'lga' and 'suburb'
    Provides backward compatibility with Phase 0 tile layout.
    """
    allowed_layers = {"pm25", "humidity", "uv", "temperature", "precipitation"}
    allowed_levels = {"lga", "suburb"}

    if layer not in allowed_layers:
        raise HTTPException(status_code=400, detail=f"Unsupported layer: {layer}")
    if level not in allowed_levels:
        raise HTTPException(status_code=400, detail=f"Invalid level: {level}. Must be 'lga' or 'suburb'")
    if not (1 <= z <= 18):
        raise HTTPException(status_code=400, detail="Invalid zoom")

    # Try level-aware path first (Phase 1 layout)
    level_aware_path = TILES_DIR / layer / level / str(z) / str(x) / f"{y}.png"

    # Fall back to legacy layout if level-specific tile doesn't exist
    legacy_path = TILES_DIR / layer / str(z) / str(x) / f"{y}.png"

    # Prefer level-aware path, fall back to legacy
    tile_path = level_aware_path if level_aware_path.exists() else legacy_path

    # Special handling for precipitation layer (geographic bounds check)
    if not tile_path.exists() and layer == "precipitation":
        precip_tif = Path("data_pipeline/data/processed/gpm/imerg_daily_precip_qld.tif")
        if precip_tif.exists():
            with rasterio.open(precip_tif) as ds:
                bounds = ds.bounds
                lon_l = x / 2**z * 360.0 - 180.0
                lon_r = (x + 1) / 2**z * 360.0 - 180.0
                lat_t = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / 2**z))))
                lat_b = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / 2**z))))
                if not (bounds.left <= lon_r and bounds.right >= lon_l and bounds.bottom <= lat_t and bounds.top >= lat_b):
                    return Response(content=TRANSPARENT_TILE.getvalue(), media_type='image/png', headers={
                        "Cache-Control": "public, max-age=300",
                        "Access-Control-Allow-Origin": "*",
                        "X-Tile-Info": f"precomputed zero tile for {layer}/{level} {z}/{x}/{y}"
                    })

    return build_tile_response(tile_path, layer, z, x, y)


@app.get("/tiles/{layer}/{z}/{x}/{y}.png")
async def get_layer_tile_legacy(layer: str, z: int, x: int, y: int):
    """
    Legacy tile endpoint (Phase 0 format - DEPRECATED)

    Provided for backward compatibility with Phase 0 frontend.
    Defaults to 'suburb' level aggregation.

    **Deprecation Notice**: This endpoint will be removed in Phase 2.
    Please use /tiles/{layer}/{level}/{z}/{x}/{y}.png instead.
    """
    allowed = {"pm25", "humidity", "uv", "temperature", "precipitation"}
    if layer not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported layer: {layer}")
    if not (1 <= z <= 18):
        raise HTTPException(status_code=400, detail="Invalid zoom")

    # Log deprecation warning
    logger.warning(
        f"Legacy tile endpoint accessed: /tiles/{layer}/{z}/{x}/{y}.png - "
        "This is deprecated and will be removed in Phase 2. "
        f"Please use /tiles/{layer}/suburb/{z}/{x}/{y}.png instead."
    )

    tile_path = TILES_DIR / layer / str(z) / str(x) / f"{y}.png"
    if not tile_path.exists() and layer == "precipitation":
        # Check missing data within geographic bounds
        precip_tif = Path("data_pipeline/data/processed/gpm/imerg_daily_precip_qld.tif")
        if precip_tif.exists():
            with rasterio.open(precip_tif) as ds:
                bounds = ds.bounds
                lon_l = x / 2**z * 360.0 - 180.0
                lon_r = (x + 1) / 2**z * 360.0 - 180.0
                lat_t = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / 2**z))))
                lat_b = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / 2**z))))
                if not (bounds.left <= lon_r and bounds.right >= lon_l and bounds.bottom <= lat_t and bounds.top >= lat_b):
                    return Response(content=TRANSPARENT_TILE.getvalue(), media_type='image/png', headers={
                        "Cache-Control": "public, max-age=300",
                        "Access-Control-Allow-Origin": "*",
                        "X-Tile-Info": f"precomputed zero tile for {layer} {z}/{x}/{y}"
                    })
    response = build_tile_response(tile_path, layer, z, x, y)
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</tiles/{layer}/suburb/{z}/{x}/{y}.png>; rel="alternate"'
    return response

@app.get("/tiles/pm25/info")
async def get_pm25_info():
    """Retrieve PM2.5 tile metadata"""
    tiles_by_zoom = {}
    metadata_thresholds = None
    metadata_path = TILES_DIR / "pm25" / "metadata.json"
    if metadata_path.exists():
        try:
            metadata_thresholds = json.loads(metadata_path.read_text(encoding="utf-8")).get("thresholds")
        except Exception:
            logger.warning("Failed to load metadata thresholds", exc_info=True)

    if TILES_DIR.exists():
        layer_dir = TILES_DIR / "pm25"
        if layer_dir.exists():
            for zoom_dir in layer_dir.iterdir():
                if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                    zoom = int(zoom_dir.name)
                    tile_count = 0
                    total_bytes = 0
                    for f in zoom_dir.rglob("*.png"):
                        tile_count += 1
                        try:
                            total_bytes += f.stat().st_size
                        except OSError:
                            pass
                    tile_size = total_bytes / 1024 / 1024
                    tiles_by_zoom[zoom] = {
                        "count": tile_count,
                        "size_mb": round(tile_size, 2)
                    }

    data_bounds = {
        "north": -9.0,
        "south": -29.0,
        "east": 154.0,
        "west": 138.0
    }

    return {
        "data_source": "ECMWF CAMS Global Atmospheric Composition Forecasts",
        "variable": "PM2.5 Surface Concentration",
        "units": "μg/m³",
        "spatial_coverage": "Queensland, Australia",
        "spatial_resolution": "0.25 degrees (~25km)",
        "temporal_resolution": "Mean of 3-hourly forecast steps",
        "data_bounds": data_bounds,
        "zoom_levels": {
            "supported": "6-13",
            "available": list(tiles_by_zoom.keys()),
            "recommended": "8-10 for best performance"
        },
        "tile_format": {
            "format": "PNG",
            "size": "256x256 pixels",
            "transparency": "Supported (RGBA)",
            "color_scheme": {
                "thresholds": metadata_thresholds or [0, 12, 35, 55, 150],
                "colors": ["#00ff00", "#ffff00", "#ff6600", "#ff0000", "#800080"],
            }
        },
        "dynamic_thresholds": metadata_thresholds,
        "tiles_statistics": tiles_by_zoom,
        "total_tiles": sum(stats["count"] for stats in tiles_by_zoom.values()),
        "total_size_mb": round(sum(stats["size_mb"] for stats in tiles_by_zoom.values()), 2),
        "api_endpoints": {
            "tile_url_template": "/tiles/pm25/{level}/{z}/{x}/{y}.png (canonical)",
            "tile_url_template_legacy": "/tiles/pm25/{z}/{x}/{y}.png (deprecated)",
            "info": "/tiles/pm25/info",
            "test": "/tiles/pm25/test",
            "health": "/health"
        }
    }


@app.get("/tiles/precipitation/info")
async def get_precipitation_info():
    """Retrieve precipitation tile metadata"""
    tiles_by_zoom = {}
    metadata_thresholds = None
    metadata_path = TILES_DIR / "precipitation" / "metadata.json"
    if metadata_path.exists():
        try:
            metadata_thresholds = json.loads(metadata_path.read_text(encoding="utf-8")).get("thresholds")
        except Exception:
            logger.warning("Failed to load precipitation metadata thresholds", exc_info=True)

    if TILES_DIR.exists():
        layer_dir = TILES_DIR / "precipitation"
        if layer_dir.exists():
            for zoom_dir in layer_dir.iterdir():
                if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                    zoom = int(zoom_dir.name)
                    tile_count = 0
                    total_bytes = 0
                    for f in zoom_dir.rglob("*.png"):
                        tile_count += 1
                        try:
                            total_bytes += f.stat().st_size
                        except OSError:
                            pass
                    tile_size = total_bytes / 1024 / 1024
                    tiles_by_zoom[zoom] = {
                        "count": tile_count,
                        "size_mb": round(tile_size, 2)
                    }

    data_bounds = {
        "north": -9.0,
        "south": -29.0,
        "east": 154.0,
        "west": 138.0
    }

    return {
        "data_source": "NASA GPM IMERG Final",
        "variable": "Daily accumulated precipitation",
        "units": "mm",
        "spatial_coverage": "Queensland, Australia",
        "spatial_resolution": "0.1 degrees (~10km)",
        "data_bounds": data_bounds,
        "zoom_levels": {
            "supported": "6-13",
            "available": list(tiles_by_zoom.keys()),
            "recommended": "8-11 for best performance"
        },
        "tile_format": {
            "format": "PNG",
            "size": "256x256 pixels",
            "transparency": "Supported (RGBA)",
            "color_scheme": {
                "thresholds": metadata_thresholds or [0, 0.5, 2, 10, 50],
                "colors": ["#ffffff", "#87ceeb", "#4169e1", "#0000ff", "#00008b"],
            }
        },
        "dynamic_thresholds": metadata_thresholds,
        "tiles_statistics": tiles_by_zoom,
        "total_tiles": sum(stats["count"] for stats in tiles_by_zoom.values()),
        "total_size_mb": round(sum(stats["size_mb"] for stats in tiles_by_zoom.values()), 2),
        "api_endpoints": {
            "tile_url_template": "/tiles/precipitation/{level}/{z}/{x}/{y}.png (canonical)",
            "tile_url_template_legacy": "/tiles/precipitation/{z}/{x}/{y}.png (deprecated)",
            "info": "/tiles/precipitation/info",
        }
    }
    """Retrieve PM2.5 tile metadata"""
    # Aggregate tile statistics
    tiles_by_zoom = {}
    metadata_thresholds = None
    metadata_path = TILES_DIR / "pm25" / "metadata.json"
    if metadata_path.exists():
        try:
            metadata_thresholds = json.loads(metadata_path.read_text(encoding="utf-8")).get("thresholds")
        except Exception:
            logger.warning("Failed to load metadata thresholds", exc_info=True)

    if TILES_DIR.exists():
        for zoom_dir in (TILES_DIR / "pm25").iterdir():
            if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                zoom = int(zoom_dir.name)
                tile_count = len(list(zoom_dir.rglob("*.png")))
                tile_size = sum(f.stat().st_size for f in zoom_dir.rglob("*.png")) / 1024 / 1024
                tiles_by_zoom[zoom] = {
                    "count": tile_count,
                    "size_mb": round(tile_size, 2)
                }
    
    # Data bounds (Queensland)
    data_bounds = {
        "north": -9.0,
        "south": -29.0,
        "east": 154.0,
        "west": 138.0
    }
    
    return {
        "data_source": "ECMWF CAMS Global Atmospheric Composition Forecasts",
        "variable": "PM2.5 Surface Concentration",
        "units": "μg/m³",
        "spatial_coverage": "Queensland, Australia",
        "spatial_resolution": "0.25 degrees (~25km)",
        "temporal_resolution": "Mean of 3-hourly forecast steps",
        "data_bounds": data_bounds,
        "zoom_levels": {
            "supported": "6-13",
            "available": list(tiles_by_zoom.keys()),
            "recommended": "8-10 for best performance"
        },
        "tile_format": {
            "format": "PNG",
            "size": "256x256 pixels",
            "transparency": "Supported (RGBA)",
            "color_scheme": {
                "thresholds": metadata_thresholds or [0, 12, 35, 55, 150],
                "colors": ["#00ff00", "#ffff00", "#ff6600", "#ff0000", "#800080"],
            }
        },
        "dynamic_thresholds": metadata_thresholds,
        "tiles_statistics": tiles_by_zoom,
        "total_tiles": sum(stats["count"] for stats in tiles_by_zoom.values()),
        "total_size_mb": round(sum(stats["size_mb"] for stats in tiles_by_zoom.values()), 2),
        "api_endpoints": {
            "tile_url_template": "/tiles/pm25/{level}/{z}/{x}/{y}.png (canonical)",
            "tile_url_template_legacy": "/tiles/pm25/{z}/{x}/{y}.png (deprecated)",
            "info": "/tiles/pm25/info",
            "test": "/tiles/pm25/test",
            "health": "/health"
        }
    }

@app.get("/tiles/pm25/test")
async def test_tiles():
    """Test tile availability"""
    test_results = []
    
    # Test a few common tiles (around Queensland coordinates)
    test_tiles = [
        (8, 241, 155),   # Near Brisbane (zoom 8)
        (9, 482, 310),   # Near Brisbane (zoom 9) 
        (10, 964, 620),  # Near Brisbane (zoom 10)
        (7, 120, 77),    # Lower resolution
        (11, 1928, 1240), # Higher resolution
    ]
    
    for z, x, y in test_tiles:
        tile_path = TILES_DIR / "pm25" / str(z) / str(x) / f"{y}.png"
        result = {
            "tile": f"{z}/{x}/{y}",
            "url": f"/tiles/pm25/{z}/{x}/{y}.png",
            "exists": tile_path.exists(),
            "size_bytes": tile_path.stat().st_size if tile_path.exists() else 0,
            "zoom_level": z
        }
        test_results.append(result)
    
    # Gather available tile samples
    available_tiles = []
    if TILES_DIR.exists():
        for zoom_dir in sorted((TILES_DIR / "pm25").iterdir()):
            if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                zoom = int(zoom_dir.name)
                # Take the first 3 tiles as samples (avoid materializing the full file list)
                for png_file in islice(zoom_dir.rglob("*.png"), 3):
                    parts = png_file.parts
                    x = parts[-2]  # parent directory name
                    y = png_file.stem  # filename without extension
                    available_tiles.append({
                        "tile": f"{zoom}/{x}/{y}",
                        "url": f"/tiles/pm25/{zoom}/{x}/{y}.png",
                        "size_bytes": png_file.stat().st_size
                    })
    
    return {
        "test_tiles": test_results,
        "summary": {
            "total_tested": len(test_tiles),
            "available": sum(1 for r in test_results if r["exists"]),
            "success_rate": f"{sum(1 for r in test_results if r['exists']) / len(test_tiles) * 100:.1f}%"
        },
        "sample_available_tiles": available_tiles[:10],  # show only the first 10 samples
        "usage_example": {
            "javascript": "fetch('/tiles/pm25/8/241/155.png').then(response => response.blob())",
            "curl": "curl -o tile.png http://localhost:8000/tiles/pm25/8/241/155.png",
            "browser": "http://localhost:8000/tiles/pm25/8/241/155.png"
        }
    }

@app.get("/tiles/pm25/demo")
async def tile_demo():
    """Tile demo page - return simple HTML preview"""
    # Find one available tile
    sample_tile = None
    layer_dir = TILES_DIR / "pm25"
    if layer_dir.exists():
        png_file = _first_png(layer_dir)
        if png_file:
            rel = png_file.relative_to(layer_dir)
            if len(rel.parts) >= 3:
                zoom = rel.parts[0]
                x = rel.parts[1]
                y = Path(rel.parts[-1]).stem
                sample_tile = f"{zoom}/{x}/{y}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CLISApp PM2.5 Tile Demo</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .tile {{ border: 1px solid #ccc; margin: 10px; display: inline-block; }}
            .info {{ background: #f5f5f5; padding: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>🌏 CLISApp PM2.5 Tile Server Demo</h1>
        
        <div class="info">
            <h3>Server Status</h3>
            <p>✅ Tile server is running successfully!</p>
            <p>📊 Total tiles available: Check <a href="/health">/health</a></p>
            <p>📋 Detailed info: <a href="/tiles/pm25/info">/tiles/pm25/info</a></p>
        </div>
        
        {f'''
        <div class="info">
            <h3>Sample Tile</h3>
            <div class="tile">
                <img src="/tiles/pm25/{sample_tile}.png" alt="PM2.5 Tile {sample_tile}">
                <p>Tile: {sample_tile}</p>
            </div>
        </div>
        ''' if sample_tile else '<p>⚠️ No tiles available</p>'}
        
        <div class="info">
            <h3>API Endpoints</h3>
            <ul>
                <li><code>/tiles/pm25/{{z}}/{{x}}/{{y}}.png</code> - Get tile</li>
                <li><code>/tiles/pm25/info</code> - Tile metadata</li>
                <li><code>/tiles/pm25/test</code> - Test tiles</li>
                <li><code>/health</code> - Server health</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>Next Steps</h3>
            <p>🚀 This tile server is ready for Phase 1 frontend integration!</p>
            <p>📱 The React Native frontend can now use these tiles with:</p>
            <code>http://localhost:8000/tiles/pm25/{{z}}/{{x}}/{{y}}.png</code>
        </div>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)

def main():
    """Launch development server"""
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🚀 Starting CLISApp Phase 0 tile server")
    
    # Check tile directory
    if not TILES_DIR.exists():
        logger.warning(f"⚠️  Tile directory does not exist: {TILES_DIR}")
        logger.info("Please run the tile generation script first")
    else:
        total_tiles = len(list(TILES_DIR.rglob("*.png")))
        logger.info(f"📊 Found {total_tiles} tile files")
    
    # Start server
    logger.info("🌐 Server address: http://localhost:8000")
    logger.info("📋 API docs: http://localhost:8000/docs")
    logger.info("🎯 Demo page: http://localhost:8000/tiles/pm25/demo")
    
    uvicorn.run(
        "tile_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
