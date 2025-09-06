Chapter 04 — APIs

Goals
- Expose REST endpoints for chat and completions with streaming.

Checkpoints
1. [x] `/v1/chat/completions` request/response schema
2. [x] `/v1/completions` request/response schema
3. [x] Streaming (chunked) support
4. [x] Input validation + error mapping (tenant header in multi)
5. [x] Concurrency limiter via ConcurrencyManager
6. [ ] Usage metrics and timings (p50/p95/p99)

Acceptance Criteria
- Happy-path and error paths covered; streaming verified locally.
