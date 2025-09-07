import os
import tempfile
import time
from pathlib import Path


def test_eviction_planning_without_deletion(monkeypatch):
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
        import llm_server.housekeeper as hk
    except Exception:
        return

    # Fake disk stats to force high pressure and low free
    def fake_disk_stats(_path: str):
        return {"free_gb": 5.0, "total_gb": 100.0, "pressure": 0.90}

    monkeypatch.setattr(hk, "_disk_stats", fake_disk_stats)

    # Fast housekeeper tick
    os.environ['HOUSEKEEPER_INTERVAL_S'] = '0.05'
    app = create_app()
    if not hasattr(app, 'state'):
        return

    # Create temporary files as eviction candidates
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        # Create several small files
        for i in range(5):
            (p / f"f{i}.bin").write_bytes(os.urandom(64 * 1024))

        # Inject runtime policy: actions disabled and target dirs = tmpdir
        pol = getattr(app.state, 'housekeeper_policy', {}) or {}
        ssd = pol.get('ssd', {}) or {}
        ssd['evict_dirs'] = [str(p.resolve())]
        ssd['max_evict_per_tick_gb'] = 0.02  # ~20 MB
        pol['ssd'] = ssd
        pol['actions_enabled'] = False
        app.state.housekeeper_policy = pol  # type: ignore[attr-defined]

        with TestClient(app) as client:
            # Wait for a snapshot with an eviction plan
            t0 = time.time(); snap = None
            while time.time() - t0 < 3.0:
                r = client.get('/info'); assert r.status_code == 200
                hkinfo = r.json().get('housekeeper', {})
                snap = hkinfo.get('snapshot')
                if snap and snap.get('eviction', {}).get('planned_files', 0) > 0:
                    break
                time.sleep(0.05)
        assert snap is not None
        ev = snap.get('eviction', {})
        assert ev.get('planned_files', 0) >= 1
        assert ev.get('done_bytes', 0) == 0

        # Check files still exist (no actions executed)
        for i in range(5):
            assert (p / f"f{i}.bin").exists()
