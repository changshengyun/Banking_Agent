from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import api_router
from .config import settings
from .db import init_database
from .mcp_runtime import mount_mcp_servers
from .seed import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段：初始化数据库结构，写入演示数据，并挂载 MCP 服务。
    # 这些步骤统一放在 lifespan 中，确保应用每次启动时状态可用。
    init_database()
    seed_demo_data()
    app.state.mcp_status = mount_mcp_servers(app)
    yield


# FastAPI 应用主实例：聚合 REST API、MCP 挂载与全局中间件配置。
app = FastAPI(
    title="Banking AI Demo Backend",
    version="0.1.0",
    lifespan=lifespan,
    description="演示版银行 AI Agent 风控系统后端，包含 FastAPI 业务 API 与 MCP 工具挂载。",
)

# 开放 CORS 以便 Flutter/Web/本地调试环境跨域访问后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由（/api/v1/*）。
app.include_router(api_router)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, error: ValueError) -> JSONResponse:
    # 统一业务异常输出，前端可直接展示 detail。
    return JSONResponse(
        status_code=400,
        content={"detail": str(error)},
    )


@app.get("/")
def root() -> dict:
    # 健康检查与运行状态入口：用于快速确认服务、模型模式与 MCP 挂载状态。
    return {
        "name": "Banking AI Demo Backend",
        "environment": settings.app_env,
        "mock_llm": settings.mock_llm,
        "mcp_status": getattr(app.state, "mcp_status", {"bank": False, "outdoor": False}),
        "message": "服务已启动，可访问 /docs 查看 REST API，/mcp/* 查看 MCP 挂载入口。",
    }
