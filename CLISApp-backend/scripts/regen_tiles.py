#!/usr/bin/env python3
"""Regenerate humidity and temperature tiles with pre-interpolation fix."""
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator

LAYERS = [
    ("humidity", "data/processing/humidity/humidity_latest.tif"),
    ("temperature", "data/processing/temp/temperature_latest.tif"),
]

for layer, tif in LAYERS:
    print(f"\n{'='*60}")
    print(f"Generating {layer} tiles (zoom 6-11)")
    print(f"{'='*60}")
    start = time.time()
    gen = PM25TileGenerator(tif, output_dir="tiles", layer_name=layer, zoom_levels=[6, 7, 8, 9, 10, 11])
    total = gen.generate_all_tiles()
    elapsed = time.time() - start
    print(f"RESULT: {layer} | {total} tiles | {elapsed:.1f}s | native_max_zoom={gen.native_max_zoom}")

print("\nDone!")
