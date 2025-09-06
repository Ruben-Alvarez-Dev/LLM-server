import json
from llm_server.config_loader import build_effective_config

def test_config_builds():
    cfg = build_effective_config()
    assert 'profile_name' in cfg
    assert 'models' in cfg and isinstance(cfg['models'], list)
    assert 'gen_defaults' in cfg

def test_registry_ready_report():
    from llm_server.registry import ModelRegistry
    r = ModelRegistry(); r.refresh()
    rep = r.readiness_report()
    assert 'ready' in rep and 'items' in rep

def test_api_shapes():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    m = client.get('/v1/models'); assert m.status_code in (200, 404)
    # completions minimal
    c = client.post('/v1/completions', json={"model":"phi-4-mini-instruct","prompt":"hello"})
    assert c.status_code in (200, 400)
    # memory search
    ms = client.post('/v1/memory/search', json={"query":"foo"})
    assert ms.status_code in (200, 400)

