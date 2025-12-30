from pathlib import Path
import sys

# Make sure the project root is on sys.path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator


def main():
    tif_path = Path("data_pipeline/data/processed/temp/cams_t2m_qld.tif")
    if not tif_path.exists():
        raise SystemExit(f"GeoTIFF not found: {tif_path}. Run process_cams_t2m_to_tif.py first.")

    generator = PM25TileGenerator(str(tif_path), layer_name="temperature")
    total_tiles = generator.generate_all_tiles()
    print(f"Temperature tiles generated: {total_tiles}")


if __name__ == "__main__":
    main()


