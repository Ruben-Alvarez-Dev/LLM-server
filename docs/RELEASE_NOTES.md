LLM-server 0.1.0 — Beacons and Soft‑Eviction (prepared)

What’s New
- RAM/SSD beacons (ok/warn/hot/critical) derived from live metrics.
- Beacons exposed under `/info.housekeeper.beacons` and in each `housekeeper.tick` log.
- `ram_headroom_gb` documented and used for the RAM beacon.
- SSD soft‑eviction prepared per tick, gated by `actions_enabled` (disabled by default).
- Eviction planning in logs; execution respects a per‑tick limit and candidate directories.

Details
- RAM thresholds: warn ≤ 6 GB, hot ≤ 2 GB, critical ≤ 0 GB; otherwise ok.
- SSD thresholds: warn ≥ soft watermark, hot ≥ hard watermark, critical with very low free (≤ 2 GB) or extreme pressure.
- `/info` includes active strategy, watermarks, `actions_enabled`, beacons, and a live snapshot (when present).
- Default candidate directories: `logs/`, `runtime/agents/`, and caches under `{models_root}` (`_cache` and `cache`). `ssd.evict_dirs` adds paths and merges with defaults.
- Per‑tick eviction cap controlled by `ssd.max_evict_per_tick_gb`.

Tests
- Coverage for beacons in `/info`, snapshot, fallback without HK, eviction planning and execution, and HK metrics.

Compatibility
- No breaking changes. New fields under `/info.housekeeper`.
