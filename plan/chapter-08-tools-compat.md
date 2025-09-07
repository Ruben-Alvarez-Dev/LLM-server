Chapter 08 — Tools & Compatibility

Goals
- OpenAI-compatible function calling (tools/tool_choice), SSE tool_calls deltas.
- Cline Plan/Act/Reflect modes, Continue (fast/smart/deep) mapping, Copilot FIM (suffix/prefix).

Checkpoints
1. [ ] Review official docs (OpenAI, Cline Plan/Act, Continue, Copilot) and lock parameter names
2. [ ] Function-calling request parsing: tools[] JSON Schema, tool_choice (auto|none|{function})
3. [ ] SSE streaming for tool_calls deltas (id/name/arguments)
4. [ ] Execution loop (opt-in): run_tools=true → tool call → tool result → assistant follow-up
5. [ ] Continue modes presets finalized; alias with `continue_mode` and presets in configs/api.yaml
6. [ ] Copilot FIM: support `suffix` + prompt template; add stops and penalties if needed
7. [ ] Update docs/api-compat.md with exact examples and edge-cases

Acceptance Criteria
- Endpoints accept tools and return tool_calls with correct SSE streaming.
- Plan/Act/Reflect/Continue mappings verifiable with known clients.
- FIM works for infill cases; smoke tests include suffix.
