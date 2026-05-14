import sys
from pathlib import Path

import pytest

# Add CLISApp-backend to sys.path so tests can import backend modules directly
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture
def debug_client(monkeypatch):
    """A TestClient with DEBUG=true so the debug router is mounted."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "debug", True)

    from app.main import create_application
    from fastapi.testclient import TestClient

    return TestClient(create_application())
