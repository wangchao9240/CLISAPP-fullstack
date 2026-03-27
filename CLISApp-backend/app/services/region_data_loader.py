"""Region data loader for Queensland boundaries.

This module reads the SSC (State Suburb Code) shapefile — the single
boundary data source for the entire application — and exposes lightweight
in-memory representations that the RegionService can use for search,
lookup and boundary queries.

The SSC shapefile contains 2,894 merged suburb-level boundaries covering
all of Queensland.  LGA groupings are derived from the SSC parent_region
field rather than from separate LGA/suburb shapefiles.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Dict, Iterable, Optional

import geopandas as gpd
from data_pipeline.processing.geo.process_boundaries import (
    SSC_SHP,
    load_shapefile,
    prepare_ssc_records,
    resolve_field_mapping,
)
from shapely.geometry import mapping, Polygon, MultiPolygon

from app.models.region import Bounds, Coordinate

logger = logging.getLogger(__name__)

AUSTRALIA_ALBERS_EPSG = 3577  # suitable for area calculations
WGS84_EPSG = 4326


_REGION_LOADER: Optional["RegionDataLoader"] = None


@dataclass(frozen=True)
class RegionGeometry:
    """Simplified geometry metadata for a region."""

    geometry: Polygon | MultiPolygon
    bounds: Bounds
    centroid: Coordinate
    area_km2: float


@dataclass(frozen=True)
class RegionRecord:
    """Flattened record for an SSC region."""

    id: str
    name: str
    type: str  # "ssc"
    state: str
    parent_region: Optional[str]
    postcode: Optional[str]
    search_key: str
    geometry: RegionGeometry
    raw_properties: Dict


class RegionDataLoader:
    """Loads Queensland SSC boundaries (single data source) into memory."""

    def __init__(self) -> None:
        self._ssc_records: Dict[str, RegionRecord] = {}
        self._load()

    def get_records(self, region_type: Optional[str] = None) -> Iterable[RegionRecord]:
        if region_type is not None and region_type != "ssc":
            return iter([])
        return self._ssc_records.values()

    def get_record(self, region_id: str) -> Optional[RegionRecord]:
        return self._ssc_records.get(region_id)

    def _load(self) -> None:
        if not SSC_SHP.exists():
            logger.warning("SSC shapefile not found at %s", SSC_SHP)
        else:
            try:
                self._ssc_records = self._parse_ssc_shapefile()
                logger.info("Loaded %d SSC regions", len(self._ssc_records))
            except Exception as exc:
                logger.error("Failed to load SSC shapefile: %s", exc, exc_info=True)
                self._ssc_records = {}

    def _parse_ssc_shapefile(self) -> Dict[str, RegionRecord]:
        logger.info("Reading SSC shapefile %s", SSC_SHP)
        ssc_gdf = load_shapefile(SSC_SHP)
        field_mapping = resolve_field_mapping(ssc_gdf.columns)
        prepared = prepare_ssc_records(ssc_gdf, field_mapping)

        records: Dict[str, RegionRecord] = {}
        for row in prepared.to_dict("records"):
            ssc_id = str(row["_ssc_id"])
            name = str(row["_name"])
            group_id = str(row["_group_id"])
            parent_name = group_id.replace("group_", "").replace("_", " ").title()
            geometry = self._build_geometry(row["geometry"])
            record = RegionRecord(
                id=ssc_id,
                name=name,
                type="ssc",
                state="QLD",
                parent_region=parent_name,
                postcode=None,
                search_key=name.lower(),
                geometry=geometry,
                raw_properties={
                    "ssc_code": str(row.get("_ssc_code", "")),
                    "group_id": group_id,
                    "area_sqkm": geometry.area_km2,
                },
            )
            records[ssc_id] = record
        return records

    def _build_geometry(self, geom: Polygon | MultiPolygon) -> RegionGeometry:
        centroid = geom.centroid
        bounds = geom.bounds  # (minx, miny, maxx, maxy)

        # Area calculation in km^2 using an equal-area projection
        area_geom = gpd.GeoSeries([geom], crs=WGS84_EPSG).to_crs(epsg=AUSTRALIA_ALBERS_EPSG)
        area_km2 = float(area_geom.area.iloc[0] / 1_000_000)

        bounds_model = Bounds(
            northeast=Coordinate(latitude=bounds[3], longitude=bounds[2]),
            southwest=Coordinate(latitude=bounds[1], longitude=bounds[0]),
        )
        centroid_coord = Coordinate(latitude=float(centroid.y), longitude=float(centroid.x))

        return RegionGeometry(
            geometry=geom,
            bounds=bounds_model,
            centroid=centroid_coord,
            area_km2=area_km2,
        )

    def to_geojson(self, record: RegionRecord) -> Dict:
        return mapping(record.geometry.geometry)


def get_loader() -> RegionDataLoader:
    """Factory helper that caches the loader singleton."""
    global _REGION_LOADER
    if _REGION_LOADER is None:
        _REGION_LOADER = RegionDataLoader()
    return _REGION_LOADER
