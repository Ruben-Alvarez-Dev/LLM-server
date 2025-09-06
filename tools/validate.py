#!/usr/bin/env python3
import json
import sys
from pathlib import Path

OK = 0
ERR = 1

ROOT = Path(__file__).resolve().parents[1]

MODELS_PATH = ROOT / 'configs' / 'models.yaml'
LIMITS_PATH = ROOT / 'configs' / 'limits.yaml'
PROFILE_PATH = ROOT / 'configs' / 'custom_profiles' / 'dev-default.yaml'
CURRENT_PROFILE_PATH = ROOT / 'runtime' / 'current_profile'

def load_jsonlike(path: Path):
    try:
        text = path.read_text()
    except FileNotFoundError:
        raise RuntimeError(f"Missing required file: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON/YAML (JSON form) at {path}: {e}")

def require(cond: bool, msg: str):
    if not cond:
        raise RuntimeError(msg)

def validate_models(models_data: dict):
    require(isinstance(models_data, dict), 'models.yaml must be an object')
    models = models_data.get('models')
    require(isinstance(models, list) and len(models) >= 1, 'models.yaml: "models" must be a non-empty array')
    seen = set()
    for m in models:
        require(isinstance(m, dict), 'Each model entry must be an object')
        name = m.get('name')
        est = m.get('est_ram_gb')
        ctx = m.get('context_max')
        require(isinstance(name, str) and name, 'Model name must be a non-empty string')
        require(name not in seen, f'Duplicate model name: {name}')
        seen.add(name)
        require(isinstance(est, (int, float)) and est >= 0, f'Model {name}: est_ram_gb must be >= 0')
        require(isinstance(ctx, int) and ctx >= 1, f'Model {name}: context_max must be integer >= 1')
    return models

def validate_limits(limits_data: dict):
    require(isinstance(limits_data, dict), 'limits.yaml must be an object')
    wm = limits_data.get('windows_max')
    cc = limits_data.get('concurrency')
    cut = limits_data.get('step_cutoff_seconds')
    require(isinstance(wm, dict) and wm, 'limits.yaml: windows_max must be a non-empty object')
    for k,v in wm.items():
        require(isinstance(k, str) and k, 'windows_max keys must be strings')
        require(isinstance(v, int) and v >= 1, f'windows_max[{k}] must be integer >= 1')
    require(isinstance(cc, dict) and cc, 'limits.yaml: concurrency must be a non-empty object')
    for k,v in cc.items():
        require(isinstance(k, str) and k, 'concurrency keys must be strings')
        require(isinstance(v, int) and v >= 0, f'concurrency[{k}] must be integer >= 0')
    require(isinstance(cut, int) and cut >= 1, 'limits.yaml: step_cutoff_seconds must be integer >= 1')
    return wm, cc, cut

def validate_profile(profile_data: dict, model_names: set):
    require(isinstance(profile_data, dict), 'profile must be an object')
    required_keys = ['profile_name','selected_models','ports','processes','concurrency','ram_budget_gb','memory_server_ram_gb','notes']
    for k in required_keys:
        require(k in profile_data, f'profile missing required key: {k}')
    name = profile_data['profile_name']
    require(isinstance(name, str) and name, 'profile_name must be a non-empty string')
    sel = profile_data['selected_models']
    require(isinstance(sel, list) and sel, 'selected_models must be a non-empty array')
    for s in sel:
        require(isinstance(s, str) and s, 'selected_models entries must be strings')
        require(s in model_names, f'selected model not found in models.yaml: {s}')
    ports = profile_data['ports']
    require(isinstance(ports, dict), 'ports must be an object')
    for p in ['orchestrator','llm_server','memory_server']:
        require(isinstance(ports.get(p), int) and ports[p] > 0, f'ports.{p} must be positive integer')
    procs = profile_data['processes']
    require(isinstance(procs, dict), 'processes must be an object')
    for p in ['orchestrator','llm_server','memory_server']:
        require(isinstance(procs.get(p), str) and procs[p], f'processes.{p} must be non-empty string')
    cc = profile_data['concurrency']
    require(isinstance(cc, dict) and cc, 'concurrency must be a non-empty object')
    for k,v in cc.items():
        require(isinstance(k, str) and k, 'concurrency keys must be strings')
        require(isinstance(v, int) and v >= 0, f'concurrency[{k}] must be integer >= 0')
    ram = profile_data['ram_budget_gb']
    mem_ram = profile_data['memory_server_ram_gb']
    require(isinstance(ram, (int,float)) and ram >= 1, 'ram_budget_gb must be >= 1')
    require(isinstance(mem_ram, (int,float)) and mem_ram >= 0, 'memory_server_ram_gb must be >= 0')
    notes = profile_data['notes']
    require(isinstance(notes, str), 'notes must be a string')
    return name, sel, int(ram), int(mem_ram)

def read_current_profile_name():
    try:
        return CURRENT_PROFILE_PATH.read_text().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Missing required file: {CURRENT_PROFILE_PATH}")

def print_ram_table(models, selected, ram_budget_gb):
    sel_set = set(selected)
    total_resident = sum(m['est_ram_gb'] for m in models if m['name'] in sel_set)
    headroom = ram_budget_gb - total_resident
    # Table header
    print("model\test_ram_gb\tresident\theadroom_gb")
    for m in models:
        resident = m['name'] in sel_set
        print(f"{m['name']}\t{m['est_ram_gb']}\t{str(resident).lower()}\t{headroom}")
    print(f"\nTotal resident: {total_resident} GB; Headroom: {headroom} GB (budget {ram_budget_gb} GB)")
    return total_resident, headroom

def main():
    try:
        models_data = load_jsonlike(MODELS_PATH)
        limits_data = load_jsonlike(LIMITS_PATH)
        profile_data = load_jsonlike(PROFILE_PATH)

        models = validate_models(models_data)
        model_names = {m['name'] for m in models}
        validate_limits(limits_data)
        profile_name, selected_models, ram_budget_gb, memory_server_ram_gb = validate_profile(profile_data, model_names)

        # current_profile consistency
        current = read_current_profile_name()
        require(current == profile_name, f"runtime/current_profile ('{current}') must equal profile_name ('{profile_name}')")

        # RAM table
        total_resident, headroom = print_ram_table(models, selected_models, ram_budget_gb)
        require(total_resident <= ram_budget_gb, 'Resident models exceed ram_budget_gb')
        require(headroom >= 5, 'Headroom must be at least 5 GB')

        print("\nValidation OK.")
        return OK
    except RuntimeError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return ERR

if __name__ == '__main__':
    sys.exit(main())

