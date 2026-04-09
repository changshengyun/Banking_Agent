from __future__ import annotations

from pydantic import BaseModel, Field


class RiskReportPayload(BaseModel):
    confirmation_token: str
    headline: str
    overall_risk_level: str
    risk_summary: str
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: str
    evidence: list[str] = Field(default_factory=list)
    generated_at: str
