from __future__ import annotations

from fastapi import FastAPI

from .config import settings

try:
    from mcp_servers.bank_server import bank_mcp
except Exception:
    bank_mcp = None


def mount_mcp_servers(app: FastAPI) -> dict[str, bool]:
    status = {"bank": False}

    if settings.mcp_bank_enabled and bank_mcp is not None:
        app.mount("/mcp/bank", bank_mcp.streamable_http_app())
        status["bank"] = True

    return status
