from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # pragma: no cover - dependency may be absent before install
    firebase_admin = None
    credentials = None
    messaging = None


logger = logging.getLogger(__name__)

FCM_TOPIC = "qld-health-alerts"
SEVERITY_ORDER = {
    "Good": 0,
    "Moderate": 1,
    "Unhealthy": 2,
    "Hazardous": 3,
}


class NotificationService:
    """Evaluate processed climate layers and broadcast health alerts through FCM."""

    def __init__(
        self,
        credentials_path: Path | None = None,
        thresholds_path: Path | None = None,
    ) -> None:
        self._project_root = Path(__file__).resolve().parents[2]
        self._credentials_path = self._resolve_path(
            credentials_path or settings.firebase_credentials_path
        )
        self._thresholds_path = self._resolve_path(
            thresholds_path or settings.health_thresholds_path
        )
        self._thresholds = self._load_thresholds()
        self._enabled = False
        self._initialize_firebase()

    def _resolve_path(self, path_value: Path) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return self._project_root / path

    def _initialize_firebase(self) -> None:
        if firebase_admin is None or credentials is None:
            logger.warning(
                "firebase-admin is not installed; broadcast notifications are disabled"
            )
            return

        try:
            firebase_admin.get_app()
            self._enabled = True
            logger.info("Using existing Firebase Admin app for notifications")
            return
        except ValueError:
            pass

        if not self._credentials_path.exists():
            logger.warning(
                "Firebase credentials not found at %s; broadcast notifications are disabled",
                self._credentials_path,
            )
            return

        try:
            credential = credentials.Certificate(str(self._credentials_path))
            firebase_admin.initialize_app(credential)
            self._enabled = True
            logger.info("Initialized Firebase Admin app for broadcast notifications")
        except Exception as exc:
            logger.warning(
                "Failed to initialize Firebase Admin SDK; notifications disabled: %s",
                exc,
            )

    def _load_thresholds(self) -> dict[str, Any]:
        try:
            with self._thresholds_path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            logger.warning(
                "Health thresholds config not found at %s", self._thresholds_path
            )
        except json.JSONDecodeError as exc:
            logger.warning(
                "Health thresholds config is invalid JSON at %s: %s",
                self._thresholds_path,
                exc,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load health thresholds config at %s: %s",
                self._thresholds_path,
                exc,
            )
        return {"layers": {}}

    def evaluate_layers(self, layer_values: dict[str, float]) -> list[dict[str, Any]]:
        breaches: list[dict[str, Any]] = []
        layers_config = self._thresholds.get("layers", {})

        for layer_key, raw_value in layer_values.items():
            layer_config = layers_config.get(layer_key)
            if not layer_config:
                continue

            value = float(raw_value)
            risk_level = self._determine_risk_level(
                value, layer_config.get("thresholds", {})
            )
            if risk_level is None or risk_level == "Good":
                continue

            breaches.append(
                {
                    "layer": layer_key,
                    "layer_name": layer_config.get("name", layer_key),
                    "risk_level": risk_level,
                    "value": round(value, 2),
                    "unit": layer_config.get("unit", ""),
                    "advice": layer_config.get("advice", {}).get(risk_level, ""),
                }
            )

        return sorted(
            breaches,
            key=lambda breach: (
                SEVERITY_ORDER.get(str(breach["risk_level"]), -1),
                float(breach["value"]),
            ),
            reverse=True,
        )

    def _determine_risk_level(
        self,
        value: float,
        thresholds: dict[str, list[float | None]],
    ) -> str | None:
        threshold_items = list(thresholds.items())
        for index, (risk_level, bounds) in enumerate(threshold_items):
            if len(bounds) != 2:
                continue

            lower_bound = bounds[0]
            upper_bound = bounds[1]

            if upper_bound is None and value >= lower_bound:
                return risk_level

            if upper_bound is None:
                continue

            if lower_bound <= value < upper_bound:
                return risk_level

        return None

    def send_broadcast_alert(self, breaches: list[dict[str, Any]]) -> bool:
        if not breaches:
            return False

        if not self._enabled or messaging is None:
            logger.warning(
                "Broadcast alert skipped because Firebase notifications are disabled"
            )
            return False

        primary_breach = breaches[0]
        title = (
            f"Climate Health Alert: "
            f"{primary_breach['layer_name']} {primary_breach['risk_level']}"
        )
        body = (
            f"{primary_breach['layer_name']} is at "
            f"{primary_breach['value']} {primary_breach['unit']}. "
            f"{primary_breach['advice']}"
        )

        if len(breaches) > 1:
            body += f" {len(breaches) - 1} additional layer(s) are also elevated."

        payload = {
            "layer": str(primary_breach["layer"]),
            "layer_name": str(primary_breach["layer_name"]),
            "risk_level": str(primary_breach["risk_level"]),
            "value": str(primary_breach["value"]),
            "unit": str(primary_breach["unit"]),
            "advice": str(primary_breach["advice"]),
            "breach_count": str(len(breaches)),
        }

        try:
            message = messaging.Message(
                topic=FCM_TOPIC,
                notification=messaging.Notification(title=title, body=body),
                data=payload,
            )
            response = messaging.send(message)
            logger.info(
                "Sent broadcast health alert to topic %s: %s", FCM_TOPIC, response
            )
            return True
        except Exception as exc:
            logger.warning("Failed to send broadcast health alert: %s", exc)
            return False

    def check_and_notify(self, layer_values: dict[str, float]) -> dict[str, Any]:
        if not self._thresholds.get("layers"):
            return {
                "checked": False,
                "breaches_found": 0,
                "notification_sent": False,
            }

        breaches = self.evaluate_layers(layer_values)
        notification_sent = self.send_broadcast_alert(breaches) if breaches else False

        return {
            "checked": True,
            "breaches_found": len(breaches),
            "notification_sent": notification_sent,
        }
