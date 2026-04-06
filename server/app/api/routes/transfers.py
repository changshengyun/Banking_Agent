from __future__ import annotations

from fastapi import APIRouter

from ...schemas.transfer import (
    TransferConfirmRequest,
    TransferConfirmResponse,
    TransferPrecheckRequest,
    TransferPrecheckResponse,
    TransferSecondaryCheckRequest,
    TransferSecondaryCheckResponse,
)
from ...services.bank_host import get_bank_host_service


router = APIRouter(tags=["transfers"])


@router.post("/transfers/precheck", response_model=TransferPrecheckResponse)
def precheck_transfer(
    payload: TransferPrecheckRequest,
) -> TransferPrecheckResponse:
    return get_bank_host_service().precheck_transfer(payload)


@router.post("/transfers/confirm", response_model=TransferConfirmResponse)
def confirm_transfer(
    payload: TransferConfirmRequest,
) -> TransferConfirmResponse:
    return get_bank_host_service().confirm_transfer(payload)


@router.post("/transfers/secondary-check", response_model=TransferSecondaryCheckResponse)
def secondary_check_transfer(
    payload: TransferSecondaryCheckRequest,
) -> TransferSecondaryCheckResponse:
    return get_bank_host_service().secondary_check_transfer(payload)
