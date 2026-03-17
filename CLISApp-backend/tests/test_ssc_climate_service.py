import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.models.climate import ClimateDataPoint, ClimateLayer
from app.services.region_service import RegionService
from app.services.ssc_climate_service import SscClimateService


def _write_ssc_payload(path: Path, *, timestamp: str, temperature: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": timestamp,
        "source": "Open-Meteo",
        "ssc_count": 1,
        "regions": {
            "ssc_10001": {
                "name": "Alpha Plains",
                "group_id": "group_brisbane_city",
                "temperature": {"value": temperature, "unit": "C"},
                "humidity": {"value": None, "unit": "%"},
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_ssc_climate_service_parses_points_and_reloads_on_mtime_change(tmp_path: Path) -> None:
    data_path = tmp_path / "ssc_climate_values.json"
    _write_ssc_payload(
        data_path,
        timestamp="2026-03-17T12:00:00Z",
        temperature=31.25,
    )

    service = SscClimateService(data_path=data_path)
    first_result = service.get_climate_for_ssc("ssc_10001")
    assert first_result is not None
    assert set(first_result) == {"temperature"}
    assert first_result["temperature"].unit == "°C"
    assert first_result["temperature"].category == "High"
    assert service.get_ssc_timestamp() == datetime(2026, 3, 17, 12, 0, tzinfo=UTC)

    time.sleep(0.01)
    _write_ssc_payload(
        data_path,
        timestamp="2026-03-17T13:30:00Z",
        temperature=18.4,
    )

    second_result = service.get_climate_for_ssc("ssc_10001")
    assert second_result is not None
    assert second_result["temperature"].value == 18.4
    assert second_result["temperature"].category == "Low"
    assert service.get_ssc_timestamp() == datetime(2026, 3, 17, 13, 30, tzinfo=UTC)


def test_region_service_prefers_ssc_data_and_falls_back_for_missing_layers() -> None:
    service = RegionService.__new__(RegionService)

    class FakeSscClimateService:
        def get_climate_for_ssc(self, ssc_id: str):
            assert ssc_id == "ssc_10001"
            return {
                "temperature": ClimateDataPoint(
                    layer=ClimateLayer.TEMPERATURE,
                    value=26.5,
                    unit="°C",
                    timestamp=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
                    quality="estimated",
                    category="Moderate",
                )
            }

    class FakeClimateDataService:
        def __init__(self) -> None:
            self.calls = []

        def available_layers(self):
            return [ClimateLayer.TEMPERATURE, ClimateLayer.HUMIDITY]

        def get_climate_at(self, latitude: float, longitude: float, layers=None):
            self.calls.append((latitude, longitude, layers))
            return {
                "humidity": ClimateDataPoint(
                    layer=ClimateLayer.HUMIDITY,
                    value=72,
                    unit="%",
                    timestamp=datetime(2026, 3, 17, 12, 0, tzinfo=UTC),
                    quality="estimated",
                    category="High",
                )
            }

    fake_point_service = FakeClimateDataService()
    service.ssc_climate_service = FakeSscClimateService()
    service.climate_service = fake_point_service

    record = SimpleNamespace(
        id="ssc_10001",
        geometry=SimpleNamespace(
            centroid=SimpleNamespace(latitude=-27.5, longitude=153.0)
        ),
    )

    result = asyncio.run(
        service._get_climate_data(record, layers=["temperature", "humidity"])
    )

    assert result is not None
    assert set(result) == {"temperature", "humidity"}
    assert result["temperature"].value == 26.5
    assert result["humidity"].value == 72
    assert fake_point_service.calls == [(-27.5, 153.0, ["humidity"])]
