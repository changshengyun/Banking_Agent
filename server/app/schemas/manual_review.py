from __future__ import annotations

from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator

from .report import RiskReportGovernancePayload

# Type definitions for manual review states
ManualReviewStatus = Literal["submitted", "in_review", "closed"]
ManualReviewOutcome = Literal["upheld", "advisory"]


class ManualReviewCreateRequest(BaseModel):
    request_reason: str = Field(min_length=10, max_length=300)


class ManualReviewUpdateRequest(BaseModel):
    status: ManualReviewStatus
    outcome: Optional[ManualReviewOutcome] = None
    review_note: Optional[str] = Field(default=None, max_length=500)
    reviewer_id: Optional[str] = Field(default=None, min_length=1, max_length=100)


class ManualReviewSnapshotPayload(BaseModel):
    headline: str
    overall_risk_level: str
    risk_summary: str
    risk_category: str
    policy_version: str
    generation_mode: str
    generated_at: str
    evidence: list[str] = Field(default_factory=list)
    governance: RiskReportGovernancePayload


class ManualReviewSummaryPayload(BaseModel):
    review_id: str
    confirmation_token: str
    status: ManualReviewStatus
    outcome: Optional[ManualReviewOutcome] = None
    request_reason: str
    headline: str
    overall_risk_level: str
    submitted_at: str
    updated_at: str
    closed_at: Optional[str] = None


class ManualReviewDetailPayload(ManualReviewSummaryPayload):
    in_review_at: Optional[str] = None
    review_note: Optional[str] = None
    reviewer_id: Optional[str] = None
    request_snapshot: ManualReviewSnapshotPayload


class ManualReviewQueueItemPayload(ManualReviewSummaryPayload):
    user_id: str


class ManualReviewListResponsePayload(BaseModel):
    items: list[ManualReviewSummaryPayload] = Field(default_factory=list)


class ManualReviewQueueResponsePayload(BaseModel):
    items: list[ManualReviewQueueItemPayload] = Field(default_factory=list)
