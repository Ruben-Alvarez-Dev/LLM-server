from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "on", "yes")


class MemoryClient:
    """Client for Memory-server with graceful stub fallback.

    If FEATURE_MEMORY=1 and remote is reachable, uses HTTP calls; otherwise
    falls back to local stub that returns empty results.
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, enabled: Optional[bool] = None) -> None:
        self.host = host or os.getenv("MEMORY_HOST", "localhost")
        try:
            self.port = int(port if port is not None else os.getenv("MEMORY_PORT", "8082"))
        except Exception:
            self.port = 8082
        self.enabled = bool(enabled) if enabled is not None else _env_bool("FEATURE_MEMORY", False)

    def _remote_url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def is_ready(self, timeout: float = 0.5) -> bool:
        if not self.enabled:
            return False
        # Try a lightweight readiness/health probe; accept any 200 JSON
        for p in ("/v1/ready", "/readyz", "/healthz", "/"):
            try:
                req = urllib.request.Request(self._remote_url(p))
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except Exception:
                continue
        return False

    def search(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Try remote first when enabled and ready
        if self.is_enabled() and self.is_ready():
            try:
                payload = json.dumps({"query": query, "k": int(k), "filters": filters or {}, "request_id": request_id}).encode("utf-8")
                req = urllib.request.Request(self._remote_url("/v1/search"), data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    text = resp.read().decode("utf-8", errors="ignore")
                    data = json.loads(text)
                    results = data.get("results") or data.get("data") or []
                    if isinstance(results, list):
                        return results  # trust remote schema
            except Exception:
                # fall through to stub
                pass

        # Stub fallback: return empty but well-formed list
        return []
