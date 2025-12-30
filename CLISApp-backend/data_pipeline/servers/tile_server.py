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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CLISApp Phase 0 Tile Server",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "tiles": "/tiles/pm25/{z}/{x}/{y}.png",
            "info": "/tiles/pm25/info",
            "health": "/health",
            "test": "/tiles/pm25/test"
        },
        "documentation": {
            "openapi": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """Health check compatible with frontend HealthStatus interface"""
    from datetime import datetime
    
    tiles_exist = TILES_DIR.exists() and any(TILES_DIR.rglob("*.png"))
    total_tiles = len(list(TILES_DIR.rglob("*.png"))) if tiles_exist else 0
    
    # Calculate total size
    total_size_mb = 0
    if tiles_exist:
        total_size_mb = sum(f.stat().st_size for f in TILES_DIR.rglob("*.png")) / 1024 / 1024
    
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
        "total_size_mb": round(total_size_mb, 2),
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

@app.get("/tiles/{layer}/{z}/{x}/{y}.png")
async def get_layer_tile(layer: str, z: int, x: int, y: int):
    """Generic layer tile: layer in {pm25, humidity, uv, temperature, precipitation}"""
    allowed = {"pm25", "humidity", "uv", "temperature", "precipitation"}
    if layer not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported layer: {layer}")
    if not (1 <= z <= 18):
        raise HTTPException(status_code=400, detail="Invalid zoom")
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
    return build_tile_response(tile_path, layer, z, x, y)

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
                    tile_count = len(list(zoom_dir.rglob("*.png")))
                    tile_size = sum(f.stat().st_size for f in zoom_dir.rglob("*.png")) / 1024 / 1024
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
            "tile_url_template": "/tiles/pm25/{z}/{x}/{y}.png",
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
                    tile_count = len(list(zoom_dir.rglob("*.png")))
                    tile_size = sum(f.stat().st_size for f in zoom_dir.rglob("*.png")) / 1024 / 1024
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
            "tile_url_template": "/tiles/precipitation/{z}/{x}/{y}.png",
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
            "tile_url_template": "/tiles/pm25/{z}/{x}/{y}.png",
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
                png_files = list(zoom_dir.rglob("*.png"))
                if png_files:
                    # Take the first 3 tiles as samples
                    for png_file in png_files[:3]:
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
    if TILES_DIR.exists():
        for zoom_dir in (TILES_DIR / "pm25").iterdir():
            if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                png_files = list(zoom_dir.rglob("*.png"))
                if png_files:
                    png_file = png_files[0]
                    parts = png_file.parts
                    zoom = parts[-3]
                    x = parts[-2]
                    y = png_file.stem
                    sample_tile = f"{zoom}/{x}/{y}"
                    break
    
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
