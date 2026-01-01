#!/usr/bin/env python3
"""
Shared helpers for pipeline logging and stdio tee-ing.
"""

from __future__ import annotations

import io
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"
LOG_DIR = BACKEND_DIR / "logs" / "pipeline"


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file(test_mode: bool = False) -> tuple[Path | None, Path | None]:
    if test_mode:
        return None, None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"pipeline-{timestamp}.log"
    latest_symlink = LOG_DIR / "pipeline-latest.log"
    return log_file, latest_symlink


def update_latest_symlink(log_file: Path | None, symlink_path: Path | None) -> None:
    if log_file is None or symlink_path is None:
        return
    try:
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to(log_file.name)
    except Exception:
        pass


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for stream in self._streams:
            stream.write(s)
        return len(s)

    def flush(self):
        for stream in self._streams:
            try:
                stream.flush()
            except ValueError:
                pass


@contextmanager
def tee_stdio_to_file(log_file: Path | None):
    if log_file is None:
        yield
        return
    ensure_log_dir()
    log_file.touch(exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log_fh:
        tee = Tee(sys.stdout, log_fh)
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = tee
            sys.stderr = tee
            yield
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
