#!/usr/bin/env python3
"""Run full pipeline: fetch fresh data + generate tiles (zoom 6-11) for all 5 layers."""
import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from data_pipeline.processing.openmeteo.process_all_layers import process_all_layers, OUTPUT_DIR_MAP, OUTPUT_BASENAME_MAP
from data_pipeline.processing.common.generate_tiles import PM25TileGenerator

ZOOM_LEVELS = [6, 7, 8, 9, 10, 11]

DIR_MAP = {
    "temperature": "temp",
    "humidity": "humidity",
    "precipitation": "precipitation",
    "uv": "uv",
    "pm25": "pm25",
}


async def main():
    # Step 1: Fetch fresh data (skip tile generation, we do it ourselves)
    logger.info("=" * 60)
    logger.info("Step 1: Fetching fresh Open-Meteo data for all layers")
    logger.info("=" * 60)
    fetch_start = time.time()
    outputs = await process_all_layers(skip_tiles=True)
    fetch_elapsed = time.time() - fetch_start
    logger.info(f"Data fetch complete in {fetch_elapsed:.1f}s")

    # Step 2: Generate tiles for each layer
    results = []
    for layer, tif_path in outputs.items():
        logger.info("=" * 60)
        logger.info(f"Step 2: Generating {layer} tiles (zoom {ZOOM_LEVELS[0]}-{ZOOM_LEVELS[-1]})")
        logger.info("=" * 60)
        start = time.time()
        gen = PM25TileGenerator(
            str(tif_path), output_dir="tiles", layer_name=layer, zoom_levels=ZOOM_LEVELS
        )
        total = gen.generate_all_tiles()
        elapsed = time.time() - start
        results.append((layer, total, elapsed, gen.native_max_zoom))
        logger.info(f"RESULT: {layer} | {total} tiles | {elapsed:.1f}s | native_max_zoom={gen.native_max_zoom}")

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Data fetch: {fetch_elapsed:.1f}s")
    for layer, total, elapsed, nmz in results:
        logger.info(f"  {layer:15s} | {total:6d} tiles | {elapsed:6.1f}s | native_max_zoom={nmz}")
    total_tiles = sum(r[1] for r in results)
    total_time = sum(r[2] for r in results)
    logger.info(f"  {'TOTAL':15s} | {total_tiles:6d} tiles | {total_time:6.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
