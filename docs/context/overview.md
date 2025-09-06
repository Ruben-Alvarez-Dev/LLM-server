AI-server: Local LLM-server + Memory-server

Architecture Summary
- Orchestrator coordinates role agents and dispatches requests to the LLM-server and Memory-server.
- LLM-server hosts multiple quantized models sized for coding, analysis, and verification roles.
- Memory-server provides NVMe-backed vector retrieval with hierarchical summaries (N1–N5) and caches hot chunks.
- A single active profile name is stored in `runtime/current_profile`, selecting config under `configs/custom_profiles/`.

Messaging Layer
- Data-plane: Redpanda (Kafka API) for high-throughput topics across inference, results, embeddings, and DLQ/retry.
- Control-plane: NATS JetStream for lightweight signals (heartbeats, start/stop, leases) per-tenant accounts.
- ETL: Benthos (Redpanda Connect) to fan-out results and ingest embeddings to vector DBs (e.g., pgvector).
- Tenancy: Single-tenant by default; multi-tenant via `TENANCY_MODE` switch without migrations. Topic/subject conventions ensure isolation.
- When to use Pulsar: strict multi-tenant with namespaces/tenants built-in, tiered storage, geo-replication. Provided as optional profile in `configs/messaging/pulsar-profile`.

High-level Flow
- Inference: API → produce InferRequest → workers consume → generate → produce InferResult → fan-out/archive via Benthos → metrics.
- Embeddings: Producers write `embeddings.ingest` → ETL batches and writes to vector store → ack/metrics.
- Control: NATS subjects per tenant for heartbeats, capacity signals, backpressure, and feature toggles.

Interfaces
- HTTP API: OpenAI-compatible endpoints for chat/completions (see `docs/context/api-compat.md`).
- MCP: Optional stdio JSON-RPC server for MCP clients (e.g., Claude Desktop/Cline), exposing `llm.chat` and future tools.
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
