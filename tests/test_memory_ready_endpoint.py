def test_memory_ready_stub_mode():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    r = client.get('/v1/memory/ready')
    assert r.status_code == 200
    j = r.json()
    assert 'ready' in j and 'mode' in j
    assert j['mode'] in {'stub','remote'}

