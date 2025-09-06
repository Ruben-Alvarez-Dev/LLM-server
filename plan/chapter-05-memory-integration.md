Chapter 05 — Memory Integration

Goals
- Integrate Memory-server retrieval into request flow (optional path).

Checkpoints
1. [ ] Client config (host/port) from profile
2. [ ] Directed retrieval pipeline hooks (N2→N5)
3. [ ] Batching + cache of hot chunks
4. [ ] Feature flag to disable/enable memory

Acceptance Criteria
- Retrieval enriches context when enabled; degradation graceful when disabled.

