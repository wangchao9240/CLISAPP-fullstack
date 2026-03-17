import asyncio
import time

from shapely.geometry import box

from app.models.region import Bounds, Coordinate
from app.services.region_data_loader import RegionGeometry, RegionRecord
from app.services.region_service import RegionService


TEST_GEOMETRY = box(153.0, -27.6, 153.1, -27.5)


class FakeLoader:
    def __init__(self, records_by_type: dict[str, list[RegionRecord]]) -> None:
        self._records_by_type = records_by_type
        self._records_by_id = {
            record.id: record
            for records in records_by_type.values()
            for record in records
        }

    def get_records(self, region_type: str | None = None):
        if region_type is None:
            return self._records_by_id.values()
        return self._records_by_type.get(region_type, [])

    def get_record(self, region_id: str):
        return self._records_by_id.get(region_id)


class StubClimateDataService:
    def available_layers(self):
        return []

    def get_climate_at(self, latitude: float, longitude: float, layers=None):
        return {}


class StubSscClimateService:
    def get_climate_for_ssc(self, ssc_id: str):
        return {}


def _make_geometry(geometry=TEST_GEOMETRY) -> RegionGeometry:
    min_x, min_y, max_x, max_y = geometry.bounds
    centroid = geometry.centroid
    return RegionGeometry(
        geometry=geometry,
        bounds=Bounds(
            northeast=Coordinate(latitude=max_y, longitude=max_x),
            southwest=Coordinate(latitude=min_y, longitude=min_x),
        ),
        centroid=Coordinate(latitude=float(centroid.y), longitude=float(centroid.x)),
        area_km2=1.0,
    )


def _make_record(
    region_id: str,
    name: str,
    region_type: str,
    *,
    parent_region: str | None = None,
    geometry=TEST_GEOMETRY,
) -> RegionRecord:
    return RegionRecord(
        id=region_id,
        name=name,
        type=region_type,
        state="QLD",
        parent_region=parent_region,
        postcode=None,
        search_key=name.lower(),
        geometry=_make_geometry(geometry),
        raw_properties={},
    )


def _make_service(records_by_type: dict[str, list[RegionRecord]]) -> RegionService:
    service = RegionService.__new__(RegionService)
    service.loader = FakeLoader(records_by_type)
    service.climate_service = StubClimateDataService()
    service.ssc_climate_service = StubSscClimateService()
    return service


def test_search_returns_ssc_by_name() -> None:
    service = _make_service(
        {
            "ssc": [
                _make_record(
                    "ssc_20161",
                    "Sunnybank Hills",
                    "ssc",
                    parent_region="Brisbane City",
                )
            ]
        }
    )

    results = asyncio.run(service.search_regions("sunny"))

    assert [result.id for result in results] == ["ssc_20161"]
    assert results[0].type == "ssc"


def test_search_returns_ssc_by_parent_region() -> None:
    service = _make_service(
        {
            "ssc": [
                _make_record(
                    "ssc_20161",
                    "Sunnybank Hills",
                    "ssc",
                    parent_region="Brisbane City",
                )
            ]
        }
    )

    results = asyncio.run(service.search_regions("brisbane"))

    assert [result.id for result in results] == ["ssc_20161"]
    assert results[0].type == "ssc"


def test_get_region_by_id_returns_ssc() -> None:
    service = _make_service(
        {
            "ssc": [
                _make_record(
                    "ssc_20161",
                    "Sunnybank Hills",
                    "ssc",
                    parent_region="Brisbane City",
                )
            ]
        }
    )

    result = asyncio.run(service.get_region_by_id("ssc_20161", include_climate_data=False))

    assert result is not None
    assert result.id == "ssc_20161"
    assert result.type == "ssc"
    assert result.name == "Sunnybank Hills"


def test_coordinate_lookup_prefers_ssc() -> None:
    service = _make_service(
        {
            "ssc": [
                _make_record(
                    "ssc_20161",
                    "Sunnybank Hills",
                    "ssc",
                    parent_region="Brisbane City",
                )
            ],
            "suburb": [
                _make_record(
                    "suburb_20161",
                    "Sunnybank Hills",
                    "suburb",
                    parent_region="Brisbane City",
                )
            ],
            "lga": [
                _make_record(
                    "lga_31000",
                    "Brisbane City",
                    "lga",
                    geometry=box(152.9, -27.7, 153.2, -27.4),
                )
            ],
        }
    )

    result = asyncio.run(
        service.get_region_by_coordinates(-27.55, 153.05, include_climate_data=False)
    )

    assert result is not None
    assert result.id == "ssc_20161"
    assert result.type == "ssc"


def test_search_performance_under_one_second() -> None:
    ssc_records = [
        _make_record(
            f"ssc_{index:05d}",
            f"Region {index}",
            "ssc",
            parent_region=f"Group {index % 20}",
        )
        for index in range(2999)
    ]
    ssc_records.append(
        _make_record(
            "ssc_20161",
            "Sunnybank Hills",
            "ssc",
            parent_region="Brisbane City",
        )
    )
    service = _make_service({"ssc": ssc_records})

    started_at = time.perf_counter()
    results = asyncio.run(service.search_regions("sunny"))
    elapsed = time.perf_counter() - started_at

    assert [result.id for result in results] == ["ssc_20161"]
    assert elapsed < 1.0
