Chapter 06 — Ops & Telemetry

Goals
- Operability: logs, tracing hooks, rate limit/backpressure.

Checkpoints
1. [ ] JSON logs with levels + fields
2. [ ] Request/trace IDs (header propagation)
3. [ ] Basic rate limit + backpressure
4. [ ] Error budget metrics (5xx, timeouts)

Acceptance Criteria
- Logs actionable and correlated; rate-limits prevent overload in local tests.

