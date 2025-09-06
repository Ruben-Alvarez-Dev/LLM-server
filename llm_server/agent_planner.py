from __future__ import annotations

import json
from typing import Any, Dict, List


def _default_graph() -> Dict[str, Any]:
    agents = [
        {"id": "router", "role": "router"},
        {"id": "coder", "role": "coder"},
        {"id": "verifier", "role": "verifier"},
        {"id": "finalizer", "role": "finalizer"},
    ]
    edges = [
        {"from": "router", "to": "coder"},
        {"from": "coder", "to": "verifier"},
        {"from": "verifier", "to": "finalizer"},
    ]
    return {"agents": agents, "edges": edges, "entry": "router", "policies": {"verify_steps": 1}}


def _nl_hints_to_overrides(nl: str) -> Dict[str, Any]:
    text = (nl or "").lower()
    overrides: Dict[str, Any] = {}
    # Tiny heuristics (non-intrusive)
    if "análisis" in text or "analysis" in text:
        overrides["include_reasoner"] = True
    if "plan" in text or "planner" in text:
        overrides["include_planner"] = True
    if "verificar dos" in text or "verify x2" in text or "double-check" in text:
        overrides["verify_steps"] = 2
    return overrides


def compile_nl_to_dsl(nl: str, hints: Dict[str, Any] | None = None) -> Dict[str, Any]:
    g = _default_graph()
    ov = _nl_hints_to_overrides(nl)
    if hints:
        ov.update(hints)
    if ov.get("include_reasoner") and not any(a["id"] == "reasoner" for a in g["agents"]):
        g["agents"].insert(1, {"id": "reasoner", "role": "reasoner"})
        g["edges"].insert(0, {"from": "router", "to": "reasoner"})
        g["edges"].insert(1, {"from": "reasoner", "to": "coder"})
    if ov.get("include_planner") and not any(a["id"] == "planner" for a in g["agents"]):
        idx = 2 if any(a["id"] == "reasoner" for a in g["agents"]) else 1
        g["agents"].insert(idx + 1, {"id": "planner", "role": "planner"})
        # rewire coder to come after planner
        g["edges"] = [e for e in g["edges"] if not (e["from"] == "router" and e["to"] == "coder")]
        prev = "reasoner" if any(a["id"] == "reasoner" for a in g["agents"]) else "router"
        g["edges"].append({"from": prev, "to": "planner"})
        g["edges"].append({"from": "planner", "to": "coder"})
    if "verify_steps" in ov:
        g.setdefault("policies", {})["verify_steps"] = int(ov.get("verify_steps", 1))
    return g


def validate_graph(dsl: Dict[str, Any]) -> Dict[str, Any]:
    # Lightweight validation consistent with docs/schema (required keys)
    ok = True
    issues: List[str] = []
    for key in ("agents", "edges", "entry"):
        if key not in dsl:
            ok = False
            issues.append(f"missing {key}")
    if not isinstance(dsl.get("agents", []), list) or not dsl.get("agents"):
        ok = False
        issues.append("agents must be non-empty list")
    if not isinstance(dsl.get("edges", []), list):
        ok = False
        issues.append("edges must be list")
    ids = {a.get("id") for a in dsl.get("agents", []) if isinstance(a, dict)}
    for e in dsl.get("edges", []):
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            ok = False
            issues.append("edge missing from/to")
            continue
        if e["from"] not in ids or e["to"] not in ids:
            ok = False
            issues.append("edge references unknown agent")
    if dsl.get("entry") not in ids:
        ok = False
        issues.append("entry not an agent id")
    return {"ok": ok, "issues": issues}


def save_current_plan(dsl: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(dsl, ensure_ascii=False, indent=2))

