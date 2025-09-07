#!/usr/bin/env python3
"""Checklists de preflight para cada parte del proyecto (solo consola).

Sin dependencias extra. Devuelve listas de (nombre, ok, detalle).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Callable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]


Result = Tuple[str, bool, str]


def _ok(name: str, detail: str = "") -> Result:
    return (name, True, detail)


def _fail(name: str, detail: str = "") -> Result:
    return (name, False, detail)


def check_python() -> Result:
    ver = sys.version.split()[0]
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 9):
        return _ok("Python >= 3.9", ver)
    return _fail("Python >= 3.9", ver)


def check_venv() -> Result:
    in_venv = (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    return _ok("Virtualenv activado", sys.prefix) if in_venv else _fail("Virtualenv activado", "no detectado")


def check_requirements() -> Result:
    mods = ["fastapi", "uvicorn", "pytest", "httpx", "pdoc"]
    missing = []
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception:
            missing.append(m)
    if not missing:
        return _ok("Dependencias importables", ", ".join(mods))
    return _fail("Dependencias importables", "faltan: " + ", ".join(missing))


def check_files_foundation() -> Result:
    must = [
        ROOT / "docs/context/manifest.json",
        ROOT / "configs/models.yaml",
        ROOT / "configs/limits.yaml",
        ROOT / "configs/custom_profiles/dev-default.yaml",
        ROOT / "configs/api.yaml",
        ROOT / "runtime/current_profile",
    ]
    missing = [str(p.relative_to(ROOT)) for p in must if not p.exists()]
    return _ok("Ficheros base presentes", "ok") if not missing else _fail("Ficheros base presentes", ", ".join(missing))


def check_profile_pointer_matches() -> Result:
    try:
        profile_name = (ROOT / "configs" / "custom_profiles" / "dev-default.yaml").read_text()
        # the file is JSON-compatible; only read its name via tools/validate is more robust; keep simple
        data = json.loads((ROOT / "configs" / "custom_profiles" / "dev-default.yaml").read_text())
        expected = data.get("profile_name")
        current = (ROOT / "runtime" / "current_profile").read_text().strip()
        return _ok("runtime/current_profile coincide", current) if current == expected else _fail("runtime/current_profile coincide", f"{current} != {expected}")
    except Exception as e:
        return _fail("runtime/current_profile coincide", str(e))


def check_llama_built() -> Result:
    binp = ROOT / "vendor/llama.cpp/build/bin/llama-cli"
    return _ok("llama.cpp compilado", str(binp)) if binp.exists() else _fail("llama.cpp compilado", "ejecuta: make llama.clone && make llama.setup && make llama.build")


def check_models_presence() -> Result:
    try:
        models_cfg = json.loads((ROOT / "configs" / "models.yaml").read_text()).get("models", [])
        models_dir = ROOT.parent / "models"
        missing = []
        from llm_server.models_catalog import CATALOG  # type: ignore
        for m in models_cfg:
            name = m.get("name")
            file = CATALOG.get(name, {}).get("file")
            if not file:
                # skip unknown
                continue
            if not (models_dir / file).exists():
                missing.append(file)
        return _ok("Modelos presentes", "ok") if not missing else _fail("Modelos presentes", f"faltan {len(missing)}: " + ", ".join(missing[:3]))
    except Exception as e:
        return _fail("Modelos presentes", str(e))


def check_http_smoke() -> Result:
    try:
        from tools.smoke_http import main as smoke_main  # type: ignore
        rc = smoke_main()
        return _ok("HTTP smoke (/healthz,/info,/models,/memory)", "ok") if rc == 0 else _fail("HTTP smoke", f"rc={rc}")
    except Exception as e:
        return _fail("HTTP smoke", str(e))


def check_messaging_configs() -> Result:
    base = ROOT / "configs" / "messaging"
    need = [base / "docker-compose.dev.yml", base / "redpanda.yaml", base / "nats.yaml", base / "tenancy.yaml"]
    missing = [str(p.relative_to(ROOT)) for p in need if not p.exists()]
    return _ok("Configs de mensajería", "ok") if not missing else _fail("Configs de mensajería", ", ".join(missing))


def run_checks(checks: List[Callable[[], Result]]) -> List[Result]:
    return [fn() for fn in checks]

