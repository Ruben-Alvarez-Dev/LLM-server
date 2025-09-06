Chapter 03 — LLM Engine

Goals
- Load and manage multiple models per configs with concurrency and limits.

Checkpoints
1. [x] Model registry reads `configs/models.yaml` and maps to ../models files
2. [x] Loader adapter (llama.cpp CLI wrapper) scaffold
3. [x] Concurrency controls per role from limits/profile
4. [x] Context window enforcement (heuristic)
5. [x] Step cutoff enforcement (timeout in runner)
6. [x] Speculative decoding hook (delegates to target for now)

Acceptance Criteria
- Registry reports readiness when llama-cli exists and files are present.
- Timeouts enforced; speculative hook present for future.
