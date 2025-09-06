Chapter 02 — Infrastructure

Goals
- Runtime configuration, process wiring, health and metrics.

Checkpoints
1. [ ] Config loader: merge order (env → profile → defaults)
2. [ ] Ports/process names honored from profile
3. [ ] Health endpoints: `/healthz`, `/readyz`
4. [ ] Basic metrics: `/metrics` (requests, latency, errors)
5. [ ] Structured logging (JSON) + request IDs
6. [ ] Graceful shutdown and timeouts

Acceptance Criteria
- Health and readiness return 200; metrics expose counters.
- Logs are structured and include request correlation IDs.

