#!/usr/bin/env python3
"""Shared helpers for end-to-end layer pipeline scripts."""

from pathlib import Path
import subprocess
import sys
from typing import Iterable


# project root (CLISApp-backend)
ROOT = Path(__file__).resolve().parents[2]


def run(cmd: Iterable[str]) -> None:
    """Run a subprocess relative to project root and exit on failure."""
    command = list(cmd)
    print("➤", " ".join(command))
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"✗ 命令失败: {command}")
        sys.exit(result.returncode)


def python(script: Path, *args: str) -> list[str]:
    """Convenience helper to build a Python execution command."""
    return [sys.executable, str(script), *args]


__all__ = ["ROOT", "run", "python"]

