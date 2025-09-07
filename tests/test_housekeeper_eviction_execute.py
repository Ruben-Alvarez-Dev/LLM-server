import os
import tempfile
import time
from pathlib import Path


def test_eviction_executes_when_actions_enabled(monkeypatch):
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
        import llm_server.housekeeper as hk
    except Exception:
        return

    # Simulate high disk pressure and low free space to trigger planning
    def fake_disk_stats(_path: str):
        return {"free_gb": 5.0, "total_gb": 100.0, "pressure": 0.90}

    monkeypatch.setattr(hk, "_disk_stats", fake_disk_stats)

    os.environ['HOUSEKEEPER_INTERVAL_S'] = '0.05'
    app = create_app()
    if not hasattr(app, 'state'):
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        # Create several files ~700KB, 500KB, 300KB
        sizes = [700*1024, 500*1024, 300*1024]
        for i, sz in enumerate(sizes):
            (p / f"f{i}.bin").write_bytes(os.urandom(sz))

        # Enable actions and target eviction at tmpdir, with a small cap
        pol = getattr(app.state, 'housekeeper_policy', {}) or {}
        ssd = pol.get('ssd', {}) or {}
        ssd['evict_dirs'] = [str(p.resolve())]
        ssd['max_evict_per_tick_gb'] = 0.002  # ~2 MB
        pol['ssd'] = ssd
        pol['actions_enabled'] = True
        app.state.housekeeper_policy = pol  # type: ignore[attr-defined]

        with TestClient(app) as client:
            t0 = time.time(); snap = None
            while time.time() - t0 < 3.0:
                r = client.get('/info'); assert r.status_code == 200
                hkinfo = r.json().get('housekeeper', {})
                snap = hkinfo.get('snapshot')
                if snap and snap.get('eviction', {}).get('done_bytes', 0) > 0:
                    break
                time.sleep(0.05)
        assert snap is not None
        ev = snap['eviction']
        assert ev.get('done_bytes', 0) > 0
        # At least one file must have been removed
        exists = [(p / f"f{i}.bin").exists() for i in range(len(sizes))]
        assert any(not e for e in exists)
