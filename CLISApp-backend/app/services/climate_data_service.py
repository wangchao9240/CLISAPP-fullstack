from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import rasterio
from rasterio.windows import Window

from app.models.climate import CLIMATE_LAYER_CONFIGS, ClimateDataPoint, ClimateLayer


@dataclass(frozen=True)
class _LayerSettings:
    layer: ClimateLayer
    path: Path
    unit: str
    data_source: str
    precision: int = 2
    scale: float = 1.0
    offset: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    transform: Optional[str] = None  # e.g. "kelvin_to_celsius", "uv_to_index"


class ClimateDataService:
    """Samples processed GeoTIFF rasters to provide point climate measurements."""

    CATEGORY_LABELS: List[str] = ["Very Low", "Low", "Moderate", "High", "Very High"]

    def __init__(self) -> None:
        base_path = (
            Path(__file__).resolve().parents[2] / "data_pipeline" / "data" / "processed"
        )

        self._order: List[ClimateLayer] = list(CLIMATE_LAYER_CONFIGS.keys())
        self._layers: Dict[ClimateLayer, _LayerSettings] = {
            ClimateLayer.PM25: _LayerSettings(
                layer=ClimateLayer.PM25,
                path=base_path / "pm25" / "pm25_qld_cams_processed.tif",
                unit="µg/m³",
                data_source="Copernicus CAMS",
                precision=1,
                min_value=0.0,
            ),
            ClimateLayer.PRECIPITATION: _LayerSettings(
                layer=ClimateLayer.PRECIPITATION,
                path=base_path / "gpm" / "imerg_daily_precip_qld.tif",
                unit="mm/day",
                data_source="NASA GPM IMERG",
                precision=1,
                min_value=0.0,
            ),
            ClimateLayer.UV: _LayerSettings(
                layer=ClimateLayer.UV,
                path=base_path / "uv" / "cams_uv_qld.tif",
                unit="UVI",
                data_source="Copernicus CAMS",
                precision=1,
                min_value=0.0,
                transform="uv_to_index",
            ),
            ClimateLayer.HUMIDITY: _LayerSettings(
                layer=ClimateLayer.HUMIDITY,
                path=base_path / "cams" / "cams_rh_qld.tif",
                unit="%",
                data_source="Copernicus CAMS",
                precision=0,
                min_value=0.0,
                max_value=100.0,
            ),
            ClimateLayer.TEMPERATURE: _LayerSettings(
                layer=ClimateLayer.TEMPERATURE,
                path=base_path / "temp" / "cams_t2m_qld.tif",
                unit="°C",
                data_source="Copernicus CAMS",
                precision=1,
            ),
        }

    def available_layers(self) -> Iterable[ClimateLayer]:
        return self._layers.keys()

    def get_climate_at(
        self,
        latitude: float,
        longitude: float,
        layers: Optional[Iterable[str]] = None,
    ) -> Dict[str, ClimateDataPoint]:
        """Sample all requested layers at the provided coordinate."""

        results: Dict[str, ClimateDataPoint] = {}

        if layers is None:
            target_layers = self._order
        else:
            target_layers = []
            for layer_name in layers:
                try:
                    layer = ClimateLayer(layer_name)
                    if layer in self._layers:
                        target_layers.append(layer)
                except ValueError:
                    continue

        for layer in target_layers:
            layer_settings = self._layers.get(layer)
            if not layer_settings or not layer_settings.path.exists():
                continue

            value = self._sample_layer(layer_settings, latitude, longitude)
            if value is None:
                continue

            value = self._apply_transform(layer_settings, value)
            value = self._apply_bounds(layer_settings, value)
            if value is None:
                continue

            category = self._categorize(layer, value)
            results[layer.value] = ClimateDataPoint(
                layer=layer,
                value=round(value, layer_settings.precision),
                unit=layer_settings.unit,
                timestamp=datetime.utcnow(),
                quality="estimated",
                category=category,
            )

        return results

    def _sample_layer(
        self,
        settings: _LayerSettings,
        latitude: float,
        longitude: float,
    ) -> Optional[float]:
        try:
            with rasterio.open(settings.path) as dataset:
                sample = next(dataset.sample([(longitude, latitude)]), None)
                value: Optional[float] = None

                if sample is not None and len(sample) > 0:
                    raw_value = sample[0]
                    if not self._is_nodata(dataset, raw_value):
                        value = float(raw_value)

                if value is not None:
                    return value

                # Fallback: search a small window around the location
                row, col = dataset.index(longitude, latitude)
                window = Window(
                    max(col - 1, 0),
                    max(row - 1, 0),
                    3,
                    3,
                )
                data = dataset.read(1, window=window, masked=True)
                if data.size == 0:
                    return None

                valid = (
                    data.compressed()
                    if np.ma.isMaskedArray(data)
                    else data[np.isfinite(data)]
                )
                if valid.size == 0:
                    return None
                return float(np.mean(valid))
        except Exception:
            return None

    def _apply_transform(self, settings: _LayerSettings, value: float) -> float:
        transformed = value * settings.scale + settings.offset
        if settings.transform == "kelvin_to_celsius":
            transformed = transformed - 273.15
        elif settings.transform == "uv_to_index":
            # CAMS biologically effective dose rate to UV index approximation
            transformed = max(transformed / 0.025, 0.0)
        return transformed

    def _apply_bounds(self, settings: _LayerSettings, value: float) -> Optional[float]:
        if settings.min_value is not None and value < settings.min_value:
            value = settings.min_value
        if settings.max_value is not None and value > settings.max_value:
            value = settings.max_value
        if not np.isfinite(value):
            return None
        return value

    def _categorize(self, layer: ClimateLayer, value: float) -> Optional[str]:
        config = CLIMATE_LAYER_CONFIGS.get(layer)
        if not config:
            return None

        thresholds = config.thresholds
        if not thresholds:
            return None

        for idx, threshold in enumerate(thresholds[1:], start=1):
            if value < threshold:
                return self.CATEGORY_LABELS[min(idx - 1, len(self.CATEGORY_LABELS) - 1)]
        return self.CATEGORY_LABELS[min(len(thresholds) - 1, len(self.CATEGORY_LABELS) - 1)]

    @staticmethod
    def _is_nodata(dataset: rasterio.io.DatasetReader, value: float) -> bool:
        if value is None:
            return True
        if dataset.nodata is not None and value == dataset.nodata:
            return True
        if isinstance(value, float) and not np.isfinite(value):
            return True
        return False
