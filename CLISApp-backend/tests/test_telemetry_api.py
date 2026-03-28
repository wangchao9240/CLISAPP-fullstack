import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.services import telemetry_service


@pytest.fixture
def telemetry_client(tmp_path, monkeypatch):
    db_path = tmp_path / "telemetry.db"
    monkeypatch.setattr(telemetry_service, "DB_PATH", db_path)
    monkeypatch.setattr(
        telemetry_service,
        "_rate_store",
        telemetry_service.BoundedRateStore(),
    )

    app = create_application()

    with TestClient(app) as client:
        yield client, db_path


def test_post_telemetry_returns_wrapped_success_and_persists_payload(
    telemetry_client,
) -> None:
    client, db_path = telemetry_client

    response = client.post(
        "/api/v1/telemetry",
        json={
            "device_id": "device-123",
            "event_date": "2026-03-29",
            "time_of_day": "09:30:00",
            "lat": -27.47,
            "lon": 153.02,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["error"] is None
    assert body["data"]["id"] == 1
    assert body["data"]["created_at"].endswith("Z")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT device_id, event_date, time_of_day, lat, lon
            FROM telemetry
            """
        ).fetchone()

    assert row == ("device-123", "2026-03-29", "09:30:00", -27.47, 153.02)


@pytest.mark.parametrize(
    ("payload", "message_fragment"),
    [
        (
            {
                "event_date": "2026-03-29",
                "time_of_day": "09:30:00",
                "lat": -27.47,
                "lon": 153.02,
            },
            "device_id",
        ),
        (
            {
                "device_id": "device-123",
                "time_of_day": "09:30:00",
                "lat": -27.47,
                "lon": 153.02,
            },
            "event_date",
        ),
        (
            {
                "device_id": "device-123",
                "event_date": "2026/03/29",
                "time_of_day": "09:30:00",
                "lat": -27.47,
                "lon": 153.02,
            },
            "event_date",
        ),
        (
            {
                "device_id": "device-123",
                "event_date": "2026-03-29",
                "time_of_day": "25:00:00",
                "lat": -27.47,
                "lon": 153.02,
            },
            "time_of_day",
        ),
        (
            {
                "device_id": "device-123",
                "event_date": "2026-03-29",
                "time_of_day": "09:30:00",
                "lat": 91.0,
                "lon": 153.02,
            },
            "lat",
        ),
        (
            {
                "device_id": "device-123",
                "event_date": "2026-03-29",
                "time_of_day": "09:30:00",
                "lat": -27.47,
                "lon": 181.0,
            },
            "lon",
        ),
    ],
)
def test_post_telemetry_returns_wrapped_validation_errors(
    telemetry_client, payload, message_fragment
) -> None:
    client, _ = telemetry_client

    response = client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "TELEMETRY_INVALID_FORMAT"
    assert message_fragment in body["error"]["message"]


def test_post_telemetry_allows_null_location(telemetry_client) -> None:
    client, db_path = telemetry_client

    response = client.post(
        "/api/v1/telemetry",
        json={
            "device_id": "device-null-location",
            "event_date": "2026-03-29",
            "time_of_day": "09:30:00",
            "lat": None,
            "lon": None,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["error"] is None
    assert body["data"]["id"] == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT lat, lon FROM telemetry").fetchone()

    assert row == (None, None)


def test_post_telemetry_rate_limits_on_sixth_request_for_same_device(
    telemetry_client,
) -> None:
    client, _ = telemetry_client
    payload = {
        "device_id": "same-device",
        "event_date": "2026-03-29",
        "time_of_day": "09:30:00",
        "lat": -27.47,
        "lon": 153.02,
    }

    for _ in range(5):
        response = client.post("/api/v1/telemetry", json=payload)
        assert response.status_code == 201

    response = client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 429
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "5 requests per minute" in body["error"]["message"]


def test_post_telemetry_rate_limit_is_independent_per_device(telemetry_client) -> None:
    client, _ = telemetry_client

    device_a = {
        "device_id": "device-a",
        "event_date": "2026-03-29",
        "time_of_day": "09:30:00",
        "lat": -27.47,
        "lon": 153.02,
    }
    device_b = {
        "device_id": "device-b",
        "event_date": "2026-03-29",
        "time_of_day": "09:30:00",
        "lat": -27.47,
        "lon": 153.02,
    }

    for _ in range(5):
        assert client.post("/api/v1/telemetry", json=device_a).status_code == 201

    assert client.post("/api/v1/telemetry", json=device_b).status_code == 201
