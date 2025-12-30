"""
Health Check API Endpoints
Basic health monitoring for the CLISApp backend
"""

from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings
import os
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": settings.app_name,
        "version": settings.app_version
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information"""
    
    # Check Redis connection
    redis_status = "unknown"
    if REDIS_AVAILABLE:
        try:
            r = redis.from_url(settings.redis_url)
            r.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
    else:
        redis_status = "not_installed"
    
    # Check data directories
    data_dirs = {}
    for name, path in {
        "data_root": settings.data_root,
        "downloads": settings.downloads_path,
        "tiles": settings.tiles_path,
        "processing": settings.processing_path
    }.items():
        data_dirs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "writable": path.exists() and os.access(path, os.W_OK)
        }
    
    # System information
    system_info = {}
    if PSUTIL_AVAILABLE:
        try:
            system_info = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent
            }
        except Exception:
            system_info = {"error": "failed_to_get_system_info"}
    else:
        system_info = {"status": "psutil_not_installed"}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": settings.app_name,
        "version": settings.app_version,
        "redis": redis_status,
        "data_directories": data_dirs,
        "system": system_info,
        "configuration": {
            "debug": settings.debug,
            "min_zoom": settings.min_zoom,
            "max_zoom": settings.max_zoom,
            "tile_size": settings.tile_size,
            "tile_format": settings.tile_format
        }
    }
