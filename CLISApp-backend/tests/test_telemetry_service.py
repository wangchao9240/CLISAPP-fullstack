import sqlite3
from datetime import datetime, timezone

from app.models.telemetry import TelemetryCreate
from app.services import telemetry_service

EXPECTED_TELEMETRY_COLUMNS = [
    "id",
    "device_id",
    "event_date",
    "time_of_day",
    "lat",
    "lon",
    "created_at",
]


def _parse_utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo == timezone.utc
    return parsed


def _table_columns(conn: sqlite3.Connection) -> list[str]:
    return [row[1] for row in conn.execute("PRAGMA table_info(telemetry)").fetchall()]


def test_init_db_creates_exact_telemetry_schema(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "telemetry.db"
    monkeypatch.setattr(telemetry_service, "DB_PATH", db_path)
    telemetry_service.init_db()

    with sqlite3.connect(db_path) as conn:
        columns = _table_columns(conn)

    assert columns == EXPECTED_TELEMETRY_COLUMNS
    assert len(columns) == 7


def test_insert_telemetry_creates_adr2_record_without_extra_metadata(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "telemetry.db"
    monkeypatch.setattr(telemetry_service, "DB_PATH", db_path)
    telemetry_service.init_db()

    # device_id is a non-PII opaque identifier per ADR-8.
    # GPS truncation is frontend responsibility per Story 5.2.
    payload = TelemetryCreate(
        device_id="device-123",
        event_date="2026-03-29",
        time_of_day="09:30:00",
        lat=-27.47,
        lon=153.02,
    )
    result = telemetry_service.insert_telemetry(payload)

    assert result.id == 1
    assert result.created_at.endswith("Z")
    _parse_utc_timestamp(result.created_at)

    with sqlite3.connect(db_path) as conn:
        schema_columns = _table_columns(conn)
        cursor = conn.execute("SELECT * FROM telemetry")
        selected_columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()

    assert schema_columns == EXPECTED_TELEMETRY_COLUMNS
    assert len(schema_columns) == 7
    assert selected_columns == EXPECTED_TELEMETRY_COLUMNS
    assert row == (
        1,
        payload.device_id,
        payload.event_date,
        payload.time_of_day,
        payload.lat,
        payload.lon,
        result.created_at,
    )


def test_insert_telemetry_allows_null_location_and_only_expected_columns(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "telemetry.db"
    monkeypatch.setattr(telemetry_service, "DB_PATH", db_path)
    telemetry_service.init_db()

    # device_id is a non-PII opaque identifier per ADR-8.
    # GPS truncation is frontend responsibility per Story 5.2.
    telemetry_service.insert_telemetry(
        TelemetryCreate(
            device_id="opaque-device-id",
            event_date="2026-03-29",
            time_of_day="10:15:00",
            lat=None,
            lon=None,
        )
    )

    with sqlite3.connect(db_path) as conn:
        columns = _table_columns(conn)
        row = conn.execute(
            "SELECT id, device_id, event_date, time_of_day, lat, lon, created_at FROM telemetry"
        ).fetchone()

    assert columns == EXPECTED_TELEMETRY_COLUMNS
    assert len(columns) == 7
    assert row[:6] == (1, "opaque-device-id", "2026-03-29", "10:15:00", None, None)
    assert row[6].endswith("Z")


def test_rate_limit_allows_first_five_requests_then_blocks_sixth(monkeypatch) -> None:
    assert telemetry_service.RATE_LIMIT == 5

    timestamps = iter([1000, 1001, 1002, 1003, 1004, 1005])
    monkeypatch.setattr(telemetry_service.time, "time", lambda: next(timestamps))
    store = telemetry_service.BoundedRateStore()

    for _ in range(5):
        assert store.is_rate_limited("device-a") is False

    assert store.is_rate_limited("device-a") is True


def test_rate_limit_is_tracked_per_device_id(monkeypatch) -> None:
    timestamps = iter(range(2000, 2012))
    monkeypatch.setattr(telemetry_service.time, "time", lambda: next(timestamps))
    store = telemetry_service.BoundedRateStore()

    for _ in range(5):
        assert store.is_rate_limited("device-a") is False

    for _ in range(5):
        assert store.is_rate_limited("device-b") is False

    assert store.is_rate_limited("device-a") is True
    assert store.is_rate_limited("device-b") is True


def test_rate_limit_resets_after_sixty_seconds(monkeypatch) -> None:
    timestamps = iter([3000, 3001, 3002, 3003, 3004, 3005, 3066])
    monkeypatch.setattr(telemetry_service.time, "time", lambda: next(timestamps))
    store = telemetry_service.BoundedRateStore()

    for _ in range(5):
        assert store.is_rate_limited("device-a") is False

    assert store.is_rate_limited("device-a") is True
    assert store.is_rate_limited("device-a") is False


def test_bounded_rate_store_evicts_oldest_keys(monkeypatch) -> None:
    timestamps = iter([4000, 4001, 4002, 4003])
    monkeypatch.setattr(telemetry_service.time, "time", lambda: next(timestamps))
    store = telemetry_service.BoundedRateStore(max_entries=2)

    assert store.is_rate_limited("device-a") is False
    assert store.is_rate_limited("device-b") is False
    assert store.is_rate_limited("device-c") is False

    assert list(store._store.keys()) == ["device-b", "device-c"]
