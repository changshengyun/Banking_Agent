from __future__ import annotations

from fastapi import APIRouter

from ...schemas.dashboard import DashboardResponse, TransactionsResponse
from ...services.bank_host import get_bank_host_service


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard() -> DashboardResponse:
    return get_bank_host_service().get_dashboard()


@router.get("/transactions", response_model=TransactionsResponse)
def get_transactions(limit: int = 20) -> TransactionsResponse:
    return get_bank_host_service().list_transactions(limit=limit)

