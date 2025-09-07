import os
import pytest


def _models_ready():
    try:
        from llm_server.registry import ModelRegistry
    except Exception:
        return False, "registry import failed"
    r = ModelRegistry(); r.refresh()
    rep = r.readiness_report()
    return bool(rep.get('ready')), rep


@pytest.mark.timeout(60)
def test_generate_with_real_model_when_present():
    ready, info = _models_ready()
    if not ready:
        pytest.skip(f"models not ready: {info}")
    from llm_server.registry import ModelRegistry
    from llm_server.generation import generate_with_llama_cli
    r = ModelRegistry(); r.refresh()
    # pick the first selected model
    name = r.selected[0]
    res = generate_with_llama_cli(r, name, prompt="Hello", overrides={"max_tokens": 16, "temperature": 0.0}, timeout_s=45, role="coder", conc=None)
    assert 'output' in res and isinstance(res['output'], str) and len(res['output']) >= 1


@pytest.mark.timeout(90)
def test_api_chat_and_completions_real_when_present():
    ready, info = _models_ready()
    if not ready:
        pytest.skip(f"models not ready: {info}")
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        pytest.skip("fastapi not available")
    app = create_app()
    if not hasattr(app, 'state'):
        pytest.skip('app not real (stub)')
    client = TestClient(app)
    # Completions non-stream
    c = client.post('/v1/completions', json={"model": app.state.config['selected_models'][0], "prompt": "hi", "max_tokens": 16, "temperature": 0.0})
    assert c.status_code == 200
    # Chat non-stream
    j = client.post('/v1/chat/completions', json={"model": app.state.config['selected_models'][0], "messages": [{"role":"user","content":"hi"}], "max_tokens": 16, "temperature": 0.0})
    assert j.status_code == 200
    # Chat stream (collect)
    with client.stream('POST', '/v1/chat/completions', json={"model": app.state.config['selected_models'][0], "messages": [{"role":"user","content":"hi"}], "stream": True, "max_tokens": 16, "temperature": 0.0}) as resp:
        chunks = list(resp.iter_lines())
    assert resp.status_code == 200
    assert any('[DONE]' in line for line in chunks)

