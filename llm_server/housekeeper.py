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
    total_gb = total / (1024 ** 3)
    used_gb = (total - avail) / (1024 ** 3) if total > 0 else 0.0
    pressure = 0.0
    if total > 0:
        used = total - avail
        pressure = max(0.0, min(1.0, used / total))
    return {"free_gb": free_gb, "total_gb": total_gb, "used_gb": used_gb, "pressure": pressure}


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
                # RAM basics
                metrics.observe("ram_free_gb", mem.get("free_gb", 0.0))
                metrics.observe("ram_total_gb", mem.get("total_gb", 0.0))
                metrics.observe("ram_used_gb", mem.get("used_gb", 0.0))
                metrics.observe("ram_pressure", mem.get("pressure", 0.0))
                # LLM-server RSS (self + children)
                llm_rss_gb = 0.0
                try:
                    if psutil is not None:
                        proc = psutil.Process(os.getpid())  # type: ignore
                        procs = [proc] + proc.children(recursive=True)
                        llm_rss_gb = sum(getattr(p.memory_info(), 'rss', 0) for p in procs) / (1024 ** 3)
                        metrics.observe("llm_rss_gb", llm_rss_gb)
                except Exception:
                    pass
                # OS+apps (approx)
                os_apps_gb = max(0.0, mem.get("used_gb", 0.0) - llm_rss_gb)
                metrics.observe("os_apps_rss_gb", os_apps_gb)
                # Free reserve and headroom
                try:
                    cfg = getattr(self.app.state, 'config', {}) or {}
                    hk_cfg = cfg.get('housekeeper', {}) or {}
                    fr = hk_cfg.get('free_reserve', {}) or {}
                    min_gb = float(fr.get('min_gb', 8.0))
                    pct = float(fr.get('pct', 0.10))
                    total_gb = float(mem.get('total_gb', 0.0))
                    free_reserve_gb = max(min_gb, total_gb * pct)
                except Exception:
                    free_reserve_gb = 8.0
                headroom_gb = mem.get("free_gb", 0.0) - free_reserve_gb
                metrics.observe("ram_free_reserve_gb", free_reserve_gb)
                metrics.observe("ram_headroom_gb", headroom_gb)
                metrics.observe("ssd_free_gb", disk.get("free_gb", 0.0))
                metrics.observe("ssd_pressure", disk.get("pressure", 0.0))
                metrics.inc("housekeeper_ticks_total", 1)
                try:
                    log.info("housekeeper.tick", extra={
                        "ram_total_gb": round(mem.get("total_gb", 0.0), 2),
                        "ram_used_gb": round(mem.get("used_gb", 0.0), 2),
                        "llm_rss_gb": round(llm_rss_gb, 2),
                        "os_apps_rss_gb": round(os_apps_gb, 2),
                        "ram_free_gb": round(mem.get("free_gb", 0.0), 2),
                        "ram_free_reserve_gb": round(free_reserve_gb, 2),
                        "ram_headroom_gb": round(headroom_gb, 2),
                        "ram_pressure": round(mem.get("pressure", 0.0), 3),
                        "ssd_free_gb": round(disk.get("free_gb", 0.0), 2),
                        "ssd_pressure": round(disk.get("pressure", 0.0), 3),
                    })
                except Exception:
                    pass
            except Exception:
                pass
            self._stop.wait(self.interval_s)
