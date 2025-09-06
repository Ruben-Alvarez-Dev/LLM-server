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
	@$(PY) - <<'PY'
from llm_server.registry import ModelRegistry
r=ModelRegistry(); r.refresh()
print(r.readiness_report())
PY

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
