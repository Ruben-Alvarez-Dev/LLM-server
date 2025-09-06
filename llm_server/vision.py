from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config_loader import build_effective_config
from .models_catalog import CATALOG


def _try_import_ocr():
    try:
        from PIL import Image  # type: ignore
    except Exception:
        Image = None  # type: ignore
    try:
        import pytesseract  # type: ignore
    except Exception:
        pytesseract = None  # type: ignore
    return Image, pytesseract


def _decode_image(data: str):
    if data.startswith("data:"):
        try:
            b64 = data.split(",", 1)[1]
        except Exception:
            b64 = data
    else:
        b64 = data
    try:
        return base64.b64decode(b64)
    except Exception:
        return None


def _load_image_from_url(url: str) -> Optional[bytes]:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:  # nosec B310
            return r.read()
    except Exception:
        return None


def _llama_cli_path() -> Optional[str]:
    # Allow override via env
    p = os.getenv("LLAMA_CLI")
    if p and Path(p).exists():
        return p
    # Default vendor path
    cand = Path(__file__).resolve().parents[1] / "vendor" / "llama.cpp" / "build" / "bin" / "llama-cli"
    if cand.exists():
        return str(cand)
    return None


def _materialize_images(images: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    paths: List[str] = []
    cleanup: List[str] = []
    for im in images:
        blob: Optional[bytes] = None
        if im.get("base64"):
            blob = _decode_image(str(im.get("base64")))
        elif im.get("url"):
            blob = _load_image_from_url(str(im.get("url")))
        if not blob:
            continue
        fd, pth = tempfile.mkstemp(prefix="vision_", suffix=".png")
        os.close(fd)
        with open(pth, "wb") as f:
            f.write(blob)
        paths.append(pth)
        cleanup.append(pth)
    return paths, cleanup


def _run_vision_llm(images: List[Dict[str, Any]], prompt: str) -> Optional[str]:
    cli = _llama_cli_path()
    if not cli:
        return None
    cfg = build_effective_config()
    vcfg = cfg.get("vision", {}) or {}
    model_name = vcfg.get("model") or "qwen2-vl-7b-instruct-q4_k_m"
    cat = CATALOG.get(model_name, {})
    file = cat.get("file")
    mmproj = cat.get("mmproj")
    if not file or not mmproj:
        return None
    model_path = Path(cfg["models_root"]) / file
    mmproj_path = Path(cfg["models_root"]) / mmproj
    if not (model_path.exists() and mmproj_path.exists()):
        return None
    img_paths, cleanup = _materialize_images(images)
    if not img_paths:
        return None
    try:
        cmd = [
            cli,
            "-m", str(model_path),
            "--mmproj", str(mmproj_path),
            "-p", prompt or "Describe the content and extract text.",
            "--temp", "0.2",
            "--top-p", "0.9",
            "-n", "512",
        ]
        for p in img_paths:
            cmd += ["--image", p]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=90).decode("utf-8", errors="ignore")
        return out.strip()
    except Exception:
        return None
    finally:
        for p in cleanup:
            try:
                os.unlink(p)
            except Exception:
                pass


def analyze(images: List[Dict[str, Any]], prompt: Optional[str] = None, tasks: Optional[List[str]] = None, ocr_mode: str = "auto") -> Dict[str, Any]:
    # Try VL model first
    vl_text: Optional[str] = _run_vision_llm(images, prompt or "")

    # OCR fallback/augment
    Image, pytesseract = _try_import_ocr()
    out_ocr: List[Dict[str, Any]] = []
    for idx, im in enumerate(images):
        text = ""
        if ocr_mode != "off" and Image is not None and pytesseract is not None:
            blob: Optional[bytes] = None
            if im.get("base64"):
                blob = _decode_image(str(im.get("base64")))
            elif im.get("url"):
                blob = _load_image_from_url(str(im.get("url")))
            if blob:
                try:
                    pil = Image.open(BytesIO(blob))
                    text = pytesseract.image_to_string(pil)
                except Exception:
                    text = ""
        out_ocr.append({"index": idx, "text": text})

    insights: List[str] = []
    issues: List[str] = []
    p = (prompt or "").lower()
    if "error" in p:
        insights.append("Focus: look for error panels, stack traces, and red badges.")
    if "code" in p:
        insights.append("Focus: monospace regions and line numbers for code blocks.")
    if "ui" in p:
        insights.append("Focus: alignment, contrast, and clickable affordances.")

    if vl_text:
        insights.append(vl_text)

    return {"ocr": out_ocr, "insights": insights, "issues": issues, "raw": {"tasks": tasks or []}}
