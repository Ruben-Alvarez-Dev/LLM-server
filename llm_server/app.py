from typing import Any, Dict

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover - optional dependency at dev time
    FastAPI = None  # type: ignore
    JSONResponse = None  # type: ignore

from .config_loader import build_effective_config
from .metrics import metrics


def create_app() -> Any:
    cfg: Dict[str, Any] = build_effective_config()
    if FastAPI is None:
        # Minimal stub app interface for environments without FastAPI
        class StubApp:
            config = cfg

        return StubApp()

    app = FastAPI(title="LLM-server", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> Dict[str, Any]:
        return {"status": "ok", "profile": cfg["profile_name"]}

    @app.get("/readyz")
    def readyz() -> Dict[str, Any]:
        # Later: check model registry readiness
        return {"ready": True}

    @app.get("/metrics")
    def metrics_endpoint():
        return JSONResponse(metrics.snapshot())

    # Attach config for downstream use
    app.state.config = cfg  # type: ignore[attr-defined]
    return app

