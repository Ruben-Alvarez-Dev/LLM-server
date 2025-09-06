LLM-server 0.1.0 — Housekeeper Beacons & SSD Soft-Eviction (prep)

Highlights
- RAM/SSD beacons (warn/hot/critical) derived from live metrics.
- Beacons exposed in `/info.housekeeper.beacons` and logged on each `housekeeper.tick`.
- `ram_headroom_gb` added to docs and used to drive RAM beacon logic.
- SSD soft-eviction is implemented per tick behind `actions_enabled` (disabled by default).
- Eviction planning is logged; execution respects per-tick cap and candidate dirs.

Details
- RAM beacon thresholds: warn ≤ 6 GB, hot ≤ 2 GB, critical ≤ 0 GB; else ok.
- SSD beacon thresholds: warn ≥ soft watermark, hot ≥ hard watermark, critical when very low free space (≤ 2 GB) or extreme pressure.
- `/info` now returns the active strategy, watermarks, actions flag, beacons, and a live snapshot (when available).
- Candidate eviction directories default to `logs/`, `runtime/agents/`, and `{models_root}/_cache|cache`; configurable via `ssd.evict_dirs`.
- Per-tick eviction target is limited by `ssd.max_evict_per_tick_gb` (default 1 GB) and aims to return below the soft watermark.

Testing
- Added test `tests/test_housekeeper_beacons.py` to validate `/info.housekeeper.beacons` presence and shape.

Compatibility
- No breaking API changes. New fields added under `/info.housekeeper`.

