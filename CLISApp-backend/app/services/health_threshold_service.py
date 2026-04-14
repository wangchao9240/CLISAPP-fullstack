from __future__ import annotations

import argparse
import json
import logging
import sys
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from app.core.config import settings

logger = logging.getLogger(__name__)

EXPECTED_CATEGORIES = ("Good", "Moderate", "Unhealthy", "Hazardous")
REQUIRED_LAYERS = ("pm25", "uv", "temperature", "humidity", "precipitation")
REQUIRED_LAYER_KEYS = ("name", "unit", "thresholds", "advice")


class HealthThresholdConfigError(ValueError):
    """Raised when health threshold configuration fails validation."""


class HealthThresholdService:
    """Load and evaluate configured health thresholds for climate layers."""

    def __init__(self, thresholds_path: Path | None = None) -> None:
        self._project_root = Path(__file__).resolve().parents[2]
        self._thresholds_path = self._resolve_path(
            thresholds_path or settings.health_thresholds_path
        )
        self._numeric_bounds: dict[str, tuple[tuple[str, float, float | None], ...]] = {}
        self._config = self._load_and_validate()

    def _resolve_path(self, path_value: Path) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return self._project_root / path

    def get_risk_level(self, layer: str, value: float) -> str | None:
        numeric_value = float(value)

        for category, lower_bound, upper_bound in self._numeric_bounds.get(layer, ()):
            if upper_bound is None:
                if numeric_value >= lower_bound:
                    return category
            elif lower_bound <= numeric_value < upper_bound:
                return category

        return None

    def get_advice(self, layer: str, risk_level: str) -> str:
        layer_config = self._config["layers"].get(layer)
        if layer_config is None:
            return ""

        advice = layer_config["advice"].get(risk_level)
        return str(advice) if advice is not None else ""

    def get_layer_config(self, layer: str) -> Mapping[str, Any] | None:
        layer_config = self._config["layers"].get(layer)
        if layer_config is None:
            return None
        # Returned mapping is a read-only view of the loaded config.
        return layer_config

    def list_layers(self) -> list[str]:
        return sorted(self._config["layers"])

    def _load_and_validate(self) -> MappingProxyType[str, Any]:
        try:
            with self._thresholds_path.open(encoding="utf-8") as handle:
                config = json.load(handle)
        except FileNotFoundError as exc:
            raise HealthThresholdConfigError(
                f"Thresholds config not found at {self._thresholds_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise HealthThresholdConfigError(
                f"Thresholds config has invalid JSON: {exc}"
            ) from exc

        self._validate_config(config)
        self._numeric_bounds = {
            layer: tuple(
                (
                    category,
                    float(bounds[0]),
                    float(bounds[1]) if bounds[1] is not None else None,
                )
                for category, bounds in cfg["thresholds"].items()
            )
            for layer, cfg in config["layers"].items()
        }
        logger.info("Loaded health thresholds config from %s", self._thresholds_path)
        return self._freeze(config)

    def _validate_config(self, config: Any) -> None:
        if not isinstance(config, dict) or not isinstance(config.get("layers"), dict):
            raise HealthThresholdConfigError("Missing top-level 'layers' key")

        layers = config["layers"]
        missing_layers = [layer for layer in REQUIRED_LAYERS if layer not in layers]
        if missing_layers:
            raise HealthThresholdConfigError(
                f"Missing required layers: {missing_layers}"
            )

        for layer_name in REQUIRED_LAYERS:
            self._validate_layer(layer_name, layers[layer_name])

    def _validate_layer(self, layer_name: str, layer_config: Any) -> None:
        if not isinstance(layer_config, dict):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' must be a mapping"
            )

        for key in REQUIRED_LAYER_KEYS:
            if key not in layer_config:
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' missing required key '{key}'"
                )

        if not isinstance(layer_config["name"], str):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' key 'name' must be a string"
            )
        if not isinstance(layer_config["unit"], str):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' key 'unit' must be a string"
            )
        if not isinstance(layer_config["thresholds"], dict):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' key 'thresholds' must be a mapping"
            )
        if not isinstance(layer_config["advice"], dict):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' key 'advice' must be a mapping"
            )

        self._validate_thresholds(layer_name, layer_config["thresholds"])
        self._validate_advice(
            layer_name, layer_config["thresholds"], layer_config["advice"]
        )

    def _validate_thresholds(
        self, layer_name: str, thresholds: dict[str, Any]
    ) -> None:
        expected_categories = list(EXPECTED_CATEGORIES)
        actual_categories = list(thresholds.keys())
        if actual_categories != expected_categories:
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' thresholds must define categories in order "
                f"{expected_categories}; found {actual_categories}"
            )

        previous_lower_bound: float | None = None
        for category, bounds in thresholds.items():
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' category '{category}' must define a "
                    "2-element [lower, upper] list"
                )

            lower_bound, upper_bound = bounds
            if not self._is_number(lower_bound):
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' category '{category}' lower bound "
                    "must be numeric"
                )
            if upper_bound is not None and not self._is_number(upper_bound):
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' category '{category}' upper bound "
                    "must be numeric or null"
                )

            numeric_lower_bound = float(lower_bound)
            if (
                previous_lower_bound is not None
                and numeric_lower_bound < previous_lower_bound
            ):
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' lower bounds must be monotonically "
                    "non-decreasing"
                )
            previous_lower_bound = numeric_lower_bound

        if thresholds["Hazardous"][1] is not None:
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' category 'Hazardous' must have an "
                "unbounded upper bound"
            )

    def _validate_advice(
        self,
        layer_name: str,
        thresholds: dict[str, Any],
        advice: dict[str, Any],
    ) -> None:
        if list(advice.keys()) != list(thresholds.keys()):
            raise HealthThresholdConfigError(
                f"layer '{layer_name}' advice keys must exactly match thresholds"
            )

        for category, advice_text in advice.items():
            if not isinstance(advice_text, str) or not advice_text.strip():
                raise HealthThresholdConfigError(
                    f"layer '{layer_name}' advice for category '{category}' "
                    "must be a non-empty string"
                )

    def _freeze(self, value: Any) -> Any:
        if isinstance(value, dict):
            return MappingProxyType(
                {key: self._freeze(child_value) for key, child_value in value.items()}
            )
        if isinstance(value, list):
            return tuple(self._freeze(item) for item in value)
        return value

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)


@lru_cache(maxsize=1)
def get_health_threshold_service() -> HealthThresholdService:
    return HealthThresholdService()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate CLISApp health threshold configuration."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Optional path to a health threshold JSON file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        service = HealthThresholdService(thresholds_path=args.path)
    except HealthThresholdConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"OK: {len(service.list_layers())} layers configured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
