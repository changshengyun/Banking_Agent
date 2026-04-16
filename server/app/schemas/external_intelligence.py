from __future__ import annotations

from pydantic import BaseModel, Field


class ExternalIntelligenceHit(BaseModel):
    provider: str
    list_name: str
    risk_level: str
    summary: str
    detail: str
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0
    block_hint: bool = False


class ExternalIntelligenceReport(BaseModel):
    status: str
    screened_entity: str
    summary: str
    max_risk_level: str
    max_score: float = 0.0
    hits: list[ExternalIntelligenceHit] = Field(default_factory=list)
