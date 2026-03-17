from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.models.climate import ClimateDataPoint, ClimateLayer
from app.services.climate_data_service import ClimateDataService

logger = logging.getLogger(__name__)


class SscClimateService:
    """Loads precomputed SSC climate averages for API responses."""

    def __init__(self, data_path: Path | None = None) -> None:
        self._data_path = data_path or (
            Path(__file__).resolve().parents[2]
            / "data_pipeline"
            / "data"
            / "processed"
            / "geo"
            / "ssc_climate_values.json"
        )
        self._cached_mtime_ns: int | None = None
        self._cached_payload: dict[str, Any] | None = None
        self._categorizer = ClimateDataService()
        self._layer_units = {
            layer.value: settings.unit
            for layer, settings in self._categorizer._layers.items()
        }
        self._layer_precision = {
            layer.value: settings.precision
            for layer, settings in self._categorizer._layers.items()
        }

    def get_climate_for_ssc(self, ssc_id: str) -> Optional[Dict[str, ClimateDataPoint]]:
        payload = self._load_payload()
        if payload is None:
            return None

        regions = payload.get("regions", {})
        if not isinstance(regions, dict):
            return None

        region_payload = regions.get(ssc_id)
        if not isinstance(region_payload, dict):
            return None

        timestamp = self.get_ssc_timestamp()
        measurements: dict[str, ClimateDataPoint] = {}

        for layer_name, raw_value in region_payload.items():
            try:
                layer = ClimateLayer(layer_name)
            except ValueError:
                continue

            if not isinstance(raw_value, dict):
                continue

            numeric_value = raw_value.get("value")
            if numeric_value is None:
                continue

            try:
                value = float(numeric_value)
            except (TypeError, ValueError):
                continue

            if not math.isfinite(value):
                continue

            category = self._categorizer._categorize(layer, value)
            measurements[layer.value] = ClimateDataPoint(
                layer=layer,
                value=round(value, self._layer_precision.get(layer.value, 2)),
                unit=self._layer_units.get(layer.value, str(raw_value.get("unit") or "")),
                timestamp=timestamp,
                quality="estimated",
                category=category,
            )

        return measurements or None

    def get_ssc_timestamp(self) -> datetime:
        payload = self._load_payload()
        if payload is None:
            return datetime.utcnow()

        raw_timestamp = payload.get("timestamp")
        if not isinstance(raw_timestamp, str):
            return datetime.utcnow()

        try:
            parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid SSC climate timestamp: %s", raw_timestamp)
            return datetime.utcnow()

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _load_payload(self) -> dict[str, Any] | None:
        if not self._data_path.exists():
            self._cached_payload = None
            self._cached_mtime_ns = None
            return None

        mtime_ns = self._data_path.stat().st_mtime_ns
        if self._cached_payload is not None and self._cached_mtime_ns == mtime_ns:
            return self._cached_payload

        try:
            with self._data_path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            logger.warning("Failed to load SSC climate data from %s: %s", self._data_path, exc)
            self._cached_payload = None
            self._cached_mtime_ns = None
            return None

        self._cached_payload = payload
        self._cached_mtime_ns = mtime_ns
        return payload
