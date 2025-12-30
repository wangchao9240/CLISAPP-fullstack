"""
Region Service
Handles geographic region data, search, and climate data integration
Supports FR-003 (Search) and FR-004 (Region Info) requirements
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from shapely.geometry import Point

from app.models.climate import CLIMATE_LAYER_CONFIGS, ClimateDataPoint
from app.models.region import (
    Bounds,
    Coordinate,
    RegionBoundary,
    RegionResponse,
    RegionSearchResult,
)
from app.services.climate_data_service import ClimateDataService
from app.services.region_data_loader import RegionDataLoader, RegionRecord, get_loader

logger = logging.getLogger(__name__)


class RegionService:
    """Service for managing geographic region data."""

    def __init__(self) -> None:
        self.loader: RegionDataLoader = get_loader()
        self.climate_service = ClimateDataService()

    async def search_regions(
        self,
        query: str,
        region_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[RegionSearchResult]:
        """Search for regions by name or parent region."""

        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matched: List[tuple[int, RegionRecord]] = []
        for record in self._iter_records(region_type):
            score = self._match_score(query_lower, record)
            if score is not None:
                matched.append((score, record))

        matched.sort(key=lambda item: item[0])
        results = [self._to_search_result(rec) for _, rec in matched[:limit]]
        logger.info("Search '%s' returned %d results", query, len(results))
        return results

    async def get_region_by_id(
        self,
        region_id: str,
        include_climate_data: bool = True,
    ) -> Optional[RegionResponse]:
        """Fetch detailed information for a region."""

        record = self.loader.get_record(region_id)
        if record is None:
            return None

        return await self._build_region_response(record, include_climate_data)

    async def get_region_climate_data(
        self,
        region_id: str,
        layers: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return climate data for the requested region."""

        record = self.loader.get_record(region_id)
        if record is None:
            return None

        climate_data = await self._get_climate_data(record, layers)
        if climate_data is None:
            return None

        centroid = record.geometry.centroid
        return {
            "region_id": record.id,
            "region_name": record.name,
            "measurements": climate_data,
            "measurement_time": datetime.utcnow(),
            "location": {
                "latitude": centroid.latitude,
                "longitude": centroid.longitude,
            },
            "interpolation_method": "nearest_neighbor_with_window",
        }

    async def get_region_by_coordinates(
        self,
        latitude: float,
        longitude: float,
        include_climate_data: bool = True,
    ) -> Optional[RegionResponse]:
        """Find the LGA or suburb whose geometry contains the coordinate."""
        point = Point(longitude, latitude)
        record = self._find_region_containing(point)
        logger.debug("Coordinate lookup lat=%s lng=%s -> %s", latitude, longitude, record.id if record else None)
        if record is None:
            return None

        return await self._build_region_response(record, include_climate_data)

    async def get_level_bounds(
        self,
        level: str,
        state: str = "QLD",
    ) -> List[RegionBoundary]:
        """Return GeoJSON boundaries for all regions of the requested level."""

        boundaries: List[RegionBoundary] = []
        for record in self._iter_records(level):
            if record.state != state:
                continue
            geometry = self.loader.to_geojson(record)
            boundary = RegionBoundary(
                region_id=record.id,
                name=record.name,
                type=record.type,  # type: ignore[arg-type]
                geometry=geometry,
                properties={
                    "area_km2": record.geometry.area_km2,
                    "parent_region": record.parent_region,
                    "postcode": record.postcode,
                },
            )
            boundaries.append(boundary)
        return boundaries

    async def get_nearby_regions(
        self,
        lat: float,
        lng: float,
        level: str,
        radius_km: float,
    ) -> List[RegionSearchResult]:
        """Find regions whose centroid falls within the radius."""

        results: List[RegionSearchResult] = []
        query_coord = Coordinate(latitude=lat, longitude=lng)
        for record in self._iter_records(level):
            distance = self._calculate_distance(
                query_coord.latitude,
                query_coord.longitude,
                record.geometry.centroid.latitude,
                record.geometry.centroid.longitude,
            )
            if distance <= radius_km:
                results.append(self._to_search_result(record))

        results.sort(
            key=lambda r: self._calculate_distance(
                lat, lng, r.location.latitude, r.location.longitude
            )
        )
        return results

    async def get_region_boundary(
        self,
        region_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return GeoJSON Feature with the region's boundary geometry."""

        record = self.loader.get_record(region_id)
        if record is None:
            return None

        geometry = self.loader.to_geojson(record)
        
        # Return as GeoJSON Feature
        return {
            "type": "Feature",
            "id": record.id,
            "properties": {
                "id": record.id,
                "name": record.name,
                "type": record.type,
                "state": record.state,
                "area_km2": record.geometry.area_km2,
                "parent_region": record.parent_region,
                "postcode": record.postcode,
            },
            "geometry": geometry,
        }

    # ------------------------------------------------------------------
    # Internal helpers

    def _iter_records(self, region_type: Optional[str]) -> Iterable[RegionRecord]:
        return self.loader.get_records(region_type)

    def _match_score(self, query_lower: str, record: RegionRecord) -> Optional[int]:
        """Simple ranking: exact prefix wins, then substring, else None."""

        if query_lower == record.search_key:
            return 0
        if record.search_key.startswith(query_lower):
            return 1
        if query_lower in record.search_key:
            return 2
        if record.parent_region and query_lower in record.parent_region.lower():
            return 3
        return None

    def _to_search_result(self, record: RegionRecord) -> RegionSearchResult:
        return RegionSearchResult(
            id=record.id,
            name=record.name,
            type=record.type,  # type: ignore[arg-type]
            state=record.state,
            location=record.geometry.centroid,
            population=None,
            area_km2=record.geometry.area_km2,
        )

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula."""

        import math

        R = 6371  # km
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def _get_climate_data(
        self,
        record: RegionRecord,
        layers: Optional[List[str]] = None,
    ) -> Optional[Dict[str, ClimateDataPoint]]:
        try:
            centroid = record.geometry.centroid
            measurements = self.climate_service.get_climate_at(
                centroid.latitude,
                centroid.longitude,
                layers,
            )
            if not measurements:
                return None
            return measurements
        except Exception as exc:
            logger.warning("Failed to obtain climate data for %s: %s", record.id, exc)
            return None

    async def _build_region_response(
        self,
        record: RegionRecord,
        include_climate_data: bool,
    ) -> RegionResponse:
        geometry = record.geometry
        current_climate = None
        if include_climate_data:
            current_climate = await self._get_climate_data(record)

        return RegionResponse(
            id=record.id,
            name=record.name,
            type=record.type,  # type: ignore[arg-type]
            state=record.state,
            location=geometry.centroid,
            bounds=geometry.bounds,
            area_km2=geometry.area_km2,
            parent_region=record.parent_region,
            postcode=record.postcode,
            population=None,
            population_density=None,
            current_climate=current_climate,
            last_updated=datetime.utcnow(),
            data_sources=self._build_data_sources(current_climate),
        )

    def _build_data_sources(
        self,
        climate: Optional[Dict[str, ClimateDataPoint]],
    ) -> List[str]:
        sources = {"Queensland Government Open Data Portal"}
        if climate:
            for point in climate.values():
                config = CLIMATE_LAYER_CONFIGS.get(point.layer)
                if config:
                    sources.add(config.data_source)
        return sorted(sources)

    def _find_region_containing(self, point: Point) -> Optional[RegionRecord]:
        # Prefer suburb level, then fall back to LGA
        for region_type in ("suburb", "lga"):
            for record in self._iter_records(region_type):
                geom = record.geometry.geometry
                if geom.contains(point) or geom.touches(point):
                    return record
        return None
