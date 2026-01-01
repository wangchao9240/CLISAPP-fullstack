from pathlib import Path
import sys

# Make sure the project root is on sys.path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator


def _resolve_temperature_tif() -> Path:
    # Canonical Open-Meteo output location (written by process_openmeteo_temp_to_tif.py)
    latest = Path("data/processing/temp/temperature_latest.tif")
    if latest.exists():
        return latest

    candidates = sorted(
        Path("data/processing/temp").glob("temperature_openmeteo_*.tif"),
        reverse=True,
    )
    if candidates:
        return candidates[0]

    raise SystemExit(
        "GeoTIFF not found for temperature tiles.\n"
        "Expected: data/processing/temp/temperature_latest.tif\n"
        "Action: run `python -m data_pipeline.processing.temp.process_openmeteo_temp_to_tif` first."
    )


def main() -> None:
    tif_path = _resolve_temperature_tif()
    generator = PM25TileGenerator(str(tif_path), layer_name="temperature")
    total_tiles = generator.generate_all_tiles()
    print(f"Temperature tiles generated: {total_tiles}")


if __name__ == "__main__":
    main()

