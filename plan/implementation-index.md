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
- [ ] Implement infra (config loader, health/metrics)
- [ ] Implement model loader + registry
- [ ] Implement APIs (chat/completions, streaming)
- [ ] Wire memory integration stubs
- [ ] Add ops/telemetry
- [ ] Tests + validation gates
- [ ] Tools & Compatibility (Ch.08)
- [ ] Agent Graph NL→DSL (Ch.09)

Checklist Index
- See chapter files for concrete checkpoints and acceptance criteria.
