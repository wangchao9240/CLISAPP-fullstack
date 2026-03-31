import json
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import box

from unittest.mock import MagicMock, patch

from data_pipeline.processing.geo.compute_ssc_averages import (
    LayerSpec,
    SscRegion,
    _mean_value_for_region,
    compute_ssc_climate_averages,
)


def _write_test_ssc_shapefile(tmp_path: Path) -> Path:
    shapefile_dir = tmp_path / "ssc"
    shapefile_dir.mkdir(parents=True, exist_ok=True)
    shapefile_path = shapefile_dir / "D_lowPopMap_A.shp"
    gdf = gpd.GeoDataFrame(
        [
            {
                "MERGED_I": "10001",
                "MERGED_N": "Alpha Plains",
                "LGA_NAME": "Brisbane City",
                "geometry": box(0.0, 1.0, 1.0, 2.0),
            },
            {
                "MERGED_I": "10002",
                "MERGED_N": "Beta Ridge",
                "LGA_NAME": "Logan City",
                "geometry": box(10.0, 10.0, 11.0, 11.0),
            },
        ],
        crs="EPSG:4326",
    ).to_crs(epsg=3577)
    gdf.to_file(shapefile_path)
    return shapefile_path


def _write_test_raster(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    transform = from_bounds(0.0, 0.0, 2.0, 2.0, data.shape[1], data.shape[0])

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=np.float32,
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
    ) as dataset:
        dataset.write(data, 1)
        dataset.update_tags(creation_time="2026-03-17T12:00:00Z")


def test_compute_ssc_climate_averages_generates_expected_json(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    shapefile_path = _write_test_ssc_shapefile(tmp_path)
    output_path = tmp_path / "processed" / "geo" / "ssc_climate_values.json"
    raster_path = tmp_path / "data" / "processing" / "temp" / "temperature_latest.tif"
    _write_test_raster(raster_path)

    layer_specs = {
        "temperature": LayerSpec(
            name="temperature",
            raster_path=raster_path,
            unit="C",
        ),
        "humidity": LayerSpec(
            name="humidity",
            raster_path=tmp_path / "missing" / "humidity_latest.tif",
            unit="%",
        ),
    }

    with caplog.at_level(logging.INFO):
        result = compute_ssc_climate_averages(
            shapefile_path=shapefile_path,
            output_path=output_path,
            layer_specs=layer_specs,
        )

    assert result["ssc_count"] == 2
    assert result["layer_coverage"]["temperature"]["available"] is True
    assert result["layer_coverage"]["temperature"]["valid_ssc_count"] == 1
    assert result["layer_coverage"]["humidity"]["available"] is False

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["source"] == "Open-Meteo"
    assert payload["ssc_count"] == 2
    assert payload["timestamp"] == "2026-03-17T12:00:00Z"
    assert payload["regions"]["ssc_10001"] == {
        "name": "Alpha Plains",
        "group_id": "group_brisbane_city",
        "temperature": {"value": 10.0, "unit": "C"},
    }
    assert payload["regions"]["ssc_10002"] == {
        "name": "Beta Ridge",
        "group_id": "group_logan_city",
        "temperature": {"value": None, "unit": "C"},
    }
    assert any("temperature had 1 SSCs with 0 valid pixels" in message for message in caplog.messages)


@patch("data_pipeline.processing.geo.compute_ssc_averages.mask")
def test_mean_value_for_region_falls_back_to_nearest_pixel(mock_mask: MagicMock) -> None:
    """When mask() raises ValueError (tiny polygon), fallback samples the centroid pixel."""
    mock_mask.side_effect = ValueError("no data within geometry")

    mock_dataset = MagicMock()
    mock_dataset.name = "test_raster.tif"
    mock_dataset.sample.return_value = iter([np.array([42.0])])

    region = SscRegion(
        ssc_id="99999",
        name="Tiny Polygon",
        group_id="group_test",
        geometry={
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.001, 0.0], [0.001, 0.001], [0.0, 0.001], [0.0, 0.0]]],
        },
    )

    result = _mean_value_for_region(mock_dataset, region)

    assert result == 42.0
    mock_dataset.sample.assert_called_once()
