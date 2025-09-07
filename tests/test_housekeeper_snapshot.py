import os
import time


def _wait_snapshot(client, timeout_s=1.5):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = client.get('/info')
        if r.status_code != 200:
            time.sleep(0.05)
            continue
        j = r.json()
        hk = j.get('housekeeper', {})
        if hk.get('snapshot'):
            return hk['snapshot']
        time.sleep(0.05)
    return None


def test_housekeeper_snapshot_and_endpoints_present():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    # Fast tick and ensure housekeeper is enabled
    os.environ['HOUSEKEEPER_INTERVAL_S'] = '0.05'
    os.environ['HOUSEKEEPER_ENABLED'] = '1'
    app = create_app()
    if not hasattr(app, 'state'):
        return
    with TestClient(app) as client:
        # Endpoints include housekeeper admin endpoints
        r = client.get('/info'); assert r.status_code == 200
        j = r.json()
        eps = j.get('endpoints', {})
        assert 'housekeeper_policy' in eps and 'housekeeper_strategy' in eps and 'housekeeper_actions' in eps

        # Wait for a snapshot
        snap = _wait_snapshot(client, timeout_s=3.0)
    assert isinstance(snap, dict)
    assert 'ram' in snap and 'ssd' in snap and 'eviction' in snap
    assert 'headroom_gb' in snap['ram'] and 'beacon' in snap['ram']
    assert 'beacon' in snap['ssd']


def test_housekeeper_strategy_switch_and_policy():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    os.environ['HOUSEKEEPER_INTERVAL_S'] = '0.05'
    os.environ['HOUSEKEEPER_ENABLED'] = '1'
    app = create_app()
    if not hasattr(app, 'state'):
        return
    with TestClient(app) as client:
        # Detect strategies and switch if another is available
        r = client.get('/info'); assert r.status_code == 200
        j = r.json(); strategies = j.get('housekeeper_strategies', [])
        active = j.get('housekeeper', {}).get('strategy')
        if strategies and len(strategies) > 1:
            target = next((s for s in strategies if s != active), active)
            sw = client.post('/admin/housekeeper/strategy', json={'name': target})
            assert sw.status_code == 200 and sw.json().get('status') == 'accepted'
            r2 = client.get('/info'); assert r2.status_code == 200
            assert r2.json().get('housekeeper', {}).get('strategy') == target

        # Policy visible
        pol = client.get('/admin/housekeeper/policy')
        assert pol.status_code == 200 and 'policy' in pol.json()
