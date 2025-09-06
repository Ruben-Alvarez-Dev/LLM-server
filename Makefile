PY=python3

.PHONY: codex validate

codex:
	@$(PY) -c "import json;d=json.load(open('docs/context/manifest.json'));print('\n'.join(f['path'] for f in sorted(d.get('files',[]), key=lambda x:(-int(x.get('priority',0)), x.get('path','')))))"

validate:
	@$(PY) tools/validate.py
