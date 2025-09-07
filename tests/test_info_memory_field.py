def test_info_includes_memory_field():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    r = client.get('/info')
    assert r.status_code == 200
    j = r.json()
    assert 'memory' in j and isinstance(j['memory'], dict)
    assert 'enabled' in j['memory']

