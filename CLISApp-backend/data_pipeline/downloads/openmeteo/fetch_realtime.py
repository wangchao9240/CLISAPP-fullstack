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
- Support for weather + air quality endpoints
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class OpenMeteoFetcher:
    """Fetches climate data from Open-Meteo API."""

    # API endpoints
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    # Batch settings
    BATCH_SIZE = 300  # Number of coordinates per API call
    MAX_CONCURRENT_REQUESTS = 5  # Concurrent API calls
    REQUEST_TIMEOUT = 30  # Seconds
    BASE_DELAY = 3.0
    MAX_DELAY = 30.0
    JITTER_FACTOR = 0.2

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
        wait=wait_exponential(multiplier=2, min=8, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
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
            "timezone": self.TIMEZONE,
            "forecast_days": 1  # Only get today's data
        }

        logger.debug(f"Fetching weather for {len(latitudes)} points")

        response = await self.session.get(self.WEATHER_URL, params=params)
        if response.status_code == 429 or response.status_code >= 500:
            response.raise_for_status()
        elif response.status_code >= 400:
            logger.error(f"Non-retryable error {response.status_code}: {response.text[:200]}")
            return None

        return response.json()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=8, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _fetch_air_quality_batch(
        self,
        latitudes: List[float],
        longitudes: List[float]
    ) -> Dict[str, Any]:
        """
        Fetch air quality data for a batch of coordinates.

        Args:
            latitudes: List of latitude values
            longitudes: List of longitude values

        Returns:
            JSON response from Open-Meteo Air Quality API

        Raises:
            httpx.HTTPError: If the API request fails
        """
        lat_str = ",".join(str(lat) for lat in latitudes)
        lon_str = ",".join(str(lon) for lon in longitudes)

        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "current": "pm2_5",
            "timezone": self.TIMEZONE,
        }

        logger.debug(f"Fetching air quality for {len(latitudes)} points")

        response = await self.session.get(self.AIR_QUALITY_URL, params=params)
        if response.status_code == 429 or response.status_code >= 500:
            response.raise_for_status()
        elif response.status_code >= 400:
            logger.error(f"Non-retryable error {response.status_code}: {response.text[:200]}")
            return None

        return response.json()

    async def _process_batch(
        self,
        batch: List[Dict[str, float]],
        all_data: Dict[str, Dict],
        error_counts: Dict[str, int],
    ) -> bool:
        """Process a single batch: fetch weather then air quality sequentially."""
        try:
            lats = [p["latitude"] for p in batch]
            lons = [p["longitude"] for p in batch]

            # Sequential requests to avoid burst (not parallel gather)
            weather_data = await self._fetch_weather_batch(lats, lons)
            await asyncio.sleep(0.5)  # Brief pause between endpoints
            air_quality_data = await self._fetch_air_quality_batch(lats, lons)

            if weather_data is None or air_quality_data is None:
                error_counts["other"] += 1
                return False

            timestamp = datetime.now(timezone.utc).isoformat()

            if isinstance(weather_data, list) or isinstance(air_quality_data, list):
                for idx, point in enumerate(batch):
                    if isinstance(weather_data, list):
                        if idx >= len(weather_data):
                            continue
                        location_weather = weather_data[idx]
                    else:
                        location_weather = weather_data

                    if isinstance(air_quality_data, list):
                        if idx >= len(air_quality_data):
                            continue
                        location_air_quality = air_quality_data[idx]
                    else:
                        location_air_quality = air_quality_data

                    key = f"{point['latitude']}:{point['longitude']}"
                    all_data[key] = {
                        "latitude": point["latitude"],
                        "longitude": point["longitude"],
                        "temperature": location_weather.get("current", {}).get("temperature_2m"),
                        "humidity": location_weather.get("current", {}).get("relative_humidity_2m"),
                        "precipitation": location_weather.get("current", {}).get("precipitation", 0.0),
                        "uv_index": location_weather.get("current", {}).get("uv_index", 0.0),
                        "pm25": location_air_quality.get("current", {}).get("pm2_5"),
                        "timestamp": timestamp,
                        "source": "open-meteo",
                    }
            else:
                point = batch[0]
                key = f"{point['latitude']}:{point['longitude']}"
                all_data[key] = {
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "temperature": weather_data.get("current", {}).get("temperature_2m"),
                    "humidity": weather_data.get("current", {}).get("relative_humidity_2m"),
                    "precipitation": weather_data.get("current", {}).get("precipitation", 0.0),
                    "uv_index": weather_data.get("current", {}).get("uv_index", 0.0),
                    "pm25": air_quality_data.get("current", {}).get("pm2_5"),
                    "timestamp": timestamp,
                    "source": "open-meteo",
                }
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                error_counts["429"] += 1
                logger.warning("Rate limited (429) on batch")
            elif e.response.status_code >= 500:
                error_counts["5xx"] += 1
                logger.warning(f"Server error ({e.response.status_code}) on batch")
            else:
                error_counts["other"] += 1
                logger.error(f"HTTP error ({e.response.status_code}) on batch")
            return False
        except httpx.TimeoutException:
            error_counts["timeout"] += 1
            logger.warning("Timeout on batch")
            return False
        except Exception as e:
            error_counts["other"] += 1
            logger.error(f"Unexpected error on batch: {e}", exc_info=True)
            return False

    async def fetch_all_data(self, grid_points: List[Dict[str, float]]) -> Dict[str, Dict]:
        """
        Fetch all climate data for Queensland grid points.

        Args:
            grid_points: List of dicts with 'latitude' and 'longitude' keys

        Returns:
            Dictionary mapping "lat:lon" to climate data dict
        """
        logger.info(f"Fetching data for {len(grid_points)} grid points")

        all_data = {}
        failed_batches = []
        error_counts = {"429": 0, "5xx": 0, "other": 0, "timeout": 0}
        current_delay = self.BASE_DELAY
        total_batches = (len(grid_points) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        for batch_idx in range(0, len(grid_points), self.BATCH_SIZE):
            batch = grid_points[batch_idx:batch_idx + self.BATCH_SIZE]
            batch_num = batch_idx // self.BATCH_SIZE + 1

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} points)")

            success = await self._process_batch(batch, all_data, error_counts)
            if not success:
                failed_batches.append(batch)

            # Adaptive delay with jitter
            jitter = current_delay * self.JITTER_FACTOR * (2 * random.random() - 1)
            await asyncio.sleep(current_delay + jitter)

            # Adjust delay based on errors
            if error_counts["429"] > 0:
                current_delay = min(current_delay * 2, self.MAX_DELAY)
                error_counts["429"] = 0  # Reset after adjusting
            else:
                current_delay = max(current_delay * 0.9, self.BASE_DELAY)

        # Retry failed batches after cooldown
        if failed_batches:
            logger.warning(f"Retrying {len(failed_batches)} failed batches after 30s cooldown")
            await asyncio.sleep(30.0)
            for i, batch in enumerate(failed_batches):
                logger.info(f"Retry batch {i+1}/{len(failed_batches)}")
                await self._process_batch(batch, all_data, error_counts)
                await asyncio.sleep(self.BASE_DELAY)

        logger.info(f"Successfully fetched data for {len(all_data)}/{len(grid_points)} points")
        logger.info(f"Error summary: {error_counts}")
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
