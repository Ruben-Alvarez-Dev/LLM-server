import os
import time


def test_metrics_expose_housekeeper_timings():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    os.environ['HOUSEKEEPER_INTERVAL_S'] = '0.05'
    app = create_app()
    if not hasattr(app, 'state'):
        return
    with TestClient(app) as client:
        # Wait for at least one tick
        time.sleep(0.15)
        r = client.get('/metrics'); assert r.status_code == 200
        m = r.json()
        # Expected keys (timing_*)
        keys = m.keys()
        assert any(k.startswith('timing_ram_headroom_gb') for k in keys)
        assert 'housekeeper_ticks_total' in m
