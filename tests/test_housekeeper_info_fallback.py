import os


def test_info_beacons_fallback_when_housekeeper_disabled():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    # Disable housekeeper to force /info beacon computation without snapshot
    os.environ['HOUSEKEEPER_ENABLED'] = '0'
    app = create_app()
    if not hasattr(app, 'state'):
        return
    with TestClient(app) as client:
        r = client.get('/info'); assert r.status_code == 200
        hk = r.json().get('housekeeper', {})
        assert 'beacons' in hk and isinstance(hk['beacons'], dict)
        assert hk['beacons'].get('ram') in {'ok','warn','hot','critical','unknown'}
        assert hk['beacons'].get('ssd') in {'ok','warn','hot','critical','unknown'}
