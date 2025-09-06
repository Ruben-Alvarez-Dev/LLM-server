from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict

from .app import create_app
from .memory_client import MemoryClient
from .schemas import tool_list
from .vision import analyze as vision_analyze
from .embeddings import embed_texts
from .voice import transcribe as voice_transcribe, tts as voice_tts
from .research import web_search


def _write(msg: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> int:
    app = create_app()
    registry = getattr(app, 'state', None) and app.state.registry
    conc = getattr(app, 'state', None) and app.state.concurrency
    mem_client = MemoryClient()

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
            tools = tool_list()
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
            elif name == "memory.search":
                query = args.get("query") or ""
                k = int(args.get("k") or 5)
                filters = args.get("filters") or None
                try:
                    results = mem_client.search(query, k=k, filters=filters)
                except Exception as e:
                    _write({"jsonrpc":"2.0","id": mid, "error": {"code": -32000, "message": f"memory.search failed: {e}"}})
                else:
                    _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps({"results": results})}]}})
            elif name == "vision.analyze":
                images = args.get("images") or []
                out = vision_analyze(images, prompt=args.get("prompt"), tasks=args.get("tasks"), ocr_mode=args.get("ocr") or "auto")
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps(out)}]}})
            elif name == "embeddings.generate":
                inp = args.get("input")
                dims = int(args.get("dimensions") or 256)
                texts = inp if isinstance(inp, list) else [inp]
                vecs = embed_texts([str(t) for t in texts], dim=dims)
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps({"object":"list","data":[{"object":"embedding","index":i,"embedding":v} for i,v in enumerate(vecs)]})}]}})
            elif name == "voice.transcribe":
                audio = args.get("audio") or {}
                out = voice_transcribe(audio_base64=audio.get("base64"), url=audio.get("url"), language=args.get("language"))
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps(out)}]}})
            elif name == "voice.tts":
                out = voice_tts(text=args.get("text",""), voice=args.get("voice"), format=args.get("format") or "mp3")
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps(out)}]}})
            elif name == "research.search":
                out = web_search(query=args.get("query",""), top_k=int(args.get("top_k") or 5), site=args.get("site"))
                _write({"jsonrpc":"2.0","id": mid, "result": {"content": [{"type":"json","text": json.dumps(out)}]}})
            else:
                _write({"jsonrpc":"2.0","id": mid, "error": {"code": -32601, "message": "Unknown tool"}})
        else:
            _write({"jsonrpc":"2.0","id": mid, "error": {"code": -32601, "message": "Method not found"}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
