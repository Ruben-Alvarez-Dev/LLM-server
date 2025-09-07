import pytest


def _models_ready():
    try:
        from llm_server.registry import ModelRegistry
    except Exception:
        return False, "registry import failed"
    r = ModelRegistry(); r.refresh()
    rep = r.readiness_report()
    return bool(rep.get('ready')), rep


@pytest.mark.timeout(120)
def test_full_flow_chat_to_result_when_models_present():
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
    # End-to-end: user -> chat -> assistant output
    model = app.state.config['selected_models'][0]
    r = client.post('/v1/chat/completions', json={
        "model": model,
        "messages": [{"role":"user","content":"Summarize: apples are red."}],
        "max_tokens": 32,
        "temperature": 0.0
    })
    assert r.status_code == 200
    out = r.json()
    assert isinstance(out.get('choices'), list) and len(out['choices']) >= 1

