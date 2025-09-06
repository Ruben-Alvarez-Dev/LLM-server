#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT.parent / "models"


SOURCES: Dict[str, Dict[str, str]] = {
    # Suggested sources (adjust to your preferred mirrors/providers)
    "deepseek-r1-qwen-32b-q4_k_m": {
        "repo": "lmstudio-community/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        "file": "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
    "qwen2.5-14b-instruct-q4_k_m": {
        "repo": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
    "phi-4-mini-instruct": {
        "repo": "microsoft/Phi-4-mini-instruct-GGUF",
        "file": "Phi-4-mini-instruct-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
}


def load_models_cfg() -> List[Dict]:
    path = ROOT / "configs" / "models.yaml"
    data = json.loads(path.read_text())
    return data.get("models", [])


def ensure_models_dir(create: bool) -> bool:
    if MODELS_DIR.exists():
        return True
    if create:
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Failed to create models dir at {MODELS_DIR}: {e}")
            return False
    return False


def print_plan(models: List[Dict]):
    print(f"Models root: {MODELS_DIR}")
    print("Planned models:")
    for m in models:
        name = m["name"]
        src = SOURCES.get(name, {})
        fname = src.get("file", "<unknown>")
        repo = src.get("repo", "<unknown>")
        provider = src.get("provider", "<unknown>")
        print(f"- {name}: {fname} from {provider}:{repo}")


def main():
    ap = argparse.ArgumentParser(description="Models directory sync/check")
    ap.add_argument("--create", action="store_true", help="Create ../models directory if missing")
    ap.add_argument("--check", action="store_true", help="Only check presence; do not download")
    args = ap.parse_args()

    models = load_models_cfg()
    ok = ensure_models_dir(create=args.create)
    if not ok and not MODELS_DIR.exists():
        print("Models directory missing. Re-run with --create or create manually.")
        return 1

    print_plan(models)
    missing = []
    for m in models:
        name = m["name"]
        src = SOURCES.get(name, {})
        fname = src.get("file")
        if not fname:
            continue
        if not (MODELS_DIR / fname).exists():
            missing.append(fname)

    if missing:
        print("\nMissing model files:")
        for f in missing:
            print(f"- {f}")
        print("\nDownload instructions (manual or with hf):")
        for m in models:
            src = SOURCES.get(m["name"], {})
            if not src:
                continue
            print(
                f"- {src['provider']}://{src['repo']}/{src['file']} -> {MODELS_DIR / src['file']}"
            )
        print("\nTip: Install HuggingFace CLI and run:\n  hf_hub_download REPO FILE --local-dir ../models")
    else:
        print("\nAll planned model files are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

