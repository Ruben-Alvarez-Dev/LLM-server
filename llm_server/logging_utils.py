import json
import logging
import os
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar
from typing import Any, Dict, Optional


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
        # Attach request_id from context when available
        rid = get_request_id()
        if rid and "request_id" not in payload:
            payload["request_id"] = rid
        return json.dumps(payload, ensure_ascii=False)


def setup_root(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    # Ensure stream handler
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        root.addHandler(h)
    # Optional file logging
    log_file = os.getenv("LOG_FILE")
    log_to_file = os.getenv("LOG_TO_FILE", "0") == "1" or bool(log_file)
    if log_to_file:
        if not log_file:
            log_dir = os.getenv("LOG_DIR", "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "llm-server.jsonl")
        # Avoid duplicate handlers to the same file
        if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == os.path.abspath(log_file) for h in root.handlers):
            fh = RotatingFileHandler(log_file, maxBytes=int(os.getenv("LOG_MAX_BYTES", "10485760")), backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")))
            fh.setFormatter(JsonFormatter())
            root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    setup_root()
    return logging.getLogger(name)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


# Simple context propagation for request_id
_REQ_ID: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_request_id(rid: Optional[str]) -> None:
    _REQ_ID.set(rid)


def get_request_id() -> Optional[str]:
    return _REQ_ID.get()
