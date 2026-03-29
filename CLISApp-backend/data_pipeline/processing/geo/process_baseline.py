"""Convert historical baseline CSV data into a frontend JSON asset."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

LOGGER = logging.getLogger("process_baseline")

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "CLISApp-backend"
FRONTEND_ROOT = REPO_ROOT / "CLISApp-frontend"
DATA_ROOT = BACKEND_ROOT / "data_pipeline" / "data"
RAW_BASELINE_DIR = DATA_ROOT / "raw" / "baseline"
DEFAULT_INPUT_PATH = RAW_BASELINE_DIR / "baseline_ref_bmT_bmTmin_bmR_1890_1960.csv"
OUTPUT_PATH = FRONTEND_ROOT / "assets" / "data" / "climate_baseline.json"

EXPECTED_ROW_COUNT = 2894
BM_T_WARNING_MIN = 15.0
BM_T_WARNING_MAX = 40.0
PERIOD = "1890-1960"
DESCRIPTION = "Average maximum temperature baseline per SSC region"
REQUIRED_COLUMNS = ("MERGED_ID", "MERGED_NAME", "bmT")


class BaselineProcessingError(ValueError):
    """Raised when the baseline CSV fails validation."""


@dataclass(frozen=True)
class BaselineRecord:
    merged_id: int
    merged_name: str
    bmt: float
    row_number: int

    @property
    def ssc_id(self) -> str:
        return f"ssc_{self.merged_id}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert historical baseline CSV into a static frontend JSON asset.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Baseline CSV input path (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"JSON output path (default: {OUTPUT_PATH})",
    )
    return parser.parse_args(argv)


def _format_timestamp(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_required_columns(fieldnames: Sequence[str] | None) -> tuple[str, ...]:
    if fieldnames is None:
        raise BaselineProcessingError(
            f"CSV is missing a header row. Required columns: {', '.join(REQUIRED_COLUMNS)}"
        )

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        found_columns = ", ".join(column for column in fieldnames if column)
        raise BaselineProcessingError(
            f"Missing required columns: {', '.join(missing_columns)}. "
            f"Found columns: {found_columns or '<none>'}"
        )

    return tuple(fieldnames)


def load_baseline_records(input_path: Path) -> tuple[BaselineRecord, ...]:
    if not input_path.exists():
        raise FileNotFoundError(f"Baseline CSV not found: {input_path}")

    records: list[BaselineRecord] = []
    seen_rows_by_id: dict[int, int] = {}

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_required_columns(reader.fieldnames)

        for row_number, row in enumerate(reader, start=2):
            raw_merged_id = (row.get("MERGED_ID") or "").strip()
            raw_name = (row.get("MERGED_NAME") or "").strip()
            raw_bmt = (row.get("bmT") or "").strip()

            try:
                merged_id = int(raw_merged_id)
            except ValueError as exc:
                raise BaselineProcessingError(
                    f"Invalid MERGED_ID '{raw_merged_id}' at row {row_number}"
                ) from exc

            if raw_bmt == "":
                raise BaselineProcessingError(
                    f"Missing bmT value at row {row_number} (MERGED_ID={merged_id})"
                )

            try:
                bmt = float(raw_bmt)
            except ValueError as exc:
                raise BaselineProcessingError(
                    f"Invalid bmT value '{raw_bmt}' at row {row_number} (MERGED_ID={merged_id})"
                ) from exc

            if merged_id in seen_rows_by_id:
                raise BaselineProcessingError(
                    f"Duplicate MERGED_ID {merged_id} found at rows "
                    f"{seen_rows_by_id[merged_id]} and {row_number}"
                )

            if not BM_T_WARNING_MIN <= bmt <= BM_T_WARNING_MAX:
                LOGGER.warning(
                    "bmT value %.2f at row %d (MERGED_ID=%s) outside expected range 15-40 C",
                    bmt,
                    row_number,
                    merged_id,
                )

            seen_rows_by_id[merged_id] = row_number
            records.append(
                BaselineRecord(
                    merged_id=merged_id,
                    merged_name=raw_name,
                    bmt=bmt,
                    row_number=row_number,
                )
            )

    return tuple(records)


def build_payload(
    records: Sequence[BaselineRecord],
    *,
    source_name: str,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = _format_timestamp(generated_at or datetime.now(UTC))
    baselines = {
        record.ssc_id: {"bmT": round(record.bmt, 2)}
        for record in sorted(records, key=lambda item: item.ssc_id)
    }
    metadata = {
        "source": source_name,
        "period": PERIOD,
        "description": DESCRIPTION,
        "generated": timestamp,
        "ssc_count": len(records),
    }
    return {
        "metadata": metadata,
        "baselines": baselines,
    }


def write_json_atomic(output_path: Path, payload: dict[str, Any]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    temp_path: Path | None = None

    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(json_text)
            handle.flush()
            os.fsync(handle.fileno())

        temp_path.replace(output_path)

        with output_path.open("r", encoding="utf-8") as handle:
            json.load(handle)

        return output_path.stat().st_size
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def process_baseline(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
    generated_at: datetime | None = None,
    expected_row_count: int = EXPECTED_ROW_COUNT,
) -> dict[str, Any]:
    records = load_baseline_records(input_path)
    if len(records) != expected_row_count:
        LOGGER.warning("Expected %d rows, got %d. Continuing.", expected_row_count, len(records))

    payload = build_payload(
        records,
        source_name=input_path.name,
        generated_at=generated_at,
    )
    file_size_bytes = write_json_atomic(output_path, payload)

    LOGGER.info("Processed %d baseline regions", len(records))
    LOGGER.info("Baseline JSON written to %s (%d bytes)", output_path, file_size_bytes)

    return {
        "ssc_count": len(records),
        "output_path": output_path,
        "file_size_bytes": file_size_bytes,
        "payload": payload,
    }


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)

    try:
        result = process_baseline(
            input_path=args.input,
            output_path=args.output,
        )
    except (BaselineProcessingError, FileNotFoundError) as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc

    print(f"Total regions: {result['ssc_count']}")
    print(f"Output path: {result['output_path']}")
    print(f"File size: {result['file_size_bytes']} bytes")


if __name__ == "__main__":
    main()
