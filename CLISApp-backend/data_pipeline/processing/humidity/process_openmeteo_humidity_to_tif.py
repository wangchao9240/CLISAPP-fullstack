"""
Open-Meteo Humidity Processing Module

Fetches humidity data from Open-Meteo API and creates GeoTIFF
for the CLISApp frontend.

Advantages over MODIS:
- Instant data (no large file downloads)
- Direct Queensland coverage (no geographic filtering needed)
- Free API, no authentication required
- ~10km resolution from BOM ACCESS-G model

Pipeline:
1. Fetch relative humidity data from Open-Meteo API
2. Create 2D numpy array from grid points
3. Convert to GeoTIFF (WGS84 projection)
4. Generate PNG tiles for map rendering
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class OpenMeteoHumidityProcessor:
    """
    Process Open-Meteo humidity data to GeoTIFF.

    Much faster than MODIS - typically completes in under 10 minutes.
    """

    # Open-Meteo API settings
    API_URL = "https://api.open-meteo.com/v1/forecast"
    BATCH_SIZE = 50  # Reduced batch size to avoid rate limits

    # Queensland bounds (same as temperature processor)
    QLD_BOUNDS = (138.0, -29.0, 154.0, -10.0)  # (min_lon, min_lat, max_lon, max_lat)

    # Grid settings - 0.5° resolution for ~1200 points (faster, API-friendly)
    GRID_RESOLUTION = 0.5  # ~50km resolution

    def __init__(
        self,
        data_root: Optional[Path] = None,
        resolution: float = 0.5
    ):
        """
        Initialize Open-Meteo humidity processor.

        Args:
            data_root: Root data directory (default: ./data)
            resolution: Grid resolution in degrees (default: 0.25° ~ 25km)
        """
        self.data_root = data_root or Path("data")
        self.output_dir = self.data_root / "processing" / "humidity"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.resolution = resolution

        # Generate grid
        self._setup_grid()

        logger.info(
            f"Initialized Open-Meteo humidity processor "
            f"(resolution={resolution}°, grid={self.n_lats}x{self.n_lons}={len(self.grid_points)} points)"
        )

    def _setup_grid(self):
        """Set up the coordinate grid."""
        min_lon, min_lat, max_lon, max_lat = self.QLD_BOUNDS

        self.lats = np.arange(max_lat, min_lat - self.resolution, -self.resolution)
        self.lons = np.arange(min_lon, max_lon + self.resolution, self.resolution)

        self.n_lats = len(self.lats)
        self.n_lons = len(self.lons)

        # Generate all grid points
        self.grid_points = []
        for lat in self.lats:
            for lon in self.lons:
                self.grid_points.append({
                    "latitude": round(float(lat), 2),
                    "longitude": round(float(lon), 2)
                })

    async def _fetch_batch(
        self,
        session,
        latitudes: List[float],
        longitudes: List[float],
        max_retries: int = 3
    ) -> Optional[Dict]:
        """Fetch humidity data for a batch of coordinates with retry logic."""
        import httpx

        lat_str = ",".join(str(lat) for lat in latitudes)
        lon_str = ",".join(str(lon) for lon in longitudes)

        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "current": "relative_humidity_2m",
            "timezone": "Australia/Brisbane"
        }

        for attempt in range(max_retries):
            try:
                response = await session.get(self.API_URL, params=params, timeout=30)

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f"Batch fetch failed: {e}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"Batch fetch failed after {max_retries} attempts: {e}")
                    return None

        return None

    async def fetch_humidity_data(self) -> Optional[np.ndarray]:
        """
        Fetch humidity data from Open-Meteo API.

        Returns:
            2D numpy array of humidity values (%), or None if failed
        """
        import httpx

        logger.info(f"Fetching humidity data for {len(self.grid_points)} grid points...")

        # Initialize data array
        data = np.full((self.n_lats, self.n_lons), np.nan, dtype=np.float32)

        async with httpx.AsyncClient() as session:
            # Process in batches
            total_batches = (len(self.grid_points) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

            for batch_idx in range(0, len(self.grid_points), self.BATCH_SIZE):
                batch = self.grid_points[batch_idx:batch_idx + self.BATCH_SIZE]
                batch_num = batch_idx // self.BATCH_SIZE + 1

                lats = [p["latitude"] for p in batch]
                lons = [p["longitude"] for p in batch]

                logger.info(f"Fetching batch {batch_num}/{total_batches}...")

                result = await self._fetch_batch(session, lats, lons)

                if result:
                    # Parse response
                    if isinstance(result, list):
                        for i, point_data in enumerate(result):
                            point = batch[i]
                            humidity = point_data.get("current", {}).get("relative_humidity_2m")
                            if humidity is not None:
                                lat_idx = int((self.lats[0] - point["latitude"]) / self.resolution + 0.5)
                                lon_idx = int((point["longitude"] - self.lons[0]) / self.resolution + 0.5)
                                if 0 <= lat_idx < self.n_lats and 0 <= lon_idx < self.n_lons:
                                    data[lat_idx, lon_idx] = humidity
                    else:
                        # Single point response
                        humidity = result.get("current", {}).get("relative_humidity_2m")
                        if humidity is not None and len(batch) > 0:
                            point = batch[0]
                            lat_idx = int((self.lats[0] - point["latitude"]) / self.resolution + 0.5)
                            lon_idx = int((point["longitude"] - self.lons[0]) / self.resolution + 0.5)
                            if 0 <= lat_idx < self.n_lats and 0 <= lon_idx < self.n_lons:
                                data[lat_idx, lon_idx] = humidity

                # Rate limiting - 10 seconds between batches to avoid 429 errors
                await asyncio.sleep(10.0)

        # Check data coverage
        valid_pixels = np.count_nonzero(~np.isnan(data))
        coverage = valid_pixels / data.size * 100
        logger.info(f"Data coverage: {valid_pixels}/{data.size} pixels ({coverage:.1f}%)")

        if valid_pixels == 0:
            logger.error("No valid humidity data received")
            return None

        return data

    def save_to_geotiff(self, data: np.ndarray, output_path: Path) -> bool:
        """
        Save humidity data to GeoTIFF.

        Args:
            data: 2D numpy array of humidity values
            output_path: Output GeoTIFF path

        Returns:
            True if successful
        """
        try:
            import rasterio
            from rasterio.transform import from_bounds
            from rasterio.crs import CRS

            min_lon, min_lat, max_lon, max_lat = self.QLD_BOUNDS

            # Create transform
            transform = from_bounds(
                min_lon, min_lat, max_lon, max_lat,
                self.n_lons, self.n_lats
            )

            # Write GeoTIFF
            profile = {
                "driver": "GTiff",
                "dtype": np.float32,
                "width": self.n_lons,
                "height": self.n_lats,
                "count": 1,
                "crs": CRS.from_epsg(4326),  # WGS84
                "transform": transform,
                "nodata": np.nan,
                "compress": "lzw"
            }

            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(data.astype(np.float32), 1)
                dst.update_tags(
                    variable="relative_humidity_2m",
                    units="percent",
                    source="Open-Meteo API (BOM ACCESS-G model)",
                    creation_time=datetime.utcnow().isoformat()
                )

            logger.info(f"Saved GeoTIFF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving GeoTIFF: {e}")
            return False

    def process_full_pipeline(self) -> Optional[Path]:
        """
        Run the complete Open-Meteo humidity processing pipeline.

        Returns:
            Path to output GeoTIFF, or None if failed
        """
        logger.info("Starting Open-Meteo humidity processing pipeline")
        start_time = datetime.now()

        try:
            # Step 1: Fetch data
            logger.info("Step 1/2: Fetching humidity data from Open-Meteo...")
            data = asyncio.run(self.fetch_humidity_data())

            if data is None:
                logger.error("Failed to fetch humidity data")
                return None

            # Step 2: Save to GeoTIFF
            logger.info("Step 2/2: Saving to GeoTIFF...")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"humidity_openmeteo_{timestamp}.tif"

            if not self.save_to_geotiff(data, output_path):
                logger.error("Failed to save GeoTIFF")
                return None

            # Create symlink to latest
            latest_link = self.output_dir / "humidity_latest.tif"
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(output_path.name)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Pipeline complete in {elapsed:.1f}s: {output_path.name}")

            return output_path

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return None


def process_humidity_openmeteo(
    data_root: Optional[Path] = None,
    resolution: float = 0.5
) -> Optional[Path]:
    """
    Convenience function to process Open-Meteo humidity data.

    Args:
        data_root: Root data directory (default: ./data)
        resolution: Grid resolution in degrees (default: 0.5° ~ 50km)

    Returns:
        Path to output GeoTIFF, or None if failed
    """
    processor = OpenMeteoHumidityProcessor(
        data_root=data_root,
        resolution=resolution
    )
    return processor.process_full_pipeline()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Open-Meteo Humidity Processing Pipeline")
    print("="*60)

    result = process_humidity_openmeteo()

    if result:
        print(f"\nSuccess! Output: {result}")
    else:
        print("\nProcessing failed. Check logs for details.")
