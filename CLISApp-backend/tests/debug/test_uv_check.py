#!/usr/bin/env python3
"""
Test UV index at different times of day.
"""

import asyncio
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher

# Brisbane coordinates
brisbane = [{"latitude": -27.47, "longitude": 153.02}]

async def main():
    async with OpenMeteoFetcher() as fetcher:
        print("Fetching current weather data for Brisbane...")
        print("=" * 60)

        data = await fetcher.fetch_all_data(brisbane)

        for key, values in data.items():
            print(f"\nBrisbane ({key}):")
            print(f"  Temperature:   {values.get('temperature')}°C")
            print(f"  Humidity:      {values.get('humidity')}%")
            print(f"  Precipitation: {values.get('precipitation')}mm")
            print(f"  UV Index:      {values.get('uv_index')}")
            print(f"  Timestamp:     {values.get('timestamp')}")

            # Explain UV index
            uv = values.get('uv_index', 0)
            if uv == 0:
                print(f"\n  ℹ️  UV Index is 0 - This is normal at night or early morning")
                print(f"      Test during daylight hours (10am-3pm Brisbane time) for UV data")
            elif uv < 3:
                print(f"\n  ☀️  UV Index: Low")
            elif uv < 6:
                print(f"\n  ☀️  UV Index: Moderate")
            elif uv < 8:
                print(f"\n  ☀️☀️  UV Index: High")
            elif uv < 11:
                print(f"\n  ☀️☀️☀️  UV Index: Very High")
            else:
                print(f"\n  ☀️☀️☀️☀️  UV Index: Extreme")

asyncio.run(main())
