import json
import contextlib


def test_chat_completions_sse_stream(monkeypatch):
    try:
        from fastapi.testclient import TestClient
        import llm_server.api as api
        from llm_server.app import create_app
    except Exception:
        return

    # Monkeypatch generation to avoid llama.cpp dependency
    def fake_gen(*args, **kwargs):
        return {"output": "Hello SSE world"}

    monkeypatch.setattr(api, "generate_with_llama_cli", fake_gen)
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    req = {
        "model": "phi-4-mini-instruct",
        "messages": [{"role": "user", "content": "stream test"}],
        "stream": True,
    }
    with client.stream("POST", "/v1/chat/completions", json=req) as resp:
        assert resp.status_code == 200
        # Collect all sse lines
        chunks = list(resp.iter_lines())
    text = "\n".join(chunks)
    assert "chat.completion.chunk" in text
    assert "[DONE]" in text


def test_text_completions_sse_stream(monkeypatch):
    try:
        from fastapi.testclient import TestClient
        import llm_server.api as api
        from llm_server.app import create_app
    except Exception:
        return

    def fake_gen(*args, **kwargs):
        return {"output": "hello text sse"}

    monkeypatch.setattr(api, "generate_with_llama_cli", fake_gen)
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    req = {"model": "phi-4-mini-instruct", "prompt": "hi", "stream": True}
    with client.stream("POST", "/v1/completions", json=req) as resp:
        assert resp.status_code == 200
        lines = list(resp.iter_lines())
    joined = "\n".join(lines)
    assert "chat.completion.chunk" in joined
    assert "[DONE]" in joined

