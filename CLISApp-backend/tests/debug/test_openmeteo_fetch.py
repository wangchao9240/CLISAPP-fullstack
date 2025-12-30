#!/usr/bin/env python3
"""
Test script for Open-Meteo data fetcher.

This script tests the Open-Meteo API integration by fetching data
for a small subset of Queensland grid points.

Usage:
    python test_openmeteo_fetch.py [--num-points N]
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.config.grid_config import GRID_POINTS, GRID_DIMENSIONS, QLD_BOUNDS
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Open-Meteo data fetcher"
    )
    parser.add_argument(
        "--num-points",
        type=int,
        default=10,
        help="Number of grid points to test (default: 10)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


async def test_fetch(num_points: int):
    """
    Test fetching data from Open-Meteo.

    Args:
        num_points: Number of grid points to fetch
    """
    logger.info("=" * 80)
    logger.info("Open-Meteo Data Fetcher Test")
    logger.info("=" * 80)

    # Display grid information
    logger.info(f"\nQueensland Grid Configuration:")
    logger.info(f"  Bounds: {QLD_BOUNDS}")
    logger.info(f"  Dimensions: {GRID_DIMENSIONS}")
    logger.info(f"  Total Grid Points: {len(GRID_POINTS)}")

    # Select test points
    test_points = GRID_POINTS[:num_points]
    logger.info(f"\nTesting with {len(test_points)} sample points:")
    for i, point in enumerate(test_points[:5], 1):
        logger.info(f"  {i}. Lat: {point['latitude']}, Lon: {point['longitude']}")
    if len(test_points) > 5:
        logger.info(f"  ... and {len(test_points) - 5} more points")

    # Fetch data
    logger.info(f"\n{'=' * 80}")
    logger.info("Fetching data from Open-Meteo API...")
    logger.info(f"{'=' * 80}\n")

    async with OpenMeteoFetcher() as fetcher:
        try:
            data = await fetcher.fetch_all_data(test_points)

            logger.info(f"\n{'=' * 80}")
            logger.info(f"Results: Successfully fetched data for {len(data)} points")
            logger.info(f"{'=' * 80}")

            # Display sample data
            logger.info("\nSample Data (first 3 points):")
            for idx, (key, values) in enumerate(list(data.items())[:3], 1):
                logger.info(f"\n  Point {idx}: {key}")
                logger.info(f"    Latitude:      {values.get('latitude')}")
                logger.info(f"    Longitude:     {values.get('longitude')}")
                logger.info(f"    Temperature:   {values.get('temperature')} °C")
                logger.info(f"    Humidity:      {values.get('humidity')} %")
                logger.info(f"    Precipitation: {values.get('precipitation')} mm")
                logger.info(f"    UV Index:      {values.get('uv_index')}")
                logger.info(f"    PM2.5:         {values.get('pm25')} µg/m³")
                logger.info(f"    Timestamp:     {values.get('timestamp')}")

            # Validate data
            logger.info(f"\n{'=' * 80}")
            logger.info("Data Validation:")
            logger.info(f"{'=' * 80}")

            valid_points = 0
            missing_fields = {}

            for key, values in data.items():
                has_all_fields = True
                for field in ['temperature', 'humidity', 'precipitation', 'uv_index', 'pm25']:
                    if values.get(field) is None:
                        has_all_fields = False
                        missing_fields[field] = missing_fields.get(field, 0) + 1

                if has_all_fields:
                    valid_points += 1

            logger.info(f"  Valid points (all fields present): {valid_points}/{len(data)}")

            if missing_fields:
                logger.warning(f"  Missing fields detected:")
                for field, count in missing_fields.items():
                    logger.warning(f"    {field}: missing in {count} points")
            else:
                logger.info(f"  ✓ All data fields present in all points")

            # Summary statistics
            logger.info(f"\n{'=' * 80}")
            logger.info("Summary Statistics:")
            logger.info(f"{'=' * 80}")

            temps = [v['temperature'] for v in data.values() if v.get('temperature') is not None]
            humidities = [v['humidity'] for v in data.values() if v.get('humidity') is not None]
            pm25s = [v['pm25'] for v in data.values() if v.get('pm25') is not None]

            if temps:
                logger.info(f"  Temperature:   Min: {min(temps):.1f}°C, Max: {max(temps):.1f}°C, Avg: {sum(temps)/len(temps):.1f}°C")
            if humidities:
                logger.info(f"  Humidity:      Min: {min(humidities):.0f}%, Max: {max(humidities):.0f}%, Avg: {sum(humidities)/len(humidities):.0f}%")
            if pm25s:
                logger.info(f"  PM2.5:         Min: {min(pm25s):.1f}, Max: {max(pm25s):.1f}, Avg: {sum(pm25s)/len(pm25s):.1f} µg/m³")

            logger.info(f"\n{'=' * 80}")
            logger.info("✓ Test completed successfully!")
            logger.info(f"{'=' * 80}\n")

            return data

        except Exception as e:
            logger.error(f"\n{'=' * 80}")
            logger.error(f"✗ Test failed with error: {e}")
            logger.error(f"{'=' * 80}\n")
            raise


async def main():
    """Main test function."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        await test_fetch(args.num_points)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
