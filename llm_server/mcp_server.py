from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict

from .app import create_app


def _write(msg: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> int:
    app = create_app()
    registry = getattr(app, 'state', None) and app.state.registry
    conc = getattr(app, 'state', None) and app.state.concurrency

    _write({"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05","serverInfo":{"name":"llm-server-mcp","version":"0.1.0"}}})
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
        except Exception:
            continue
        mid = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        if method == "initialize":
            _write({"jsonrpc":"2.0","id": mid, "result": {"capabilities": {"tools": {"list": True, "call": True}}}})
        elif method == "tools/list":
            tools = [
                {"name":"llm.chat","description":"Chat completion via local models","inputSchema":{"type":"object","properties":{"model":{"type":"string"},"messages":{"type":"array"},"params":{"type":"object"}}}},
            ]
            _write({"jsonrpc":"2.0","id": mid, "result": {"tools": tools}})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name == "llm.chat":
                from .generation import generate_with_llama_cli
                model = args.get("model")
                messages = args.get("messages") or []
                prompt = "\n".join([m.get("content","") if isinstance(m, dict) else str(m) for m in messages])
                res = generate_with_llama_cli(registry, model, prompt, overrides=args.get("params"), role="coder", conc=conc)
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"text","text": res.get("output", "")}]} })
            else:
                _write({"jsonrpc":"2.0","id": mid, "error": {"code": -32601, "message": "Unknown tool"}})
        else:
            _write({"jsonrpc":"2.0","id": mid, "error": {"code": -32601, "message": "Method not found"}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

