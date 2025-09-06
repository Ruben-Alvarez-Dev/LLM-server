Chapter 02 — Infrastructure

Goals
- Runtime configuration, process wiring, health and metrics.

Checkpoints
1. [x] Config loader: merge order (env → profile → defaults)
2. [ ] Ports/process names honored from profile
3. [x] Health endpoints: `/healthz`, `/readyz`
4. [x] Basic metrics: `/metrics` (requests, latency, errors)
5. [ ] Structured logging (JSON) + request IDs
6. [ ] Graceful shutdown and timeouts
7. [x] Build tooling: llama.cpp Metal targets + models download helper

Acceptance Criteria
- Health and readiness return 200; metrics expose counters.
- Logs are structured and include request correlation IDs.
