"""
Structured pipeline execution logging helpers.

Inspect recent pipeline runs with:
    journalctl -u clisapp-pipeline --since "4 hours ago"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import sys
from types import MappingProxyType
from typing import Literal


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.max_level


def configure_pipeline_logging(level: int = logging.INFO) -> None:
    """Configure root logging so INFO goes to stdout and ERROR+ to stderr."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.addFilter(_MaxLevelFilter(logging.ERROR))
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)


@dataclass(frozen=True)
class LayerResult:
    layer_name: str
    status: Literal["success", "failed", "skipped"]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    error_message: str | None = None
    error_traceback: str | None = None

    @property
    def error_type(self) -> str | None:
        if not self.error_traceback:
            return None

        last_line = self.error_traceback.strip().splitlines()[-1]
        if ":" in last_line:
            return last_line.split(":", 1)[0].strip()
        return last_line.strip() or None

    def to_log_dict(self, run_id: str, *, data_timestamp: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "event": "pipeline_layer",
            "run_id": run_id,
            "layer_name": self.layer_name,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": round(self.duration_seconds, 3),
        }
        if data_timestamp is not None:
            payload["data_timestamp"] = data_timestamp
        if self.error_type is not None:
            payload["error_type"] = self.error_type
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        if self.error_traceback is not None:
            payload["error_traceback"] = self.error_traceback
        return payload


@dataclass(frozen=True)
class PipelineExecutionLog:
    run_id: str
    start_time: datetime
    end_time: datetime | None
    trigger_type: Literal["scheduled", "manual"]
    layer_results: dict[str, LayerResult]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "layer_results",
            MappingProxyType(dict(self.layer_results)),
        )

    @property
    def duration_seconds(self) -> float | None:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time).total_seconds(), 3)

    def format_summary(self, data_timestamp: str | None = None) -> str:
        statuses = {
            layer_name: layer_result.status
            for layer_name, layer_result in self.layer_results.items()
        }
        attempted = len(statuses)
        succeeded = sum(status == "success" for status in statuses.values())
        failed = sum(status == "failed" for status in statuses.values())
        skipped = sum(status == "skipped" for status in statuses.values())

        payload: dict[str, object] = {
            "event": "pipeline_summary",
            "run_id": self.run_id,
            "trigger_type": self.trigger_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "layers_processed": list(statuses.keys()),
            "layer_statuses": statuses,
        }
        if data_timestamp is not None:
            payload["data_timestamp"] = data_timestamp
        return json.dumps(payload, sort_keys=True)


def log_layer_result(
    logger: logging.Logger,
    run_id: str,
    layer_result: LayerResult,
    *,
    data_timestamp: str | None = None,
) -> None:
    message = json.dumps(
        layer_result.to_log_dict(run_id, data_timestamp=data_timestamp),
        sort_keys=True,
    )
    if layer_result.status == "failed":
        logger.error(message)
    else:
        logger.info(message)

