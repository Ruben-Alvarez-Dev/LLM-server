#!/usr/bin/env python3
import argparse
import os
import subprocess as sp
import sys
import time
from pathlib import Path

# Ensure repo root on sys.path so module imports work
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from typing import Optional, Dict, List


def run(cmd: List[str], env: Optional[Dict] = None) -> int:
    print(f"\n$ {' '.join(cmd)}")
    return sp.call(cmd, env=env or os.environ.copy())


def hr(title: str = "") -> None:
    line = "=" * 72
    print("\n" + line)
    if title:
        print(title)
        print(line)


def explain() -> None:
    hr("Test Suite Overview")
    print("- validate: schema + profile + RAM budget check")
    print("- checks: preflight por parte (instalaciones, ficheros, procesos)")
    print("- test.fast: fast API/config coverage")
    print("- test.sse: streaming SSE for chat/completions (no models needed)")
    print("- test.housekeeper: housekeeping metrics, snapshot, admin")
    print("- test.agents: NL→DSL planning + persistence")
    print("- smoke: start app and hit key endpoints")
    print("- all: full pytest run")


def do_validate() -> int:
    hr("Validate config")
    return run([sys.executable, str(ROOT / "tools" / "validate.py")])


def do_pytest(args: List[str]) -> int:
    return run([sys.executable, "-m", "pytest", "-q", *args])


def do_smoke() -> int:
    hr("HTTP Smoke")
    env = os.environ.copy()
    env.setdefault("RATE_LIMIT_ENABLED", "0")
    return run([sys.executable, str(ROOT / "tools" / "smoke_http.py")], env=env)


def do_smoke_extended() -> int:
    hr("HTTP Smoke (Extended)")
    env = os.environ.copy()
    env.setdefault("RATE_LIMIT_ENABLED", "0")
    return run([sys.executable, str(ROOT / "tools" / "smoke_extended.py")], env=env)


def pretty_results(title: str, results: List[tuple]) -> None:
    hr(title)
    for name, ok, detail in results:
        mark = "[✔]" if ok else "[✖]"
        print(f" {mark} {name}" + (f" — {detail}" if detail else ""))


def do_checks(part: str) -> int:
    from tools.checks import (
        run_checks,
        check_python,
        check_venv,
        check_requirements,
        check_files_foundation,
        check_profile_pointer_matches,
        check_llama_built,
        check_models_presence,
        check_http_smoke,
        check_messaging_configs,
    )
    common = [check_python, check_venv, check_requirements, check_files_foundation, check_profile_pointer_matches]
    parts = {
        "foundation": common,
        "api": common + [check_http_smoke],
        "models": common + [check_llama_built, check_models_presence],
        "messaging": common + [check_messaging_configs],
        "all": common + [check_http_smoke, check_llama_built, check_models_presence, check_messaging_configs],
    }
    checks = parts.get(part)
    if not checks:
        print(f"Parte desconocida: {part}")
        return 1
    res = run_checks(checks)
    pretty_results(f"Preflight: {part}", res)
    # exit code 0 only if all passed
    return 0 if all(ok for _, ok, _ in res) else 2


def menu() -> int:
    explain()
    print("\nSeleccione una opción:")
    print(" 1) validate")
    print(" 2) checks (foundation)")
    print(" 3) checks (api)")
    print(" 4) checks (models)")
    print(" 5) checks (messaging)")
    print(" 6) test.fast")
    print(" 7) test.sse")
    print(" 8) test.housekeeper")
    print(" 9) test.agents")
    print(" 10) smoke")
    print(" 11) smoke (extended)")
    print(" 12) all (pytest)")
    print(" 0) salir")
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0
    from glob import glob
    hk = sorted(glob(str(ROOT / "tests" / "test_housekeeper_*.py")))
    # Convert to relative paths for pytest output prettiness
    hk_rel = [str(Path(p).relative_to(ROOT)) for p in hk]
    mapping = {
        "1": lambda: do_validate(),
        "2": lambda: do_checks("foundation"),
        "3": lambda: do_checks("api"),
        "4": lambda: do_checks("models"),
        "5": lambda: do_checks("messaging"),
        "6": lambda: do_pytest(["tests/test_config_and_api.py", "tests/test_schemas_endpoints.py", "tests/test_info_memory_field.py", "tests/test_memory_ready_endpoint.py"]),
        "7": lambda: do_pytest(["tests/test_api_sse.py"]),
        "8": lambda: do_pytest(hk_rel + ["tests/test_metrics_housekeeper.py"]),
        "9": lambda: do_pytest(["tests/test_agents_nl_dsl.py"]),
        "10": lambda: do_smoke(),
        "11": lambda: do_smoke_extended(),
        "12": lambda: do_pytest([]),
        "0": lambda: 0,
    }
    fn = mapping.get(choice)
    if not fn:
        print("Opción no válida")
        return 1
    return fn()


def main() -> int:
    ap = argparse.ArgumentParser(description="Terminal test runner (menu or flags)")
    ap.add_argument("--fast", action="store_true", help="Run fast API/config tests")
    ap.add_argument("--sse", action="store_true", help="Run SSE streaming tests")
    ap.add_argument("--housekeeper", action="store_true", help="Run housekeeper tests")
    ap.add_argument("--agents", action="store_true", help="Run agents plan tests")
    ap.add_argument("--validate", action="store_true", help="Run validator")
    ap.add_argument("--smoke", action="store_true", help="Run HTTP smoke")
    ap.add_argument("--all", action="store_true", help="Run all pytest")
    args = ap.parse_args()

    if args.validate:
        return do_validate()
    if args.fast:
            return do_pytest(["tests/test_config_and_api.py", "tests/test_schemas_endpoints.py", "tests/test_info_memory_field.py", "tests/test_memory_ready_endpoint.py"])
    if args.sse:
        return do_pytest(["tests/test_api_sse.py"])
    if args.housekeeper:
        from glob import glob as _glob
        hk = sorted(_glob(str(ROOT / "tests" / "test_housekeeper_*.py")))
        hk_rel = [str(Path(p).relative_to(ROOT)) for p in hk]
        return do_pytest(hk_rel + ["tests/test_metrics_housekeeper.py"])
    if args.agents:
        return do_pytest(["tests/test_agents_nl_dsl.py"])
    if args.smoke:
        return do_smoke()
    if args.all:
        return do_pytest([])
    # default interactive menu
    return menu()


if __name__ == "__main__":
    raise SystemExit(main())
