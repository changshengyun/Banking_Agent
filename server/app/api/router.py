from __future__ import annotations

from fastapi import APIRouter

from .routes import agent, dashboard, transfers


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(dashboard.router)
api_router.include_router(transfers.router)
api_router.include_router(agent.router)

