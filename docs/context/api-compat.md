API Compatibility Overview

Goals
- 100% compatibility (request/response shapes) with OpenAI Chat Completions where applicable.
- Support for parameters commonly used by Cline Plan/Act, Continue modes, and GitHub Copilot-like flows.
- Dual interface: HTTP API and MCP (Model Context Protocol) server for stdio-jsonrpc integrations.

Endpoints (HTTP)
- GET /v1/models — list available models from the active profile.
- POST /v1/chat/completions — OpenAI-compatible request/response; supports streaming (SSE).
- POST /v1/completions — legacy text completions (basic compatibility).
- GET /info — metadata, endpoints, header policy, port block rules (7x/7y).
- GET /v1/tools — tool catalog with JSON Schemas (HTTP + MCP parity).
- GET /schemas/{name}.json — serve individual JSON Schemas (e.g., memory.search).
- GET /v1/ports — mapping of agent slots (B100+NN) and model slots (B200+NN) with ports.
- POST /v1/embeddings — OpenAI-style embeddings; deterministic stub in this release.
- POST /v1/voice/transcribe — ASR stub; returns structure with empty text unless backend present.
- POST /v1/voice/tts — TTS stub; returns base64 placeholder.
- POST /v1/research/search — Web/search stub; deterministic results.
- GET /v1/vision/ready — readiness (vl/ocr/none) with details.
- GET /v1/embeddings/ready — readiness stub.
- GET /v1/voice/ready — readiness stub (voice hub may be disabled by default).
- GET /v1/research/ready — readiness stub.
- POST /admin/profile/switch { name } — switch active profile; hot‑reloads config/registry.

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
  - `memory.search` — same schema as HTTP; returns `{ results: [...] }`.
  - `embeddings.generate` — OpenAI-like embeddings output.
  - `voice.transcribe` / `voice.tts` — mirror HTTP schemas.
  - `research.search` — mirror HTTP schema.
  - `agents.plan` — NL→DSL planning (parity with HTTP), persists current plan optionally.
  - `agents.current` — returns current agent-graph DSL if present.
- Usage: `make mcp.run` starts the MCP server on stdio for compatible clients.

Tenant Model
- Single-tenant only in this release. Header `X-Tenant-Id` is accepted but ignored; multi-tenant is disabled.
- Topic naming (when messaging is enabled): `llm.<tenant>.<domain>.v1`.

Vision Endpoint
- POST /v1/vision/analyze — Analyze screenshots/images; returns OCR text and heuristic insights.
- MCP tool `vision.analyze` mirrors the HTTP schema and result.

Examples
- HTTP Request:
  {
    "images": [
      { "base64": "<BASE64_IMAGE>", "purpose": "screenshot" }
    ],
    "prompt": "Detect console errors and summarize UI issues",
    "ocr": "auto",
    "tasks": ["ocr","errors","ui"]
  }
- HTTP Response:
  {
    "ocr": [ { "index": 0, "text": "...extracted text..." } ],
    "insights": ["Focus: look for error panels, stack traces, and red badges."],
    "issues": [],
    "raw": { "tasks": ["ocr","errors","ui"] }
  }
- MCP tools/call (vision.analyze):
  { "name": "vision.analyze", "arguments": { "images": [{"base64":"<BASE64>"}], "prompt": "OCR code and errors", "ocr": "auto" } }

Function Calling
- Prep mode enabled: if `tool_choice={type:'function', function:{name:'memory.search'}}`, HTTP chat returns `tool_calls` with arguments and `finish_reason:'tool_calls'`. The client/orchestrator executes the tool (HTTP/MCP) and decides next step.
- Closed‑loop (opcional): añade `server_tools_execute: true` (o `FC_CLOSED_LOOP=1`) para ejecutar `memory.search` en servidor y devolver un resumen directo.

Examples (chat with memory.search)
- Prep (cliente orquesta):
  {
    "model": "phi-4-mini-instruct",
    "messages": [{"role":"user","content":"find X in memory"}],
    "tool_choice": {"type":"function","function": {"name":"memory.search"}}
  }
- Closed‑loop (servidor ejecuta):
  {
    "model": "phi-4-mini-instruct",
    "messages": [{"role":"user","content":"find X in memory"}],
    "tool_choice": {"type":"function","function": {"name":"memory.search"}},
    "server_tools_execute": true
  }

Admin & Limits
- Rate limit básico: 429 configurable por env (`RATE_LIMIT_ENABLED`, `RATE_LIMIT_RPS`, `RATE_LIMIT_BURST`).
- Voice hub: deshabilitado por defecto; activar con `FEATURE_VOICE=1` para que aparezca en `/info` y `/v1/ports`.
