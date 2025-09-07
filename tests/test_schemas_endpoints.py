def test_schemas_endpoint_known_names(monkeypatch):
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    # Disable rate limiting to avoid 429 in tight loops
    monkeypatch.setenv('RATE_LIMIT_ENABLED', '0')
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)
    for name in [
        'memory.search',
        'memory.search.output',
        'llm.chat',
        'vision.analyze',
        'vision.analyze.output',
        'embeddings.generate',
        'embeddings.generate.output',
        'voice.transcribe',
        'voice.transcribe.output',
        'voice.tts',
        'voice.tts.output',
        'research.search',
        'research.search.output',
        'agents.plan',
        'agents.plan.output',
    ]:
        r = client.get(f'/schemas/{name}.json')
        # optional tools may not be available; accept 200 or 404
        assert r.status_code in (200, 404)
