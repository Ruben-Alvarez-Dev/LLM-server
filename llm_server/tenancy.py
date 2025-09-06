from __future__ import annotations

import os
from typing import Optional


def require_tenant(tenant_header: Optional[str]) -> str:
    """
    Multi-tenant is disabled for this release.
    Always returns a single logical tenant id.
    Header X-Tenant-Id is accepted but ignored.
    """
    # Note: kept envs for future versions but ignored purposely
    return os.getenv("DEFAULT_TENANT_ID", "main")
