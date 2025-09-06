from __future__ import annotations

import os
import threading
import time
from typing import Dict, Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional
    psutil = None  # type: ignore

import shutil


def _mem_stats() -> Dict[str, float]:
    total = 0.0
    avail = 0.0
    try:
        if psutil is not None:  # type: ignore
            vm = psutil.virtual_memory()  # type: ignore
            total = float(vm.total)
            avail = float(vm.available)
    except Exception:
        total = 0.0
        avail = 0.0
    free_gb = avail / (1024 ** 3)
    pressure = 0.0
    if total > 0:
        used = total - avail
        pressure = max(0.0, min(1.0, used / total))
    return {"free_gb": free_gb, "pressure": pressure}


def _disk_stats(path: str) -> Dict[str, float]:
    try:
        usage = shutil.disk_usage(path)
        total = float(usage.total)
        free = float(usage.free)
    except Exception:
        total = 0.0
        free = 0.0
    free_gb = free / (1024 ** 3)
    pressure = 0.0
    if total > 0:
        used = total - free
        pressure = max(0.0, min(1.0, used / total))
    return {"free_gb": free_gb, "pressure": pressure}


class Housekeeper:
    def __init__(self, app, interval_s: float, disk_path: str) -> None:
        self.app = app
        self.interval_s = max(1.0, float(interval_s))
        self.disk_path = disk_path
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        t = threading.Thread(target=self._run, name="housekeeper", daemon=True)
        self._thread = t
        t.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass

    def _run(self) -> None:
        from .metrics import metrics
        from .logging_utils import get_logger
        log = get_logger("llm-server")
        while not self._stop.is_set():
            try:
                mem = _mem_stats()
                disk = _disk_stats(self.disk_path)
                metrics.observe("ram_free_gb", mem.get("free_gb", 0.0))
                metrics.observe("ram_pressure", mem.get("pressure", 0.0))
                metrics.observe("ssd_free_gb", disk.get("free_gb", 0.0))
                metrics.observe("ssd_pressure", disk.get("pressure", 0.0))
                metrics.inc("housekeeper_ticks_total", 1)
                try:
                    log.info("housekeeper.tick", extra={
                        "ram_free_gb": round(mem.get("free_gb", 0.0), 2),
                        "ram_pressure": round(mem.get("pressure", 0.0), 3),
                        "ssd_free_gb": round(disk.get("free_gb", 0.0), 2),
                        "ssd_pressure": round(disk.get("pressure", 0.0), 3),
                    })
                except Exception:
                    pass
            except Exception:
                pass
            self._stop.wait(self.interval_s)

