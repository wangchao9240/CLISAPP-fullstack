"""
CLISApp Backend Main Application
FastAPI application entry point with API routes and middleware
"""

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
    
    # Mount static files for tile serving
    tiles_path = Path(settings.tiles_path)
    if tiles_path.exists():
        app.mount("/tiles", StaticFiles(directory=str(tiles_path)), name="tiles")
        logger.info(f"Mounted tiles directory: {tiles_path}")
    
    # Include API routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(tiles.router, prefix="/api/v1", tags=["tiles"])
    app.include_router(regions.router, prefix="/api/v1", tags=["regions"])
    
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
