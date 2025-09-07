#!/usr/bin/env python3
"""Extended smoke: non-stream + stream for /v1/completions and /v1/chat/completions.

Runs fully in-process using FastAPI TestClient and monkeypatches generation,
so no models or llama.cpp binaries are required.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def mark(ok: bool, title: str, detail: str = "") -> None:
    badge = "[✔]" if ok else "[✖]"
    line = f" {badge} {title}"
    if detail:
        line += f" — {detail}"
    print(line)


def main() -> int:
    os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
    # Ensure repo on path
    ROOT = str(Path(__file__).resolve().parents[1])
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    try:
        import llm_server.api as api
        from llm_server.app import create_app
        from fastapi.testclient import TestClient
    except Exception as e:
        print(f"Extended smoke prerequisites missing: {e}", file=sys.stderr)
        return 1

    # Monkeypatch generation to avoid llama.cpp
    def fake_gen(*args, **kwargs):
        # Return deterministic small output
        return {"output": "hello-world"}

    api.generate_with_llama_cli = fake_gen  # type: ignore[attr-defined]

    app = create_app()
    if not hasattr(app, "state"):
        print("FastAPI not available; stub app present.")
        return 0
    client = TestClient(app)

    ok_all = True

    # Basic GETs
    r = client.get("/healthz"); ok = (r.status_code == 200); mark(ok, "/healthz", str(r.status_code)); ok_all &= ok
    r = client.get("/info"); ok = (r.status_code == 200); mark(ok, "/info", str(r.status_code)); ok_all &= ok

    # Completions (non-stream)
    payload = {"model": "phi-4-mini-instruct", "prompt": "hi"}
    r = client.post("/v1/completions", json=payload)
    ok = (r.status_code == 200 and isinstance(r.json().get("choices", []), list))
    mark(ok, "POST /v1/completions (non-stream)", f"http {r.status_code}")
    ok_all &= ok

    # Completions (stream)
    payload["stream"] = True
    try:
      with client.stream("POST", "/v1/completions", json=payload) as resp:
          lines = list(resp.iter_lines())
      joined = "\n".join(lines)
      ok = (resp.status_code == 200 and "[DONE]" in joined)
    except Exception as e:
      ok = False
    mark(ok, "POST /v1/completions (stream)")
    ok_all &= ok

    # Chat (non-stream)
    chat_req = {
        "model": "phi-4-mini-instruct",
        "messages": [{"role": "user", "content": "hello"}],
    }
    r = client.post("/v1/chat/completions", json=chat_req)
    ok = (r.status_code == 200 and isinstance(r.json().get("choices", []), list))
    mark(ok, "POST /v1/chat/completions (non-stream)", f"http {r.status_code}")
    ok_all &= ok

    # Chat (stream)
    chat_req_stream = dict(chat_req)
    chat_req_stream["stream"] = True
    try:
      with client.stream("POST", "/v1/chat/completions", json=chat_req_stream) as resp:
          chunks = list(resp.iter_lines())
      text = "\n".join(chunks)
      ok = (resp.status_code == 200 and "[DONE]" in text)
    except Exception:
      ok = False
    mark(ok, "POST /v1/chat/completions (stream)")
    ok_all &= ok

    print("\nExtended smoke:", "OK" if ok_all else "FAIL")
    return 0 if ok_all else 2


if __name__ == "__main__":
    raise SystemExit(main())

