import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from data_pipeline.processing.geo import process_baseline


FIXED_GENERATED_AT = datetime(2026, 3, 29, 1, 2, 3, tzinfo=UTC)
DEFAULT_HEADERS = ["", "MERGED_ID", "MERGED_NAME", "bmT"]


def _write_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    headers: list[str] | None = None,
    bom: bool = False,
    line_ending: str = "\n",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header_values = headers or DEFAULT_HEADERS
    lines = [",".join(header_values)]
    for row in rows:
        lines.append(",".join(row.get(header, "") for header in header_values))
    content = line_ending.join(lines) + line_ending
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(content, encoding=encoding, newline="")
    return path


def _read_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_process_baseline_happy_path_writes_expected_payload(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "baseline.csv",
        [
            {"": "2", "MERGED_ID": "30003", "MERGED_NAME": "Beta", "bmT": "27.32001"},
            {"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.64447247"},
        ],
    )
    output_path = tmp_path / "assets" / "data" / "climate_baseline.json"

    result = process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=2,
    )

    payload = _read_payload(output_path)
    assert result["ssc_count"] == 2
    assert result["output_path"] == output_path
    assert payload == {
        "metadata": {
            "source": "baseline.csv",
            "period": "1890-1960",
            "description": "Average maximum temperature baseline per SSC region",
            "generated": "2026-03-29T01:02:03Z",
            "ssc_count": 2,
        },
        "baselines": {
            "ssc_30002": {"bmT": 27.64},
            "ssc_30003": {"bmT": 27.32},
        },
    }


def test_process_baseline_reads_utf8_bom_csv(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "baseline_bom.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.5"}],
        bom=True,
    )
    output_path = tmp_path / "out.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    payload = _read_payload(output_path)
    assert payload["baselines"]["ssc_30002"] == {"bmT": 27.5}


def test_process_baseline_raises_for_missing_required_column(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "missing_column.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha"}],
        headers=["", "MERGED_ID", "MERGED_NAME"],
    )

    with pytest.raises(process_baseline.BaselineProcessingError, match="Missing required columns: bmT"):
        process_baseline.process_baseline(input_path=input_path, output_path=tmp_path / "out.json")


def test_process_baseline_raises_for_empty_bmt_value(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "missing_bmt.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": ""}],
    )

    with pytest.raises(process_baseline.BaselineProcessingError, match="Missing bmT value"):
        process_baseline.process_baseline(input_path=input_path, output_path=tmp_path / "out.json")


def test_process_baseline_raises_for_duplicate_merged_id(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "duplicate.csv",
        [
            {"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.1"},
            {"": "2", "MERGED_ID": "30002", "MERGED_NAME": "Beta", "bmT": "27.2"},
        ],
    )

    with pytest.raises(process_baseline.BaselineProcessingError, match="Duplicate MERGED_ID 30002"):
        process_baseline.process_baseline(input_path=input_path, output_path=tmp_path / "out.json")


def test_process_baseline_raises_for_non_numeric_merged_id(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "bad_id.csv",
        [{"": "1", "MERGED_ID": "abc", "MERGED_NAME": "Alpha", "bmT": "27.1"}],
    )

    with pytest.raises(process_baseline.BaselineProcessingError, match="Invalid MERGED_ID 'abc'"):
        process_baseline.process_baseline(input_path=input_path, output_path=tmp_path / "out.json")


def test_process_baseline_raises_for_non_numeric_bmt(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "bad_bmt.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "N/A"}],
    )

    with pytest.raises(process_baseline.BaselineProcessingError, match="Invalid bmT value 'N/A'"):
        process_baseline.process_baseline(input_path=input_path, output_path=tmp_path / "out.json")


def test_process_baseline_warns_for_out_of_range_bmt(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    input_path = _write_csv(
        tmp_path / "warning.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "45.0"}],
    )
    output_path = tmp_path / "warning.json"

    with caplog.at_level(logging.WARNING, logger=process_baseline.LOGGER.name):
        process_baseline.process_baseline(
            input_path=input_path,
            output_path=output_path,
            generated_at=FIXED_GENERATED_AT,
            expected_row_count=1,
        )

    assert any("outside expected range 15-40 C" in message for message in caplog.messages)
    payload = _read_payload(output_path)
    assert payload["baselines"]["ssc_30002"]["bmT"] == 45.0


def test_process_baseline_rounds_bmt_to_two_decimal_places(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "rounding.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.645"}],
    )
    output_path = tmp_path / "rounding.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    payload = _read_payload(output_path)
    assert payload["baselines"]["ssc_30002"]["bmT"] == 27.64


def test_process_baseline_maps_ids_to_ssc_prefix(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "mapping.csv",
        [{"": "1", "MERGED_ID": "33262", "MERGED_NAME": "Zilzie", "bmT": "27.58824181"}],
    )
    output_path = tmp_path / "mapping.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    payload = _read_payload(output_path)
    assert "ssc_33262" in payload["baselines"]


def test_process_baseline_output_contains_metadata_and_baselines(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "structure.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.5"}],
    )
    output_path = tmp_path / "structure.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    payload = _read_payload(output_path)
    assert set(payload) == {"metadata", "baselines"}


def test_process_baseline_metadata_ssc_count_matches_baseline_count(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "count.csv",
        [
            {"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.1"},
            {"": "2", "MERGED_ID": "30003", "MERGED_NAME": "Beta", "bmT": "27.2"},
            {"": "3", "MERGED_ID": "30004", "MERGED_NAME": "Gamma", "bmT": "27.3"},
        ],
    )
    output_path = tmp_path / "count.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=3,
    )

    payload = _read_payload(output_path)
    assert payload["metadata"]["ssc_count"] == len(payload["baselines"]) == 3


def test_process_baseline_empty_csv_with_headers_only_succeeds(tmp_path: Path) -> None:
    input_path = _write_csv(tmp_path / "empty.csv", [])
    output_path = tmp_path / "empty.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=0,
    )

    payload = _read_payload(output_path)
    assert payload["metadata"]["ssc_count"] == 0
    assert payload["baselines"] == {}


def test_process_baseline_creates_missing_output_directory(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "dirs.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.5"}],
    )
    output_path = tmp_path / "nested" / "assets" / "data" / "climate_baseline.json"

    process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    assert output_path.exists()


def test_process_baseline_writes_output_atomically(tmp_path: Path) -> None:
    input_path = _write_csv(
        tmp_path / "atomic.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.5"}],
    )
    output_path = tmp_path / "atomic" / "climate_baseline.json"

    result = process_baseline.process_baseline(
        input_path=input_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_row_count=1,
    )

    assert output_path.exists()
    assert result["file_size_bytes"] == output_path.stat().st_size
    assert not any(path.suffix == ".tmp" for path in output_path.parent.iterdir())


def test_process_baseline_warns_for_row_count_mismatch_and_continues(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    input_path = _write_csv(
        tmp_path / "row_count.csv",
        [{"": "1", "MERGED_ID": "30002", "MERGED_NAME": "Alpha", "bmT": "27.5"}],
    )
    output_path = tmp_path / "row_count.json"

    with caplog.at_level(logging.WARNING, logger=process_baseline.LOGGER.name):
        process_baseline.process_baseline(
            input_path=input_path,
            output_path=output_path,
            generated_at=FIXED_GENERATED_AT,
        )

    assert any("Expected 2894 rows, got 1" in message for message in caplog.messages)
    assert output_path.exists()


def test_parse_args_defaults_and_overrides() -> None:
    defaults = process_baseline.parse_args([])
    assert defaults.input == process_baseline.DEFAULT_INPUT_PATH
    assert defaults.output == process_baseline.OUTPUT_PATH

    custom = process_baseline.parse_args(["--input", "/tmp/input.csv", "--output", "/tmp/output.json"])
    assert custom.input == Path("/tmp/input.csv")
    assert custom.output == Path("/tmp/output.json")
