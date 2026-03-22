import sqlite3
import time
import logging
from pathlib import Path
from app.models.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)

DB_PATH = Path("./data/telemetry.db")

# Rate limiting: max requests per IP per minute
RATE_LIMIT = 30
_rate_store: dict[str, list[float]] = {}


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                layer      TEXT,
                region_type TEXT,
                zoom_level INTEGER,
                platform   TEXT,
                app_version TEXT,
                created_at REAL NOT NULL
            )
        """)
        conn.commit()


def is_rate_limited(client_id: str) -> bool:
    now = time.time()
    window = now - 60
    timestamps = [t for t in _rate_store.get(client_id, []) if t > window]
    _rate_store[client_id] = timestamps
    if len(timestamps) >= RATE_LIMIT:
        return True
    _rate_store[client_id].append(now)
    return False


def insert_event(event: TelemetryEvent) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """INSERT INTO telemetry
               (event_type, layer, region_type, zoom_level, platform, app_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_type.value,
                event.layer,
                event.region_type,
                event.zoom_level,
                event.platform,
                event.app_version,
                time.time(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
