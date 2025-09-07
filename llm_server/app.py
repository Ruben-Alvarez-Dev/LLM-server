"""Application initialization and middleware.

Provides:
- `create_app()`: builds the FastAPI app with endpoints, metrics, and housekeeper.
- Request context middleware: IDs, structured access logs, and rate limiting.

Google-style docstrings to ease automatic documentation.
"""

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
from .logging_utils import get_logger, new_request_id, set_request_id
import threading
from .housekeeper import Housekeeper


class _RateLimiter:
    """Simple per-client IP token bucket.

    Args:
        rps (float): Tokens per second (allowed average).
        burst (int): Maximum accumulated burst.
    """

    def __init__(self, rps: float, burst: int) -> None:
        self.rps = max(0.0, float(rps))
        self.burst = max(1, int(burst))
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)

    def allow(self, key: str, now: float) -> bool:
        """Consume 1 token and return True if allowed.

        Args:
            key (str): Client identifier (e.g., IP).
            now (float): Current timestamp.

        Returns:
            bool: True if the request is allowed, False if rate limited.
        """
        if self.rps <= 0:
            return True
        with self._lock:
            tokens, last = self._buckets.get(key, (self.burst, now))
            # refill
            elapsed = max(0.0, now - last)
            tokens = min(self.burst, tokens + elapsed * self.rps)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            tokens -= 1.0
            self._buckets[key] = (tokens, now)
            return True
try:
    from .api import router as api_router
except Exception:
    api_router = None


def create_app() -> Any:
    """Create and initialize the application.

    Returns:
        Any: FastAPI instance (or StubApp when FastAPI isn't available).
    """
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
        # Basic rate limiting per-client (optional via env)
        import os as _os
        _rl_enabled = _os.getenv("RATE_LIMIT_ENABLED", "1") in ("1", "true", "on")
        if _rl_enabled:
            try:
                rps = float(_os.getenv("RATE_LIMIT_RPS", "20"))
                burst = int(_os.getenv("RATE_LIMIT_BURST", "40"))
            except Exception:
                rps, burst = 20.0, 40
            limiter = getattr(app.state, "_limiter", None)
            if limiter is None or getattr(limiter, "rps", None) != rps or getattr(limiter, "burst", None) != burst:
                limiter = _RateLimiter(rps=rps, burst=burst)
                app.state._limiter = limiter  # type: ignore[attr-defined]
            client = getattr(request, "client", None)
            ip = getattr(client, "host", "?")
            now = __import__("time").time()
            key = f"{ip}"
            if not limiter.allow(key, now):
                metrics.inc("rate_limited_total", 1)
                metrics.inc(f"rate_limited_total:{request.method} {request.url.path}", 1)
                try:
                    log.info("rate_limit", extra={"ip": ip, "method": request.method, "path": request.url.path, "rps": limiter.rps, "burst": limiter.burst})
                except Exception:
                    pass
                return JSONResponse({"error": {"code": 429, "message": "rate limit exceeded"}}, status_code=429)
        # Incoming header support
        try:
            incoming = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
        except Exception:
            incoming = None
        rid = incoming or new_request_id()
        setattr(request.state, "request_id", rid)
        set_request_id(rid)
        start = __import__("time").time()
        status = 500
        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 200)
            # Propagate X-Request-Id on response
            try:
                response.headers["X-Request-Id"] = rid
            except Exception:
                pass
            return response
        except Exception as e:  # pragma: no cover
            raise
        finally:
            dur = (__import__("time").time() - start) * 1000.0
            # Route label (template if available)
            route_path = None
            try:
                route = request.scope.get("route")
                route_path = getattr(route, "path", None)
            except Exception:
                route_path = None
            path_label = route_path or request.url.path
            method = getattr(request, "method", "").upper() or "?"
            key_overall = "http_request"
            key_route = f"http_request:{method} {path_label}"

            metrics.inc("requests_total", 1)
            metrics.inc(f"requests_total:{method} {path_label}", 1)
            try:
                if int(status) >= 500:
                    metrics.inc("errors_total", 1)
                    metrics.inc(f"errors_total:{method} {path_label}", 1)
            except Exception:
                pass
            metrics.observe_duration(key_overall, dur)
            metrics.observe_duration(key_route, dur)
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "route": path_label,
                    "dur_ms": round(dur, 2),
                    "request_id": rid,
                    "status": status,
                },
            )
            # Clear context var
            set_request_id(None)

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

    # Background housekeeper (metrics-only currently). Metrics always-on per policy; env overrides supported.
    try:
        import os as _os
        from contextlib import asynccontextmanager
        hk_cfg = cfg.get("housekeeper", {}) or {}
        strategies = hk_cfg.get("strategies", {}) or {}
        default_strategy = hk_cfg.get("default_strategy", "balanced")
        active_name = _os.getenv("HOUSEKEEPER_STRATEGY", default_strategy)
        policy = strategies.get(active_name) or strategies.get(default_strategy) or {}
        metrics_always_on = bool(policy.get("metrics_always_on", True))
        # Env override retains backward compat
        if _os.getenv("HOUSEKEEPER_ENABLED") in ("0", "false", "off"):
            metrics_always_on = False
        interval_s = float(_os.getenv("HOUSEKEEPER_INTERVAL_S", str(policy.get("interval_s", 10))))
        disk_path = str((__import__("pathlib").Path(policy.get("ssd", {}).get("path", cfg.get("models_root", "."))).resolve()))
        app.state.housekeeper_strategy = active_name  # type: ignore[attr-defined]
        app.state.housekeeper_policy = policy  # type: ignore[attr-defined]
        if metrics_always_on:
            hk = Housekeeper(app, interval_s=interval_s, disk_path=disk_path)
            app.state._housekeeper = hk  # type: ignore[attr-defined]

        @asynccontextmanager
        async def _lifespan(_app):  # pragma: no cover
            # startup
            try:
                hk_obj = getattr(_app.state, "_housekeeper", None)
                if hk_obj:
                    hk_obj.start()
            except Exception:
                pass
            try:
                yield
            finally:
                try:
                    hk_obj = getattr(_app.state, "_housekeeper", None)
                    if hk_obj:
                        hk_obj.stop()
                except Exception:
                    pass

        try:
            app.router.lifespan_context = _lifespan  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass
    return app
