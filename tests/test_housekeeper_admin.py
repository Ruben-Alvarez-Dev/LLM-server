def test_housekeeper_actions_toggle_updates_info():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    # initial
    info1 = client.get('/info'); assert info1.status_code == 200
    j1 = info1.json(); hk1 = j1.get('housekeeper', {})
    assert isinstance(hk1, dict)
    assert 'actions_enabled' in hk1
    initial = bool(hk1.get('actions_enabled'))

    # toggle to opposite
    r = client.post('/admin/housekeeper/actions', json={'enabled': (not initial)})
    assert r.status_code == 200 and r.json().get('status') == 'accepted'

    info2 = client.get('/info'); assert info2.status_code == 200
    j2 = info2.json(); hk2 = j2.get('housekeeper', {})
    assert bool(hk2.get('actions_enabled')) is (not initial)

    # toggle back
    r2 = client.post('/admin/housekeeper/actions', json={'enabled': initial})
    assert r2.status_code == 200 and r2.json().get('status') == 'accepted'
    info3 = client.get('/info'); assert info3.status_code == 200
    j3 = info3.json(); hk3 = j3.get('housekeeper', {})
    assert bool(hk3.get('actions_enabled')) is initial

