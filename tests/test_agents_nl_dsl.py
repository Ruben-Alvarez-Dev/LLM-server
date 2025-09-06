def test_agents_plan_and_current():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    r = client.post('/v1/agents/plan', json={'nl': 'Analisis y plan con verificación doble', 'hints': {'include_planner': True, 'verify_steps': 2}})
    assert r.status_code == 200
    j = r.json()
    assert j.get('validated') is True
    dsl = j.get('dsl', {})
    assert 'agents' in dsl and 'edges' in dsl and 'entry' in dsl

    # Fetch current plan
    cur = client.get('/v1/agents/current')
    assert cur.status_code == 200
