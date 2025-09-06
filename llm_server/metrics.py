"""Métricas incrustadas ligeras para el servidor.

Exponen contadores, gauges simples (observe) y ventanas deslizantes de duraciones
para percentiles (p50/p95/p99). Están pensadas para consumo vía `/metrics` y
no pretenden reemplazar a Prometheus.

Docstrings en estilo Google para generación automática de documentación.
"""

import threading
from time import time
from typing import Dict


class Metrics:
    """Contenedor thread-safe de métricas.

    Métodos principales:
      - inc: incrementa contadores.
      - observe: registra el último valor de un gauge.
      - observe_duration: acumula duraciones para percentiles.
      - snapshot: exporta todas las métricas en un dict.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "requests_total": 0,
            "errors_total": 0,
        }
        self._timings: Dict[str, float] = {}
        self._durations_ms: Dict[str, list[float]] = {}

    def inc(self, key: str, by: int = 1) -> None:
        """Incrementa el contador `key` en `by` (por defecto 1)."""
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + by

    def observe(self, key: str, value: float) -> None:
        """Registra el valor actual de un gauge identificado por `key`."""
        with self._lock:
            self._timings[key] = value

    def snapshot(self) -> Dict[str, float]:
        """Devuelve una instantánea de contadores, gauges y percentiles.

        Returns:
            Dict[str, float]: Métricas aplanadas listas para serializar.
        """
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
        """Acumula una duración en ms bajo `key` manteniendo una ventana `max_keep`.

        Args:
            key (str): Nombre lógico de la métrica de duración.
            value_ms (float): Duración en milisegundos.
            max_keep (int): Límite de muestras retenidas (ventana). Defaults a 512.
        """
        with self._lock:
            arr = self._durations_ms.setdefault(key, [])
            arr.append(float(value_ms))
            if len(arr) > max_keep:
                # keep recent window
                self._durations_ms[key] = arr[-max_keep:]


metrics = Metrics()
