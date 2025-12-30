#!/usr/bin/env python3
"""Upsample tiles to higher zoom levels by simple replication."""

import argparse
import logging
from pathlib import Path
from typing import Iterable

from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def upsample_layer(tiles_root: Path, layer: str, min_zoom: int, max_zoom: int) -> int:
    layer_dir = tiles_root / layer
    if not layer_dir.exists():
        logger.error("Layer directory not found: %s", layer_dir)
        return 0

    total = 0
    for zoom in range(min_zoom, max_zoom):
        src_dir = layer_dir / str(zoom)
        dst_dir = layer_dir / str(zoom + 1)
        if not src_dir.exists():
            logger.warning("Zoom %s missing for layer %s", zoom, layer)
            continue
        logger.info("Upsampling layer=%s from z%s -> z%s", layer, zoom, zoom + 1)
        created = _upsample_step(src_dir, dst_dir)
        logger.info("Created %s tiles at z%s", created, zoom + 1)
        total += created
    return total


def _upsample_step(src_dir: Path, dst_dir: Path) -> int:
    count = 0
    for x_dir in src_dir.iterdir():
        if not x_dir.is_dir() or not x_dir.name.isdigit():
            continue
        x = int(x_dir.name)
        for y_file in x_dir.glob("*.png"):
            try:
                img = Image.open(y_file)
            except Exception:
                continue
            y = int(y_file.stem)
            for dx in (0, 1):
                for dy in (0, 1):
                    cx = x * 2 + dx
                    cy = y * 2 + dy
                    out_dir = dst_dir / str(cx)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    img.save(out_dir / f"{cy}.png")
                    count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Upsample tiles by replication")
    parser.add_argument("layers", nargs="*", help="Layer names to upsample")
    parser.add_argument("--tiles-root", default="tiles", help="Root directory containing layer folders")
    parser.add_argument("--min-zoom", type=int, default=10, help="Lowest existing zoom to upsample from")
    parser.add_argument("--max-zoom", type=int, default=13, help="Highest zoom to create")
    args = parser.parse_args()

    tiles_root = Path(args.tiles_root)
    if not tiles_root.exists():
        raise SystemExit(f"Tiles root not found: {tiles_root}")

    if args.layers:
        layers = args.layers
    else:
        layers = [p.name for p in tiles_root.iterdir() if p.is_dir()]

    total = 0
    for layer in layers:
        total += upsample_layer(tiles_root, layer, args.min_zoom, args.max_zoom)

    logger.info("Upsampling complete. Total tiles created: %s", total)


if __name__ == "__main__":
    main()
