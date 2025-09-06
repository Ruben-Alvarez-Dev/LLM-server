from typing import Any, Dict

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover - optional dependency at dev time
    FastAPI = None  # type: ignore
    JSONResponse = None  # type: ignore

from .config_loader import build_effective_config
from .registry import ModelRegistry
from .metrics import metrics
from .logging_utils import get_logger, new_request_id
try:
    from .api import router as api_router
except Exception:
    api_router = None


def create_app() -> Any:
    cfg: Dict[str, Any] = build_effective_config()
    if FastAPI is None:
        # Minimal stub app interface for environments without FastAPI
        class StubApp:
            config = cfg

        return StubApp()

    app = FastAPI(title="LLM-server", version="0.1.0")
    log = get_logger("llm-server")

    # Request ID + structured access logs
    @app.middleware("http")
    async def request_context(request, call_next):  # type: ignore[no-redef]
        rid = new_request_id()
        setattr(request.state, "request_id", rid)
        start = __import__("time").time()
        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 200)
            return response
        except Exception as e:  # pragma: no cover
            metrics.inc("errors_total", 1)
            raise
        finally:
            dur = (__import__("time").time() - start) * 1000.0
            metrics.inc("requests_total", 1)
            metrics.observe_duration("http_request", dur)
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "dur_ms": round(dur, 2),
                    "request_id": rid,
                },
            )

    @app.get("/healthz")
    def healthz() -> Dict[str, Any]:
        return {"status": "ok", "profile": cfg["profile_name"]}

    registry = ModelRegistry()
    registry.refresh()
    # Concurrency manager (stored for future API usage)
    try:
        from .concurrency import ConcurrencyManager

        conc = ConcurrencyManager()
    except Exception:
        conc = None

    @app.get("/readyz")
    def readyz() -> Dict[str, Any]:
        return registry.readiness_report()

    @app.get("/metrics")
    def metrics_endpoint():
        return JSONResponse(metrics.snapshot())

    # API endpoints
    if api_router is not None:
        app.include_router(api_router)

    # Attach config for downstream use
    app.state.config = cfg  # type: ignore[attr-defined]
    app.state.registry = registry  # type: ignore[attr-defined]
    app.state.concurrency = conc  # type: ignore[attr-defined]
    return app
