import sqlite3
import time
import logging
from collections import OrderedDict
from pathlib import Path
from app.models.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)

DB_PATH = Path("./data/telemetry.db")

# Rate limiting: max requests per IP per minute
RATE_LIMIT = 30
# Maximum unique client IDs tracked (prevents unbounded memory growth)
MAX_RATE_STORE_ENTRIES = 10_000


class BoundedRateStore:
    """LRU-evicting rate store that caps the number of tracked clients."""

    def __init__(self, max_entries: int = MAX_RATE_STORE_ENTRIES):
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._max_entries = max_entries

    def is_rate_limited(self, client_id: str) -> bool:
        now = time.time()
        window = now - 60
        timestamps = [t for t in self._store.get(client_id, []) if t > window]

        if client_id in self._store:
            self._store.move_to_end(client_id)
        self._store[client_id] = timestamps

        if len(timestamps) >= RATE_LIMIT:
            return True

        self._store[client_id].append(now)

        # Evict oldest entries if over capacity
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

        return False


_rate_store = BoundedRateStore()


def is_rate_limited(client_id: str) -> bool:
    return _rate_store.is_rate_limited(client_id)


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


def insert_event(event: TelemetryEvent) -> int:
    """Synchronous DB insert — must be called from a thread pool, not the event loop."""
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
