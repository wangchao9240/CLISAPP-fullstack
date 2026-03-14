"""Send a test FCM notification to the qld-health-alerts topic.

Usage:
    python scripts/send_test_notification.py
"""

import sys
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "data" / "firebase-service-account.json"
TOPIC = "qld-health-alerts"


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"Firebase credentials not found at {CREDENTIALS_PATH}")
        sys.exit(1)

    cred = credentials.Certificate(str(CREDENTIALS_PATH))
    firebase_admin.initialize_app(cred)

    message = messaging.Message(
        notification=messaging.Notification(
            title="Climate Health Alert",
            body="UV Index is HIGH (9.2) in South East Queensland. Apply SPF 50+ sunscreen and seek shade between 10am-2pm.",
        ),
        topic=TOPIC,
    )

    response = messaging.send(message)
    print(f"Notification sent successfully!")
    print(f"  Topic: {TOPIC}")
    print(f"  Message ID: {response}")


if __name__ == "__main__":
    main()
