from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi import Query

from ...schemas.manual_review import ManualReviewDetailPayload
from ...schemas.manual_review import ManualReviewListResponsePayload
from ...schemas.manual_review import ManualReviewQueueResponsePayload
from ...schemas.manual_review import ManualReviewUpdateRequest
from ...services.bank_host import get_bank_host_service


router = APIRouter(tags=["manual-reviews"])


@router.get(
    "/manual-reviews",
    response_model=ManualReviewListResponsePayload,
)
def list_manual_reviews(
    status: Literal["all", "submitted", "in_review", "closed"] = Query(default="all"),
) -> ManualReviewListResponsePayload:
    return get_bank_host_service().list_manual_reviews(limit=20, status=status)


@router.get(
    "/manual-reviews/queue",
    response_model=ManualReviewQueueResponsePayload,
)
def list_manual_review_queue() -> ManualReviewQueueResponsePayload:
    return get_bank_host_service().list_manual_review_queue()


@router.get(
    "/manual-reviews/{review_id}",
    response_model=ManualReviewDetailPayload,
)
def get_manual_review(review_id: str) -> ManualReviewDetailPayload:
    return get_bank_host_service().get_manual_review(review_id)


@router.patch(
    "/manual-reviews/{review_id}",
    response_model=ManualReviewDetailPayload,
)
def update_manual_review(
    review_id: str,
    payload: ManualReviewUpdateRequest,
) -> ManualReviewDetailPayload:
    return get_bank_host_service().update_manual_review(
        review_id=review_id,
        payload=payload,
    )
