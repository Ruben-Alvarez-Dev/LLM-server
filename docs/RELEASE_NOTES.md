LLM-server 0.1.0 — Beacons y Soft‑Eviction (preparado)

Lo nuevo
- Beacons RAM/SSD (ok/warn/hot/critical) derivados de métricas en vivo.
- Beacons expuestos en `/info.housekeeper.beacons` y en cada `housekeeper.tick` de logs.
- `ram_headroom_gb` documentado y usado para el beacon de RAM.
- Soft‑eviction de SSD preparado por tick, detrás de `actions_enabled` (desactivado por defecto).
- Planificación de evicción en logs; ejecución respeta un límite por tick y directorios candidatos.

Detalles
- Umbrales RAM: warn ≤ 6 GB, hot ≤ 2 GB, critical ≤ 0 GB; si no, ok.
- Umbrales SSD: warn ≥ soft watermark, hot ≥ hard watermark, critical con libre muy bajo (≤ 2 GB) o presión extrema.
- `/info` incluye estrategia activa, watermarks, `actions_enabled`, beacons y snapshot en vivo (si existe).
- Directorios candidatos por defecto: `logs/`, `runtime/agents/` y caches bajo `{models_root}` (`_cache` y `cache`). `ssd.evict_dirs` añade rutas y se fusiona con los defaults.
- Límite de evicción por tick controlado por `ssd.max_evict_per_tick_gb`.

Pruebas
- Cobertura para beacons en `/info`, snapshot, fallback sin HK, planificación y ejecución de evicción, y métricas del HK.

Compatibilidad
- Sin cambios incompatibles. Campos nuevos bajo `/info.housekeeper`.
