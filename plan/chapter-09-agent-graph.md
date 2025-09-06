Chapter 09 — Agent Graph (NL → DSL)

Goals
- Permitir definir agentes y flujos (circuito) en lenguaje natural y compilar a un DSL validado.

Checkpoints
1. [ ] Schema DSL (`docs/context/schemas/agent_graph.schema.json`): agents[], edges[], entry/exit, policies
2. [ ] Docs de diseño (`docs/context/agents.md`) con ejemplos A/B y desde cero
3. [ ] Endpoints: `POST /v1/agents/plan` y `POST /v1/profile/plan` (aceptan NL + flags)
4. [ ] Selección de modelo para parsing (14B por defecto; escalar a 32B si `complexity=high`)
5. [ ] Compilación síncrona: NL → JSON estricto → validación → persistir en `runtime/agents/current.yaml`
6. [ ] Compilación asíncrona (opcional): producir evento `llm.<tenant>.agents.plan.v1` y worker
7. [ ] Hot-reload del grafo y sanity checks (entrada/salida, sin ciclos prohibidos)

Acceptance Criteria
- El usuario puede “hablar” tanto a nivel perfil como de cada agente; el sistema unifica y compila a un único grafo válido.
- Persistimos NL y DSL para auditoría; se puede rehacer la compilación bajo demanda.

