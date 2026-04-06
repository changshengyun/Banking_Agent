from __future__ import annotations

from pydantic import BaseModel, Field

from .common import ClientContext, DecisionType, TransactionItem
from .external_intelligence import ExternalIntelligenceReport
from .risk import RiskClassificationPayload


class TransferPrecheckRequest(BaseModel):
    payee_name: str = Field(min_length=1, max_length=40)
    amount: float = Field(gt=0)
    context: ClientContext


class ExplainScoreBreakdown(BaseModel):
    flag_s: float
    g_behavior: float
    g_dynamic: float
    final_risk: float


class ExplainNode(BaseModel):
    id: str
    title: str
    level: str
    summary: str
    detail: str
    score: float


class ExplainPack(BaseModel):
    headline: str
    recommended_action: str
    score_breakdown: ExplainScoreBreakdown
    nodes: list[ExplainNode]


class TransferPrecheckResponse(BaseModel):
    decision: DecisionType
    risk_level: str
    flag_s: float
    g_behavior: float
    g_dynamic: float
    final_risk: float
    reasons: list[str]
    confirmation_token: str
    assistant_message: str
    risk_classification: RiskClassificationPayload
    external_intelligence: ExternalIntelligenceReport
    explain_pack: ExplainPack


class TransferConfirmRequest(BaseModel):
    confirmation_token: str


class TransferConfirmResponse(BaseModel):
    success: bool
    assistant_message: str
    cash_balance: float
    wealth_balance: float
    total_assets: float
    latest_transaction: TransactionItem


class TransferSecondaryCheckRequest(BaseModel):
    confirmation_token: str
    user_reply: str = Field(min_length=1, max_length=500)
    context: ClientContext


class TransferSecondaryCheckResponse(BaseModel):
    secondary_decision: str
    reasons: list[str]
    final_risk_after_secondary: float
    assistant_message: str
    semantic_red_flags: list[str] = Field(default_factory=list)
    risk_classification: RiskClassificationPayload
    external_intelligence: ExternalIntelligenceReport
    explain_pack: ExplainPack
