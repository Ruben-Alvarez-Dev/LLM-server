from __future__ import annotations

import os
from typing import Optional


def require_tenant(tenant_header: Optional[str]) -> str:
    mode = os.getenv("TENANCY_MODE", "single").lower()
    if mode == "multi":
        if not tenant_header:
            raise ValueError("missing X-Tenant-Id header in multi-tenant mode")
        return tenant_header
    return os.getenv("DEFAULT_TENANT_ID", "main")

