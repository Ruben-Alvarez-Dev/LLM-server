from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Dict

from .config_loader import build_effective_config


class ConcurrencyManager:
    def __init__(self) -> None:
        cfg = build_effective_config()
        # Priority: profile.concurrency > limits.concurrency
        limits_cc = (cfg.get("limits", {}) or {}).get("concurrency", {})
        prof_cc = cfg.get("concurrency", {}) or {}
        merged: Dict[str, int] = dict(limits_cc)
        merged.update({k: int(v) for k, v in prof_cc.items()})
        self._limits: Dict[str, int] = {k: (v if v > 0 else 0) for k, v in merged.items()}
        self._locks: Dict[str, threading.Semaphore] = {
            role: threading.Semaphore(max(1, limit)) if limit > 0 else threading.Semaphore(2**31 - 1)
            for role, limit in self._limits.items()
        }

    def limit_for(self, role: str) -> int:
        return int(self._limits.get(role, 1))

    @contextmanager
    def acquire(self, role: str):
        sem = self._locks.get(role)
        if sem is None:
            sem = self._locks.setdefault(role, threading.Semaphore(self.limit_for(role)))
        sem.acquire()
        try:
            yield
        finally:
            sem.release()

