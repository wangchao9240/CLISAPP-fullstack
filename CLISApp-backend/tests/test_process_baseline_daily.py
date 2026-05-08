import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from data_pipeline.processing.geo import process_baseline_daily


FIXED_GENERATED_AT = datetime(2026, 5, 8, 1, 2, 3, tzinfo=UTC)
DAILY_HEADERS = [
    "MERGED_ID",
    "suburb_name",
    "day",
    "baseline_mT",
    "baseline_MT",
    "baseline_rf",
    "baseline_tmean",
    "n_years",
]


def _write_yearly_csv(path: Path, merged_ids: list[int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["MERGED_ID", "MERGED_NAME", "bmT"])
        writer.writeheader()
        for merged_id in merged_ids:
            writer.writerow(
                {
                    "MERGED_ID": merged_id,
                    "MERGED_NAME": f"Region {merged_id}",
                    "bmT": "27.5",
                }
            )
    return path


def _daily_row(merged_id: int, day: int, *, tmean: float | None = None) -> dict[str, object]:
    return {
        "MERGED_ID": merged_id,
        "suburb_name": f"Region {merged_id}",
        "day": day,
        "baseline_mT": 18.04 + day / 1000,
        "baseline_MT": 29.96 + day / 1000,
        "baseline_rf": 2.54 + day / 1000,
        "baseline_tmean": (23.14 + day / 1000) if tmean is None else tmean,
        "n_years": 71,
    }


def _write_daily_xlsx(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "in"
    sheet.append(DAILY_HEADERS)
    for row in rows:
        sheet.append([row[column] for column in DAILY_HEADERS])
    workbook.save(path)
    return path


def _complete_rows(merged_ids: list[int]) -> list[dict[str, object]]:
    return [_daily_row(merged_id, day) for merged_id in merged_ids for day in range(1, 367)]


def _read_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_process_baseline_daily_complete_fixture_writes_packed_arrays(tmp_path: Path) -> None:
    input_path = _write_daily_xlsx(tmp_path / "daily.xlsx", _complete_rows([30002, 30003, 30004]))
    yearly_path = _write_yearly_csv(tmp_path / "yearly.csv", [30002, 30003, 30004])
    output_path = tmp_path / "climate_baseline_daily.json"

    result = process_baseline_daily.process_baseline_daily(
        input_path=input_path,
        yearly_input_path=yearly_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_ssc_count=3,
    )

    payload = _read_payload(output_path)
    assert result["ssc_count"] == 3
    assert payload["metadata"] == {
        "source": "daily.xlsx",
        "period": "1890-1960",
        "description": "Per-day historical baseline (min/mean/max temp + rainfall) per SSC",
        "generated": "2026-05-08T01:02:03Z",
        "ssc_count": 3,
        "expected_ssc_count": 3,
        "missing_ssc_ids": [],
        "partial_ssc_ids": {},
        "truncation_note": "Source xlsx may be truncated; no missing SSCs detected against yearly baseline.",
        "field_units": {"tmean": "°C", "MT": "°C", "mT": "°C", "rf": "mm/day"},
    }
    assert set(payload["baselines"]) == {"ssc_30002", "ssc_30003", "ssc_30004"}
    assert len(payload["baselines"]["ssc_30002"]["tmean"]) == 366
    assert payload["baselines"]["ssc_30002"]["tmean"][0] == 23.1
    assert payload["baselines"]["ssc_30002"]["MT"][0] == 30.0
    assert payload["baselines"]["ssc_30002"]["mT"][0] == 18.0
    assert payload["baselines"]["ssc_30002"]["rf"][0] == 2.5


def test_process_baseline_daily_partial_fixture_records_partial_ssc(tmp_path: Path) -> None:
    input_path = _write_daily_xlsx(
        tmp_path / "partial.xlsx",
        [_daily_row(33228, day) for day in range(1, 352)],
    )
    yearly_path = _write_yearly_csv(tmp_path / "yearly.csv", [33228])
    output_path = tmp_path / "partial.json"

    process_baseline_daily.process_baseline_daily(
        input_path=input_path,
        yearly_input_path=yearly_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_ssc_count=1,
    )

    payload = _read_payload(output_path)
    assert payload["metadata"]["partial_ssc_ids"] == {"33228": 351}
    assert len(payload["baselines"]["ssc_33228"]["tmean"]) == 366
    assert payload["baselines"]["ssc_33228"]["tmean"][350] == 23.5
    assert payload["baselines"]["ssc_33228"]["tmean"][351] is None


def test_process_baseline_daily_missing_fixture_diffs_against_yearly_csv(tmp_path: Path) -> None:
    input_path = _write_daily_xlsx(tmp_path / "missing.xlsx", _complete_rows([30002, 30003]))
    yearly_path = _write_yearly_csv(tmp_path / "yearly.csv", [30002, 30003, 30004, 30005])
    output_path = tmp_path / "missing.json"

    process_baseline_daily.process_baseline_daily(
        input_path=input_path,
        yearly_input_path=yearly_path,
        output_path=output_path,
        generated_at=FIXED_GENERATED_AT,
        expected_ssc_count=4,
    )

    payload = _read_payload(output_path)
    assert payload["metadata"]["ssc_count"] == 2
    assert payload["metadata"]["expected_ssc_count"] == 4
    assert payload["metadata"]["missing_ssc_ids"] == [30004, 30005]


def test_process_baseline_daily_out_of_range_fixture_warns_and_emits_json(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rows = [_daily_row(30002, day) for day in range(1, 367)]
    rows[0]["baseline_tmean"] = 40.0
    input_path = _write_daily_xlsx(tmp_path / "out_of_range.xlsx", rows)
    yearly_path = _write_yearly_csv(tmp_path / "yearly.csv", [30002])
    output_path = tmp_path / "out_of_range.json"

    with caplog.at_level(logging.WARNING, logger=process_baseline_daily.LOGGER.name):
        process_baseline_daily.process_baseline_daily(
            input_path=input_path,
            yearly_input_path=yearly_path,
            output_path=output_path,
            generated_at=FIXED_GENERATED_AT,
            expected_ssc_count=1,
        )

    assert any("baseline_tmean value 40.00" in message for message in caplog.messages)
    payload = _read_payload(output_path)
    assert payload["baselines"]["ssc_30002"]["tmean"][0] == 40.0


def test_process_baseline_daily_preserves_na_values_as_null_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    rows = [_daily_row(30002, day) for day in range(1, 367)]
    rows[34]["baseline_mT"] = "NA"
    rows[34]["baseline_MT"] = "NA"
    rows[34]["baseline_rf"] = "NA"
    rows[34]["baseline_tmean"] = "NA"
    input_path = _write_daily_xlsx(tmp_path / "na_values.xlsx", rows)
    yearly_path = _write_yearly_csv(tmp_path / "yearly.csv", [30002])
    output_path = tmp_path / "na_values.json"

    with caplog.at_level(logging.WARNING, logger=process_baseline_daily.LOGGER.name):
        process_baseline_daily.process_baseline_daily(
            input_path=input_path,
            yearly_input_path=yearly_path,
            output_path=output_path,
            generated_at=FIXED_GENERATED_AT,
            expected_ssc_count=1,
        )

    assert any("NA baseline_tmean value" in message for message in caplog.messages)
    payload = _read_payload(output_path)
    assert payload["baselines"]["ssc_30002"]["tmean"][34] is None
    assert payload["baselines"]["ssc_30002"]["MT"][34] is None
    assert payload["baselines"]["ssc_30002"]["mT"][34] is None
    assert payload["baselines"]["ssc_30002"]["rf"][34] is None
