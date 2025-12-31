#!/usr/bin/env python3
"""
API Service Management Script

Manages the lifecycle of the CLISApp API service:
- api-up: Start the API service on port 8080
- api-down: Stop the API service

Uses PID file for process tracking and supports test mode for deterministic testing.
"""
import os
import sys
import signal
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).parent.parent.absolute()
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

DEFAULT_STATE_DIR = BACKEND_DIR / "logs" / "api"
STATE_DIR = Path(os.environ.get("API_STATE_DIR", str(DEFAULT_STATE_DIR))).resolve()
LOG_DIR = Path(os.environ.get("API_LOG_DIR", str(STATE_DIR))).resolve()

PID_FILE = STATE_DIR / "api.pid"
META_FILE = STATE_DIR / "api.meta.json"

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# API configuration
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8080"))
HEALTH_URL = f"http://localhost:{API_PORT}/api/v1/health"
DOCS_URL = f"http://localhost:{API_PORT}/docs"

# Test mode flag
TEST_MODE = os.environ.get("API_TEST_MODE") == "1"
FORCE_KILL = os.environ.get("API_FORCE_KILL") == "1"


def ensure_log_dir():
    """Ensure log directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_pid_from_file():
    """Read PID from file. Returns None if file doesn't exist or is invalid."""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        return pid
    except (ValueError, OSError):
        return None


def is_process_running(pid):
    """Check if process with given PID is running."""
    if pid is None:
        return False

    try:
        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks if process exists
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True


def get_process_command(pid):
    """Get the command line for a process. Returns None if process not found or error."""
    if pid is None:
        return None

    try:
        # Use ps command for cross-platform compatibility (macOS/Linux)
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def read_meta():
    try:
        return json.loads(META_FILE.read_text())
    except (OSError, ValueError):
        return None


def write_meta(meta: dict):
    META_FILE.write_text(json.dumps(meta, indent=2))


def cleanup_state(pid: int | None = None):
    """Remove PID/meta and any per-pid logpath helper file."""
    for path in (PID_FILE, META_FILE):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    if pid:
        logpath_file = LOG_DIR / f"api-{pid}.logpath"
        try:
            if logpath_file.exists():
                logpath_file.unlink()
        except OSError:
            pass


def verify_process_ownership(pid):
    """Verify that the PID belongs to a CLISApp API process started by this script."""
    if not is_process_running(pid):
        return False

    meta = read_meta() or {}
    meta_pid = meta.get("pid")
    expected = meta.get("expected_cmd_substrings")

    cmd = get_process_command(pid)
    if cmd is None:
        # Some environments restrict process inspection (ps/command line). In that case, rely on meta.
        if isinstance(meta_pid, int) and meta_pid == pid:
            return True
        if os.environ.get("API_DEBUG"):
            print(f"[DEBUG] Could not read command for PID {pid} and no matching meta.pid", file=sys.stderr)
        return False

    if not isinstance(expected, list) or not expected:
        # Legacy fallback: best-effort detection
        expected = ["uvicorn", "app.main:app"]

    haystack = cmd.lower()
    is_ours = all(str(token).lower() in haystack for token in expected)
    if os.environ.get("API_DEBUG"):
        print(f"[DEBUG] PID {pid} command: {cmd}", file=sys.stderr)
        print(f"[DEBUG] expected_cmd_substrings: {expected}", file=sys.stderr)
        print(f"[DEBUG] ownership check: {is_ours}", file=sys.stderr)
    return is_ours


def get_log_file_for_pid(pid):
    """Get the log file path associated with a PID."""
    meta = read_meta() or {}
    log_path = meta.get("log_file")
    if isinstance(log_path, str) and log_path:
        return Path(log_path)

    # Read log path from PID file's companion .logpath file
    logpath_file = LOG_DIR / f"api-{pid}.logpath"
    if logpath_file.exists():
        try:
            return Path(logpath_file.read_text().strip())
        except (ValueError, OSError):
            pass
    # Fallback: assume latest symlink
    latest_link = LOG_DIR / "api-latest.log"
    if latest_link.exists():
        return latest_link
    return None


def start_api():
    """Start the API service."""
    ensure_log_dir()

    # Check if already running (with ownership verification)
    existing_pid = get_pid_from_file()
    if existing_pid:
        if is_process_running(existing_pid) and verify_process_ownership(existing_pid):
            existing_log = get_log_file_for_pid(existing_pid)
            print(f"  API service already running (PID: {existing_pid})")
            print(f"  Health: {HEALTH_URL}")
            print(f"  Docs:   {DOCS_URL}")
            if existing_log:
                print(f"  Log:    {existing_log}")
            print()
            print(f"  Action: Run 'make api-down' to stop the service")
            return 0

        if is_process_running(existing_pid) and not verify_process_ownership(existing_pid):
            print(f"  ERROR: PID file exists but does not look like a CLISApp API process (PID: {existing_pid})")
            print()
            print(f"  Action: Remove stale PID file if safe: rm {PID_FILE}")
            print(f"          Or set API_STATE_DIR to an isolated directory and retry")
            return 1

        # stale pid (process not running): cleanup and continue
        cleanup_state(existing_pid)

    # Generate timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"api-{timestamp}.log"
    latest_link = LOG_DIR / "api-latest.log"
    stable_link = LOG_DIR / "api.log"

    # Start the service
    try:
        if TEST_MODE:
            # Test mode: use dummy process that sleeps
            print("  [TEST MODE] Starting dummy API process...")
            with open(log_file, "w") as log_handle:
                process = subprocess.Popen(
                    [PYTHON_CMD, "-c", "import time; time.sleep(3600)", "clisapp-api-service"],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=False,  # Keep same session to allow sandboxed stop/signals
                )
        else:
            # Production mode: start uvicorn
            print("  Starting API service...")
            uvicorn_cmd = [
                PYTHON_CMD, "-m", "uvicorn",
                "app.main:app",
                "--host", API_HOST,
                "--port", str(API_PORT),
            ]

            with open(log_file, "w") as log_handle:
                process = subprocess.Popen(
                    uvicorn_cmd,
                    cwd=BACKEND_DIR,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # Detach from terminal
                )

        # Write PID file
        PID_FILE.write_text(str(process.pid))

        # Write log path file for this PID
        logpath_file = LOG_DIR / f"api-{process.pid}.logpath"
        logpath_file.write_text(str(log_file))

        # Create/update latest symlink(s) (best-effort)
        for link in (latest_link, stable_link):
            try:
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(log_file.name)
            except OSError:
                pass

        expected_cmd_substrings = ["clisapp-api-service"] if TEST_MODE else ["uvicorn", "app.main:app"]
        write_meta(
            {
                "pid": process.pid,
                "expected_cmd_substrings": expected_cmd_substrings,
                "log_file": str(log_file),
                "started_at": time.time(),
            }
        )

        # Give process time to start
        time.sleep(0.5)

        # Verify it's still running
        if not is_process_running(process.pid):
            print(f"  ERROR: API service failed to start")
            print(f"  Check log: {log_file}")
            cleanup_state(process.pid)
            return 1

        # Print success message
        print(f"  ✓ API service started (PID: {process.pid})")
        print()
        print(f"  Health: {HEALTH_URL}")
        print(f"  Docs:   {DOCS_URL}")
        print(f"  Log:    {log_file}")
        print()

        return 0

    except Exception as e:
        print(f"  ERROR: Failed to start API service: {e}")
        cleanup_state(existing_pid)
        return 1


def stop_api():
    """Stop the API service."""
    # Get PID from file
    pid = get_pid_from_file()

    if pid is None:
        print("  API service not running (no PID file)")
        return 0

    if not is_process_running(pid):
        print(f"  API service not running (stale PID: {pid})")
        cleanup_state(pid)
        return 0

    if not verify_process_ownership(pid) and not FORCE_KILL:
        print(f"  ERROR: Refusing to stop PID {pid} (not verified as CLISApp API process)")
        print()
        print(f"  Action: If this PID is safe to kill, rerun with API_FORCE_KILL=1")
        print(f"          Or remove stale state: rm {PID_FILE} {META_FILE}")
        return 1

    # Terminate process (we've verified it's ours)
    print(f"  Stopping API service (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)

        # Wait for process to terminate (max 5 seconds)
        for _ in range(50):
            if not is_process_running(pid):
                break
            time.sleep(0.1)
        else:
            # Process didn't terminate, force kill
            print(f"  Process didn't terminate gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)

        cleanup_state(pid)

        print("  ✓ API service stopped")
        return 0

    except ProcessLookupError:
        # Process already gone
        cleanup_state(pid)
        print("  ✓ API service stopped")
        return 0
    except PermissionError:
        print(f"  ERROR: No permission to stop process {pid}")
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: api_service.py {up|down}")
        return 1

    command = sys.argv[1]

    if command == "up":
        return start_api()
    elif command == "down":
        return stop_api()
    else:
        print(f"Unknown command: {command}")
        print("Usage: api_service.py {up|down}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
