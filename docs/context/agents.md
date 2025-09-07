Agent Graph — Design and NL → DSL Flow

Objective
- Allow defining profiles and agents (roles, models, concurrency, windows, relationships) via natural language, and compile it to a validated, executable DSL.

DSL (summary)
- agents: [{ id, role, model, window, concurrency, description }]
- edges: [{ from, to, when? }]
- entry: string, exit: string | [string]
- policies: { escalate_to_32b_if: [rules], verify_steps: number }

When and How
1) NL input at profile or agent level
   - Via endpoints: `POST /v1/profile/plan` and `POST /v1/agents/plan` (or MCP equivalents).
   - You may send global descriptions (profile) and specific ones (per agent); the engine unifies them.
2) Model selection for parsing
   - Default: Qwen2.5-14B-Instruct (fast enough and good quality for structured extraction).
   - If `complexity=high` or `strict=true`, escalate to DeepSeek-R1-Distill-Qwen-32B.
3) Compilation NL → strict JSON
   - Structured extraction prompt (force valid DSL JSON according to schema).
   - Validate against `agent_graph.schema.json`.
4) Persistence and reload
   - Save raw NL for audit + compiled DSL at `runtime/agents/current.yaml`.
   - The router reloads the graph; `make validate` checks consistency (single entry, no disallowed cycles).
5) Optional async
   - Emit `llm.<tenant>.agents.plan.v1` and let a worker compile and notify.

Examples
- Template A (core slots): Router(01) → Reasoner(02) → Planner(03) → Coder(08) → Verifier(06) → Finalizer(10)
- From scratch: “I want Router, Planner, Coder, Style Reviewer and Logic Reviewer; Planner always queries memory.”
  - The compiler generates agents[] and edges[] with appropriate `when`; policies include `verify_steps: 2`.

Slots and Approaches (reference; each profile defines its own template)
- 01 Router — diagnostic-routing (reference)
- 02 Reasoner — deep-reason (reference)
- 03 Planner — plan-steps (reference)
- 04 Fast Action — quick-fix (reference)
- 05 Retriever — memory-bridge (reference)
- 06 Verifier — fast-verify (reference)
- 08 Coder — implement-safe (reference)
- 09 Debugger — failure-analysis (reference)
- 10 Finalizer — summarize-handoff (reference)

Contracts
- The orchestra exposes a single HUB (input/output) and internal routing is asynchronous (messaging). There are no public per-agent endpoints.
- External services to the orchestra (vision, voice, research, embeddings, etc.) do expose their own endpoints as defined by the profile.
- Minimal NL→DSL planning:
  - `POST /v1/agents/plan` — input `{ nl?: string, hints?: object, save?: bool }` → `{ dsl, validated, issues }`. Saves to `runtime/agents/current.yaml` when `save=true`.
  - `GET /v1/agents/current` — returns the current DSL if present.
