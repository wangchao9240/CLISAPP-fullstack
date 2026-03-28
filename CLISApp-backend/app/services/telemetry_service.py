from __future__ import annotations

import logging
import sqlite3
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from app.models.telemetry import TelemetryCreate, TelemetryCreatedData

logger = logging.getLogger(__name__)

DB_PATH = Path("./data/telemetry.db")

RATE_LIMIT = 5
MAX_RATE_STORE_ENTRIES = 10_000
TELEMETRY_COLUMNS = [
    "id",
    "device_id",
    "event_date",
    "time_of_day",
    "lat",
    "lon",
    "created_at",
]


class BoundedRateStore:
    """LRU-evicting rate store that caps the number of tracked devices."""

    def __init__(self, max_entries: int = MAX_RATE_STORE_ENTRIES):
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._max_entries = max_entries

    def is_rate_limited(self, device_id: str) -> bool:
        now = time.time()
        window = now - 60
        timestamps = [t for t in self._store.get(device_id, []) if t > window]

        if device_id in self._store:
            self._store.move_to_end(device_id)
        self._store[device_id] = timestamps

        if len(timestamps) >= RATE_LIMIT:
            return True

        self._store[device_id].append(now)

        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

        return False


_rate_store = BoundedRateStore()


def is_rate_limited(device_id: str) -> bool:
    return _rate_store.is_rate_limited(device_id)


def _create_telemetry_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id   TEXT NOT NULL,
            event_date  TEXT NOT NULL,
            time_of_day TEXT NOT NULL,
            lat         REAL,
            lon         REAL,
            created_at  TEXT NOT NULL
        )
        """
    )


def _current_columns(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("PRAGMA table_info(telemetry)").fetchall()
    return [row[1] for row in rows]


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        columns = _current_columns(conn)
        if columns and columns != TELEMETRY_COLUMNS:
            # Intentional destructive reset: Story 5.1 replaces the Sprint 1-2
            # telemetry schema, and the story explicitly allows data loss here.
            logger.info("Resetting telemetry table to ADR-2 schema")
            conn.execute("DROP TABLE telemetry")

        _create_telemetry_table(conn)
        conn.commit()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def insert_telemetry(event: TelemetryCreate) -> TelemetryCreatedData:
    """Persist a telemetry event exactly as received.

    `device_id` is a non-PII opaque identifier sourced from
    `react-native-device-info` per ADR-8, so this backend stores the provided
    value verbatim instead of trying to infer whether it "looks like" PII.

    GPS truncation is frontend responsibility per Story 5.2. The backend stores
    whatever latitude/longitude values it receives without altering precision.

    This is a synchronous DB insert and must be called from a thread pool, not
    the event loop.
    """
    created_at = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO telemetry (
                device_id,
                event_date,
                time_of_day,
                lat,
                lon,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.device_id,
                event.event_date,
                event.time_of_day,
                event.lat,
                event.lon,
                created_at,
            ),
        )
        conn.commit()
        return TelemetryCreatedData(id=int(cursor.lastrowid), created_at=created_at)
