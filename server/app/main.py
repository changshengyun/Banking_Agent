from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import api_router
from .config import settings
from .db import init_database
from .errors import NotFoundError
from .mcp_runtime import mount_mcp_servers
from .seed import seed_demo_data
from .services.embedding_service import get_embedding_service
from .services.risk_knowledge_base import get_risk_knowledge_base_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    seed_demo_data()
    try:
        get_embedding_service().prewarm()
        get_risk_knowledge_base_service().prewarm()
    except Exception as error:
        logging.warning("Startup prewarm skipped: %s", error)
    app.state.mcp_status = mount_mcp_servers(app)
    yield


app = FastAPI(
    title="Banking AI Demo Backend",
    version="0.1.0",
    lifespan=lifespan,
    description="演示版银行 AI Agent 风控系统后端，包含 FastAPI 业务 API 与 MCP 工具挂载。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(NotFoundError)
async def not_found_error_handler(_: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": str(error)},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, error: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(error)},
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "Banking AI Demo Backend",
        "environment": settings.app_env,
        "mcp_status": getattr(app.state, "mcp_status", {"bank": False}),
        "message": "服务已启动，可访问 /docs 查看 REST API，/mcp/bank 查看 MCP 挂载入口。",
    }
