# AI-server — Codex Pack

Purpose
- Provide a clean, runnable baseline for a local LLM-server + Memory-server setup with clear limits, roles, and a single active profile pointer at `runtime/current_profile`.
- Normalize context so Codex/Cline can quickly load key docs, configs, and schemas.

Critical Paths
- Configs: `configs/models.yaml`, `configs/limits.yaml`, `configs/custom_profiles/dev-default.yaml`
- Runtime: `runtime/current_profile` (must contain the active profile name)
- Schemas: `docs/context/schemas/*.schema.json`
- Validator: `tools/validate.py` and `Makefile` targets `codex` and `validate`
- Context: `docs/context/*` (overview, llm-server, memory-server, limits, playbooks)

Rules of Work
- Treat base profiles as read-only; edit only custom profiles.
- Keep model RAM within `ram_budget_gb` with ≥ 5 GB headroom.
- Respect role concurrency from `configs/limits.yaml` or the active profile.
- Use `docs/context/limits.md` for RAM math and validation rules.

How to Use with Codex/Cline
- Start at `docs/context/manifest.json` to load key files by priority.
- Use `make codex` to print the manifest entries.
- Use `make validate` to verify files, schemas, and RAM plan; it prints a RAM table showing resident set and headroom.

Default Profile Pointer
- `runtime/current_profile` should contain the string `dev-default`.
