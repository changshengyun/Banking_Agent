from __future__ import annotations

from fastapi import FastAPI

from .config import settings

try:
    from mcp_servers.bank_server import bank_mcp
    from mcp_servers.outdoor_server import outdoor_mcp
except Exception:
    bank_mcp = None
    outdoor_mcp = None


def mount_mcp_servers(app: FastAPI) -> dict[str, bool]:
    status = {"bank": False, "outdoor": False}

    if settings.mcp_bank_enabled and bank_mcp is not None:
        app.mount("/mcp/bank", bank_mcp.streamable_http_app())
        status["bank"] = True

    if settings.mcp_outdoor_enabled and outdoor_mcp is not None:
        app.mount("/mcp/outdoor", outdoor_mcp.streamable_http_app())
        status["outdoor"] = True

    return status

