import asyncio
import logging
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.utils.redis_cache import ClimateDataCache
from data_pipeline.config.grid_config import GRID_POINTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache():
    logger.info("Starting Redis cache test...")
    
    # Initialize cache
    try:
        cache = ClimateDataCache()
        cache.clear_cache()
        logger.info("Cache cleared")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Ensure Redis is running on localhost:6379")
        return

    # Fetch and cache data
    logger.info("Fetching data from Open-Meteo...")
    async with OpenMeteoFetcher(cache=cache) as fetcher:
        # Use a small batch for testing, including Brisbane
        test_points = GRID_POINTS[:5] + [{'latitude': -27.47, 'longitude': 153.02}]
        data = await fetcher.fetch_and_cache(test_points, ttl=60)
        logger.info(f"Fetched and cached {len(data)} points")

    # Verify cache
    logger.info("Verifying cache...")
    cached_data = cache.get_all_points()
    logger.info(f"Retrieved {len(cached_data)} points from cache")
    
    if len(cached_data) == len(data):
        logger.info("✅ Cache count matches")
    else:
        logger.error(f"❌ Cache count mismatch: expected {len(data)}, got {len(cached_data)}")

    # Check Brisbane point
    brisbane_key = "-27.47:153.02"
    cached_point = cache.get_point_data(f"climate:current:{brisbane_key}")
    
    if cached_point:
        logger.info(f"✅ Retrieved Brisbane point: {brisbane_key}")
        for k, v in cached_point.items():
            logger.info(f"   {k}: {v}")
            
        if cached_point.get('pm25') is not None:
            logger.info(f"✅ PM2.5 data present: {cached_point['pm25']}")
        else:
            logger.warning("⚠️ PM2.5 data is None (might be too far from station?)")
    else:
        logger.error(f"❌ Failed to retrieve Brisbane point: {brisbane_key}")

    # Check update time
    last_update = cache.get_last_update()
    logger.info(f"Last update: {last_update}")

if __name__ == "__main__":
    asyncio.run(test_cache())
