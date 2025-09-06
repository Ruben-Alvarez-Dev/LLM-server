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
