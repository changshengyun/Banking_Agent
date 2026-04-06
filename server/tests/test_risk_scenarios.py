from __future__ import annotations

from typing import Any

import pytest


def _build_payload(
    *,
    payee_name: str,
    amount: float,
    city: str,
    semantic_summary: str,
    recent_page: str = "home",
    last_action: str = "tap_transfer",
    input_pause_count: int | None = None,
    input_duration_ms: int | None = None,
    extra_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    coordinates = {
        "上海": (31.2304, 121.4737),
        "北京": (39.9042, 116.4074),
        "西安": (34.3416, 108.9398),
    }
    lat, lng = coordinates.get(city, (31.2304, 121.4737))
    context: dict[str, Any] = {
        "session_id": "risk-scenario-test",
        "device_id": "risk-test-device",
        "platform": "pytest",
        "current_city": city,
        "lat": lat,
        "lng": lng,
        "recent_page": recent_page,
        "last_action": last_action,
        "semantic_summary": semantic_summary,
    }
    if input_pause_count is not None:
        context["input_pause_count"] = input_pause_count
    if input_duration_ms is not None:
        context["input_duration_ms"] = input_duration_ms
    if extra_signals:
        context["extra_signals"] = extra_signals

    return {
        "payee_name": payee_name,
        "amount": amount,
        "context": context,
    }


@pytest.mark.parametrize(
    ("payload", "expected_decision", "expected_risk_level"),
    [
        pytest.param(
            _build_payload(
                payee_name="小b",
                amount=300,
                city="上海",
                semantic_summary="日常生活转账。",
            ),
            "pass",
            "low",
            id="pass_low_known_payee",
        ),
        pytest.param(
            _build_payload(
                payee_name="小c",
                amount=8000,
                city="北京",
                semantic_summary="普通转账需求。",
            ),
            "interrogate",
            "medium",
            id="interrogate_medium_static",
        ),
        pytest.param(
            _build_payload(
                payee_name="小d",
                amount=6000,
                city="西安",
                semantic_summary="对方说临时借钱让我马上转。",
            ),
            "interrogate",
            "medium",
            id="interrogate_medium_semantic",
        ),
        pytest.param(
            _build_payload(
                payee_name="小e",
                amount=2000,
                city="上海",
                semantic_summary="对方要求转到safe account并提供verification code。",
            ),
            "block",
            "high",
            id="block_high_hard_keyword",
        ),
        pytest.param(
            _build_payload(
                payee_name="小f",
                amount=20000,
                city="北京",
                semantic_summary="这是临时退款，请马上处理。",
                recent_page="message",
                last_action="copy_paste",
                input_pause_count=8,
                input_duration_ms=900,
                extra_signals={
                    "paste_count": 1,
                    "app_switch_count": 2,
                },
            ),
            "block",
            "high",
            id="block_high_weighted_score",
        ),
    ],
)
def test_precheck_by_risk_scenarios(
    payload: dict[str, Any],
    expected_decision: str,
    expected_risk_level: str,
) -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["decision"] == expected_decision
        assert body["risk_level"] == expected_risk_level
        assert body["confirmation_token"]
        for key in ("flag_s", "g_behavior", "g_dynamic", "final_risk"):
            assert key in body
            assert 0.0 <= float(body[key]) <= 1.0
        assert body["risk_classification"]["risk_category"]
        assert body["risk_classification"]["matched_scenarios"]


def test_block_transfer_cannot_be_confirmed() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json=_build_payload(
                payee_name="小f",
                amount=3000,
                city="西安",
                semantic_summary="请转到safe account并把verification code告诉我。",
            ),
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "block"

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": precheck_body["confirmation_token"]},
        )
        assert confirm.status_code == 400
        assert "拦截" in confirm.json()["detail"]
