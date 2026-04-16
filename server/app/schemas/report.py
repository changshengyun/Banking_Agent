from __future__ import annotations

from pydantic import BaseModel, Field


class RiskReportGovernancePayload(BaseModel):
    report_version: str
    policy_version: str
    generation_mode: str
    source_stage: str
    secondary_decision: str
    risk_category: str
    external_intelligence_level: str
    trace_events: list[str] = Field(default_factory=list)


class RiskReportPayload(BaseModel):
    confirmation_token: str
    headline: str
    overall_risk_level: str
    risk_summary: str
    risk_factors: list[str] = Field(default_factory=list)
    recommended_action: str
    evidence: list[str] = Field(default_factory=list)
    governance: RiskReportGovernancePayload
    generated_at: str


class RiskReportListItemPayload(BaseModel):
    confirmation_token: str
    headline: str
    overall_risk_level: str
    risk_summary: str
    risk_category: str
    policy_version: str
    generation_mode: str
    generated_at: str


class RiskReportListResponsePayload(BaseModel):
    items: list[RiskReportListItemPayload] = Field(default_factory=list)
