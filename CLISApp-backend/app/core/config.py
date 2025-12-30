"""
CLISApp Backend Configuration
Centralized configuration management using Pydantic Settings
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Info
    app_name: str = Field(default="CLISApp Backend", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")
    
    # CORS Settings
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Data Sources
    copernicus_cds_api_key: Optional[str] = Field(default=None, env="COPERNICUS_CDS_API_KEY")
    copernicus_cds_url: str = Field(
        default="https://cds.climate.copernicus.eu/api/v2",
        env="COPERNICUS_CDS_URL"
    )
    nasa_username: Optional[str] = Field(default=None, env="NASA_USERNAME")
    nasa_password: Optional[str] = Field(default=None, env="NASA_PASSWORD")
    
    # File Paths
    data_root: Path = Field(default=Path("./data"), env="DATA_ROOT")
    downloads_path: Path = Field(default=Path("./data/downloads"), env="DOWNLOADS_PATH")
    tiles_path: Path = Field(default=Path("./data/tiles"), env="TILES_PATH")
    processing_path: Path = Field(default=Path("./data/processing"), env="PROCESSING_PATH")
    
    # Tile Generation Settings
    tile_size: int = Field(default=256, env="TILE_SIZE")
    min_zoom: int = Field(default=6, env="MIN_ZOOM")
    max_zoom: int = Field(default=12, env="MAX_ZOOM")
    tile_format: str = Field(default="png", env="TILE_FORMAT")
    
    # Cache Settings
    tile_cache_ttl: int = Field(default=3600, env="TILE_CACHE_TTL")  # 1 hour
    max_cache_size: int = Field(default=1000, env="MAX_CACHE_SIZE")  # MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directories exist
        self.create_data_directories()
    
    def create_data_directories(self):
        """Create necessary data directories if they don't exist"""
        directories = [
            self.data_root,
            self.downloads_path,
            self.tiles_path,
            self.processing_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def queensland_bounds(self) -> dict:
        """Queensland geographic bounds for data clipping"""
        return {
            "north": -10.0,
            "south": -29.0,
            "east": 154.0,
            "west": 138.0
        }


# Global settings instance
settings = Settings()
