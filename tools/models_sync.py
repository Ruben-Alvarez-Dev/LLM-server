#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
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
    ap.add_argument("--download", action="store_true", help="Download missing models via HF if HF_TOKEN is set")
    ap.add_argument("--token", type=str, default=None, help="Optional HF token (or use env HF_TOKEN)")
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

    if missing and args.download:
        token = args.token or os.getenv("HF_TOKEN")
        if not token:
            print("HF token not provided. Set HF_TOKEN env or pass --token.")
            return 1
        print("\nAttempting download of missing files (this may take a long time):")
        for m in models:
            src = SOURCES.get(m["name"], {})
            if not src:
                continue
            fname = src.get("file")
            if not fname or fname not in missing:
                continue
            repo = src["repo"]
            url = f"https://huggingface.co/{repo}/resolve/main/{fname}"
            dest = MODELS_DIR / fname
            try:
                _download_with_auth(url, dest, token)
                print(f"Downloaded -> {dest}")
            except Exception as e:
                print(f"Failed to download {fname}: {e}")

        # Re-check
        missing = [f for f in missing if not (MODELS_DIR / f).exists()]

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

# --- helpers ---

def _download_with_auth(url: str, dest: Path, token: str, chunk: int = 1024 * 1024) -> None:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                _print_progress(dest.name, downloaded, total)
    print()

def _print_progress(name: str, done: int, total: int) -> None:
    if total <= 0:
        sys.stdout.write(f"\r{name}: {done/1e6:.1f}MB")
        sys.stdout.flush()
        return
    pct = 100.0 * done / total
    sys.stdout.write(f"\r{name}: {pct:5.1f}% ({done/1e6:.1f}/{total/1e6:.1f}MB)")
    sys.stdout.flush()
