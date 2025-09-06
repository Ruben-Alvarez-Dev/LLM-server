Chapter 03 — LLM Engine

Goals
- Load and manage multiple models per configs with concurrency and limits.

Checkpoints
1. [ ] Model registry reads `configs/models.yaml`
2. [ ] Loader adapter (e.g., llama.cpp) abstraction
3. [ ] Concurrency controls per role from limits/profile
4. [ ] Context window enforcement
5. [ ] Step cutoff enforcement (8–15s)
6. [ ] Speculative decoding hook (7–8B → 32B)

Acceptance Criteria
- Selected models load successfully; concurrent requests respect limits.
- Timeouts and windows are enforced per request.

