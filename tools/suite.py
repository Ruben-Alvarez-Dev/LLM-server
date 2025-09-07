#!/usr/bin/env python3
"""QA Suite Orchestrator (one command, pretty summaries).

Runs preflight checks, validator, targeted test groups, and extended smoke.
Prints concise progress + results and stores full logs under artifacts/.
"""
from __future__ import annotations

import datetime as _dt
import os
import subprocess as sp
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ts() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def _badge(ok: bool) -> str:
    return "[✔]" if ok else "[✖]"


def _run(cmd: List[str], log_name: str, env: dict | None = None) -> Tuple[bool, str]:
    ART.mkdir(parents=True, exist_ok=True)
    log_path = ART / log_name
    try:
        proc = sp.run(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, env=env or os.environ.copy(), text=True)
        out = proc.stdout or ""
        log_path.write_text(out)
        return (proc.returncode == 0, str(log_path))
    except Exception as e:
        log_path.write_text(str(e))
        return (False, str(log_path))


def _print_step(n: int, total: int, title: str) -> None:
    print(f"[{n}/{total}] {title} …")


def _print_done(ok: bool, title: str, log: str | None = None) -> None:
    if ok:
        print(f"  {_badge(True)} {title}")
    else:
        hint = f" (detalles: {log})" if log else ""
        print(f"  {_badge(False)} {title}{hint}")


def preflight() -> Tuple[bool, str]:
    # Reuse checks foundation + api minimally
    try:
        from tools.checks import (
            run_checks,
            check_python,
            check_venv,
            check_requirements,
            check_files_foundation,
            check_profile_pointer_matches,
        )
        res = run_checks([check_python, check_venv, check_requirements, check_files_foundation, check_profile_pointer_matches])
        ok = all(r[1] for r in res)
        # Format a compact summary string
        parts = [f"{_badge(r[1])} {r[0]}" for r in res]
        return ok, "; ".join(parts)
    except Exception as e:
        return False, f"checks error: {e}"


def main() -> int:
    # plan steps; optionally extend with real models tests
    total = 7
    step = 1
    results: List[Tuple[str, bool, str]] = []

    # Always keep rate limit off for suite
    env = os.environ.copy()
    env.setdefault("RATE_LIMIT_ENABLED", "0")

    # 1) Preflight
    _print_step(step, total, "Preflight checks")
    ok, detail = preflight()
    results.append(("Preflight", ok, detail))
    _print_done(ok, "Preflight", None if ok else detail)
    step += 1

    # 2) Validate
    _print_step(step, total, "Validate config and RAM budget")
    ok, log = _run([sys.executable, str(ROOT / "tools" / "validate.py")], f"validate-{_ts()}.log", env)
    results.append(("Validate", ok, log))
    _print_done(ok, "Validate", log)
    step += 1

    # 3) Tests: fast
    _print_step(step, total, "Tests (fast)")
    fast_args = [
        "-m",
        "pytest",
        "-q",
        str(ROOT / "tests" / "test_config_and_api.py"),
        str(ROOT / "tests" / "test_schemas_endpoints.py"),
        str(ROOT / "tests" / "test_info_memory_field.py"),
        str(ROOT / "tests" / "test_memory_ready_endpoint.py"),
    ]
    ok, log = _run([sys.executable, *fast_args], f"tests-fast-{_ts()}.log", env)
    results.append(("Tests fast", ok, log))
    _print_done(ok, "Tests (fast)", log)
    step += 1

    # 4) Tests: SSE
    _print_step(step, total, "Tests (SSE)")
    ok, log = _run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_api_sse.py")], f"tests-sse-{_ts()}.log", env)
    results.append(("Tests sse", ok, log))
    _print_done(ok, "Tests (SSE)", log)
    step += 1

    # 5) Tests: housekeeper
    _print_step(step, total, "Tests (housekeeper)")
    # Expand glob in python: collect matching files
    hk_files = [str(p) for p in sorted((ROOT / "tests").glob("test_housekeeper_*.py"))]
    hk_files.append(str(ROOT / "tests" / "test_metrics_housekeeper.py"))
    ok, log = _run([sys.executable, "-m", "pytest", "-q", *hk_files], f"tests-housekeeper-{_ts()}.log", env)
    results.append(("Tests housekeeper", ok, log))
    _print_done(ok, "Tests (housekeeper)", log)
    step += 1

    # 6) Tests: agents
    _print_step(step, total, "Tests (agents)")
    ok, log = _run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_agents_nl_dsl.py")], f"tests-agents-{_ts()}.log", env)
    results.append(("Tests agents", ok, log))
    _print_done(ok, "Tests (agents)", log)
    step += 1

    # 7) Smoke extended
    _print_step(step, total, "HTTP smoke (extended)")
    ok, log = _run([sys.executable, str(ROOT / "tools" / "smoke_extended.py")], f"smoke-extended-{_ts()}.log", env)
    results.append(("Smoke extended", ok, log))
    _print_done(ok, "HTTP smoke (extended)", log)

    # Optional: real model tests if registry reports ready
    try:
        from llm_server.registry import ModelRegistry
        r = ModelRegistry(); r.refresh()
        if r.ready():
            extra = [
                ("Tests models (real)", [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_models_real.py")], f"tests-models-real-{_ts()}.log"),
                ("Tests e2e (real)",    [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests" / "test_e2e_full.py")], f"tests-e2e-real-{_ts()}.log"),
            ]
            for title, cmd, logname in extra:
                print(f"[+] {title} …")
                ok, log = _run(cmd, logname, env)
                results.append((title, ok, log))
                _print_done(ok, title, log)
        else:
            print("[i] Real models no disponibles: se omiten tests reales (usa make models.download)")
    except Exception:
        print("[i] No se pudo determinar el estado de modelos; se omiten tests reales")

    # Summary
    print("\n================ Summary ================")
    passed = sum(1 for title, ok, _ in results if ok and title != "Preflight")
    total_crit = sum(1 for title, _, _ in results if title != "Preflight")
    for title, ok, detail in results:
        hint = "" if ok else f" — detalles: {detail}"
        print(f" {_badge(ok)} {title}{hint}")
    print(f"Overall: {passed}/{total_crit} OK (preflight es informativo)")
    print(f"Logs: {ART}/")

    return 0 if passed == total_crit else 2


if __name__ == "__main__":
    raise SystemExit(main())
