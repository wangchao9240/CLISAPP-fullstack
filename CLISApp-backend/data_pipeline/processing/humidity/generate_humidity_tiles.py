from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator

def _resolve_humidity_tif() -> Path:
    # Canonical Open-Meteo output location (written by process_openmeteo_humidity_to_tif.py)
    latest = Path("data/processing/humidity/humidity_latest.tif")
    if latest.exists():
        return latest

    candidates = sorted(
        Path("data/processing/humidity").glob("humidity_openmeteo_*.tif"),
        reverse=True,
    )
    if candidates:
        return candidates[0]

    raise SystemExit(
        "GeoTIFF not found for humidity tiles.\n"
        "Expected: data/processing/humidity/humidity_latest.tif\n"
        "Action: run `python -m data_pipeline.processing.humidity.process_openmeteo_humidity_to_tif` first."
    )

def main():
    tif_path = _resolve_humidity_tif()

    tiles_root = Path("tiles")
    layer = "humidity"

    generator = PM25TileGenerator(str(tif_path), layer_name=layer, zoom_levels=[6, 7, 8, 9, 10, 11, 12, 13])
    total_tiles = generator.generate_all_tiles()

    layer_dir = tiles_root / layer
    if not (layer_dir / "13").exists():
        from subprocess import run
        cmd = [sys.executable, str(Path(__file__).resolve().parents[1] / "common" / "upsample_zoom11_to_12.py"), "--tiles-root", str(tiles_root), "--min-zoom", "11", "--max-zoom", "13", layer]
        run(cmd, check=False)

    print(f"Humidity tiles generated (target zoom 6-13): {total_tiles}")

if __name__ == "__main__":
    main()

