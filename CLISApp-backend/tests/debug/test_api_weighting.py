#!/usr/bin/env python3
"""
Test Open-Meteo API weighting for batch requests.

This script tests different batch sizes to understand how Open-Meteo
calculates weighted API calls.
"""

import asyncio
import httpx
from datetime import datetime

async def test_batch_weighting():
    """Test API call weighting with different batch sizes."""

    print("=" * 80)
    print("Open-Meteo API Weighting Test")
    print("=" * 80)
    print("\nTesting to understand how batch requests are weighted...")
    print("This will help us calculate actual daily API usage.\n")

    # Test configurations
    tests = [
        {
            "name": "Single Point",
            "coords": [{"lat": -27.47, "lon": 153.02}],
        },
        {
            "name": "10 Points",
            "coords": [{"lat": -27.0 + i*0.5, "lon": 153.0} for i in range(10)],
        },
        {
            "name": "50 Points",
            "coords": [{"lat": -27.0 + i*0.2, "lon": 153.0} for i in range(50)],
        },
        {
            "name": "100 Points (Our Batch Size)",
            "coords": [{"lat": -27.0 + i*0.1, "lon": 153.0} for i in range(100)],
        },
    ]

    async with httpx.AsyncClient(timeout=30) as client:
        for test in tests:
            coords = test["coords"]
            lats = ",".join(str(c["lat"]) for c in coords)
            lons = ",".join(str(c["lon"]) for c in coords)

            print(f"\nTest: {test['name']}")
            print(f"Coordinates: {len(coords)} points")

            # Make request
            try:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lats,
                        "longitude": lons,
                        "current": "temperature_2m,relative_humidity_2m,precipitation,uv_index",
                        "timezone": "Australia/Brisbane"
                    }
                )

                # Check response headers for rate limit info
                headers = response.headers

                print(f"  Status: {response.status_code}")
                print(f"  Response Size: {len(response.content)} bytes")

                # Look for rate limit headers
                if "X-RateLimit-Limit" in headers:
                    print(f"  Rate Limit: {headers['X-RateLimit-Limit']}")
                if "X-RateLimit-Remaining" in headers:
                    print(f"  Remaining: {headers['X-RateLimit-Remaining']}")
                if "X-RateLimit-Reset" in headers:
                    print(f"  Reset: {headers['X-RateLimit-Reset']}")

                # Calculate estimated weight
                data_points = len(coords) * 4  # 4 variables
                estimated_weight = max(1, data_points / 100)  # Rough estimate
                print(f"  Data Points: {data_points}")
                print(f"  Estimated Weight: ~{estimated_weight:.1f}x")

                # Brief delay to avoid rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                print(f"  Error: {e}")

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
    print("\nNote: Open-Meteo doesn't expose exact weighting in headers.")
    print("Based on documentation and response sizes, we can estimate:")
    print("  - Current-only requests: Lower weight (~2-5x)")
    print("  - With hourly data: Higher weight (~10-50x)")
    print("  - More coordinates = higher weight")
    print("\nRecommendation:")
    print("  - Start with 20-25 minute intervals to stay under 10k/day")
    print("  - Monitor usage and adjust as needed")
    print("  - Consider upgrading to commercial tier if needed ($50-150/month)")

asyncio.run(test_batch_weighting())
