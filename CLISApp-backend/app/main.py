"""
CLISApp Backend Main Application
FastAPI application entry point with API routes and middleware
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

from app.core.config import settings
from app.api.v1 import tiles, regions, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Queensland Climate Information System API",
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # DEPRECATED: Static tile mount (Phase 1 - disabled by default, Phase 2 - removed)
    # This legacy static mount creates a third tile-serving surface on :8080/tiles/*
    # which bypasses API logic and creates contract ambiguity.
    #
    # Canonical tile serving topology:
    #   - Development: Tile server on :8000 serves /tiles/{layer}/{level}/{z}/{x}/{y}.png
    #   - Production: Same topology via Render clisapp-tiles service
    #   - API on :8080 provides /api/v1/tiles/* for metadata/status/on-demand generation
    #
    # Migration path: Use dedicated tile server (:8000) for tile images
    # Removal plan: Phase 2 (after verifying no production dependencies)
    #
    # To enable this deprecated mount (NOT RECOMMENDED):
    #   Set ENABLE_LEGACY_STATIC_TILES=true in environment
    enable_static_tiles = os.environ.get("ENABLE_LEGACY_STATIC_TILES", "false").lower() == "true"

    if enable_static_tiles:
        tiles_path = Path(settings.tiles_path)
        if tiles_path.exists():
            app.mount("/tiles", StaticFiles(directory=str(tiles_path)), name="tiles")
            logger.warning(
                f"⚠️  DEPRECATED: Static tile mount enabled at /tiles (tiles_path={tiles_path}). "
                "This creates a third tile-serving surface and will be removed in Phase 2. "
                "Please migrate to dedicated tile server at :8000/tiles for tile images."
            )
        else:
            logger.warning(
                f"⚠️  DEPRECATED: Static tile mount requested but tiles_path does not exist: {tiles_path}"
            )
    else:
        logger.info(
            "Static tile mount disabled (canonical topology). "
            "Tile images served by dedicated tile server on :8000/tiles"
        )
    
    # Include API routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(tiles.router, prefix="/api/v1", tags=["tiles"])
    app.include_router(regions.router, prefix="/api/v1", tags=["regions"])

    # Legacy health endpoint for backward compatibility (Phase 1)
    # This provides compatibility with Phase 0 frontend that uses /health
    # Will be removed in Phase 2
    @app.get("/health", tags=["health"], deprecated=True)
    async def legacy_health_check():
        """
        Legacy health check endpoint (DEPRECATED)

        This endpoint is provided for backward compatibility with Phase 0 frontend.

        **Deprecation Notice**: This endpoint will be removed in Phase 2.
        Please use `/api/v1/health` instead.
        """
        # Log deprecation warning
        logger.warning(
            "Legacy /health endpoint accessed - this is deprecated and will be removed in Phase 2. "
            "Please use /api/v1/health instead."
        )

        # Delegate to canonical health handler to avoid code duplication
        from app.api.v1.health import health_check
        response_data = await health_check()

        # Return response with deprecation headers
        from fastapi import Response
        response = Response(
            content=str(response_data),
            media_type="application/json",
            headers={
                "Deprecation": "true",
                "Link": '</api/v1/health>; rel="alternate"',
            }
        )

        # Manually serialize the response data
        import json
        from datetime import datetime

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        response_json = json.dumps(response_data, default=json_serial)

        return Response(
            content=response_json,
            media_type="application/json",
            headers={
                "Deprecation": "true",
                "Link": '</api/v1/health>; rel="alternate"',
            }
        )
    
    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks"""
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"Data root: {settings.data_root}")
        
        # Ensure data directories exist
        settings.create_data_directories()
        logger.info("Data directories initialized")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks"""
        logger.info("Shutting down CLISApp Backend")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler"""
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )
    
    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
