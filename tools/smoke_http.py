#!/usr/bin/env python3
"""Lightweight HTTP smoke test without requiring models or llama.cpp.

Starts a uvicorn server from the in-process FastAPI app and checks key endpoints.
"""
import os
import threading
import time
import sys
import httpx
from pathlib import Path

# Ensure repository root is on sys.path when running from tools/
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
    port = int(os.getenv("PORT", "8091"))

    try:
        from llm_server.app import create_app
        import uvicorn
    except Exception as e:
        print(f"Smoke prerequisites missing: {e}", file=sys.stderr)
        return 1

    app = create_app()
    if not hasattr(app, "state"):
        print("FastAPI not available; stub app present.")
        return 0

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)

    th = threading.Thread(target=server.run, daemon=True)
    th.start()

    base = f"http://127.0.0.1:{port}"
    ok = False
    for _ in range(60):
        try:
            r = httpx.get(base + "/healthz", timeout=0.5)
            if r.status_code == 200:
                ok = True
                break
        except Exception:
            pass
        time.sleep(0.25)
    if not ok:
        print("Server did not become ready", file=sys.stderr)
        server.should_exit = True
        th.join(timeout=2.0)
        return 1

    def _check(path: str, allow=(200,)):
        r = httpx.get(base + path, timeout=1.0)
        if r.status_code not in allow:
            raise RuntimeError(f"{path} -> {r.status_code}")
        print(path, "->", r.status_code)

    try:
        _check("/healthz")
        _check("/info")
        _check("/v1/models")
        _check("/v1/memory/ready")
    finally:
        server.should_exit = True
        th.join(timeout=2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
