#!/usr/bin/env python3
"""Boundary preprocessing utilities.

Reads the raw Queensland LGA and suburb shapefiles and exports simplified
GeoJSON that the mobile frontend can bundle as static assets.

Outputs:
    data/processed/geo/
        ├─ lga_boundaries.json            # All 78 LGAs
        └─ suburbs/
             └─ <lga_id>.json            # Suburbs grouped per LGA

The exporter performs light geometry simplification to keep payload size
manageable on devices while preserving topology.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Tuple

import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


LOGGER = logging.getLogger("process_boundaries")

DATA_ROOT = Path(__file__).resolve().parents[3] / "data_pipeline" / "data"
RAW_GEO_ROOT = DATA_ROOT / "raw" / "geo"
PROCESSED_ROOT = DATA_ROOT / "processed" / "geo"

LGA_SHP = RAW_GEO_ROOT / "LGA_boundaries" / "Local_Government_Areas.shp"
SUBURB_SHP = RAW_GEO_ROOT / "suburb_boundaries" / "Locality_Boundaries.shp"

# Empirically tuned tolerance: ~50 metres in degrees (~0.0005)
SIMPLIFY_TOLERANCE = 0.0005


def load_shapefile(path: Path) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Shapefile not found: {path}")
    LOGGER.info("Reading %s", path)
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf = gdf.dropna(subset=["geometry"])
    return gdf


def simplify_geometry(geom) -> dict:
    simplified = geom.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    return mapping(simplified)


def export_lga_boundaries(lga_gdf: gpd.GeoDataFrame, out_dir: Path) -> Dict[str, dict]:
    features: Dict[str, dict] = {}
    for row in lga_gdf.itertuples(index=False):
        lga_code = getattr(row, "lga_code", None)
        if not lga_code:
            continue
        lga_id = f"lga_{lga_code}"
        geom = simplify_geometry(row.geometry)
        feature = {
            "type": "Feature",
            "id": lga_id,
            "properties": {
                "id": lga_id,
                "name": str(getattr(row, "lga", "")).title(),
                "state": "QLD",
                "area_sqkm": getattr(row, "shape_Area", None),
            },
            "geometry": geom,
        }
        features[lga_id] = feature

    collection = {
        "type": "FeatureCollection",
        "features": list(features.values()),
    }
    out_path = out_dir / "lga_boundaries.json"
    out_path.write_text(json.dumps(collection))
    LOGGER.info("Exported %d LGA features -> %s", len(features), out_path)
    return features


def export_suburb_boundaries(
    suburb_gdf: gpd.GeoDataFrame,
    lga_features: Dict[str, dict],
    out_dir: Path,
) -> None:
    suburbs_dir = out_dir / "suburbs"
    suburbs_dir.mkdir(parents=True, exist_ok=True)

    grouped: Dict[str, Dict[str, dict]] = {}
    for row in suburb_gdf.itertuples(index=False):
        loc_code = getattr(row, "loc_code", None)
        parent_lga_raw = getattr(row, "lga", None)
        if loc_code is None or parent_lga_raw is None:
            continue
        suburb_id = f"suburb_{loc_code}"
        parent_name = str(parent_lga_raw).title()

        # Find matching LGA feature by name fallback
        lga_id = next(
            (fid for fid, feat in lga_features.items() if feat["properties"]["name"] == parent_name),
            None,
        )
        if lga_id is None:
            LOGGER.warning("Skipping suburb %s - parent LGA %s not found", suburb_id, parent_name)
            continue

        geom = simplify_geometry(row.geometry)
        feature = {
            "type": "Feature",
            "id": suburb_id,
            "properties": {
                "id": suburb_id,
                "name": str(getattr(row, "locality", "")).title(),
                "state": "QLD",
                "lga_id": lga_id,
                "area_sqkm": getattr(row, "shape_Area", None),
            },
            "geometry": geom,
        }
        grouped.setdefault(lga_id, {})[suburb_id] = feature

    for lga_id, features in grouped.items():
        collection = {
            "type": "FeatureCollection",
            "features": list(features.values()),
        }
        out_path = suburbs_dir / f"{lga_id}.json"
        out_path.write_text(json.dumps(collection))
        LOGGER.info("Exported %d suburbs for %s -> %s", len(features), lga_id, out_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    lga_gdf = load_shapefile(LGA_SHP)
    suburb_gdf = load_shapefile(SUBURB_SHP)

    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)

    lga_features = export_lga_boundaries(lga_gdf, PROCESSED_ROOT)
    export_suburb_boundaries(suburb_gdf, lga_features, PROCESSED_ROOT)


if __name__ == "__main__":
    main()


