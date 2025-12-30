#!/usr/bin/env python3
"""
Preflight validation script for CLISAPP.

Checks:
- Required tools: python3, pip, node, npm
- Repo-local prerequisites: .env file, node_modules
- Port availability: API (8080), tiles (8000)

Usage: python3 scripts/preflight.py
Environment variables for port override:
  PREFLIGHT_API_PORT   - API port to check (default: 8080)
  PREFLIGHT_TILES_PORT - Tiles port to check (default: 8000)

Exit codes:
  0 - All checks passed
  1 - One or more checks failed
"""
import os
import socket
import subprocess
import sys
from pathlib import Path
import errno


# ANSI colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_pass(name: str, detail: str = ""):
    """Print a passing check."""
    detail_str = f" ({detail})" if detail else ""
    print(f"  {GREEN}PASS{RESET} {name}{detail_str}")


def print_fail(name: str, action: str):
    """Print a failing check with actionable next step."""
    print(f"  {RED}FAIL{RESET} {name}")
    print(f"       {YELLOW}Action:{RESET} {action}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{BOLD}== {title} =={RESET}")


def check_command(cmd: list[str], name: str) -> tuple[bool, str]:
    """Check if a command exists and get its version."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            # Extract just the version line
            version = version.split("\n")[0]
            return True, version
        return False, ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, ""


def parse_port(env_key: str, default: int) -> tuple[bool, int, str]:
    raw = os.environ.get(env_key)
    if raw is None or raw == "":
        return True, default, ""
    try:
        port = int(raw)
    except ValueError:
        return False, default, f"{env_key} must be an integer (got: {raw!r})"
    if not (1 <= port <= 65535):
        return False, default, f"{env_key} must be between 1 and 65535 (got: {port})"
    return True, port, ""


def _has_listen_socket_lsof(port: int) -> tuple[bool | None, str]:
    """
    Best-effort listener detection via lsof.
    Returns (True/False, detail) if lsof exists, otherwise (None, detail).
    """
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError:
        return None, "lsof not available"
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, f"lsof failed: {exc}"

    has_listen = bool(result.stdout.strip())
    return has_listen, "lsof probe"


def _has_listen_socket_connect(port: int) -> tuple[bool | None, str]:
    """
    Best-effort listener detection via TCP connect probe.
    - connect success => listener exists
    - connection refused => likely no listener
    - permission/timeouts => unknown
    """
    for host, family in (("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)):
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            rc = sock.connect_ex((host, port))
        except OSError as exc:
            sock.close()
            if isinstance(exc, PermissionError):
                return None, f"connect probe permission denied ({host})"
            return None, f"connect probe error ({host}): {exc}"
        finally:
            try:
                sock.close()
            except OSError:
                pass

        if rc == 0:
            return True, f"connect probe ({host})"

    return False, "connect probe"


def check_port_availability(port: int) -> tuple[str, str]:
    """
    Determine port status.
    Returns ("available"|"in_use"|"unknown", detail).

    Preference order:
    1) Bind probe (most accurate for availability)
    2) lsof listener probe
    3) TCP connect probe
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", port))
        return "available", "bind probe"
    except OSError as exc:
        if isinstance(exc, PermissionError) or getattr(exc, "errno", None) in (errno.EPERM, errno.EACCES):
            has_listen, detail = _has_listen_socket_lsof(port)
            if has_listen is True:
                return "in_use", detail
            if has_listen is False:
                return "available", detail

            has_listen2, detail2 = _has_listen_socket_connect(port)
            if has_listen2 is True:
                return "in_use", detail2
            if has_listen2 is False:
                return "available", detail2
            return "unknown", detail2

        if getattr(exc, "errno", None) == errno.EADDRINUSE:
            return "in_use", "bind probe"
        return "unknown", f"bind probe error: {exc}"
    finally:
        try:
            sock.close()
        except OSError:
            pass


def run_preflight() -> int:
    """Run all preflight checks. Returns 0 if all pass, 1 otherwise."""
    repo_root = Path(os.environ.get("PREFLIGHT_REPO_ROOT", Path(__file__).parent.parent)).resolve()
    all_passed = True

    print(f"{BOLD}CLISAPP Preflight Checks{RESET}")
    print("=" * 40)

    # ========================================
    # Required Tools
    # ========================================
    print_section("Required Tools")

    # python3
    ok, version = check_command(["python3", "--version"], "python3")
    if ok:
        print_pass("python3", version)
    else:
        print_fail("python3", "Install Python 3: https://python.org/downloads/")
        all_passed = False

    # pip (via python3 -m pip)
    ok, version = check_command(["python3", "-m", "pip", "--version"], "pip")
    if ok:
        print_pass("pip", version)
    else:
        print_fail("pip", "Run: python3 -m ensurepip --upgrade")
        all_passed = False

    # node
    ok, version = check_command(["node", "--version"], "node")
    if ok:
        print_pass("node", version)
    else:
        print_fail("node", "Install Node.js: https://nodejs.org/ or `brew install node`")
        all_passed = False

    # npm
    ok, version = check_command(["npm", "--version"], "npm")
    if ok:
        print_pass("npm", version)
    else:
        print_fail("npm", "npm is bundled with Node.js; reinstall Node.js if missing")
        all_passed = False

    # ========================================
    # Repo-Local Prerequisites
    # ========================================
    print_section("Repo-Local Prerequisites")

    # Backend .env file
    backend_env = repo_root / "CLISApp-backend" / ".env"
    backend_env_example = repo_root / "CLISApp-backend" / ".env.example"
    if backend_env.exists():
        print_pass("CLISApp-backend/.env", "exists")
    else:
        if backend_env_example.exists():
            print_fail(
                "CLISApp-backend/.env",
                f"Run: cp {backend_env_example} {backend_env}"
            )
        else:
            print_fail(
                "CLISApp-backend/.env",
                "Create .env file in CLISApp-backend/ with required config"
            )
        all_passed = False

    # Frontend node_modules
    frontend_modules = repo_root / "CLISApp-frontend" / "node_modules"
    frontend_package = repo_root / "CLISApp-frontend" / "package.json"
    if frontend_modules.exists() and frontend_modules.is_dir():
        print_pass("CLISApp-frontend/node_modules", "exists")
    else:
        if frontend_package.exists():
            print_fail(
                "CLISApp-frontend/node_modules",
                "Run: cd CLISApp-frontend && npm install"
            )
        else:
            print_fail(
                "CLISApp-frontend/node_modules",
                "Frontend package.json missing; check repo structure"
            )
        all_passed = False

    # ========================================
    # Port Availability
    # ========================================
    print_section("Port Availability")

    ok, api_port, err = parse_port("PREFLIGHT_API_PORT", 8080)
    if not ok:
        print_fail("PREFLIGHT_API_PORT", f"Set a valid port number (e.g. 8080). Details: {err}")
        all_passed = False

    ok, tiles_port, err = parse_port("PREFLIGHT_TILES_PORT", 8000)
    if not ok:
        print_fail("PREFLIGHT_TILES_PORT", f"Set a valid port number (e.g. 8000). Details: {err}")
        all_passed = False

    # API port
    status, detail = check_port_availability(api_port)
    if status == "available":
        print_pass(f"Port {api_port} (API)", "available")
    elif status == "in_use":
        print_fail(
            f"Port {api_port} (API)",
            f"Port appears in use ({detail}). Run: lsof -nP -iTCP:{api_port} -sTCP:LISTEN  (then kill the process or change config)"
        )
        all_passed = False
    else:
        print_fail(
            f"Port {api_port} (API)",
            f"Unable to determine availability ({detail}). Run: lsof -nP -iTCP:{api_port} -sTCP:LISTEN"
        )
        all_passed = False

    # Tiles port
    status, detail = check_port_availability(tiles_port)
    if status == "available":
        print_pass(f"Port {tiles_port} (Tiles)", "available")
    elif status == "in_use":
        print_fail(
            f"Port {tiles_port} (Tiles)",
            f"Port appears in use ({detail}). Run: lsof -nP -iTCP:{tiles_port} -sTCP:LISTEN  (then kill the process or change config)"
        )
        all_passed = False
    else:
        print_fail(
            f"Port {tiles_port} (Tiles)",
            f"Unable to determine availability ({detail}). Run: lsof -nP -iTCP:{tiles_port} -sTCP:LISTEN"
        )
        all_passed = False

    # ========================================
    # Summary
    # ========================================
    print()
    if all_passed:
        print(f"{GREEN}{BOLD}All preflight checks passed!{RESET}")
        print("You can now run: make up")
        return 0
    else:
        print(f"{RED}{BOLD}Some preflight checks failed.{RESET}")
        print("Please resolve the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(run_preflight())
