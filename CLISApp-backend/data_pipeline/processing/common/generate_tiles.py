#!/usr/bin/env python3
"""
Tile generation script - convert GeoTIFF into XYZ tiles
"""

import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.windows import Window
from PIL import Image
import math
import os
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings
import json
from datetime import datetime

logger = logging.getLogger(__name__)


DEFAULT_TILE_ALPHA = 200  # Reduced alpha for smoother blending (was 235)


def hex_to_rgba(hex_color: str, alpha: int = DEFAULT_TILE_ALPHA) -> List[int]:
    """Convert hex color to RGBA list with provided alpha."""
    color = hex_color.lstrip('#')
    if len(color) == 3:
        color = ''.join(ch * 2 for ch in color)
    if len(color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return [r, g, b, alpha]


DEFAULT_LAYER_STYLES: Dict[str, Dict[str, List]] = {
    "pm25": {
        "color_breaks": [0, 12, 35, 55, 150],
        "colors": [
            hex_to_rgba("#00ff00"),
            hex_to_rgba("#87ff00"),
            hex_to_rgba("#ffff00"),
            hex_to_rgba("#ff6600"),
            hex_to_rgba("#ff0000"),
        ],
    },
    "precipitation": {
        "color_breaks": [0, 0.5, 2, 10, 50],
        "colors": [
            hex_to_rgba("#ffffff"),
            hex_to_rgba("#87ceeb"),
            hex_to_rgba("#4169e1"),
            hex_to_rgba("#0000ff"),
            hex_to_rgba("#00008b"),
        ],
    },
    "uv": {
        "color_breaks": [0, 3, 6, 8, 11],
        "colors": [
            hex_to_rgba("#289500"),
            hex_to_rgba("#f7e400"),
            hex_to_rgba("#f85900"),
            hex_to_rgba("#d8001d"),
            hex_to_rgba("#6b49c8"),
        ],
    },
    "humidity": {
        "color_breaks": [0, 30, 50, 70, 90],
        "colors": [
            hex_to_rgba("#8B4513"),
            hex_to_rgba("#DAA520"),
            hex_to_rgba("#FFD700"),
            hex_to_rgba("#87CEEB"),
            hex_to_rgba("#4169E1"),
        ],
    },
    "temperature": {
        "color_breaks": [0, 10, 20, 30, 40],
        "colors": [
            hex_to_rgba("#0000ff"),
            hex_to_rgba("#87ceeb"),
            hex_to_rgba("#ffff00"),
            hex_to_rgba("#ff6600"),
            hex_to_rgba("#ff0000"),
        ],
    },
}

class PM25TileGenerator:
    def __init__(self, geotiff_file, output_dir="tiles", layer_name: str = "pm25", color_breaks=None, colors=None, zoom_levels=None, use_legacy_thresholds: bool = False, thresholds_override: Optional[List[float]] = None):
        self.geotiff_file = geotiff_file
        self.output_dir = output_dir
        self.layer_name = layer_name
        self.tile_size = 256
        self.zoom_levels = zoom_levels or [6, 7, 8, 9, 10, 11, 12, 13]
        self.data_min: Optional[float] = None
        self.data_max: Optional[float] = None
        self.dynamic_thresholds: Optional[List[float]] = None
        self.use_legacy_thresholds = use_legacy_thresholds
        self.thresholds_override = thresholds_override
        
        # Default PM2.5 color mapping (based on WHO guidance)
        layer_style = DEFAULT_LAYER_STYLES.get(layer_name, {})

        if color_breaks is not None:
            self.color_breaks = color_breaks
        elif thresholds_override is not None and not use_legacy_thresholds:
            self.color_breaks = thresholds_override
        else:
            self.color_breaks = layer_style.get("color_breaks", [0, 12, 35, 55, 150, 250, 500])

        if colors is not None:
            self.colors = colors
        else:
            self.colors = layer_style.get("colors", [
                hex_to_rgba("#00ff00"),
                hex_to_rgba("#ffff00"),
                hex_to_rgba("#ff6600"),
                hex_to_rgba("#ff0000"),
                hex_to_rgba("#800080"),
                hex_to_rgba("#4B0082"),
            ])
    
    def deg2num(self, lat_deg, lon_deg, zoom):
        """Convert latitude/longitude to tile coordinates"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (xtile, ytile)
    
    def num2deg(self, xtile, ytile, zoom):
        """Convert tile coordinates back to latitude/longitude"""
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def apply_pm25_colormap(self, data):
        """Apply layer color mapping with smooth linear interpolation between color breaks"""
        # Create RGBA image
        height, width = data.shape
        rgba_image = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Handle NaN values and zero values
        # Treat 0 as valid to avoid gaps from boundary resampling producing 0 pixels
        valid_mask = ~np.isnan(data)
        data = np.where(np.isnan(data), 0.0, data)
        
        # Apply smooth color mapping with linear interpolation
        for i in range(len(self.color_breaks) - 1):
            lower = self.color_breaks[i]
            upper = self.color_breaks[i + 1]
            
            # Find pixels in this range
            mask = valid_mask & (data >= lower) & (data < upper)
            
            if not np.any(mask):
                continue
            
            # Linear interpolation factor (0.0 at lower, 1.0 at upper)
            # Avoid division by zero
            range_width = upper - lower
            if range_width > 0:
                t = (data[mask] - lower) / range_width
                t = np.clip(t, 0.0, 1.0)  # Ensure t is in [0, 1]
                
                # Interpolate each color channel
                color_start = np.array(self.colors[i], dtype=np.float32)
                color_end = np.array(self.colors[i + 1], dtype=np.float32)
                
                # Linear interpolation: color = (1-t) * start + t * end
                interpolated = (1 - t[:, np.newaxis]) * color_start + t[:, np.newaxis] * color_end
                rgba_image[mask] = interpolated.astype(np.uint8)
            else:
                # Degenerate case: use start color
                rgba_image[mask] = self.colors[i]
        
        # Handle out-of-range values (beyond last break)
        max_mask = valid_mask & (data >= self.color_breaks[-1])
        rgba_image[max_mask] = self.colors[-1]
        
        # Keep transparent background as [0, 0, 0, 0]
        
        return rgba_image
    
    def fill_missing_with_neighbor_mean(self, data: np.ndarray) -> np.ndarray:
        """Fill 0 or NaN pixels using nearest neighbors (priority: up, down, left, right)"""
        source = np.where(np.isnan(data), 0.0, data).astype(np.float32)
        if not np.any(source == 0):
            return source

        filled = source.copy()

        up = np.zeros_like(filled)
        up[1:, :] = source[:-1, :]

        down = np.zeros_like(filled)
        down[:-1, :] = source[1:, :]

        left = np.zeros_like(filled)
        left[:, 1:] = source[:, :-1]

        right = np.zeros_like(filled)
        right[:, :-1] = source[:, 1:]

        for neighbor in (up, down, left, right):
            mask = (filled == 0) & (neighbor != 0)
            if np.any(mask):
                filled[mask] = neighbor[mask]

        return filled

    def _valid_tile_index(self, zoom: int, x: int, y: int) -> bool:
        limit = 2 ** zoom
        return 0 <= x < limit and 0 <= y < limit

    def _extract_tile_data(self, src: rasterio.io.DatasetReader, zoom: int, x: int, y: int) -> Optional[np.ndarray]:
        lat_max, lon_min = self.num2deg(x, y, zoom)
        lat_min, lon_max = self.num2deg(x + 1, y + 1, zoom)

        try:
            window = rasterio.windows.from_bounds(
                lon_min, lat_min, lon_max, lat_max,
                src.transform
            )
        except Exception:
            return None

        if window.width <= 0 or window.height <= 0:
            return None

        try:
            data = src.read(1, window=window)
        except Exception:
            return None

        if data.size == 0 or np.all(np.isnan(data)):
            return None

        if data.shape != (256, 256):
            from rasterio.transform import from_bounds
            dst_transform = from_bounds(
                lon_min, lat_min, lon_max, lat_max, 256, 256
            )

            resampled = np.empty((256, 256), dtype=np.float32)
            reproject(
                data.reshape(1, *data.shape),
                resampled.reshape(1, 256, 256),
                src_transform=rasterio.windows.transform(window, src.transform),
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=src.crs,
                resampling=Resampling.bilinear  # Changed from 'nearest' for smoother transitions
            )
            data = resampled

        return data

    def _get_neighbor_data_with_max_value(
        self,
        src: rasterio.io.DatasetReader,
        zoom: int,
        x: int,
        y: int,
    ) -> Optional[np.ndarray]:
        neighbors: Tuple[Tuple[int, int], ...] = (
            (x, y - 1),  # north
            (x, y + 1),  # south
            (x - 1, y),  # west
            (x + 1, y),  # east
        )

        best_data: Optional[np.ndarray] = None
        best_value = -np.inf

        for nx, ny in neighbors:
            if not self._valid_tile_index(zoom, nx, ny):
                continue

            neighbor_data = self._extract_tile_data(src, zoom, nx, ny)
            if neighbor_data is None:
                continue

            if np.all(np.isnan(neighbor_data)):
                continue

            try:
                candidate_value = float(np.nanmax(neighbor_data))
            except ValueError:
                continue

            if candidate_value > best_value:
                best_value = candidate_value
                best_data = neighbor_data

        return best_data

    def generate_tile(self, zoom, x, y):
        """Generate a single tile"""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
                with rasterio.open(self.geotiff_file) as src:
                    data = self._extract_tile_data(src, zoom, x, y)

            if data is None:
                return None

            valid_mask = ~np.isnan(data)
            valid_ratio = float(np.count_nonzero(valid_mask)) / data.size
            if valid_ratio == 0.0 or valid_ratio < 0.02:
                return None

            # Apply color mapping
            data = self.fill_missing_with_neighbor_mean(data)
            rgba_data = self.apply_pm25_colormap(data)

            if np.all(rgba_data[:, :, 3] == 0):  # fully transparent
                return None

            img = Image.fromarray(rgba_data, 'RGBA')

            tile_dir = os.path.join(self.output_dir, self.layer_name, str(zoom), str(x))
            os.makedirs(tile_dir, exist_ok=True)

            tile_path = os.path.join(tile_dir, f"{y}.png")
            img.save(tile_path, 'PNG')

            return tile_path

        except Exception as e:
            logger.debug(f"Failed to generate tile {zoom}/{x}/{y}: {e}")
            return None
    
    def generate_tiles_for_zoom(self, zoom):
        """Generate all tiles for the specified zoom level"""
        logger.info(f"Starting tile generation for zoom level {zoom}")
        
        # Read dataset bounds
        with rasterio.open(self.geotiff_file) as src:
            bounds = src.bounds
            west, south, east, north = bounds
        
        # Compute tile range
        x_min, y_max = self.deg2num(south, west, zoom)  # southwest corner
        x_max, y_min = self.deg2num(north, east, zoom)   # northeast corner
        
        # Add margins to ensure coverage
        x_min = max(0, x_min - 1)
        y_min = max(0, y_min - 1)
        x_max = min(2**zoom - 1, x_max + 1)
        y_max = min(2**zoom - 1, y_max + 1)
        
        tiles_generated = 0
        total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
        
        logger.info(f"Zoom {zoom}: tile range X({x_min}-{x_max}) Y({y_min}-{y_max})")
        logger.info(f"Zoom {zoom}: processing {total_tiles} tile positions")
        
        # Generate tiles in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    future = executor.submit(self.generate_tile, zoom, x, y)
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                if result:
                    tiles_generated += 1
                    if tiles_generated % 20 == 0:
                        logger.info(f"Zoom {zoom}: generated {tiles_generated} valid tiles")
        
        logger.info(f"Zoom {zoom} complete: generated {tiles_generated} valid tiles")
        return tiles_generated
    
    def generate_all_tiles(self):
        """Generate tiles for all configured zoom levels"""
        logger.info(f"Starting tile generation, output directory: {self.output_dir}")
        logger.info(f"Source data file: {self.geotiff_file}")
        
        # Validate source file
        if not os.path.exists(self.geotiff_file):
            raise FileNotFoundError(f"GeoTIFF file does not exist: {self.geotiff_file}")
        
        # Read source dataset information
        with rasterio.open(self.geotiff_file) as src:
            logger.info(f"Dataset size: {src.width} x {src.height} pixels")
            logger.info(f"Coordinate reference system: {src.crs}")
            logger.info(f"Bounds: {src.bounds}")
            data_range = src.read(1)
            self.data_min = float(np.nanmin(data_range))
            self.data_max = float(np.nanmax(data_range))
            logger.info(f"Data range: {self.data_min:.2f} - {self.data_max:.2f}")

        self._maybe_prepare_dynamic_thresholds()
        
        total_generated = 0
        
        for zoom in self.zoom_levels:
            generated = self.generate_tiles_for_zoom(zoom)
            total_generated += generated
        
        logger.info(f"Tile generation complete! Total tiles generated: {total_generated}")
        
        # Generate tile statistics
        self.generate_tile_stats()
        self._write_metadata()

        return total_generated
    
    def generate_tile_stats(self):
        """Generate tile statistics"""
        stats = {}
        total_tiles = 0
        total_size = 0
        
        for zoom in self.zoom_levels:
            zoom_dir = os.path.join(self.output_dir, self.layer_name, str(zoom))
            if os.path.exists(zoom_dir):
                zoom_tiles = len(list(Path(zoom_dir).rglob("*.png")))
                zoom_size = sum(f.stat().st_size for f in Path(zoom_dir).rglob("*.png"))
                
                stats[zoom] = {
                    "tiles": zoom_tiles,
                    "size_mb": zoom_size / 1024 / 1024
                }
                total_tiles += zoom_tiles
                total_size += zoom_size
        
        logger.info("=== Tile generation statistics ===")
        for zoom, stat in stats.items():
            logger.info(f"Zoom {zoom}: {stat['tiles']} tiles, {stat['size_mb']:.2f} MB")
        
        logger.info(f"Total: {total_tiles} tiles, {total_size/1024/1024:.2f} MB")

    def _maybe_prepare_dynamic_thresholds(self) -> None:
        if self.layer_name not in {"pm25", "precipitation"}:
            return
        if self.use_legacy_thresholds:
            return
        if self.thresholds_override is not None:
            self.dynamic_thresholds = self.thresholds_override
            self.color_breaks = self.thresholds_override
            return
        if self.data_max is None or self.data_min is None:
            return
        num_classes = len(self.colors)
        if num_classes < 2:
            return
        max_val = float(self.data_max)
        if not np.isfinite(max_val) or max_val <= 0:
            max_val = 1.0
        start_val = 0.0
        if max_val <= start_val:
            max_val = start_val + 1.0
        max_val = _round_up_to_nice_value(max_val)
        thresholds = np.linspace(start_val, max_val, num_classes)
        dynamic_breaks = [round(float(t), 2) for t in thresholds]
        self.dynamic_thresholds = dynamic_breaks
        # Ensure thresholds are strictly increasing
        for i in range(1, len(dynamic_breaks)):
            if dynamic_breaks[i] <= dynamic_breaks[i - 1]:
                dynamic_breaks[i] = dynamic_breaks[i - 1] + 0.01
        self.color_breaks = dynamic_breaks

    def _write_metadata(self) -> None:
        # Write metadata.json for ALL layers (for mobile app to display last update time)
        thresholds = self.dynamic_thresholds or self.color_breaks
        metadata = {
            "layer": self.layer_name,
            "data_min": round(float(self.data_min or 0.0), 2),
            "data_max": round(float(self.data_max or 0.0), 2),
            "thresholds": [round(float(v), 2) for v in thresholds],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "use_legacy_thresholds": self.use_legacy_thresholds,
        }
        metadata_path = Path(self.output_dir) / self.layer_name / "metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

def main():
    args = sys.argv[1:]
    geotiff_file: Path | None = None
    layer = "pm25"
    zooms = None
    legacy_thresholds = False
    thresholds_override: Optional[List[float]] = None

    if args:
        geotiff_file = Path(args[0])
        rest = args[1:]
        if rest and not rest[0].replace('-', '').isdigit() and rest[0] not in {"--legacy-thresholds", "--thresholds"}:
            layer = rest[0]
            rest = rest[1:]
        while rest:
            token = rest[0]
            if token == "--legacy-thresholds":
                legacy_thresholds = True
                rest = rest[1:]
            elif token == "--thresholds" and len(rest) > 1:
                thresholds_override = _parse_thresholds_arg(rest[1])
                rest = rest[2:]
            elif token.replace('-', '').isdigit():
                zooms = _parse_zoom_arg(token)
                rest = rest[1:]
            else:
                rest = rest[1:]
    else:
        geotiff_file = _auto_find_latest_tif()
        layer = _infer_layer_from_path(geotiff_file) if geotiff_file else "pm25"

    if geotiff_file is None or not geotiff_file.exists():
        print(f"❌ GeoTIFF file not found: {geotiff_file}")
        sys.exit(1)

    try:
        generator = PM25TileGenerator(
            str(geotiff_file),
            layer_name=layer,
            zoom_levels=zooms or [6, 7, 8, 9, 10, 11, 12, 13],
            use_legacy_thresholds=legacy_thresholds,
            thresholds_override=thresholds_override,
        )
        total_tiles = generator.generate_all_tiles()
        
        print("✅ Tiles generated successfully!")
        print(f"📊 Total tiles: {total_tiles}")
        print(f"📁 Output directory: {generator.output_dir}/{generator.layer_name}/")
        print("\n📝 Next steps:")
        print("   python data_pipeline/servers/tile_server.py")
        
    except Exception as e:
        print(f"❌ Tile generation failed: {e}")
        logger.error(f"Tile generation failed: {e}")
        sys.exit(1)


def _parse_zoom_arg(zoom_arg: str) -> list[int]:
    if "-" in zoom_arg:
        start, end = map(int, zoom_arg.split("-", 1))
        return list(range(start, end + 1))
    return [int(zoom_arg)]


def _parse_thresholds_arg(threshold_arg: str) -> List[float]:
    return [float(value.strip()) for value in threshold_arg.split(",") if value.strip()]


def _auto_find_latest_tif() -> Path | None:
    search_dirs = [
        Path("data_pipeline/data/processed"),
        Path("data/processed"),
    ]
    tif_candidates = []
    for directory in search_dirs:
        if directory.exists():
            tif_candidates.extend(directory.rglob("*.tif"))
    return max(tif_candidates, key=os.path.getctime) if tif_candidates else None


def _infer_layer_from_path(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    name = path.name.lower()
    if "humidity" in parts or "rh" in name:
        return "humidity"
    if "uv" in parts:
        return "uv"
    if "temp" in parts or "temperature" in name:
        return "temperature"
    if "gpm" in parts or "precip" in name:
        return "precipitation"
    return "pm25"


def _round_up_to_nice_value(value: float) -> float:
    if value <= 0:
        return 1.0
    thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                  120, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
    for threshold in thresholds:
        if value <= threshold:
            return float(threshold)
    order = 10 ** int(math.log10(value))
    return float(math.ceil(value / order) * order)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
