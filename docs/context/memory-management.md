Memory Management & Cleanup (Multi-Level)

Goals
- Avoid performance cliffs by proactive, continuous housekeeping.
- Bound RAM and SSD usage under configurable ceilings, with zero/near‑zero impact.

Layers
- RAM: model residency, working sets, request buffers.
- SSD/NVMe: caches (chunks, embeddings, temp images/artifacts), logs.

Signals
- RAM free/used, RSS of processes, page faults, GC pressure (Python), request queue depth.
- SSD free/used, write rate, inode pressure, per‑cache size.

Policies (initial sketch)
- Thresholds: soft/hard watermarks (e.g., RAM soft 80%, hard 90%; SSD soft 75%, hard 85%).
- Actions RAM: shrink buffers, drop cold caches, reduce concurrency (soft), evict non‑critical residents (hard).
- Actions SSD: LRU/W-TinyLFU for caches, time‑based TTL for temp artifacts, back‑pressure ingest when hard watermark nears.

Execution Model
- Always‑on background sweep (low‑priority), incremental, time‑sliced, observable via metrics/logs.
- No blocking sweeps. All actions are chunked (bounded per tick).

Observability
- Metrics: `ram_free_gb`, `ram_pressure`, `ssd_free_gb`, `ssd_pressure`, `ram_headroom_gb`, `cache_evictions_total`, `backpressure_events_total`.
- Beacons: RAM/SSD health beacons derived from headroom/pressure.
  - RAM beacon uses `ram_headroom_gb`: `warn` (≤ 6 GB), `hot` (≤ 2 GB), `critical` (≤ 0 GB), else `ok`.
  - SSD beacon uses disk `pressure` vs soft/hard watermarks (`soft_pct`/`hard_pct`), plus a `critical` guard for very low free space (≤ 2 GB).
- Logs: `housekeeper.tick` includes `ram_beacon` and `ssd_beacon`, and eviction planning fields.

Profiles & YAML
- Policies config lives in `configs/housekeeper.yaml` with three predefined strategies:
  - `balanced` (default): soft RAM 80%/hard 90%; SSD 75%/85%; 10s tick.
  - `performance`: soft RAM 85%/hard 95%; SSD 80%/92%; 5s tick.
  - `safety`: soft RAM 70%/hard 85%; SSD 70%/82%; 15s tick.
- Switch at runtime: `POST /admin/housekeeper/strategy {"name":"performance"}`.
- Inspect current policy: `GET /admin/housekeeper/policy`.
- `/info.housekeeper` muestra estrategia activa y umbrales.
  - También expone `beacons: {ram, ssd}` y un `snapshot` en vivo (cuando está disponible) con `headroom` y presiones.
 - Activar/desactivar acciones (evicciones/backpressure) en caliente:
   - `POST /admin/housekeeper/actions {"enabled": true|false}`
   - Actualiza `actions_enabled` en la política activa; el housekeeper la respeta en los ticks siguientes.

Always-On Metrics
- RAM/SSD metrics are always on; actions are gated by policy/flags.
- Exposed fields: `ram_free_gb`, `ram_pressure`, `ssd_free_gb`, `ssd_pressure`, `housekeeper_ticks_total`.

SSD Soft-Eviction (prepared)
- A per-tick soft-eviction is implemented behind `actions_enabled` (disabled by default).
- When disk pressure exceeds `ssd.soft_pct`, the housekeeper plans evictions up to `ssd.max_evict_per_tick_gb` toward returning under the soft watermark.
- Candidate directories default to `logs/`, `runtime/agents/`, and `{models_root}/_cache|cache` and are configurable via `ssd.evict_dirs`.
- With actions disabled, eviction is not executed; planning details are logged in `housekeeper.tick`.

Ejemplos
```
curl -s -X POST localhost:8081/admin/housekeeper/actions -H 'Content-Type: application/json' -d '{"enabled": true}'
curl -s localhost:8081/admin/housekeeper/policy | jq
curl -s localhost:8081/info | jq '.housekeeper'
```

Next Steps
- Validate no impact under load via stress tests; tune tick cadence and step sizes.
