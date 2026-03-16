from __future__ import annotations

from pydantic import BaseModel, Field

from .common import ClientContext, SuggestedAction, ToolUsage


class ChatMessageInput(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessageInput]
    context: ClientContext


class ChatResponse(BaseModel):
    assistant_message: str
    used_tools: list[ToolUsage]
    suggested_actions: list[SuggestedAction]

