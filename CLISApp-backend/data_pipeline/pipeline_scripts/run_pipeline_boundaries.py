#!/usr/bin/env python3
"""CLI entrypoint for boundary preprocessing."""

from pathlib import Path
import subprocess


SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "processing" / "geo"
PROCESS_SCRIPT = SCRIPT_ROOT / "process_boundaries.py"


def main() -> None:
    result = subprocess.run(["python", str(PROCESS_SCRIPT)], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()


