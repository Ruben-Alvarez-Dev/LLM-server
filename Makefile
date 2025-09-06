PY=python3

.PHONY: codex validate

codex:
	@$(PY) -c "import json;d=json.load(open('docs/context/manifest.json'));print('\n'.join(f['path'] for f in sorted(d.get('files',[]), key=lambda x:(-int(x.get('priority',0)), x.get('path','')))))"

validate:
	@$(PY) tools/validate.py

.PHONY: run models

run:
	@$(PY) -c "import llm_server.main as m; import sys; sys.exit(m.main())"

models:
	@$(PY) tools/models_sync.py --create --check

.PHONY: models.verify
models.verify:
	@$(PY) -c "from llm_server.registry import ModelRegistry; r=ModelRegistry(); r.refresh(); import json; print(json.dumps(r.readiness_report(), indent=2))"

.PHONY: messaging-up messaging-down
messaging-up:
	docker compose -f configs/messaging/docker-compose.dev.yml up -d

messaging-down:
	docker compose -f configs/messaging/docker-compose.dev.yml down -v

.PHONY: api.smoke mcp.run
api.smoke:
	@. .venv/bin/activate; python - <<'PY'
from fastapi.testclient import TestClient
from llm_server.app import create_app
app=create_app();
if not hasattr(app,'state'): print('FastAPI not available'); raise SystemExit(1)
client=TestClient(app)
r=client.get('/v1/models'); print('models:', r.status_code, r.json())
r=client.post('/v1/chat/completions', json={'model':'phi-4-mini-instruct','messages':[{'role':'user','content':'say hi'}]}); print('chat:', r.status_code)
PY

mcp.run:
	@. .venv/bin/activate; python -c "import llm_server.mcp_server as m; m.main()"

# llama.cpp setup and build (Metal on macOS)
LLAMA_DIR=vendor/llama.cpp

.PHONY: llama.clone llama.setup llama.build llama.clean llama.test models.download

llama.clone:
	@if [ ! -d $(LLAMA_DIR) ]; then \
		git clone --depth 1 https://github.com/ggerganov/llama.cpp $(LLAMA_DIR); \
	else \
		echo "llama.cpp already cloned at $(LLAMA_DIR)"; \
	fi

llama.setup: llama.clone
	@cmake -S $(LLAMA_DIR) -B $(LLAMA_DIR)/build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release

llama.build:
	@cmake --build $(LLAMA_DIR)/build --config Release -j

llama.test:
	@$(LLAMA_DIR)/build/bin/llama-cli -h || true

llama.clean:
	@rm -rf $(LLAMA_DIR)/build

models.download:
	@HF_TOKEN="$$HF_TOKEN" $(PY) tools/models_sync.py --create --download
