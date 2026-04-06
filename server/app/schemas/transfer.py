from __future__ import annotations

from pydantic import BaseModel, Field

from .common import ClientContext, DecisionType, TransactionItem


class TransferPrecheckRequest(BaseModel):
    payee_name: str = Field(min_length=1, max_length=40)
    amount: float = Field(gt=0)
    context: ClientContext


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
