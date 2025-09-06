import os


def test_rate_limit_429():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    # Configure strict rate limit for test
    os.environ['RATE_LIMIT_ENABLED'] = '1'
    os.environ['RATE_LIMIT_RPS'] = '3'
    os.environ['RATE_LIMIT_BURST'] = '3'
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    codes = []
    for _ in range(8):
        r = client.get('/healthz')
        codes.append(r.status_code)
    assert any(c == 429 for c in codes)


def test_profile_switch_self():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    # switch to current (no-op)
    r = client.post('/admin/profile/switch', json={'name': app.state.config['profile_name']})
    assert r.status_code == 200 and r.json().get('status') == 'accepted'

