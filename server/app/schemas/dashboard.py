from __future__ import annotations

from pydantic import BaseModel

from .common import SpendingCategory, TransactionItem


class DashboardResponse(BaseModel):
    user_name: str
    cash_balance: float
    wealth_balance: float
    total_assets: float
    currency: str
    recent_transactions: list[TransactionItem]
    spending_summary: list[SpendingCategory]
    demo_tip: str


class TransactionsResponse(BaseModel):
    items: list[TransactionItem]
    spending_summary: list[SpendingCategory]

