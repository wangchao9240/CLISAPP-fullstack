import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.downloads import common


def test_build_lead_hours_valid():
    assert common.build_lead_hours(3) == ["0", "1", "2", "3"]


def test_build_lead_hours_bounds():
    with pytest.raises(ValueError):
        common.build_lead_hours(-1)
    with pytest.raises(ValueError):
        common.build_lead_hours(121)


def test_write_metadata(tmp_path):
    data_file = tmp_path / "sample.nc"
    data_file.write_bytes(b"")
    payload = {"foo": "bar"}
    meta_path = common.write_metadata(data_file, payload)
    assert json.loads(meta_path.read_text()) == payload


def test_parse_bbox():
    assert common.parse_bbox("-9,138,-29,154") == [-9.0, 138.0, -29.0, 154.0]
    with pytest.raises(ValueError):
        common.parse_bbox("1,2,3")


def test_generate_grid_points():
    bbox = [-9.0, 138.0, -29.0, 154.0]
    grid = common.generate_grid_points(bbox, 10)
    assert grid[0] == (-29.0, 138.0)
    assert grid[-1] == (-9.0, 154.0)
    assert len(grid) == 9


def test_generate_grid_points_invalid_step():
    with pytest.raises(ValueError):
        common.generate_grid_points([-9.0, 138.0, -29.0, 154.0], 0)
