from __future__ import annotations

from fastapi import APIRouter

from ...schemas.risk import RiskClassificationPayload
from ...schemas.transfer import (
    TransferCancelRequest,
    TransferCancelResponse,
    TransferConfirmRequest,
    TransferConfirmResponse,
    TransferPrecheckRequest,
    TransferPrecheckResponse,
    TransferSecondaryCheckRequest,
    TransferSecondaryCheckResponse,
)
from ...services.bank_host import get_bank_host_service


router = APIRouter(tags=["transfers"])


@router.post("/transfers/classify-risk", response_model=RiskClassificationPayload)
def classify_transfer_risk(
    payload: TransferPrecheckRequest,
) -> RiskClassificationPayload:
    return get_bank_host_service().classify_transfer_risk(payload)


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


@router.post("/transfers/cancel", response_model=TransferCancelResponse)
def cancel_transfer(
    payload: TransferCancelRequest,
) -> TransferCancelResponse:
    return get_bank_host_service().cancel_transfer(payload)


@router.post("/transfers/secondary-check", response_model=TransferSecondaryCheckResponse)
def secondary_check_transfer(
    payload: TransferSecondaryCheckRequest,
) -> TransferSecondaryCheckResponse:
    return get_bank_host_service().secondary_check_transfer(payload)
