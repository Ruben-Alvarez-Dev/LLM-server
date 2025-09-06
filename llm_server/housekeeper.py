from __future__ import annotations

import os
import threading
import time
from typing import Dict, List, Optional, Tuple

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
    total_gb = total / (1024 ** 3)
    pressure = 0.0
    if total > 0:
        used = total - free
        pressure = max(0.0, min(1.0, used / total))
    return {"free_gb": free_gb, "total_gb": total_gb, "pressure": pressure}


def _beacon_ram(headroom_gb: float) -> str:
    try:
        h = float(headroom_gb)
    except Exception:
        h = 0.0
    if h <= 0.0:
        return "critical"
    if h <= 2.0:
        return "hot"
    if h <= 6.0:
        return "warn"
    return "ok"


def _beacon_ssd(pressure: float, free_gb: float, soft_pct: float, hard_pct: float) -> str:
    try:
        p = float(pressure)
        f = float(free_gb)
        soft = float(soft_pct)
        hard = float(hard_pct)
    except Exception:
        p, f, soft, hard = 0.0, 0.0, 0.75, 0.85
    if f <= 2.0 or p >= min(0.99, hard + 0.07):
        return "critical"
    if p >= hard:
        return "hot"
    if p >= soft:
        return "warn"
    return "ok"


def _list_files_by_oldest(paths: List[str]) -> List[Tuple[str, int, float]]:
    out: List[Tuple[str, int, float]] = []
    import os
    from pathlib import Path
    for base in paths:
        try:
            p = Path(base)
            if not p.exists():
                continue
            for root, dirs, files in os.walk(p, topdown=True):
                # skip hidden dirs and git
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
                for fn in files:
                    try:
                        fp = Path(root) / fn
                        st = fp.stat()
                        out.append((str(fp), int(st.st_size), float(st.st_mtime)))
                    except Exception:
                        continue
        except Exception:
            continue
    out.sort(key=lambda x: x[2])
    return out


def _plan_ssd_eviction(paths: List[str], target_bytes: int) -> Tuple[List[str], int]:
    if target_bytes <= 0:
        return [], 0
    files = _list_files_by_oldest(paths)
    chosen: List[str] = []
    total = 0
    for fp, sz, _ in files:
        chosen.append(fp)
        total += sz
        if total >= target_bytes:
            break
    return chosen, total


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
                # Compute beacons based on policy
                try:
                    pol = getattr(self.app.state, 'housekeeper_policy', {}) or {}
                    ram = pol.get('ram', {}) or {}
                    ssd = pol.get('ssd', {}) or {}
                    ram_beacon = _beacon_ram(headroom_gb)
                    ssd_beacon = _beacon_ssd(disk.get('pressure', 0.0), disk.get('free_gb', 0.0), float(ssd.get('soft_pct', 0.75)), float(ssd.get('hard_pct', 0.85)))
                except Exception:
                    ram_beacon = _beacon_ram(headroom_gb)
                    ssd_beacon = _beacon_ssd(disk.get('pressure', 0.0), disk.get('free_gb', 0.0), 0.75, 0.85)

                # Optionally plan and perform SSD soft-eviction per tick (actions gated)
                evict_plan_bytes = 0
                evict_done_bytes = 0
                evict_candidates: List[str] = []
                try:
                    pol = getattr(self.app.state, 'housekeeper_policy', {}) or {}
                    actions_enabled = bool(pol.get('actions_enabled', False))
                    ssd_pol = pol.get('ssd', {}) or {}
                    soft_pct = float(ssd_pol.get('soft_pct', 0.75))
                    max_evict_gb = float(ssd_pol.get('max_evict_per_tick_gb', 1.0))
                    # if above soft watermark, plan evictions up to target
                    # compute required bytes to reach soft watermark
                    total_gb = float(disk.get('total_gb', 0.0))
                    free_gb = float(disk.get('free_gb', 0.0))
                    if total_gb > 0:
                        threshold_used_gb = soft_pct * total_gb
                        required_free_gb = max(0.0, total_gb - threshold_used_gb)
                        deficit_gb = max(0.0, required_free_gb - free_gb)
                    else:
                        deficit_gb = 0.0
                    target_gb = min(max_evict_gb, max(0.0, deficit_gb))
                    target_bytes = int(target_gb * (1024 ** 3))
                    # Candidate dirs default: logs, runtime/agents, models_root/cache if exists
                    from pathlib import Path
                    cfg = getattr(self.app.state, 'config', {}) or {}
                    models_root = str(Path(cfg.get('models_root', '.')).resolve())
                    default_dirs = [
                        str(Path('logs').resolve()),
                        str((Path('runtime') / 'agents').resolve()),
                        str((Path(models_root) / '_cache').resolve()),
                        str((Path(models_root) / 'cache').resolve()),
                    ]
                    raw_dirs = ssd_pol.get('evict_dirs')
                    if isinstance(raw_dirs, list) and raw_dirs:
                        evict_dirs = [str(Path(d).resolve()) for d in raw_dirs] + default_dirs
                        # de-dup preserving order
                        seen = set()
                        evict_dirs = [d for d in evict_dirs if not (d in seen or seen.add(d))]
                    else:
                        evict_dirs = default_dirs
                    # Plan
                    if target_bytes > 0 and disk.get('pressure', 0.0) >= soft_pct:
                        candidates, planned_bytes = _plan_ssd_eviction(evict_dirs, target_bytes)
                        evict_plan_bytes = planned_bytes
                        evict_candidates = candidates
                        if actions_enabled and candidates:
                            freed = 0
                            import os
                            for fp in candidates:
                                try:
                                    sz = os.path.getsize(fp)
                                except Exception:
                                    sz = 0
                                try:
                                    os.remove(fp)
                                    freed += sz
                                except Exception:
                                    continue
                            evict_done_bytes = freed
                            try:
                                metrics.inc('cache_evictions_total', len(candidates))
                                metrics.observe('last_evict_bytes', float(freed))
                            except Exception:
                                pass
                except Exception:
                    pass

                # Store snapshot for /info
                try:
                    snap = {
                        'ts': time.time(),
                        'ram': {
                            'total_gb': mem.get('total_gb', 0.0),
                            'used_gb': mem.get('used_gb', 0.0),
                            'free_gb': mem.get('free_gb', 0.0),
                            'free_reserve_gb': free_reserve_gb,
                            'headroom_gb': headroom_gb,
                            'pressure': mem.get('pressure', 0.0),
                            'beacon': ram_beacon,
                        },
                        'ssd': {
                            'total_gb': disk.get('total_gb', 0.0),
                            'free_gb': disk.get('free_gb', 0.0),
                            'pressure': disk.get('pressure', 0.0),
                            'beacon': ssd_beacon,
                        },
                        'eviction': {
                            'planned_bytes': evict_plan_bytes,
                            'done_bytes': evict_done_bytes,
                            'planned_files': len(evict_candidates),
                        },
                    }
                    setattr(self.app.state, 'housekeeper_snapshot', snap)
                except Exception:
                    pass
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
                        "ram_beacon": ram_beacon,
                        "ssd_beacon": ssd_beacon,
                        "evict_planned_mb": round(evict_plan_bytes / (1024 ** 2), 2) if evict_plan_bytes else 0.0,
                        "evict_done_mb": round(evict_done_bytes / (1024 ** 2), 2) if evict_done_bytes else 0.0,
                    })
                except Exception:
                    pass
            except Exception:
                pass
            self._stop.wait(self.interval_s)
