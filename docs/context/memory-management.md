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
- Metrics: `ram_free_gb`, `ram_pressure`, `ssd_free_gb`, `ssd_pressure`, `cache_evictions_total`, `backpressure_events_total`.
- Logs: `housekeeper.tick`, `evict`, `backpressure` with reasons and sizes.

Profiles & YAML
- Policies config lives in `configs/housekeeper.yaml` with three predefined strategies:
  - `balanced` (default): soft RAM 80%/hard 90%; SSD 75%/85%; 10s tick.
  - `performance`: soft RAM 85%/hard 95%; SSD 80%/92%; 5s tick.
  - `safety`: soft RAM 70%/hard 85%; SSD 70%/82%; 15s tick.
- Switch at runtime: `POST /admin/housekeeper/strategy {"name":"performance"}`.
- Inspect current policy: `GET /admin/housekeeper/policy`.
- `/info.housekeeper` muestra estrategia activa y umbrales.

Always-On Metrics
- RAM/SSD metrics are always on; actions are gated by policy/flags.
- Exposed fields: `ram_free_gb`, `ram_pressure`, `ssd_free_gb`, `ssd_pressure`, `housekeeper_ticks_total`.

Next Steps
- Validate no impact under load via stress tests; tune tick cadence and step sizes.
