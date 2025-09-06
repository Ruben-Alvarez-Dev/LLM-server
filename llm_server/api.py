from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .generation import generate_with_llama_cli, speculative_generate
from .tenancy import require_tenant
from .messaging_stub import KafkaProducerStub
from .memory_client import MemoryClient
from .schemas import tool_list, get_schema_by_name
from .vision import analyze as vision_analyze, readiness as vision_readiness
from .embeddings import embed_texts
from .voice import transcribe as voice_transcribe, tts as voice_tts
from .research import web_search
from .logging_utils import get_logger
from .agent_planner import compile_nl_to_dsl, validate_graph, save_current_plan
from .housekeeper import _beacon_ram, _beacon_ssd, _mem_stats, _disk_stats  # type: ignore


class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    stream: bool = False
    user: Optional[str] = None
    continue_mode: Optional[str] = None
    act_as: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None
    server_tools_execute: Optional[bool] = None


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    stream: bool = False


def get_resources(request: Request):
    registry = request.app.state.registry
    conc = request.app.state.concurrency
    cfg = request.app.state.config
    return registry, conc, cfg


router = APIRouter()
producer = KafkaProducerStub()
mem_client = MemoryClient()
log = get_logger("llm-server")


def _topic_namer(tenant: str, domain: str) -> str:
    # Align with Go TopicNamer: single -> llm.<DEFAULT_TENANT_ID>.<domain>
    # Here we always build explicit with tenant resolved by require_tenant
    return f"llm.{tenant}.{domain}"


@router.get("/v1/models")
def list_models(request: Request):
    reg, _, cfg = get_resources(request)
    return {"object": "list", "data": [{"id": m.name, "object": "model"} for m in reg.list()]}


@router.get("/info")
def info(request: Request):
    _, _, cfg = get_resources(request)
    base = int(cfg["ports"]["llm_server"]) // 1000 * 1000
    agents_prefix = base + 100
    models_prefix = base + 200
    voice_enabled = os.getenv("FEATURE_VOICE", "0") in ("1","true","on")
    hk_cfg = cfg.get("housekeeper", {}) or {}
    strategies = hk_cfg.get("strategies", {}) or {}
    active = getattr(request.app.state, 'housekeeper_strategy', None) or hk_cfg.get("default_strategy", "balanced")
    pol = strategies.get(active, {})
    # Housekeeper policy and live snapshot
    snap = getattr(request.app.state, 'housekeeper_snapshot', None)
    pol = strategies.get(active, {})
    # Compute beacons from snapshot or on-the-fly
    def _compute_beacons():
        try:
            if snap:
                ram_b = snap.get('ram', {}).get('beacon', 'unknown')
                ssd_b = snap.get('ssd', {}).get('beacon', 'unknown')
                return ram_b, ssd_b
            # fallback live compute
            mem = _mem_stats()
            disk = _disk_stats(str((__import__("pathlib").Path(pol.get("ssd", {}).get("path", cfg.get("models_root", "."))).resolve())) )
            # free reserve/headroom
            fr = (cfg.get('housekeeper', {}) or {}).get('free_reserve', {}) or {}
            min_gb = float(fr.get('min_gb', 8.0)); pct = float(fr.get('pct', 0.10))
            total_gb = float(mem.get('total_gb', 0.0))
            free_reserve_gb = max(min_gb, total_gb * pct)
            headroom_gb = mem.get('free_gb', 0.0) - free_reserve_gb
            ram_b = _beacon_ram(headroom_gb)
            ssd_pol = pol.get('ssd', {}) or {}
            ssd_b = _beacon_ssd(disk.get('pressure', 0.0), disk.get('free_gb', 0.0), float(ssd_pol.get('soft_pct', 0.75)), float(ssd_pol.get('hard_pct', 0.85)))
            return ram_b, ssd_b
        except Exception:
            return 'unknown', 'unknown'

    ram_beacon, ssd_beacon = _compute_beacons()
    hk = {
        "enabled": True,
        "strategy": active,
        "interval_s": pol.get("interval_s", 10),
        "ram_watermarks": {"soft_pct": pol.get("ram", {}).get("soft_pct", 0.8), "hard_pct": pol.get("ram", {}).get("hard_pct", 0.9)},
        "ssd_watermarks": {"soft_pct": pol.get("ssd", {}).get("soft_pct", 0.75), "hard_pct": pol.get("ssd", {}).get("hard_pct", 0.85)},
        "actions_enabled": bool(pol.get("actions_enabled", False)),
        "beacons": {"ram": ram_beacon, "ssd": ssd_beacon},
        **({"snapshot": snap} if snap else {}),
    }
    return {
        "name": "llm-server",
        "version": "0.1.0",
        "profile": cfg.get("profile_name"),
        "ports": cfg.get("ports", {}),
        "vision": cfg.get("vision", {}),
        "embeddings": cfg.get("embeddings", []),
        "housekeeper": hk,
        "housekeeper_strategies": list(strategies.keys()),
        "port_blocks": {
            "agents": {"prefix": agents_prefix, "range": [agents_prefix + 1, agents_prefix + 99]},
            "models": {"prefix": models_prefix, "range": [models_prefix + 1, models_prefix + 99]},
            "rule": "If base is B000, agents=B100+NN, models=B200+NN; ports ending in 0 are HUBs",
        },
        "endpoints": {
            "openapi": "/openapi.json",
            "docs": "/docs",
            "health": "/healthz",
            "ready": "/readyz",
            "metrics": "/metrics",
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
            "completions": "/v1/completions",
            "memory_search": "/v1/memory/search",
            "vision_analyze": "/v1/vision/analyze",
            "vision_ready": "/v1/vision/ready",
            "embeddings": "/v1/embeddings",
            "embeddings_list": "/v1/embeddings/list",
            "embeddings_named": "/v1/embeddings/{name}",
            "embeddings_ready": "/v1/embeddings/ready",
            "embeddings_named_ready": "/v1/embeddings/{name}/ready",
            "housekeeper_policy": "/admin/housekeeper/policy",
            "housekeeper_strategy": "/admin/housekeeper/strategy",
            "housekeeper_actions": "/admin/housekeeper/actions",
            **({
                "voice_transcribe": "/v1/voice/transcribe",
                "voice_tts": "/v1/voice/tts",
                "voice_ready": "/v1/voice/ready",
            } if voice_enabled else {}),
            "research_search": "/v1/research/search",
            "research_ready": "/v1/research/ready",
            "tools": "/v1/tools",
            "schemas": "/schemas/{name}.json",
            "ports": "/v1/ports",
        },
        "headers": {"request_id": "X-Request-Id", "tenant": {"name": "X-Tenant-Id", "status": "disabled"}},
    }


@router.get("/v1/tools")
def list_tools():
    return {"tools": tool_list()}


@router.get("/schemas/{name}.json")
def schema_by_name(name: str):
    try:
        sch = get_schema_by_name(name)
    except KeyError:
        raise HTTPException(status_code=404, detail="schema not found")
    return JSONResponse(sch)


    


@router.get("/v1/ports")
def ports_map(request: Request):
    reg, _, cfg = get_resources(request)
    base = int(cfg["ports"]["llm_server"]) // 1000 * 1000
    agents_prefix = base + 100
    models_prefix = base + 200
    voice_enabled = os.getenv("FEATURE_VOICE", "0") in ("1","true","on")
    # Only hub endpoints (0-ending). Individuals (1-9) not exposed in this release.
    hubs = [
        {"name": "orchestrator", "port": agents_prefix + 10},
        {"name": "vision", "port": models_prefix + 20},
        {"name": "research", "port": models_prefix + 50},
    ]
    # allocate embeddings hubs by config (30 + 10*i)
    for i, emb in enumerate(cfg.get("embeddings", [])[:9]):
        hubs.append({"name": f"embeddings-{emb.get('name','e'+str(i))}", "port": models_prefix + 30 + 10 * i})
    if voice_enabled:
        hubs.insert(3, {"name": "voice", "port": models_prefix + 40})
    return {
        "base": base,
        "ranges": {
            "agents": [agents_prefix + 1, agents_prefix + 99],
            "models": [models_prefix + 1, models_prefix + 99],
        },
        "hubs": hubs,
        "rule": "Ports ending in 0 are HUB endpoints; individuals (1-9) are not exposed",
    }


class VisionImage(BaseModel):
    url: Optional[str] = None
    base64: Optional[str] = None
    purpose: Optional[str] = None


class VisionAnalyzeRequest(BaseModel):
    images: List[VisionImage]
    prompt: Optional[str] = None
    tasks: Optional[List[str]] = None
    ocr: Optional[str] = "auto"


@router.post("/v1/vision/analyze")
def vision_analyze_endpoint(req: VisionAnalyzeRequest, request: Request):
    imgs = [
        {k: v for k, v in {
            "url": i.url, "base64": i.base64, "purpose": i.purpose
        }.items() if v is not None}
        for i in req.images
    ]
    try:
        log.info("vision.analyze", extra={"images": len(imgs), "ocr": req.ocr or "auto", "has_prompt": bool(req.prompt)})
    except Exception:
        pass
    out = vision_analyze(imgs, prompt=req.prompt, tasks=req.tasks, ocr_mode=req.ocr or "auto")
    return JSONResponse(out)


@router.get("/v1/vision/ready")
def vision_ready():
    return JSONResponse(vision_readiness())


class EmbeddingsRequest(BaseModel):
    model: Optional[str] = None
    input: Any
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None
    name: Optional[str] = None


@router.post("/v1/embeddings")
def embeddings_endpoint(req: EmbeddingsRequest, request: Request):
    cfg = request.app.state.config
    embeddings_cfg = cfg.get("embeddings", [])
    default_dim = int(embeddings_cfg[0].get("dimensions", 256)) if embeddings_cfg else 256
    texts = req.input if isinstance(req.input, list) else [req.input]
    dim = int(req.dimensions or default_dim)
    try:
        log.info("embeddings.generate", extra={"count": len(texts), "dim": dim, "format": req.encoding_format or "float", "name": req.name or (embeddings_cfg and embeddings_cfg[0].get('name'))})
    except Exception:
        pass
    vecs = embed_texts([str(t) for t in texts], dim=dim)
    if req.encoding_format == "base64":
        import base64, array
        data_items = []
        for i, v in enumerate(vecs):
            arr = array.array('f', v).tobytes()
            data_items.append({"object": "embedding", "index": i, "embedding": base64.b64encode(arr).decode("ascii")})
    else:
        data_items = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vecs)]
    return JSONResponse({"object": "list", "data": data_items, "model": req.model or "stub-embeddings", "usage": {"prompt_tokens": 0, "total_tokens": 0}})


@router.post("/v1/embeddings/{name}")
def embeddings_named_endpoint(name: str, req: EmbeddingsRequest, request: Request):
    cfg = request.app.state.config
    embeddings_cfg = {e.get("name"): e for e in cfg.get("embeddings", [])}
    ecfg = embeddings_cfg.get(name)
    if not ecfg:
        raise HTTPException(status_code=404, detail="embeddings not found")
    # Prefer provided dimensions, else config default
    if req.dimensions is None:
        req.dimensions = int(ecfg.get("dimensions", 256))
    req.name = name
    return embeddings_endpoint(req, request)


@router.get("/v1/embeddings/ready")
def embeddings_ready():
    return JSONResponse({"ready": True, "mode": "stub", "dimensions_default": 256})


@router.get("/v1/embeddings/{name}/ready")
def embeddings_named_ready(name: str, request: Request):
    cfg = request.app.state.config
    embeddings_cfg = {e.get("name"): e for e in cfg.get("embeddings", [])}
    ecfg = embeddings_cfg.get(name)
    if not ecfg:
        raise HTTPException(status_code=404, detail="embeddings not found")
    return JSONResponse({"ready": True, "mode": "stub", "dimensions_default": int(ecfg.get("dimensions", 256))})


@router.get("/v1/embeddings/list")
def embeddings_list(request: Request):
    cfg = request.app.state.config
    return JSONResponse({"items": cfg.get("embeddings", [])})


class VoiceTranscribeRequest(BaseModel):
    audio: Dict[str, Optional[str]]
    language: Optional[str] = None


@router.post("/v1/voice/transcribe")
def voice_transcribe_endpoint(req: VoiceTranscribeRequest):
    try:
        log.info("voice.transcribe", extra={"language": req.language or "auto", "has_audio": bool(req.audio.get("base64") or req.audio.get("url"))})
    except Exception:
        pass
    return JSONResponse(voice_transcribe(audio_base64=req.audio.get("base64"), url=req.audio.get("url"), language=req.language))


class VoiceTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    format: Optional[str] = "mp3"


@router.post("/v1/voice/tts")
def voice_tts_endpoint(req: VoiceTTSRequest):
    try:
        log.info("voice.tts", extra={"len_text": len(req.text or ""), "voice": req.voice or "default", "format": req.format or "mp3"})
    except Exception:
        pass
    return JSONResponse(voice_tts(text=req.text, voice=req.voice, format=req.format or "mp3"))


@router.get("/v1/voice/ready")
def voice_ready():
    return JSONResponse({"ready": True, "mode": "stub"})


class ResearchSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    site: Optional[str] = None


@router.post("/v1/research/search")
def research_search_endpoint(req: ResearchSearchRequest):
    try:
        log.info("research.search", extra={"query_len": len(req.query or ""), "top_k": int(req.top_k or 5), "site": req.site or "*"})
    except Exception:
        pass
    return JSONResponse(web_search(req.query, top_k=int(req.top_k or 5), site=req.site))


class AgentsPlanRequest(BaseModel):
    nl: Optional[str] = None
    hints: Optional[Dict[str, Any]] = None
    save: bool = True


@router.post("/v1/agents/plan")
def agents_plan(req: AgentsPlanRequest, request: Request):
    dsl = compile_nl_to_dsl(req.nl or "", req.hints or {})
    val = validate_graph(dsl)
    try:
        log.info("agents.plan", extra={"validated": val.get("ok", False)})
    except Exception:
        pass
    if req.save and val.get("ok"):
        from .config_loader import ROOT
        out = (ROOT / "runtime" / "agents")
        out.mkdir(parents=True, exist_ok=True)
        save_current_plan(dsl, str(out / "current.yaml"))
    return JSONResponse({"dsl": dsl, "validated": bool(val.get("ok")), "issues": val.get("issues", [])})


@router.get("/v1/agents/current")
def agents_current():
    from .config_loader import ROOT
    path = ROOT / "runtime" / "agents" / "current.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="no current plan")
    try:
        import json as _json
        return JSONResponse(_json.loads(path.read_text()))
    except Exception:
        return JSONResponse({"error": "invalid plan file"}, status_code=500)


class ProfileSwitchRequest(BaseModel):
    name: str


@router.post("/admin/profile/switch")
def profile_switch(req: ProfileSwitchRequest, request: Request):
    from pathlib import Path
    from .config_loader import ROOT, build_effective_config
    # Validate profile exists
    path = ROOT / "configs" / "custom_profiles" / f"{req.name}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="profile not found")
    # Write runtime pointer
    (ROOT / "runtime" / "current_profile").write_text(req.name)
    # Rebuild config and registry/concurrency
    app = request.app
    cfg = build_effective_config()
    app.state.config = cfg  # type: ignore[attr-defined]
    try:
        from .registry import ModelRegistry
        from .concurrency import ConcurrencyManager
        reg = ModelRegistry(); reg.refresh()
        app.state.registry = reg  # type: ignore[attr-defined]
        app.state.concurrency = ConcurrencyManager()  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        log.info("profile.switch", extra={"to": req.name})
    except Exception:
        pass
    # Report readiness snapshot
    rep = getattr(app.state, 'registry', None) and app.state.registry.readiness_report()
    return JSONResponse({"status": "accepted", "profile": req.name, "readiness": rep or {}})


class HousekeeperSwitchRequest(BaseModel):
    name: str


@router.post("/admin/housekeeper/strategy")
def housekeeper_switch(req: HousekeeperSwitchRequest, request: Request):
    cfg = request.app.state.config
    hk_cfg = cfg.get("housekeeper", {}) or {}
    strategies = hk_cfg.get("strategies", {}) or {}
    if req.name not in strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    pol = strategies[req.name]
    # update app state
    request.app.state.housekeeper_strategy = req.name  # type: ignore[attr-defined]
    request.app.state.housekeeper_policy = pol  # type: ignore[attr-defined]
    # restart thread if exists
    hk = getattr(request.app.state, "_housekeeper", None)
    try:
        if hk:
            hk.stop()
    except Exception:
        pass
    try:
        from .housekeeper import Housekeeper
        disk_path = str((__import__("pathlib").Path(pol.get("ssd", {}).get("path", cfg.get("models_root", "."))).resolve()))
        new_hk = Housekeeper(request.app, interval_s=float(pol.get("interval_s", 10)), disk_path=disk_path)
        request.app.state._housekeeper = new_hk  # type: ignore[attr-defined]
        new_hk.start()
    except Exception:
        pass
    return JSONResponse({"status": "accepted", "strategy": req.name, "policy": pol})


@router.get("/admin/housekeeper/policy")
def housekeeper_policy(request: Request):
    pol = getattr(request.app.state, 'housekeeper_policy', {})
    name = getattr(request.app.state, 'housekeeper_strategy', None)
    return JSONResponse({"strategy": name, "policy": pol})


class HousekeeperActionsRequest(BaseModel):
    enabled: bool


@router.post("/admin/housekeeper/actions")
def housekeeper_actions(req: HousekeeperActionsRequest, request: Request):
    # Toggle actions_enabled at runtime; persists in in-memory policy
    cfg = request.app.state.config
    hk_cfg = cfg.get("housekeeper", {}) or {}
    strategies = hk_cfg.get("strategies", {}) or {}
    name = getattr(request.app.state, 'housekeeper_strategy', None) or hk_cfg.get("default_strategy", "balanced")
    pol = getattr(request.app.state, 'housekeeper_policy', None) or strategies.get(name, {})
    # mutate policy and state
    try:
        pol["actions_enabled"] = bool(req.enabled)
        request.app.state.housekeeper_policy = pol  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        log.info("housekeeper.actions_toggle", extra={"enabled": bool(req.enabled), "strategy": name})
    except Exception:
        pass
    return JSONResponse({"status": "accepted", "strategy": name, "actions_enabled": bool(req.enabled)})


@router.get("/v1/research/ready")
def research_ready():
    return JSONResponse({"ready": True, "mode": "stub"})


@router.post("/v1/completions")
def completions(req: CompletionRequest, request: Request, x_tenant_id: Optional[str] = Header(default=None)):
    registry, conc, cfg = get_resources(request)
    try:
        tenant = require_tenant(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Non-streaming path
    # Build overrides from request
    overrides = {k: v for k, v in dict(temperature=req.temperature, top_p=req.top_p, top_k=req.top_k, max_tokens=req.max_tokens).items() if v is not None}

    if not req.stream:
        t0 = time.time()
        res = generate_with_llama_cli(registry, req.model, req.prompt, overrides=overrides, role="coder", conc=conc)
        latency_ms = int((time.time() - t0) * 1000)
        # Optionally publish result
        if producer.available():
            try:
                topic = _topic_namer(tenant, "infer.results.v1")
                payload = json.dumps({"tenant_id": tenant, "model": req.model, "output": res.get("output", ""), "latency_ms": latency_ms}).encode()
                producer.produce(topic, key=None, headers={"tenant": tenant}, value=payload)
            except Exception:
                pass
        # OpenAI-style response
        return JSONResponse({
            "id": f"cmpl-{int(time.time()*1000)}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {"text": res.get("output", ""), "index": 0, "finish_reason": None}
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    # Streaming path: run once and stream the buffer in chunks
    def _gen_sse():
        res = generate_with_llama_cli(registry, req.model, req.prompt, overrides=overrides, role="coder", conc=conc)
        out = res.get("output", "")
        created = int(time.time())
        model = req.model
        cid = f"chatcmpl-{int(time.time()*1000)}"
        # stream in small chunks
        for i in range(0, len(out), 64):
            delta = out[i:i+64]
            evt = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices":[{"index":0, "delta": {"content": delta}, "finish_reason": None}]}
            yield f"data: {json.dumps(evt)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(_gen_sse(), media_type="text/event-stream")


@router.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, request: Request, x_tenant_id: Optional[str] = Header(default=None)):
    registry, conc, cfg = get_resources(request)
    try:
        tenant = require_tenant(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Simple prompt assembly: concatenate user messages
    # Content may be string or parts; flatten simply
    parts = []
    for m in req.messages:
        if isinstance(m.content, list):
            parts.extend([p.get("text", "") if isinstance(p, dict) else str(p) for p in m.content])
        else:
            parts.append(str(m.content))
    prompt = "\n".join(parts)

    # Function-calling (prep): if an explicit tool_choice=function is provided
    # we emit a tool_calls response instead of model output. This primes
    # integration with OpenAI tools/tool_choice without full planning.
    tc = req.tool_choice
    chosen_fn = None
    if isinstance(tc, dict) and tc.get("type") == "function":
        f = tc.get("function") or {}
        chosen_fn = f.get("name")
    # Explicitly support memory.search as a first tool
    if chosen_fn == "memory.search":
        # naive args: use the latest user content as the query
        q = ""
        for m in reversed(req.messages):
            if (m.role or "").lower() == "user":
                if isinstance(m.content, list):
                    q = " ".join([p.get("text", "") if isinstance(p, dict) else str(p) for p in m.content])
                else:
                    q = str(m.content)
                break
        # Optional closed-loop execution (feature flag or explicit request)
        execute = bool(req.server_tools_execute) or os.getenv("FC_CLOSED_LOOP", "0") in ("1","true","on")
        if execute:
            try:
                res = mem_client.search(q, k=5)
            except Exception:
                res = []
            summary_lines = []
            for r in res[:5]:
                rid = r.get("id")
                sc = r.get("score")
                txt = r.get("text", "")
                summary_lines.append(f"- {rid} (score {sc}): {txt}")
            content = "Memory search results:\n" + ("\n".join(summary_lines) if summary_lines else "<no results>")
            return JSONResponse({
                "id": f"chatcmpl-{int(time.time()*1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
        else:
            tool_call = {
                "id": f"call-{int(time.time()*1000)}",
                "type": "function",
                "function": {"name": "memory.search", "arguments": json.dumps({"query": q, "k": 5})},
            }
            return JSONResponse({
                "id": f"chatcmpl-{int(time.time()*1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "tool_calls": [tool_call]},
                    "finish_reason": "tool_calls",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })

    # Continue-mode presets
    overrides = {}
    if req.continue_mode:
        mode = req.continue_mode.lower()
        presets = request.app.state.config.get("api_presets", {}) if hasattr(request.app.state, "config") else {}
        # fall back to configs/api.yaml
        try:
            from pathlib import Path
            import json as _json
            path = Path("configs/api.yaml")
            if path.exists():
                data = _json.loads(path.read_text())
                presets = data.get("presets", {})
        except Exception:
            pass
        cm = (presets.get("continue_modes", {}) or {}).get(mode, {})
        overrides.update(cm)
    for k in ("temperature","top_p","top_k","max_tokens"):
        v = getattr(req, k, None)
        if v is not None:
            overrides[k] = v

    if not req.stream:
        t0 = time.time()
        res = generate_with_llama_cli(registry, req.model, prompt, overrides=overrides, role="coder", conc=conc)
        latency_ms = int((time.time() - t0) * 1000)
        if producer.available():
            try:
                topic = _topic_namer(tenant, "infer.results.v1")
                payload = json.dumps({"tenant_id": tenant, "model": req.model, "output": res.get("output", ""), "latency_ms": latency_ms}).encode()
                producer.produce(topic, key=None, headers={"tenant": tenant}, value=payload)
            except Exception:
                pass
        # OpenAI-style chat response
        return JSONResponse({
            "id": f"chatcmpl-{int(time.time()*1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": res.get("output", "")}, "finish_reason": None}
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    def _gen_sse():
        res = generate_with_llama_cli(registry, req.model, prompt, overrides=overrides, role="coder", conc=conc)
        out = res.get("output", "")
        created = int(time.time())
        model = req.model
        cid = f"chatcmpl-{int(time.time()*1000)}"
        # initial role delta (optional per OpenAI spec)
        first_evt = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(first_evt)}\n\n"
        for i in range(0, len(out), 64):
            delta = out[i:i+64]
            evt = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices":[{"index":0, "delta": {"content": delta}, "finish_reason": None}]}
            yield f"data: {json.dumps(evt)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(_gen_sse(), media_type="text/event-stream")


class MemorySearchRequest(BaseModel):
    query: str
    k: int = 5
    filters: Optional[Dict[str, Any]] = None


@router.post("/v1/memory/search")
def memory_search(req: MemorySearchRequest, request: Request, x_tenant_id: Optional[str] = Header(default=None)):
    try:
        tenant = require_tenant(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out = mem_client.search(req.query, k=req.k, filters=req.filters)
    return {"tenant_id": tenant, "results": out}
