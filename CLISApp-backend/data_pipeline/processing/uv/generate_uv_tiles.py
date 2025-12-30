from pathlib import Path
import sys

# Ensure project root (CLISApp-backend) is on sys.path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator


def main():
    tif_path = Path("data_pipeline/data/processed/uv/cams_uv_qld.tif")
    if not tif_path.exists():
        raise SystemExit(f"GeoTIFF not found: {tif_path}. Run process_cams_uv_to_tif.py first.")

    generator = PM25TileGenerator(str(tif_path), layer_name="uv")
    total_tiles = generator.generate_all_tiles()
    print(f"UV tiles generated: {total_tiles}")


if __name__ == "__main__":
    main()


