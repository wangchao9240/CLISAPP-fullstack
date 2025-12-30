from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[3]))

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator


def parse_zooms(args: list[str]) -> list[int]:
    if not args:
        return [6, 7, 8, 9, 10]
    zooms: set[int] = set()
    for arg in args:
        if "-" in arg:
            start, end = arg.split("-", 1)
            zooms.update(range(int(start), int(end) + 1))
        else:
            zooms.add(int(arg))
    cleaned = sorted(z for z in zooms if 0 <= z <= 22)
    if not cleaned:
        raise SystemExit("No valid zoom levels provided")
    return cleaned


def main():
    tif_path = Path("data_pipeline/data/processed/gpm/imerg_daily_precip_qld.tif")
    if not tif_path.exists():
        raise SystemExit(f"GeoTIFF not found: {tif_path}. Run process_imerg_daily_to_tif.py first.")

    zooms = parse_zooms(sys.argv[1:])
    generator = PM25TileGenerator(str(tif_path), layer_name="precipitation", zoom_levels=zooms)
    total_tiles = generator.generate_all_tiles()
    print(f"Precipitation tiles generated (zooms {zooms[0]}-{zooms[-1]}): {total_tiles}")


if __name__ == "__main__":
    main()


