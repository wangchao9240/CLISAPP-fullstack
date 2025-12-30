"""
Real-time climate data fetcher from Open-Meteo API.

This module fetches current and forecast weather/air quality data from Open-Meteo
for all grid points across Queensland. Data is fetched in batches to respect
API rate limits and URL length constraints.

Open-Meteo API Documentation:
- Weather: https://open-meteo.com/en/docs
- Air Quality: https://open-meteo.com/en/docs/air-quality-api

Features:
- Batch fetching for multiple coordinates
- Automatic retry on failure (with exponential backoff for rate limits)
- Redis caching
- Support for both current and hourly forecast data
- Integration with CAMS Global Model for PM2.5 (Plan B)
"""

from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OpenMeteoFetcher:
    """Fetches climate data from Open-Meteo API."""

    # API endpoints
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    AIR_QUALITY_URL = "https://api.open-meteo.com/v1/air-quality"

    # Batch settings
    BATCH_SIZE = 100  # Number of coordinates per API call
    MAX_CONCURRENT_REQUESTS = 5  # Concurrent API calls
    REQUEST_TIMEOUT = 30  # Seconds

    # Timezone for Queensland
    TIMEZONE = "Australia/Brisbane"

    def __init__(self, cache=None):
        """
        Initialize the fetcher.

        Args:
            cache: Optional ClimateDataCache instance for caching.
        """
        self.cache = cache
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=70)
    )
    async def _fetch_weather_batch(
        self,
        latitudes: List[float],
        longitudes: List[float]
    ) -> Dict[str, Any]:
        """
        Fetch weather data for a batch of coordinates.

        Args:
            latitudes: List of latitude values
            longitudes: List of longitude values

        Returns:
            JSON response from Open-Meteo API

        Raises:
            httpx.HTTPError: If the API request fails
        """
        # Build comma-separated coordinate strings
        lat_str = ",".join(str(lat) for lat in latitudes)
        lon_str = ",".join(str(lon) for lon in longitudes)

        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "current": "temperature_2m,relative_humidity_2m,precipitation,uv_index",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,uv_index",
            "timezone": self.TIMEZONE,
            "forecast_days": 1  # Only get today's data
        }

        logger.debug(f"Fetching weather for {len(latitudes)} points")

        response = await self.session.get(self.WEATHER_URL, params=params)
        response.raise_for_status()

        return response.json()

    async def fetch_all_data(self, grid_points: List[Dict[str, float]]) -> Dict[str, Dict]:
        """
        Fetch all climate data for Queensland grid points.

        Args:
            grid_points: List of dicts with 'latitude' and 'longitude' keys

        Returns:
            Dictionary mapping "lat:lon" to climate data dict
        """
        logger.info(f"Fetching data for {len(grid_points)} grid points")

        # Fetch PM2.5 data from CAMS Global Model
        from data_pipeline.downloads.cams.fetch_pm25 import CamsPM25Fetcher
        
        pm25_values = []
        try:
            cams_fetcher = CamsPM25Fetcher()
            logger.info("Fetching PM2.5 data from CAMS Global Model...")
            # This might take a while if downloading new data
            pm25_values = cams_fetcher.get_pm25_for_grid(grid_points)
            logger.info(f"Mapped CAMS PM2.5 data for {len(pm25_values)} points")
        except Exception as e:
            logger.error(f"Failed to fetch CAMS PM2.5 data: {e}")
            pm25_values = [None] * len(grid_points)

        all_data = {}
        total_batches = (len(grid_points) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        # Process in batches
        for batch_idx in range(0, len(grid_points), self.BATCH_SIZE):
            batch = grid_points[batch_idx:batch_idx + self.BATCH_SIZE]
            batch_num = batch_idx // self.BATCH_SIZE + 1

            # Get corresponding PM2.5 values for this batch
            batch_pm25 = pm25_values[batch_idx:batch_idx + self.BATCH_SIZE]

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} points)")

            try:
                # Extract coordinates
                lats = [p["latitude"] for p in batch]
                lons = [p["longitude"] for p in batch]

                # Fetch weather only
                weather_data = await self._fetch_weather_batch(lats, lons)

                # Parse and merge data
                timestamp = datetime.now(timezone.utc).isoformat()

                # Open-Meteo returns a list when querying multiple coordinates
                if isinstance(weather_data, list):
                    # Multiple locations as a list
                    for idx, point in enumerate(batch):
                        if idx >= len(weather_data):
                            continue

                        key = f"{point['latitude']}:{point['longitude']}"
                        location_weather = weather_data[idx]
                        
                        # Get PM2.5 from our pre-fetched list
                        pm25_val = batch_pm25[idx] if idx < len(batch_pm25) else None

                        all_data[key] = {
                            "latitude": point["latitude"],
                            "longitude": point["longitude"],
                            "temperature": location_weather.get("current", {}).get("temperature_2m"),
                            "humidity": location_weather.get("current", {}).get("relative_humidity_2m"),
                            "precipitation": location_weather.get("current", {}).get("precipitation", 0.0),
                            "uv_index": location_weather.get("current", {}).get("uv_index", 0.0),
                            "pm25": pm25_val,
                            "timestamp": timestamp,
                            "source": "open-meteo+cams"
                        }
                else:
                    # Single location
                    point = batch[0]
                    key = f"{point['latitude']}:{point['longitude']}"
                    pm25_val = batch_pm25[0] if batch_pm25 else None
                    
                    all_data[key] = {
                        "latitude": point["latitude"],
                        "longitude": point["longitude"],
                        "temperature": weather_data.get("current", {}).get("temperature_2m"),
                        "humidity": weather_data.get("current", {}).get("relative_humidity_2m"),
                        "precipitation": weather_data.get("current", {}).get("precipitation", 0.0),
                        "uv_index": weather_data.get("current", {}).get("uv_index", 0.0),
                        "pm25": pm25_val,
                        "timestamp": timestamp,
                        "source": "open-meteo+cams"
                    }

                # Rate limiting - sleep longer to avoid minutely limit
                await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}", exc_info=True)
                continue

        logger.info(f"Successfully fetched data for {len(all_data)} points")
        return all_data

    async def fetch_and_cache(
        self,
        grid_points: List[Dict[str, float]],
        ttl: int = 3600
    ) -> Dict[str, Dict]:
        """
        Fetch data and cache to Redis in one operation.

        Args:
            grid_points: List of coordinate dictionaries
            ttl: Redis cache TTL in seconds

        Returns:
            Fetched climate data dictionary
        """
        data = await self.fetch_all_data(grid_points)
        
        if self.cache:
            logger.info(f"Caching {len(data)} points to Redis (TTL: {ttl}s)")
            self.cache.cache_all_points(data, ttl=ttl)
            
        return data


async def main():
    """Main function for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Import grid points
    from data_pipeline.config.grid_config import GRID_POINTS

    # Test with first 10 points
    test_points = GRID_POINTS[:10]

    logger.info(f"Testing Open-Meteo fetcher with {len(test_points)} points")

    async with OpenMeteoFetcher() as fetcher:
        data = await fetcher.fetch_all_data(test_points)

        logger.info(f"Fetched data for {len(data)} points")
        logger.info("\nSample data:")
        for key, values in list(data.items())[:3]:
            logger.info(f"\n{key}:")
            for field, value in values.items():
                logger.info(f"  {field}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
