AI-server: Local LLM-server + Memory-server

Architecture Summary
- Orchestrator coordinates role agents and dispatches requests to the LLM-server and Memory-server.
- LLM-server hosts multiple quantized models sized for coding, analysis, and verification roles.
- Memory-server provides NVMe-backed vector retrieval with hierarchical summaries (N1–N5) and caches hot chunks.
- A single active profile name is stored in `runtime/current_profile`, selecting config under `configs/custom_profiles/`.

Data Flow
- User prompt → Router → (Planner/Architect) → Coder → Verifiers → Finalizer.
- Each role calls LLM-server with its context window limits and may query Memory-server for relevant context.
- Memory-server retrieves vectors by directed retrieval (task → components → files → chunks) with batching and caching.

Key Directories
- `docs/context/` — design docs, limits, schemas, playbooks, and manifest used by Codex/Cline.
- `configs/` — models, limits, roles, base/custom profiles.
- `runtime/` — runtime pointers and ephemeral state; `runtime/current_profile` holds the active profile name.
- `tools/` — validation and ops utilities.

Profiles
- Base profiles (`configs/base_profiles`) are reference-only.
- Custom profiles (`configs/custom_profiles`) are editable; `dev-default.yaml` is the default development profile.
