"""Region data loader for Queensland LGA and suburb boundaries.

This module reads the shapefiles that were downloaded into
`data_pipeline/data/raw/geo/` and exposes lightweight in-memory
representations that the RegionService can use for search, lookup and
boundary queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import geopandas as gpd
from shapely.geometry import mapping, Polygon, MultiPolygon

from app.models.region import Bounds, Coordinate

logger = logging.getLogger(__name__)


DATA_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "data_pipeline"
    / "data"
    / "raw"
    / "geo"
)

LGA_SHAPEFILE = DATA_ROOT / "LGA_boundaries" / "Local_Government_Areas.shp"
SUBURB_SHAPEFILE = DATA_ROOT / "suburb_boundaries" / "Locality_Boundaries.shp"

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
    """Flattened record for either an LGA or suburb."""

    id: str
    name: str
    type: str  # "lga" or "suburb"
    state: str
    parent_region: Optional[str]
    postcode: Optional[str]
    search_key: str
    geometry: RegionGeometry
    raw_properties: Dict


class RegionDataLoader:
    """Loads Queensland LGA and suburb shapefiles into memory."""

    def __init__(self) -> None:
        self._lga_records: Dict[str, RegionRecord] = {}
        self._suburb_records: Dict[str, RegionRecord] = {}
        self._load()

    @cached_property
    def all_records(self) -> Dict[str, RegionRecord]:
        combined = {**self._lga_records, **self._suburb_records}
        return combined

    def get_records(self, region_type: Optional[str] = None) -> Iterable[RegionRecord]:
        if region_type == "lga":
            return self._lga_records.values()
        if region_type == "suburb":
            return self._suburb_records.values()
        return self.all_records.values()

    def get_record(self, region_id: str) -> Optional[RegionRecord]:
        return self.all_records.get(region_id)

    def _load(self) -> None:
        if not LGA_SHAPEFILE.exists():
            logger.warning("LGA shapefile not found at %s", LGA_SHAPEFILE)
        else:
            self._lga_records = self._parse_lga_shapefile()
            logger.info("Loaded %d LGA regions", len(self._lga_records))

        if not SUBURB_SHAPEFILE.exists():
            logger.warning("Suburb shapefile not found at %s", SUBURB_SHAPEFILE)
        else:
            self._suburb_records = self._parse_suburb_shapefile()
            logger.info("Loaded %d suburb regions", len(self._suburb_records))

    def _parse_lga_shapefile(self) -> Dict[str, RegionRecord]:
        gdf = self._read_shapefile(LGA_SHAPEFILE)
        records: Dict[str, RegionRecord] = {}
        for row in gdf.itertuples(index=False):
            lga_code = getattr(row, "lga_code", None)
            if not lga_code:
                continue
            region_id = f"lga_{str(lga_code)}"
            name = getattr(row, "lga", None) or getattr(row, "adminarean", "")
            geometry = self._build_geometry(row.geometry)
            record = RegionRecord(
                id=region_id,
                name=name.title(),
                type="lga",
                state="QLD",
                parent_region=None,
                postcode=None,
                search_key=name.lower(),
                geometry=geometry,
                raw_properties={
                    "admintypen": getattr(row, "admintypen", None),
                    "adminarean": getattr(row, "adminarean", None),
                    "abbrev_nam": getattr(row, "abbrev_nam", None),
                    "lga_code": lga_code,
                    "area_sqkm": geometry.area_km2,
                },
            )
            records[region_id] = record
        return records

    def _parse_suburb_shapefile(self) -> Dict[str, RegionRecord]:
        gdf = self._read_shapefile(SUBURB_SHAPEFILE)
        records: Dict[str, RegionRecord] = {}
        for row in gdf.itertuples(index=False):
            loc_code = getattr(row, "loc_code", None)
            if loc_code is None:
                continue
            raw_name = getattr(row, "locality", None)
            if not raw_name:
                continue
            name = str(raw_name).title()
            region_id = f"suburb_{str(loc_code)}"
            parent_lga_raw = getattr(row, "lga", None)
            parent_lga = str(parent_lga_raw).title() if parent_lga_raw else None
            geometry = self._build_geometry(row.geometry)
            record = RegionRecord(
                id=region_id,
                name=name,
                type="suburb",
                state="QLD",
                parent_region=parent_lga,
                postcode=None,
                search_key=name.lower(),
                geometry=geometry,
                raw_properties={
                    "admintypen": getattr(row, "admintypen", None),
                    "adminarean": getattr(row, "adminarean", None),
                    "loc_code": loc_code,
                    "lga": parent_lga,
                    "area_sqkm": geometry.area_km2,
                },
            )
            records[region_id] = record
        return records

    def _read_shapefile(self, path: Path) -> gpd.GeoDataFrame:
        logger.info("Reading shapefile %s", path)
        gdf = gpd.read_file(path)
        if gdf.crs is None or gdf.crs.to_epsg() != WGS84_EPSG:
            gdf = gdf.to_crs(epsg=WGS84_EPSG)
        gdf = gdf.dropna(subset=["geometry"])
        return gdf

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
