import threading
from time import time
from typing import Dict


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "requests_total": 0,
            "errors_total": 0,
        }
        self._timings: Dict[str, float] = {}
        self._durations_ms: Dict[str, list[float]] = {}

    def inc(self, key: str, by: int = 1) -> None:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + by

    def observe(self, key: str, value: float) -> None:
        with self._lock:
            self._timings[key] = value

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            data: Dict[str, float] = {}
            data.update(self._counters)
            data.update({f"timing_{k}": v for k, v in self._timings.items()})
            # percentiles for known timers
            for name, arr in self._durations_ms.items():
                if not arr:
                    continue
                xs = sorted(arr)
                def pct(p: float) -> float:
                    if not xs:
                        return 0.0
                    i = max(0, min(len(xs)-1, int(round(p * (len(xs)-1)))))
                    return xs[i]
                data[f"{name}_p50_ms"] = pct(0.50)
                data[f"{name}_p95_ms"] = pct(0.95)
                data[f"{name}_p99_ms"] = pct(0.99)
            data["ts"] = time()
            return data

    def observe_duration(self, key: str, value_ms: float, max_keep: int = 512) -> None:
        with self._lock:
            arr = self._durations_ms.setdefault(key, [])
            arr.append(float(value_ms))
            if len(arr) > max_keep:
                # keep recent window
                self._durations_ms[key] = arr[-max_keep:]


metrics = Metrics()
