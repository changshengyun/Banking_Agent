from __future__ import annotations

from pydantic import BaseModel


class RiskClassificationPayload(BaseModel):
    risk_category: str
    risk_level: str
    block_hint: bool
    matched_keywords: list[str]
    matched_scenarios: list[str]
    analysis: str
    follow_up_questions: list[str]
    suggested_reply_examples: list[str]
