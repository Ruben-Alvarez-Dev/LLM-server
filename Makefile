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
	@. .venv/bin/activate; python -c "from fastapi.testclient import TestClient; from llm_server.app import create_app; app=create_app(); import sys, json; print('fastapi', hasattr(app,'state')); client=TestClient(app); r=client.get('/v1/models'); print('models:', r.status_code, len(r.json().get('data',[]))); r=client.post('/v1/chat/completions', json={'model':'phi-4-mini-instruct','messages':[{'role':'user','content':'say hi'}]}); print('chat:', r.status_code)"

mcp.run:
	@. .venv/bin/activate; python -c "import llm_server.mcp_server as m; m.main()"

.PHONY: smoke
smoke:
	@python3 tools/smoke_http.py

.PHONY: smoke.ext
smoke.ext:
	@python3 tools/smoke_extended.py

.PHONY: checks checks.api checks.models checks.messaging
checks:
	@python3 tools/test_runner.py --validate || true; python3 tools/test_runner.py --smoke || true; python3 tools/test_runner.py --fast || true

checks.api:
	@$(PY) -c "from tools.test_runner import do_checks; import sys; sys.exit(do_checks('api'))"

checks.models:
	@$(PY) -c "from tools.test_runner import do_checks; import sys; sys.exit(do_checks('models'))"

checks.messaging:
	@$(PY) -c "from tools.test_runner import do_checks; import sys; sys.exit(do_checks('messaging'))"

.PHONY: docs
docs:
	@. .venv/bin/activate; python -m pdoc -o docs/site llm_server || echo "Instala pdoc (pip install pdoc) para generar docs HTML"

.PHONY: test
test:
	@. .venv/bin/activate; PYTHONPATH=. pytest -q

.PHONY: test.all test.fast test.sse test.housekeeper test.agents tui
test.all:
	@python3 -m pytest -q

test.fast:
	@python3 -m pytest -q tests/test_config_and_api.py tests/test_schemas_endpoints.py tests/test_info_memory_field.py tests/test_memory_ready_endpoint.py

test.sse:
	@python3 -m pytest -q tests/test_api_sse.py

test.housekeeper:
	@python3 -m pytest -q tests/test_housekeeper_*.py tests/test_metrics_housekeeper.py

test.agents:
	@python3 -m pytest -q tests/test_agents_nl_dsl.py

.PHONY: test.models test.e2e
test.models:
	@python3 -m pytest -q tests/test_models_real.py

test.e2e:
	@python3 -m pytest -q tests/test_e2e_full.py

tui:
	@python3 tools/test_runner.py

.PHONY: logs.enable logs.tail
logs.enable:
	@mkdir -p logs; echo "Enable file logging by exporting LOG_TO_FILE=1 (and optional LOG_FILE/LOG_DIR)."

logs.tail:
	@mkdir -p logs; tail -f logs/llm-server.jsonl

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

.PHONY: start start.bg stop
start:
	@echo "Starting LLM-server (fg). Set PORT_LLM_SERVER to override port.";
	@RATE_LIMIT_ENABLED=$${RATE_LIMIT_ENABLED:-0} PORT_LLM_SERVER=$${PORT_LLM_SERVER:-8081} $(PY) -m llm_server.main

start.bg:
	@echo "Starting LLM-server (bg). Logs at logs/uvicorn_local.log; PID at runtime/server.pid";
	@mkdir -p logs runtime;
	@RATE_LIMIT_ENABLED=$${RATE_LIMIT_ENABLED:-0} PORT_LLM_SERVER=$${PORT_LLM_SERVER:-8081} $(PY) -m llm_server.main > logs/uvicorn_local.log 2>&1 & echo $$! > runtime/server.pid; echo PID: $$(cat runtime/server.pid)

stop:
	@echo "Stopping LLM-server (bg) if running";
	@if [ -f runtime/server.pid ]; then kill `cat runtime/server.pid` 2>/dev/null || true; rm -f runtime/server.pid; echo stopped; else echo "no runtime/server.pid"; fi

.PHONY: suite
suite:
	@$(PY) tools/suite.py
