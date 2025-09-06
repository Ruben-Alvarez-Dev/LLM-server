import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]


def _load_json_or_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    # Try JSON first (our YAML files are JSON-compatible), then YAML if available
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore

            return yaml.safe_load(text)
        except Exception as e:  # pragma: no cover - optional dependency
            raise RuntimeError(f"Failed to parse {path} as JSON or YAML: {e}")


def load_runtime_profile_name() -> str:
    p = ROOT / "runtime" / "current_profile"
    return p.read_text().strip()


def load_profile(profile_name: str) -> Dict[str, Any]:
    path = ROOT / "configs" / "custom_profiles" / f"{profile_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")
    return _load_json_or_yaml(path)


def load_models() -> Dict[str, Any]:
    path = ROOT / "configs" / "models.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Models file not found: {path}")
    return _load_json_or_yaml(path)


def load_limits() -> Dict[str, Any]:
    path = ROOT / "configs" / "limits.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Limits file not found: {path}")
    return _load_json_or_yaml(path)


def load_housekeeper() -> Dict[str, Any]:
    path = ROOT / "configs" / "housekeeper.yaml"
    if not path.exists():
        return {"default_strategy": "balanced", "strategies": {}}
    return _load_json_or_yaml(path)


def effective_ports(profile: Dict[str, Any]) -> Tuple[int, int, int]:
    ports = profile.get("ports") or {}
    return int(ports.get("orchestrator", 8080)), int(ports.get("llm_server", 8081)), int(ports.get("memory_server", 8082))


def env_override(port_key: str, default: int) -> int:
    v = os.getenv(port_key)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def build_effective_config() -> Dict[str, Any]:
    """Merge order: env overrides -> profile -> defaults.

    Defaults are minimal; profile provides most values; ENV can override ports.
    """
    profile_name = load_runtime_profile_name()
    profile = load_profile(profile_name)
    models_cfg = load_models()
    limits_cfg = load_limits()
    hk_cfg = load_housekeeper()

    orch, llm_port, mem_port = effective_ports(profile)
    # ENV overrides
    orch = env_override("PORT_ORCHESTRATOR", orch)
    llm_port = env_override("PORT_LLM_SERVER", llm_port)
    mem_port = env_override("PORT_MEMORY_SERVER", mem_port)

    gen_defaults = (limits_cfg.get("gen_defaults") or {}).copy()
    # ENV overrides for quick tuning
    def _envf(name: str, cast):
        v = os.getenv(name)
        if v is None:
            return None
        try:
            return cast(v)
        except Exception:
            return None

    for key, cast in [
        ("temperature", float),
        ("top_p", float),
        ("top_k", int),
        ("repeat_penalty", float),
        ("max_tokens", int),
        ("seed", int),
    ]:
        env_key = f"GEN_{key.upper()}"
        val = _envf(env_key, cast)
        if val is not None:
            gen_defaults[key] = val

    cfg = {
        "profile_name": profile_name,
        "ports": {"orchestrator": orch, "llm_server": llm_port, "memory_server": mem_port},
        "concurrency": profile.get("concurrency", {}),
        "ram_budget_gb": profile.get("ram_budget_gb", 70),
        "memory_server_ram_gb": profile.get("memory_server_ram_gb", 10),
        "selected_models": profile.get("selected_models", []),
        "models": models_cfg.get("models", []),
        "limits": limits_cfg,
        "gen_defaults": gen_defaults,
        # models root outside this repo (parent directory)
        "models_root": str((ROOT.parent / "models").resolve()),
        "processes": profile.get("processes", {}),
        "vision": profile.get("vision", {"model": "qwen2-vl-7b-instruct-q4_k_m"}),
        "embeddings": profile.get("embeddings", [{"name": "default", "dimensions": 256, "purpose": "general"}]),
        "housekeeper": hk_cfg,
        "notes": profile.get("notes", ""),
    }
    return cfg
