Agent Graph — Diseño y Flujo NL → DSL

Objetivo
- Permitir definir perfiles y agentes (roles, modelos, concurrencia, ventanas, relaciones) mediante lenguaje natural, y compilarlo a un DSL validado y ejecutable.

DSL (resumen)
- agents: [{ id, role, model, window, concurrency, description }]
- edges: [{ from, to, when? }]
- entry: string, exit: string | [string]
- policies: { escalate_to_32b_if: [rules], verify_steps: number }

Momento y Cómo ocurre
1) Entrada NL en perfil o agente
   - Vía endpoints: `POST /v1/profile/plan` y `POST /v1/agents/plan` (o MCP homólogos).
   - Se pueden enviar descripciones globales (perfil) y específicas (por agente); el motor las unifica.
2) Selección de modelo para parsing
   - Por defecto Qwen2.5-14B-Instruct (rapidez y calidad suficiente para extracción estructurada).
   - Si `complexity=high` o `strict=true`, se escala a DeepSeek-R1-Distill-Qwen-32B.
3) Compilación NL → JSON estricto
   - Prompt de extracción estructurada (forzamos JSON válido del DSL según schema).
   - Validamos contra `agent_graph.schema.json`.
4) Persistencia y recarga
   - Guardamos NL crudo para auditoría + DSL compilado en `runtime/agents/current.yaml`.
   - El router recarga el grafo; `make validate` verifica consistencia (entrada única, sin ciclos no permitidos).
5) Async opcional
   - Podemos producir `llm.<tenant>.agents.plan.v1` y que un worker compile y notifique.

Ejemplos
- Plantilla A (3 agentes): Router → Coder → Verifier (x2)
- Desde cero: “Quiero Router, Planner, Coder, Reviewer de estilo y Reviewer de lógica; Planner siempre consulta memoria”.
  - El compilador genera agents[] y edges[] con `when` adecuados; policies incluyen `verify_steps: 2`.

