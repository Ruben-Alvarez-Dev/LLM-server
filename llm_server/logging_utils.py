import json
import logging
import sys
import time
import uuid
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname.lower(),
            "ts": getattr(record, "ts", time.time()),
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=False)


def setup_root(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root.addHandler(h)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    setup_root()
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]

