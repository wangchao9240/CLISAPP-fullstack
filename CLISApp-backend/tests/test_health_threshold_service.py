from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from app.services.health_threshold_service import (
    HealthThresholdConfigError,
    HealthThresholdService,
    get_health_threshold_service,
)
from app.services.notification_service import NotificationService

EXPECTED_CATEGORIES = ("Good", "Moderate", "Unhealthy", "Hazardous")
EXPECTED_LAYERS = ("pm25", "uv", "temperature", "humidity", "precipitation")


def build_valid_config() -> dict[str, object]:
    return {
        "layers": {
            "pm25": {
                "name": "PM2.5 Concentration",
                "unit": "ug/m3",
                "thresholds": {
                    "Good": [0, 12],
                    "Moderate": [12, 35],
                    "Unhealthy": [35, 55],
                    "Hazardous": [55, None],
                },
                "advice": {
                    "Good": "Air quality is satisfactory.",
                    "Moderate": "Sensitive groups should limit prolonged outdoor exertion.",
                    "Unhealthy": "Everyone should reduce outdoor activity.",
                    "Hazardous": "Avoid all outdoor activity. Stay indoors with windows closed.",
                },
            },
            "uv": {
                "name": "UV Index",
                "unit": "UVI",
                "thresholds": {
                    "Good": [0, 3],
                    "Moderate": [3, 6],
                    "Unhealthy": [6, 8],
                    "Hazardous": [8, None],
                },
                "advice": {
                    "Good": "UV levels are low.",
                    "Moderate": "Wear sunscreen and a hat.",
                    "Unhealthy": "Seek shade around midday.",
                    "Hazardous": "Avoid direct sun exposure.",
                },
            },
            "temperature": {
                "name": "2m Temperature",
                "unit": "C",
                "thresholds": {
                    "Good": [0, 10],
                    "Moderate": [10, 20],
                    "Unhealthy": [20, 30],
                    "Hazardous": [30, None],
                },
                "advice": {
                    "Good": "Temperature is comfortable.",
                    "Moderate": "Carry water.",
                    "Unhealthy": "Limit strenuous outdoor activity.",
                    "Hazardous": "Avoid outdoor exertion.",
                },
            },
            "humidity": {
                "name": "Relative Humidity",
                "unit": "%",
                "thresholds": {
                    "Good": [0, 30],
                    "Moderate": [30, 50],
                    "Unhealthy": [50, 70],
                    "Hazardous": [70, None],
                },
                "advice": {
                    "Good": "Humidity is comfortable.",
                    "Moderate": "Drink water regularly.",
                    "Unhealthy": "Reduce strenuous activity.",
                    "Hazardous": "Move to a cool, dry place.",
                },
            },
            "precipitation": {
                "name": "Precipitation",
                "unit": "mm/hour",
                "thresholds": {
                    "Good": [0, 0.5],
                    "Moderate": [0.5, 2],
                    "Unhealthy": [2, 10],
                    "Hazardous": [10, None],
                },
                "advice": {
                    "Good": "Conditions are manageable.",
                    "Moderate": "Carry rain protection.",
                    "Unhealthy": "Avoid unnecessary travel.",
                    "Hazardous": "Stay off flooded roads.",
                },
            },
        }
    }


@pytest.fixture
def valid_config_path(tmp_path: Path) -> Path:
    path = tmp_path / "health_thresholds.json"
    path.write_text(json.dumps(build_valid_config()), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def valid_config_path_module(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("health_cfg") / "health_thresholds.json"
    path.write_text(json.dumps(build_valid_config()), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def service_module(valid_config_path_module: Path) -> HealthThresholdService:
    return HealthThresholdService(valid_config_path_module)


@pytest.fixture(scope="module")
def real_service_module() -> HealthThresholdService:
    real_config_path = Path(__file__).resolve().parents[1] / "data" / "health_thresholds.json"
    return HealthThresholdService(real_config_path)


def mutate_missing_layers(config: dict[str, object]) -> None:
    config.pop("layers")


def mutate_missing_required_layer(config: dict[str, object]) -> None:
    config["layers"].pop("pm25")


def mutate_missing_thresholds(config: dict[str, object]) -> None:
    config["layers"]["pm25"].pop("thresholds")


def mutate_missing_advice(config: dict[str, object]) -> None:
    config["layers"]["pm25"].pop("advice")


def mutate_three_categories(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"].pop("Unhealthy")


def mutate_five_categories(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"]["Extreme"] = [999, None]


def mutate_wrong_order(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"] = {
        "Moderate": [12, 35],
        "Good": [0, 12],
        "Unhealthy": [35, 55],
        "Hazardous": [55, None],
    }


def mutate_hazardous_upper_bound(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"]["Hazardous"] = [55, 99]


def mutate_non_monotonic_lower_bounds(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"]["Unhealthy"] = [11, 55]


def mutate_threshold_not_two_elements(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"]["Good"] = [0]


def mutate_string_bound(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["thresholds"]["Good"] = ["0", 12]


def mutate_missing_advice_entry(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["advice"].pop("Unhealthy")


def mutate_empty_advice(config: dict[str, object]) -> None:
    config["layers"]["pm25"]["advice"]["Unhealthy"] = ""


def write_config(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "health_thresholds.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_get_risk_level_handles_pm25_boundaries(
    service_module: HealthThresholdService,
) -> None:
    assert service_module.get_risk_level("pm25", 0.0) == "Good"
    assert service_module.get_risk_level("pm25", 11.9) == "Good"
    assert service_module.get_risk_level("pm25", 12.0) == "Moderate"
    assert service_module.get_risk_level("pm25", 35.0) == "Unhealthy"
    assert service_module.get_risk_level("pm25", 55.0) == "Hazardous"
    assert service_module.get_risk_level("pm25", 500.0) == "Hazardous"
    assert service_module.get_risk_level("pm25", -1.0) is None


@pytest.mark.parametrize(
    ("layer", "value", "expected"),
    [
        ("uv", 6.5, "Unhealthy"),
        ("temperature", 25.0, "Unhealthy"),
        ("humidity", 60.0, "Unhealthy"),
        ("precipitation", 4.0, "Unhealthy"),
    ],
)
def test_get_risk_level_handles_other_layers(
    service_module: HealthThresholdService, layer: str, value: float, expected: str
) -> None:
    assert service_module.get_risk_level(layer, value) == expected


def test_get_risk_level_returns_none_for_unknown_layer(
    service_module: HealthThresholdService,
) -> None:
    assert service_module.get_risk_level("unknown_layer", 10.0) is None


def test_get_advice_and_layer_config(service_module: HealthThresholdService) -> None:
    assert (
        service_module.get_advice("pm25", "Unhealthy")
        == "Everyone should reduce outdoor activity."
    )
    assert service_module.get_advice("pm25", "NonExistent") == ""
    assert service_module.get_layer_config("pm25")["name"] == "PM2.5 Concentration"
    assert service_module.get_layer_config("missing") is None


def test_list_layers_returns_sorted_keys(service_module: HealthThresholdService) -> None:
    assert service_module.list_layers() == sorted(EXPECTED_LAYERS)


@pytest.mark.parametrize(
    ("mutator", "expected_message"),
    [
        (mutate_missing_layers, "Missing top-level 'layers' key"),
        (mutate_missing_required_layer, "Missing required layers"),
        (mutate_missing_thresholds, "layer 'pm25' missing required key 'thresholds'"),
        (mutate_missing_advice, "layer 'pm25' missing required key 'advice'"),
        (
            mutate_three_categories,
            "layer 'pm25' thresholds must define categories in order",
        ),
        (
            mutate_five_categories,
            "layer 'pm25' thresholds must define categories in order",
        ),
        (
            mutate_wrong_order,
            "layer 'pm25' thresholds must define categories in order",
        ),
        (
            mutate_hazardous_upper_bound,
            "layer 'pm25' category 'Hazardous' must have an unbounded upper bound",
        ),
        (
            mutate_non_monotonic_lower_bounds,
            "layer 'pm25' lower bounds must be monotonically non-decreasing",
        ),
        (
            mutate_threshold_not_two_elements,
            "layer 'pm25' category 'Good' must define a 2-element [lower, upper] list",
        ),
        (
            mutate_string_bound,
            "layer 'pm25' category 'Good' lower bound must be numeric",
        ),
        (
            mutate_missing_advice_entry,
            "layer 'pm25' advice keys must exactly match thresholds",
        ),
        (
            mutate_empty_advice,
            "layer 'pm25' advice for category 'Unhealthy' must be a non-empty string",
        ),
    ],
)
def test_invalid_config_raises_clear_error(
    tmp_path: Path, mutator, expected_message: str
) -> None:
    payload = copy.deepcopy(build_valid_config())
    mutator(payload)
    config_path = write_config(tmp_path, payload)

    with pytest.raises(HealthThresholdConfigError, match=re.escape(expected_message)):
        HealthThresholdService(config_path)


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "missing.json"

    with pytest.raises(HealthThresholdConfigError, match="config not found"):
        HealthThresholdService(config_path)


def test_invalid_json_raises_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "health_thresholds.json"
    config_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(HealthThresholdConfigError, match="invalid JSON"):
        HealthThresholdService(config_path)


def test_get_health_threshold_service_returns_cached_singleton(
    valid_config_path: Path, monkeypatch
) -> None:
    get_health_threshold_service.cache_clear()
    monkeypatch.setattr(
        "app.services.health_threshold_service.settings.health_thresholds_path",
        valid_config_path,
    )

    first = get_health_threshold_service()
    second = get_health_threshold_service()

    assert first is second
    get_health_threshold_service.cache_clear()


@pytest.mark.parametrize("layer", EXPECTED_LAYERS)
def test_real_config_uses_unhealthy_categories(
    real_service_module: HealthThresholdService, layer: str
) -> None:
    layer_config = real_service_module.get_layer_config(layer)

    assert layer_config is not None
    assert tuple(layer_config["thresholds"].keys()) == EXPECTED_CATEGORIES
    assert "Poor" not in layer_config["thresholds"]


def test_real_config_pm25_spot_check(
    real_service_module: HealthThresholdService,
) -> None:
    assert real_service_module.list_layers() == sorted(EXPECTED_LAYERS)
    assert real_service_module.get_risk_level("pm25", 35.0) == "Unhealthy"


def test_notification_service_evaluate_layers_uses_unhealthy_name(tmp_path: Path) -> None:
    real_config_path = Path(__file__).resolve().parents[1] / "data" / "health_thresholds.json"
    service = NotificationService(
        credentials_path=tmp_path / "missing-service-account.json",
        thresholds_path=real_config_path,
    )

    breaches = service.evaluate_layers({"pm25": 40.0})

    assert len(breaches) == 1
    assert breaches[0]["risk_level"] == "Unhealthy"
