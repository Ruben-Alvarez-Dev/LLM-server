Master Development Plan

Scope
- LLM-server baseline with Memory-server integration points.
- Single-branch workflow (main), organic commits per feature.

Chapters
- Chapter 01 — Foundation: repo scaffolding, configs, schemas, validator, CI hooks (lightweight), remote.
- Chapter 02 — Infrastructure: runtime config loader, process/ports, health/metrics, logging.
- Chapter 03 — LLM Engine: model registry + loader, concurrency, windows, step cutoff, speculative decoding hooks.
- Chapter 04 — APIs: chat/completions endpoints, request validation, streaming, errors/timeouts.
- Chapter 05 — Memory Integration: client stubs, directed retrieval hooks, caching.
- Chapter 06 — Ops & Telemetry: structured logs, request IDs, rate limits, backpressure.
- Chapter 07 — QA & Validation: unit/integration smoke, RAM validation checks, profile validation.
- Chapter 08 — Tools & Compatibility: OpenAI function-calling, Cline Plan/Act, Continue modes, Copilot FIM.
- Chapter 09 — Agent Graph (NL → DSL): definición de agentes/circuitos por lenguaje natural y compilación a DSL.

Status
- [x] Initialize context pack, configs, schemas, validator, profile, Makefile
- [x] Connect remote (SSH), push baseline
- [x] Implement infra (config loader, health/metrics)  
  (logging/IDs tracked in Ch.06)
- [x] Implement model loader + registry  
  (runner via llama.cpp CLI; windows/timeout enforced)
- [x] Implement APIs (chat/completions, streaming)
- [x] Messaging layer base (Redpanda+NATS, schemas, scripts, SDK)
 - [x] Wire memory integration stubs
- [x] Add ops/telemetry
- [x] Discovery endpoints (/info, /v1/tools, /schemas)
- [x] MCP tools parity with HTTP schemas
- [x] Disable multi-tenant for this release
- [x] Add profile-agnostic Vision endpoint (HTTP+MCP)
- [x] Tests + validation gates (smoke, CI)
- [x] Tools & Compatibility (Ch.08) — prep + optional closed-loop
- [x] Agent Graph NL→DSL (Ch.09) — esqueleto mínimo (plan/current)

Backlog (Next)
- [x] Embeddings config validation and docs (multi-instance)
- [x] Memory management (multi-level RAM/SSD): design + housekeeper stub (metrics only)

Checklist Index
- See chapter files for concrete checkpoints and acceptance criteria.
