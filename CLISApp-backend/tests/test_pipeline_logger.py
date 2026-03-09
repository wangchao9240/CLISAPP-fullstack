import asyncio
import importlib
import json
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from data_pipeline.pipeline_logger import LayerResult, PipelineExecutionLog


def parse_json_line(line: str) -> dict:
    return json.loads(line)


class FakeArray:
    def __init__(self, values):
        self.values = values
        self.shape = (len(values), len(values[0]) if values else 0)
        self.size = sum(len(row) for row in values)

    def astype(self, _dtype):
        return self


class FakeMask:
    def __init__(self, values):
        self.values = values

    def __invert__(self):
        return FakeMask([[not cell for cell in row] for row in self.values])


STUB_MODULES = [
    "numpy", "rasterio", "rasterio.crs", "rasterio.transform",
    "data_pipeline.downloads.openmeteo.fetch_realtime",
]


def ensure_scientific_stubs():
    """Inject lightweight stubs for heavy scientific dependencies.

    Tracks which modules were injected so cleanup can restore original state.
    """
    if "numpy" not in sys.modules:
        numpy_module = types.ModuleType("numpy")
        numpy_module.float32 = float
        numpy_module.nan = float("nan")

        def arange(start, stop, step):
            values = []
            current = start
            while current <= stop + 1e-9:
                values.append(current)
                current += step
            return values

        def isnan(array):
            return FakeMask(
                [
                    [cell != cell for cell in row]
                    for row in getattr(array, "values", array)
                ]
            )

        def count_nonzero(mask):
            values = getattr(mask, "values", mask)
            return sum(1 for row in values for cell in row if cell)

        numpy_module.arange = arange
        numpy_module.isnan = isnan
        numpy_module.count_nonzero = count_nonzero
        sys.modules["numpy"] = numpy_module

    if "rasterio" not in sys.modules:
        rasterio_module = types.ModuleType("rasterio")

        def open_(*args, **kwargs):
            raise AssertionError("rasterio.open should be patched in tests")

        rasterio_module.open = open_
        sys.modules["rasterio"] = rasterio_module

    if "rasterio.crs" not in sys.modules:
        crs_module = types.ModuleType("rasterio.crs")

        class CRS:
            @staticmethod
            def from_epsg(_value):
                return "EPSG:4326"

        crs_module.CRS = CRS
        sys.modules["rasterio.crs"] = crs_module

    if "rasterio.transform" not in sys.modules:
        transform_module = types.ModuleType("rasterio.transform")
        transform_module.from_bounds = lambda *args, **kwargs: ("transform", args, kwargs)
        sys.modules["rasterio.transform"] = transform_module

    if "data_pipeline.downloads.openmeteo.fetch_realtime" not in sys.modules:
        fetch_module = types.ModuleType("data_pipeline.downloads.openmeteo.fetch_realtime")

        class OpenMeteoFetcher:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

            async def fetch_all_data(self, _grid_points):
                return {}

        fetch_module.OpenMeteoFetcher = OpenMeteoFetcher
        sys.modules["data_pipeline.downloads.openmeteo.fetch_realtime"] = fetch_module


@pytest.fixture()
def process_module():
    """Load process_all_layers with stubs, clean up sys.modules after test."""
    saved = {k: sys.modules[k] for k in STUB_MODULES if k in sys.modules}
    ensure_scientific_stubs()
    sys.modules.pop("data_pipeline.config.grid_config", None)
    sys.modules.pop("data_pipeline.processing.openmeteo.process_all_layers", None)
    mod = importlib.import_module("data_pipeline.processing.openmeteo.process_all_layers")
    yield mod
    # Restore original modules or remove stubs
    for key in STUB_MODULES:
        if key in saved:
            sys.modules[key] = saved[key]
        else:
            sys.modules.pop(key, None)
    sys.modules.pop("data_pipeline.config.grid_config", None)
    sys.modules.pop("data_pipeline.processing.openmeteo.process_all_layers", None)


def test_pipeline_execution_log_and_layer_result_are_frozen():
    start_time = datetime(2026, 3, 8, 1, 0, 0)
    end_time = start_time + timedelta(seconds=12)
    layer_result = LayerResult(
        layer_name="temperature",
        status="success",
        start_time=start_time,
        end_time=end_time,
        duration_seconds=12.0,
    )
    execution_log = PipelineExecutionLog(
        run_id="run-123",
        start_time=start_time,
        end_time=end_time,
        trigger_type="manual",
        layer_results={"temperature": layer_result},
    )

    assert execution_log.layer_results["temperature"] == layer_result

    with pytest.raises(AttributeError):
        layer_result.status = "failed"

    with pytest.raises(AttributeError):
        execution_log.run_id = "run-456"


def test_format_summary_with_mixed_results_is_parseable():
    start_time = datetime(2026, 3, 8, 1, 0, 0)
    success_end = start_time + timedelta(seconds=10)
    failed_end = start_time + timedelta(seconds=18)

    execution_log = PipelineExecutionLog(
        run_id="run-456",
        start_time=start_time,
        end_time=start_time + timedelta(seconds=20),
        trigger_type="scheduled",
        layer_results={
            "temperature": LayerResult(
                layer_name="temperature",
                status="success",
                start_time=start_time,
                end_time=success_end,
                duration_seconds=10.0,
            ),
            "humidity": LayerResult(
                layer_name="humidity",
                status="failed",
                start_time=start_time,
                end_time=failed_end,
                duration_seconds=18.0,
                error_message="humidity exploded",
                error_traceback="Traceback ... RuntimeError: humidity exploded",
            ),
        },
    )

    summary = execution_log.format_summary(data_timestamp="20260308_010000")
    payload = parse_json_line(summary)

    assert payload["event"] == "pipeline_summary"
    assert payload["run_id"] == "run-456"
    assert payload["trigger_type"] == "scheduled"
    assert payload["attempted"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert payload["skipped"] == 0
    assert payload["data_timestamp"] == "20260308_010000"
    assert payload["layer_statuses"] == {
        "temperature": "success",
        "humidity": "failed",
    }
    assert payload["duration_seconds"] == pytest.approx(20.0)


def test_process_all_layers_continues_after_single_layer_failure(process_module, monkeypatch, caplog):

    class DummyFetcher:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

        async def fetch_all_data(self, grid_points):
            return {
                "1.0:2.0": {
                    "temperature": 25.0,
                    "humidity": 60.0,
                    "precipitation": 1.5,
                    "uv_index": 7.0,
                    "pm25": 12.0,
                }
            }

    def fake_arrays(_):
        return {
            layer: FakeArray([[1.0]])
            for layer in process_module.LAYER_FIELD_MAP
        }

    def fake_write_geotiff(layer, data, timestamp):
        return Path(f"/tmp/{layer}_{timestamp}.tif")

    def fake_generate_tiles(layer, tif_path):
        if layer == "humidity":
            raise RuntimeError("humidity exploded")

    monkeypatch.setattr(process_module, "OpenMeteoFetcher", DummyFetcher)
    monkeypatch.setattr(process_module, "GRID_POINTS", [{"latitude": 1.0, "longitude": 2.0}])
    monkeypatch.setattr(process_module, "_build_layer_arrays", fake_arrays)
    monkeypatch.setattr(process_module, "_write_geotiff", fake_write_geotiff)
    monkeypatch.setattr(process_module, "_generate_tiles", fake_generate_tiles)

    caplog.set_level("INFO")

    outputs, execution_log = asyncio.run(
        process_module.process_all_layers(skip_tiles=False, trigger_type="manual")
    )

    assert set(outputs) == {"temperature", "precipitation", "uv", "pm25"}
    assert execution_log.layer_results["humidity"].status == "failed"
    assert execution_log.layer_results["humidity"].error_message == "humidity exploded"
    assert "RuntimeError: humidity exploded" in execution_log.layer_results["humidity"].error_traceback

    layer_logs = [
        parse_json_line(record.message)
        for record in caplog.records
        if '"event": "pipeline_layer"' in record.message
    ]
    summary_logs = [
        parse_json_line(record.message)
        for record in caplog.records
        if '"event": "pipeline_summary"' in record.message
    ]

    assert any(
        log["layer_name"] == "humidity"
        and log["status"] == "failed"
        and log["error_type"] == "RuntimeError"
        for log in layer_logs
    )
    assert summary_logs[-1]["attempted"] == 5
    assert summary_logs[-1]["succeeded"] == 4
    assert summary_logs[-1]["failed"] == 1


def test_summary_log_format_keeps_key_fields_extractable():
    start_time = datetime(2026, 3, 8, 1, 0, 0)
    end_time = start_time + timedelta(seconds=5)
    execution_log = PipelineExecutionLog(
        run_id="run-789",
        start_time=start_time,
        end_time=end_time,
        trigger_type="manual",
        layer_results={
            "uv": LayerResult(
                layer_name="uv",
                status="skipped",
                start_time=start_time,
                end_time=end_time,
                duration_seconds=5.0,
            )
        },
    )

    payload = parse_json_line(execution_log.format_summary(data_timestamp="20260308_020000"))

    assert payload["run_id"] == "run-789"
    assert payload["attempted"] == 1
    assert payload["skipped"] == 1
    assert payload["start_time"] == "2026-03-08T01:00:00"
    assert payload["end_time"] == "2026-03-08T01:00:05"
