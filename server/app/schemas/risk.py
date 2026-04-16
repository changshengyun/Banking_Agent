from __future__ import annotations

from pydantic import BaseModel, Field


class RiskClassificationPayload(BaseModel):
    risk_category: str
    risk_level: str
    block_hint: bool
    matched_keywords: list[str]
    high_risk_phrase_hits: list[str] = Field(default_factory=list)
    matched_scenarios: list[str]
    analysis: str
    follow_up_questions: list[str]
    suggested_reply_examples: list[str]
