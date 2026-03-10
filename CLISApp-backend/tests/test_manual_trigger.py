import fcntl
import importlib
import subprocess
import sys
import types
from pathlib import Path

import pytest


STUB_MODULES = [
    "numpy",
    "rasterio",
    "rasterio.crs",
    "rasterio.transform",
    "data_pipeline.downloads.openmeteo.fetch_realtime",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_CRON_SCRIPT = REPO_ROOT / "scripts" / "setup-cron.sh"
MANUAL_TRIGGER_SCRIPT = REPO_ROOT / "scripts" / "manual-pipeline-trigger.sh"


def ensure_scientific_stubs() -> None:
    if "numpy" not in sys.modules:
        numpy_module = types.ModuleType("numpy")
        numpy_module.float32 = float
        numpy_module.nan = float("nan")
        numpy_module.arange = lambda *args, **kwargs: []
        numpy_module.isnan = lambda array: array
        numpy_module.count_nonzero = lambda array: 0
        sys.modules["numpy"] = numpy_module

    if "rasterio" not in sys.modules:
        rasterio_module = types.ModuleType("rasterio")
        rasterio_module.open = lambda *args, **kwargs: None
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
    saved = {key: sys.modules[key] for key in STUB_MODULES if key in sys.modules}
    ensure_scientific_stubs()
    sys.modules.pop("data_pipeline.config.grid_config", None)
    sys.modules.pop("data_pipeline.processing.openmeteo.process_all_layers", None)
    module = importlib.import_module("data_pipeline.processing.openmeteo.process_all_layers")
    yield module
    for key in STUB_MODULES:
        if key in saved:
            sys.modules[key] = saved[key]
        else:
            sys.modules.pop(key, None)
    sys.modules.pop("data_pipeline.config.grid_config", None)
    sys.modules.pop("data_pipeline.processing.openmeteo.process_all_layers", None)


def test_normalize_trigger_type_defaults_to_manual(process_module):
    assert process_module._normalize_trigger_type(None) == "manual"
    assert process_module._normalize_trigger_type("") == "manual"
    assert process_module._normalize_trigger_type("bogus") == "manual"


def test_normalize_trigger_type_scheduled(process_module):
    assert process_module._normalize_trigger_type("scheduled") == "scheduled"
    assert process_module._normalize_trigger_type(" SCHEDULED ") == "scheduled"


def test_setup_cron_template_uses_lock_guard_and_manual_script_exists():
    setup_cron = SETUP_CRON_SCRIPT.read_text(encoding="utf-8")

    assert 'LOCK_FILE="/var/lock/clisapp-pipeline.lock"' in setup_cron
    assert "flock -n 9" in setup_cron
    assert 'exit 75' in setup_cron
    assert 'export PIPELINE_TRIGGER=scheduled' not in setup_cron

    # Verify cron line passes PIPELINE_TRIGGER=scheduled as inline env var
    assert 'PIPELINE_TRIGGER=scheduled /opt/clisapp/run-pipeline.sh' in setup_cron

    assert MANUAL_TRIGGER_SCRIPT.exists()
    manual_trigger = MANUAL_TRIGGER_SCRIPT.read_text(encoding="utf-8")
    assert "set -euo pipefail" in manual_trigger


def test_second_lock_attempt_is_rejected(tmp_path):
    lock_file = tmp_path / "clisapp-pipeline.lock"
    primary = lock_file.open("w", encoding="utf-8")
    contender_code = """
import fcntl
import os
import sys

fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o644)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(75)
raise SystemExit(0)
"""
    try:
        fcntl.flock(primary, fcntl.LOCK_EX | fcntl.LOCK_NB)
        contender = subprocess.run(
            [
                sys.executable,
                "-c",
                contender_code,
                str(lock_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        primary.close()

    assert contender.returncode == 75
