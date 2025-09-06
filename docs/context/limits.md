RAM and Limits (M1 Ultra)

Budgets
- Keep global overhead at ~25–30 GB out of total system RAM.
- Reserve ~10 GB for Memory-server.
- Allocate the remaining free RAM to the LLM-server; target ~70 GB free for models on this machine.

Windows and Concurrency
- Active windows: 32B → 48–64K, 14B → 24K, 7–8B → 16K.
- Concurrency: Analysis/Distillation = 1, Coder = 2, Verifiers = 3.
- Step cutoff: 8–15 seconds (default 12s).

Validation Rules
- Resident model set must fit within `ram_budget_gb` with ≥ 5 GB headroom.
- Memory-server usage is accounted separately via `memory_server_ram_gb`.
- `runtime/current_profile` must point to an existing custom profile.

RAM Plan (Example)
- Total free for LLM-server: 70 GB
- Memory-server reserve: 10 GB
- Orchestration overhead: 15–20 GB (kept outside the 70 GB figure)
- Remaining for resident models: 70 GB

Recommended Residency
- DeepSeek-R1-Distill-Qwen-32B (Q4_K_M): ~20 GB
- Qwen2.5-14B-Instruct (Q4_K_M): ~9 GB
- Phi-4-mini-instruct: ~5 GB
- Sum resident: ~34 GB → headroom: ~36 GB (≥ 5 GB ✓)

See `configs/*.yaml` for concrete windows and concurrency, and run `make validate` to see the RAM table.
