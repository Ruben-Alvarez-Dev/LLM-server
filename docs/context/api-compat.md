API Compatibility Overview

Goals
- 100% compatibility (request/response shapes) with OpenAI Chat Completions where applicable.
- Support for parameters commonly used by Cline Plan/Act, Continue modes, and GitHub Copilot-like flows.
- Dual interface: HTTP API and MCP (Model Context Protocol) server for stdio-jsonrpc integrations.

Endpoints (HTTP)
- GET /v1/models — list available models from the active profile.
- POST /v1/chat/completions — OpenAI-compatible request/response; supports streaming (SSE).
- POST /v1/completions — legacy text completions (basic compatibility).

Streaming (SSE)
- Uses `text/event-stream` with `data: {chunk}` JSON lines and a final `data: [DONE]` line.
- Chunk shape: `{object:"chat.completion.chunk", model, created, id, choices:[{index, delta:{role?, content?}, finish_reason} ]}`.

Parameters
- Temperature, top_p, top_k, max_tokens, repeat_penalty, seed (defaults in `configs/limits.yaml: gen_defaults`).
- Continue modes: `continue_mode`: `fast|smart|deep` (optional) maps to preset params.
- Plan/Act: `act_as`: `plan|act|reflect` (optional) for routing; no behavior change by default.
- Deep Reasoning: `reasoning`: `{ enabled: bool, effort?: 'low'|'medium'|'high' }` toggle; currently advisory.

MCP Support
- Provides an MCP server over stdio (JSON-RPC 2.0) exposing tools:
  - `llm.chat`: fields {model, messages, params} — mirrors HTTP chat.
  - `memory.search` (stub) — placeholder for Memory-server integration.
- Usage: `make mcp.run` starts the MCP server on stdio for compatible clients.

Tenant Model
- Single-tenant by default; `TENANCY_MODE=multi` requires header `X-Tenant-Id`.
- Topic naming (when messaging is enabled): `llm.<tenant>.<domain>.v1`.

