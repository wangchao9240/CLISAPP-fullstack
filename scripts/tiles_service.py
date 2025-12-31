#!/usr/bin/env python3
"""
Tile Server Service Management Script

Manages the lifecycle of the CLISApp Tile Server service:
- tiles-up: Start the tile server on port 8000
- tiles-down: Stop the tile server

Uses PID file for process tracking and supports test mode for deterministic testing.
"""
import os
import sys
import signal
import subprocess
import time
import json
import socket
import errno
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


# Paths (relative to repository root)
REPO_ROOT = Path(__file__).parent.parent.absolute()
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"

DEFAULT_STATE_DIR = BACKEND_DIR / "logs" / "tiles"
STATE_DIR = Path(os.environ.get("TILES_STATE_DIR", str(DEFAULT_STATE_DIR))).resolve()
LOG_DIR = Path(os.environ.get("TILES_LOG_DIR", str(STATE_DIR))).resolve()

PID_FILE = STATE_DIR / "tiles.pid"
META_FILE = STATE_DIR / "tiles.meta.json"

# Python interpreter - prefer venv if available
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
PYTHON_CMD = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

# Tile server configuration
TILES_HOST = os.environ.get("TILES_HOST", "0.0.0.0")
TILES_PORT = int(os.environ.get("TILES_PORT", "8000"))
HEALTH_URL = f"http://localhost:{TILES_PORT}/health"
DEMO_URL = f"http://localhost:{TILES_PORT}/tiles/pm25/demo"

# Test mode flag
TEST_MODE = os.environ.get("TILES_TEST_MODE") == "1"
FORCE_KILL = os.environ.get("TILES_FORCE_KILL") == "1"


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
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
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


def meta_indicates_test_mode(meta: dict | None) -> bool:
    if not isinstance(meta, dict):
        return False
    expected = meta.get("expected_cmd_substrings")
    if not isinstance(expected, list):
        return False
    return any("clisapp-tiles-service" in str(token).lower() for token in expected)


def write_meta(meta: dict):
    META_FILE.write_text(json.dumps(meta, indent=2))


def cleanup_state(pid: int | None = None):
    for path in (PID_FILE, META_FILE):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    if pid:
        logpath_file = LOG_DIR / f"tiles-{pid}.logpath"
        try:
            if logpath_file.exists():
                logpath_file.unlink()
        except OSError:
            pass


def verify_process_ownership(pid):
    """Verify that the PID belongs to a tile server process started by this script."""
    if not is_process_running(pid):
        return False

    meta = read_meta() or {}
    meta_pid = meta.get("pid")
    expected = meta.get("expected_cmd_substrings")

    cmd = get_process_command(pid)
    if cmd is None:
        return isinstance(meta_pid, int) and meta_pid == pid

    if not isinstance(expected, list) or not expected:
        expected = ["uvicorn", "data_pipeline.servers.tile_server:app"]

    haystack = cmd.lower()
    return all(str(token).lower() in haystack for token in expected)


def get_log_file_for_pid(pid):
    meta = read_meta() or {}
    log_path = meta.get("log_file")
    if isinstance(log_path, str) and log_path:
        return Path(log_path)

    logpath_file = LOG_DIR / f"tiles-{pid}.logpath"
    if logpath_file.exists():
        try:
            return Path(logpath_file.read_text().strip())
        except (ValueError, OSError):
            pass

    latest_link = LOG_DIR / "tiles-latest.log"
    if latest_link.exists():
        return latest_link
    return None


def ensure_uvicorn_available():
    result = subprocess.run(
        [PYTHON_CMD, "-c", "import uvicorn"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True

    err = (result.stderr or result.stdout or "").strip()
    print("  ERROR: Tile server dependencies missing: uvicorn is not importable")
    if err:
        print(f"  Detail: {err.splitlines()[-1]}")
    print()
    print("  Action: Create/activate backend venv and install dependencies, then retry:")
    print(f"          cd {BACKEND_DIR} && python3 -m venv venv && ./venv/bin/python -m pip install -r requirements.txt")
    return False


def can_bind(host: str, port: int) -> tuple[bool, str | None]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(1)
        return True, None
    except OSError as e:
        code = errno.errorcode.get(e.errno, "UNKNOWN")
        return False, f"{e.errno} {code}: {e}"
    finally:
        try:
            s.close()
        except Exception:
            pass


def is_tiles_healthy(timeout_seconds: float = 0.5) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout_seconds) as response:
            return response.status == 200
    except Exception:
        return False


def start_tiles():
    """Start the tile server."""
    ensure_log_dir()

    # Check if already running
    existing_pid = get_pid_from_file()
    if existing_pid:
        if is_process_running(existing_pid) and verify_process_ownership(existing_pid):
            existing_log = get_log_file_for_pid(existing_pid)
            existing_meta = read_meta()
            if not TEST_MODE and meta_indicates_test_mode(existing_meta):
                print(f"  ERROR: Found a tiles service process started in TEST MODE (dummy) (PID: {existing_pid})")
                if existing_log:
                    print(f"  Log:    {existing_log}")
                print()
                print("  This dummy process does not serve HTTP, so /health and /tiles/... will time out.")
                print("  Likely cause: a previous test run (pytest) was interrupted and didn't clean up.")
                print()
                print("  Action: Run 'make tiles-down' to stop it, then rerun 'make tiles-up'")
                return 1
            print(f"  Tile server already running (PID: {existing_pid})")
            print(f"  Health: {HEALTH_URL}")
            print(f"  Demo:   {DEMO_URL}")
            if existing_log:
                print(f"  Log:    {existing_log}")
            print()
            if not TEST_MODE and not is_tiles_healthy():
                print("  WARNING: Process is running but /health is not responding")
                if existing_log:
                    print(f"  Check log: {existing_log}")
                print()
            print("  Action: Run 'make tiles-down' to stop the service")
            return 0

        if is_process_running(existing_pid) and not verify_process_ownership(existing_pid):
            print(f"  ERROR: PID file exists but does not look like a CLISApp tile-server process (PID: {existing_pid})")
            print()
            print(f"  Action: Remove stale PID file if safe: rm {PID_FILE}")
            print("          Or set TILES_STATE_DIR to an isolated directory and retry")
            return 1

        cleanup_state(existing_pid)

    # Start the service
    if not TEST_MODE and not ensure_uvicorn_available():
        return 1

    if not TEST_MODE:
        ok, err = can_bind(TILES_HOST, TILES_PORT)
        if not ok:
            print(f"  ERROR: Cannot bind tile server to {TILES_HOST}:{TILES_PORT}")
            if err:
                print(f"  Detail: {err}")
            print()
            if err and "EPERM" in err:
                print("  Likely cause: This execution environment forbids opening listening sockets (sandbox restriction).")
                print("  Action: Run `make tiles-up` from your local terminal (outside sandbox), or adjust your Codex sandbox permissions.")
            else:
                print("  Action: If port is in use, stop the service: make tiles-down")
                print("          Or override port: TILES_PORT=18000 make tiles-up")
                print("          Or override host: TILES_HOST=127.0.0.1 make tiles-up")
            return 1

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = LOG_DIR / f"tiles-{timestamp}.log"
    latest_link = LOG_DIR / "tiles-latest.log"
    stable_link = LOG_DIR / "tiles.log"

    try:
        if TEST_MODE:
            print("  [TEST MODE] Starting dummy tile server process...")
            with open(log_file, "w") as log_handle:
                process = subprocess.Popen(
                    [PYTHON_CMD, "-c", "import time; time.sleep(3600)", "clisapp-tiles-service"],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=False,  # Keep same session to allow sandboxed stop/signals
                )
        else:
            print("  Starting tile server...")
            uvicorn_cmd = [
                PYTHON_CMD,
                "-m",
                "uvicorn",
                "data_pipeline.servers.tile_server:app",
                "--host",
                TILES_HOST,
                "--port",
                str(TILES_PORT),
            ]

            with open(log_file, "w") as log_handle:
                process = subprocess.Popen(
                    uvicorn_cmd,
                    cwd=BACKEND_DIR,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )

        PID_FILE.write_text(str(process.pid))

        logpath_file = LOG_DIR / f"tiles-{process.pid}.logpath"
        logpath_file.write_text(str(log_file))

        for link in (latest_link, stable_link):
            try:
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to(log_file.name)
            except OSError:
                pass

        expected_cmd_substrings = ["clisapp-tiles-service"] if TEST_MODE else ["uvicorn", "data_pipeline.servers.tile_server:app"]
        write_meta(
            {
                "pid": process.pid,
                "expected_cmd_substrings": expected_cmd_substrings,
                "log_file": str(log_file),
                "started_at": time.time(),
            }
        )

        time.sleep(0.5)

        if process.poll() is not None or not is_process_running(process.pid):
            print("  ERROR: Tile server failed to start")
            print(f"  Check log: {log_file}")
            cleanup_state(process.pid)
            return 1

        if not TEST_MODE:
            health_ok = False
            deadline = time.time() + 10.0
            while time.time() < deadline:
                if process.poll() is not None or not is_process_running(process.pid):
                    print("  ERROR: Tile server exited during startup")
                    print(f"  Check log: {log_file}")
                    cleanup_state(process.pid)
                    return 1
                if is_tiles_healthy():
                    health_ok = True
                    break
                time.sleep(0.2)

            if not health_ok:
                print("  WARNING: Tile server started, but /health is not responding yet")
                print(f"  Check log: {log_file}")

        print(f"  ✓ Tile server started (PID: {process.pid})")
        print()
        print(f"  Health: {HEALTH_URL}")
        print(f"  Demo:   {DEMO_URL}")
        print(f"  Log:    {log_file}")
        print()

        return 0
    except Exception as e:
        print(f"  ERROR: Failed to start tile server: {e}")
        cleanup_state(existing_pid)
        return 1
def stop_tiles():
    """Stop the tile server."""
    # Get PID from file
    pid = get_pid_from_file()

    if pid is None:
        print("  Tile server not running (no PID file)")
        return 0

    # Check if process is actually running
    if not is_process_running(pid):
        print(f"  Tile server not running (stale PID: {pid})")
        cleanup_state(pid)
        return 0

    if not verify_process_ownership(pid) and not FORCE_KILL:
        print(f"  ERROR: Refusing to stop PID {pid} (not verified as CLISApp tile-server process)")
        print()
        print("  Action: If this PID is safe to kill, rerun with TILES_FORCE_KILL=1")
        print(f"          Or remove stale state: rm {PID_FILE} {META_FILE}")
        return 1

    # Terminate process
    print(f"  Stopping tile server (PID: {pid})...")
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

        print("  ✓ Tile server stopped")
        return 0

    except ProcessLookupError:
        # Process already gone
        cleanup_state(pid)
        print("  ✓ Tile server stopped")
        return 0
    except PermissionError:
        print(f"  ERROR: No permission to stop process {pid}")
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: tiles_service.py {up|down}")
        return 1

    command = sys.argv[1]

    if command == "up":
        return start_tiles()
    elif command == "down":
        return stop_tiles()
    else:
        print(f"Unknown command: {command}")
        print("Usage: tiles_service.py {up|down}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
