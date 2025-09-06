from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Optional

from .registry import ModelRegistry


def merge_params(defaults: Dict[str, object], overrides: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    p = dict(defaults or {})
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def build_llama_cli_args(model_path: Path, prompt: str, params: Dict[str, object]) -> list[str]:
    args = [
        "-m",
        str(model_path),
        "-p",
        prompt,
        "-n",
        str(int(params.get("max_tokens", 256))),
        "--temp",
        str(float(params.get("temperature", 0.2))),
        "--top-p",
        str(float(params.get("top_p", 0.9))),
        "-nkvl",  # keep best? placeholder/no-keep to reduce context growth
        "--repeat-penalty",
        str(float(params.get("repeat_penalty", 1.1))),
    ]
    top_k = params.get("top_k")
    if top_k is not None:
        args += ["--top-k", str(int(top_k))]
    seed = params.get("seed")
    if seed is not None:
        args += ["-s", str(int(seed))]
    return args


def generate_with_llama_cli(registry: ModelRegistry, model_name: str, prompt: str, overrides: Optional[Dict[str, object]] = None, timeout_s: Optional[int] = None) -> Dict[str, object]:
    # Ensure model exists
    spec = registry.get(model_name)
    if not spec or not spec.path.exists():
        return {"error": f"model {model_name} not available"}

    params = merge_params(registry.cfg.get("gen_defaults", {}), overrides)
    cmd = [str(registry.cfg.get("processes", {}).get("llm_server", ""))]  # not used; kept for future
    # Use llama.cpp built CLI directly
    llama_cli = str((Path(__file__).resolve().parents[1] / "vendor" / "llama.cpp" / "build" / "bin" / "llama-cli"))
    cmd = [llama_cli] + build_llama_cli_args(spec.path, prompt, params)

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout_s or 60).decode("utf-8", errors="ignore")
        return {"model": model_name, "prompt": prompt, "output": out, "params": params}
    except subprocess.TimeoutExpired:
        return {"error": "generation timeout"}
    except subprocess.CalledProcessError as e:
        return {"error": f"llama-cli failed: {e.output.decode('utf-8', errors='ignore')[:200]}"}


def speculative_generate(registry: ModelRegistry, draft_model: str, target_model: str, prompt: str, overrides: Optional[Dict[str, object]] = None, timeout_s: Optional[int] = None) -> Dict[str, object]:
    # Hook for speculative decoding; placeholder delegates to target
    # Later, use llama.cpp examples/speculative to implement a coordinated run.
    return generate_with_llama_cli(registry, target_model, prompt, overrides, timeout_s)

