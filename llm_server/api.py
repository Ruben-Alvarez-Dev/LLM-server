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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    params: Optional[Dict[str, Any]] = None
    stream: bool = False


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    params: Optional[Dict[str, Any]] = None
    stream: bool = False


def get_resources(request: Request):
    registry = request.app.state.registry
    conc = request.app.state.concurrency
    cfg = request.app.state.config
    return registry, conc, cfg


router = APIRouter()
producer = KafkaProducerStub()


def _topic_namer(tenant: str, domain: str) -> str:
    # Align with Go TopicNamer: single -> llm.<DEFAULT_TENANT_ID>.<domain>
    # Here we always build explicit with tenant resolved by require_tenant
    return f"llm.{tenant}.{domain}"


@router.post("/v1/completions")
def completions(req: CompletionRequest, request: Request, x_tenant_id: Optional[str] = Header(default=None)):
    registry, conc, cfg = get_resources(request)
    try:
        tenant = require_tenant(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Non-streaming path
    if not req.stream:
        t0 = time.time()
        res = generate_with_llama_cli(registry, req.model, req.prompt, overrides=req.params, role="coder", conc=conc)
        latency_ms = int((time.time() - t0) * 1000)
        # Optionally publish result
        if producer.available():
            try:
                topic = _topic_namer(tenant, "infer.results.v1")
                payload = json.dumps({"tenant_id": tenant, "model": req.model, "output": res.get("output", ""), "latency_ms": latency_ms}).encode()
                producer.produce(topic, key=None, headers={"tenant": tenant}, value=payload)
            except Exception:
                pass
        return JSONResponse({"model": req.model, "result": res, "latency_ms": latency_ms})

    # Streaming path: run once and stream the buffer in chunks
    def _gen():
        res = generate_with_llama_cli(registry, req.model, req.prompt, overrides=req.params, role="coder", conc=conc)
        out = res.get("output", "")
        chunk = 1024
        for i in range(0, len(out), chunk):
            yield out[i : i + chunk]

    return StreamingResponse(_gen(), media_type="text/plain")


@router.post("/v1/chat/completions")
def chat_completions(req: ChatRequest, request: Request, x_tenant_id: Optional[str] = Header(default=None)):
    registry, conc, cfg = get_resources(request)
    try:
        tenant = require_tenant(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Simple prompt assembly: concatenate user messages
    prompt = "\n".join(m.content for m in req.messages)

    if not req.stream:
        t0 = time.time()
        res = generate_with_llama_cli(registry, req.model, prompt, overrides=req.params, role="coder", conc=conc)
        latency_ms = int((time.time() - t0) * 1000)
        if producer.available():
            try:
                topic = _topic_namer(tenant, "infer.results.v1")
                payload = json.dumps({"tenant_id": tenant, "model": req.model, "output": res.get("output", ""), "latency_ms": latency_ms}).encode()
                producer.produce(topic, key=None, headers={"tenant": tenant}, value=payload)
            except Exception:
                pass
        return JSONResponse({"model": req.model, "result": res, "latency_ms": latency_ms})

    def _gen():
        res = generate_with_llama_cli(registry, req.model, prompt, overrides=req.params, role="coder", conc=conc)
        out = res.get("output", "")
        chunk = 1024
        for i in range(0, len(out), chunk):
            yield out[i : i + chunk]

    return StreamingResponse(_gen(), media_type="text/plain")

