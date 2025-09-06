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
            data["ts"] = time()
            return data


metrics = Metrics()

