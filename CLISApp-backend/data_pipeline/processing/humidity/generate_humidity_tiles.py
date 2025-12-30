from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator

def main():
    tif_path = Path("data_pipeline/data/processed/cams/cams_rh_qld.tif")
    if not tif_path.exists():
        raise SystemExit(f"GeoTIFF not found: {tif_path}. Run process_humidity_from_cams.py first.")

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


