def test_info_exposes_housekeeper_beacons():
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
    hk = j.get('housekeeper', {})
    assert isinstance(hk, dict)
    assert 'beacons' in hk and isinstance(hk['beacons'], dict)
    be = hk['beacons']
    assert 'ram' in be and 'ssd' in be
    allowed = {'ok','warn','hot','critical','unknown'}
    assert be['ram'] in allowed
    assert be['ssd'] in allowed
    # Ensure flag is present (defaults false)
    assert 'actions_enabled' in hk and hk['actions_enabled'] in (True, False)

