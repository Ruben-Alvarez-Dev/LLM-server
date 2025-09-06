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


def _topic_namer(tenant: str, domain: str) -> str:
    # Align with Go TopicNamer: single -> llm.<DEFAULT_TENANT_ID>.<domain>
    # Here we always build explicit with tenant resolved by require_tenant
    return f"llm.{tenant}.{domain}"


@router.get("/v1/models")
def list_models(request: Request):
    reg, _, cfg = get_resources(request)
    return {"object": "list", "data": [{"id": m.name, "object": "model"} for m in reg.list()]}


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
