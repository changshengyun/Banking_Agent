from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ClientContext(BaseModel):
    session_id: str = Field(default="session-demo")
    device_id: str = Field(default="android-demo-001")
    platform: str = Field(default="android")
    current_city: str = Field(default="Shanghai")
    lat: float = Field(default=31.2304)
    lng: float = Field(default=121.4737)
    recent_page: str = Field(default="home")
    last_action: str = Field(default="open_home")
    semantic_summary: str = Field(
        default="User is browsing home page and preparing a transfer."
    )
    input_pause_count: Optional[int] = Field(default=None, ge=0)
    input_duration_ms: Optional[int] = Field(default=None, ge=0)
    extra_signals: Optional[dict[str, Any]] = Field(default=None)


class TransactionItem(BaseModel):
    id: str
    title: str
    subtitle: str
    amount: float
    is_income: bool
    category: str
    city: str
    created_at: str
    status: str


class SpendingCategory(BaseModel):
    category: str
    total_amount: float


class ToolUsage(BaseModel):
    name: str
    summary: str


class SuggestedAction(BaseModel):
    label: str
    action: str


DecisionType = Literal["pass", "interrogate", "block"]

