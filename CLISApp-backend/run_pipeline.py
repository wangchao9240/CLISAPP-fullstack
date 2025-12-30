"""
CLISApp Data Pipeline Orchestrator
Runs the full pipeline: Fetch -> Interpolate -> Generate Tiles
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from data_pipeline.config import grid_config
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.processing.common.interpolate_to_raster import RasterInterpolator
from data_pipeline.processing.common.generate_tiles import PM25TileGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline():
    logger.info("=== Starting CLISApp Data Pipeline ===")
    
    # 1. Fetch Data
    logger.info("--- Step 1: Fetching Data ---")
    
    # Use a smaller subset for testing if needed, or full grid
    grid_points = grid_config.GRID_POINTS
    
    # Fetch and cache (TTL 1 hour)
    async with OpenMeteoFetcher() as fetcher:
        data_map = await fetcher.fetch_and_cache(grid_points, ttl=3600)
    
    if not data_map:
        logger.error("Failed to fetch data. Aborting.")
        return
        
    # Convert dict map to list of points for interpolator
    points_list = list(data_map.values())
    logger.info(f"Fetched {len(points_list)} data points.")
    
    # 2. Interpolate to Raster
    logger.info("--- Step 2: Interpolating to Raster ---")
    interpolator = RasterInterpolator(resolution=0.05) # 0.05 deg ~= 5km
    
    layers = ['temperature', 'humidity', 'precipitation', 'uv_index', 'pm25']
    # Map internal keys to layer names expected by tile generator
    layer_mapping = {
        'temperature': 'temperature',
        'humidity': 'humidity',
        'precipitation': 'precipitation',
        'uv_index': 'uv',
        'pm25': 'pm25'
    }
    
    processed_rasters = {}
    
    for key in layers:
        layer_name = layer_mapping.get(key, key)
        output_tif = Path(f"data/processed/{layer_name}_latest.tif")
        
        success = interpolator.interpolate_to_tif(
            points_list, 
            key, 
            output_tif, 
            method='linear' if key != 'precipitation' else 'nearest' # Precip can be sparse
        )
        
        if success:
            processed_rasters[layer_name] = output_tif
            
    # 3. Generate Tiles
    logger.info("--- Step 3: Generating Tiles ---")
    output_tiles_dir = Path("tiles")
    
    for layer_name, tif_path in processed_rasters.items():
        logger.info(f"Generating tiles for {layer_name}...")
        try:
            generator = PM25TileGenerator(
                str(tif_path),
                output_dir=str(output_tiles_dir),
                layer_name=layer_name,
                zoom_levels=[6, 7, 8, 9, 10, 11, 12] # Adjust zooms as needed
            )
            generator.generate_all_tiles()
        except Exception as e:
            logger.error(f"Failed to generate tiles for {layer_name}: {e}")
            
    logger.info("=== Pipeline Complete ===")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
