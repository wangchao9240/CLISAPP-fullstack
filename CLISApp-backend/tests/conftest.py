import sys
from pathlib import Path

# Add CLISApp-backend to sys.path so tests can import backend modules directly
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
