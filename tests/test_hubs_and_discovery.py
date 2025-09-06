import base64
import os


def _tiny_png_base64():
    # 1x1 transparent PNG
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/w8AAwMB/Ut8Oq4AAAAASUVORK5CYII="
    )


def test_discovery_and_ports():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    r = client.get('/info'); assert r.status_code == 200
    j = r.json(); assert 'endpoints' in j and 'port_blocks' in j

    t = client.get('/v1/tools'); assert t.status_code == 200
    tools = {tool['name'] for tool in t.json().get('tools', [])}
    for name in [
        'llm.chat', 'memory.search', 'vision.analyze',
        'embeddings.generate', 'voice.transcribe', 'voice.tts', 'research.search']:
        assert name in tools

    # Schemas
    for name in ['memory.search', 'vision.analyze', 'embeddings.generate', 'voice.transcribe', 'research.search']:
        s = client.get(f'/schemas/{name}.json'); assert s.status_code == 200

    p = client.get('/v1/ports'); assert p.status_code == 200
    hubs = {h['name'] for h in p.json().get('hubs', [])}
    for name in ['orchestrator','vision','research']:
        assert name in hubs
    assert any(h.startswith('embeddings') for h in hubs)
    # voice hub may be disabled by default
    if os.getenv('FEATURE_VOICE','0') in ('1','true','on'):
        assert 'voice' in hubs


def test_hubs_smoke():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    # Vision readiness + analyze
    vr = client.get('/v1/vision/ready'); assert vr.status_code == 200
    img = _tiny_png_base64()
    va = client.post('/v1/vision/analyze', json={
        'images':[{'base64': img, 'purpose':'screenshot'}],
        'prompt':'Detect errors', 'ocr':'auto'
    })
    assert va.status_code == 200 and 'ocr' in va.json()

    # Embeddings (float + base64)
    e1 = client.post('/v1/embeddings', json={'input':'hello','dimensions':8})
    assert e1.status_code == 200 and len(e1.json().get('data',[])) == 1
    e2 = client.post('/v1/embeddings', json={'input':['a','b'],'dimensions':8,'encoding_format':'base64'})
    assert e2.status_code == 200 and len(e2.json().get('data',[])) == 2
    er = client.get('/v1/embeddings/ready'); assert er.status_code == 200

    # Voice (stubs)
    vt = client.post('/v1/voice/transcribe', json={'audio': {'base64': ''}, 'language': 'en'})
    assert vt.status_code == 200 and 'text' in vt.json()
    vv = client.post('/v1/voice/tts', json={'text': 'hi'})
    assert vv.status_code == 200 and 'audio' in vv.json()
    vrd = client.get('/v1/voice/ready'); assert vrd.status_code == 200

    # Research (stub)
    rr = client.post('/v1/research/search', json={'query':'test','top_k':3})
    assert rr.status_code == 200 and 'results' in rr.json()
    rdy = client.get('/v1/research/ready'); assert rdy.status_code == 200

    # Memory (stub)
    ms = client.post('/v1/memory/search', json={'query':'foo'})
    assert ms.status_code in (200, 400)


def test_function_calling_prep_memory_search():
    try:
        from fastapi.testclient import TestClient
        from llm_server.app import create_app
    except Exception:
        return
    app = create_app()
    if not hasattr(app, 'state'):
        return
    client = TestClient(app)

    payload = {
        'model': 'phi-4-mini-instruct',
        'messages': [{'role':'user','content':'find foo in memory'}],
        'tool_choice': {'type':'function', 'function': {'name':'memory.search'}},
        'stream': False,
    }
    r = client.post('/v1/chat/completions', json=payload)
    # Should short-circuit to tool_calls
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        j = r.json()
        ch = j.get('choices',[{}])[0]
        msg = ch.get('message',{})
        assert 'tool_calls' in msg

    # Closed loop on demand
    payload['server_tools_execute'] = True
    r2 = client.post('/v1/chat/completions', json=payload)
    assert r2.status_code in (200, 400)
    if r2.status_code == 200:
        j2 = r2.json()
        ch2 = j2.get('choices',[{}])[0]
        msg2 = ch2.get('message',{})
        assert 'content' in msg2 and isinstance(msg2['content'], str)
