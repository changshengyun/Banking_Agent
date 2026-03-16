from __future__ import annotations

from fastapi import APIRouter

from ...schemas.chat import ChatRequest, ChatResponse
from ...services.agent_service import get_agent_service


router = APIRouter(tags=["agent"])


@router.post("/agent/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    return await get_agent_service().chat(payload)

