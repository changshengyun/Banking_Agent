from __future__ import annotations

from typing import Any

import pytest


def _assert_explain_pack_contract(body: dict[str, Any]) -> None:
    explain_pack = body["explain_pack"]
    assert set(explain_pack.keys()) == {
        "headline",
        "recommended_action",
        "score_breakdown",
        "nodes",
    }
    assert [node["id"] for node in explain_pack["nodes"]] == [
        "static",
        "behavior",
        "semantic",
        "external_intelligence",
        "decision",
    ]
    for node in explain_pack["nodes"]:
        assert set(node.keys()) == {
            "id",
            "title",
            "level",
            "summary",
            "detail",
            "score",
        }
        assert node["level"] in {"low", "medium", "high"}
        assert 0.0 <= float(node["score"]) <= 1.0


def _assert_external_intelligence_contract(body: dict[str, Any]) -> None:
    report = body["external_intelligence"]
    assert report["status"] in {"clear", "hit"}
    assert report["max_risk_level"] in {"low", "medium", "high"}
    assert 0.0 <= float(report["max_score"]) <= 1.0


def _assert_risk_classification_contract(
    body: dict[str, Any],
    *,
    expect_phrase_hits: bool | None = None,
) -> None:
    classification = body["risk_classification"]
    assert classification["risk_category"]
    assert classification["risk_level"] in {"low", "medium", "high"}
    assert isinstance(classification["block_hint"], bool)
    assert isinstance(classification["matched_keywords"], list)
    assert isinstance(classification["high_risk_phrase_hits"], list)
    assert classification["matched_scenarios"]
    assert isinstance(classification["follow_up_questions"], list)
    assert isinstance(classification["suggested_reply_examples"], list)
    assert classification["analysis"]
    if expect_phrase_hits is True:
        assert classification["high_risk_phrase_hits"]
    elif expect_phrase_hits is False:
        assert classification["high_risk_phrase_hits"] == []


def _assert_secondary_semantic_red_flags_contract(
    body: dict[str, Any],
    *,
    expect_non_empty: bool | None = None,
) -> None:
    assert "semantic_red_flags" in body
    assert isinstance(body["semantic_red_flags"], list)
    assert all(isinstance(item, str) for item in body["semantic_red_flags"])
    if expect_non_empty is True:
        assert body["semantic_red_flags"]
    elif expect_non_empty is False:
        assert body["semantic_red_flags"] == []


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
        _assert_risk_classification_contract(body)
        _assert_external_intelligence_contract(body)
        _assert_explain_pack_contract(body)


def test_precheck_negated_high_risk_terms_not_escalated() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    payload = _build_payload(
        payee_name="小b",
        amount=300,
        city="上海",
        semantic_summary="收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert body["decision"] == "pass"
        assert body["risk_level"] == "low"
        assert body["risk_classification"]["risk_category"] == "正常转账"
        assert body["risk_classification"]["high_risk_phrase_hits"] == []
        _assert_risk_classification_contract(body, expect_phrase_hits=False)
        _assert_external_intelligence_contract(body)
        _assert_explain_pack_contract(body)


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
                semantic_summary="请转到安全账户，并把验证码发给我。",
            ),
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "block"
        _assert_risk_classification_contract(
            precheck_body,
            expect_phrase_hits=True,
        )
        assert "转到安全账户" in precheck_body["risk_classification"]["high_risk_phrase_hits"]

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": precheck_body["confirmation_token"]},
        )
        assert confirm.status_code == 400
        assert "拦截" in confirm.json()["detail"]


def test_investment_fraud_classification() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    payload = _build_payload(
        payee_name="投资顾问甲",
        amount=6800,
        city="北京",
        semantic_summary="老师带单，稳赚不赔，今晚拉升，让我跟单转账。",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200
        body = response.json()

    assert body["decision"] == "block"
    assert body["risk_level"] == "high"
    _assert_risk_classification_contract(body, expect_phrase_hits=True)
    assert body["risk_classification"]["risk_category"] == "投资理财诈骗"
    assert body["risk_classification"]["risk_level"] == "high"
    assert "稳赚不赔" in body["risk_classification"]["high_risk_phrase_hits"]


def test_romance_scam_classification() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    payload = _build_payload(
        payee_name="网恋对象甲",
        amount=5200,
        city="西安",
        semantic_summary="网恋对象说转账后就来见你，让我先帮忙买机票。",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200
        body = response.json()

    assert body["decision"] == "block"
    assert body["risk_level"] == "high"
    _assert_risk_classification_contract(body, expect_phrase_hits=True)
    assert body["risk_classification"]["risk_category"] == "情感诈骗"
    assert body["risk_classification"]["risk_level"] == "high"
    assert "转账后就来见你" in body["risk_classification"]["high_risk_phrase_hits"]


def test_part_time_fraud_classification() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    payload = _build_payload(
        payee_name="兼职客服甲",
        amount=2600,
        city="北京",
        semantic_summary="兼职刷单先垫付后返现，再做一单就能提现。",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200
        body = response.json()

    assert body["decision"] == "block"
    assert body["risk_level"] == "high"
    _assert_risk_classification_contract(body, expect_phrase_hits=True)
    assert body["risk_classification"]["risk_category"] == "刷单兼职诈骗"
    assert body["risk_classification"]["risk_level"] == "high"
    assert "先垫付后返现" in body["risk_classification"]["high_risk_phrase_hits"]


def test_empty_semantic_summary_uses_contextual_fallback() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    payload = _build_payload(
        payee_name="陌生账户Z",
        amount=8000,
        city="北京",
        semantic_summary="",
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/transfers/precheck", json=payload)
        assert response.status_code == 200
        body = response.json()

    assert body["decision"] != "pass"
    assert body["risk_level"] != "low"
    _assert_risk_classification_contract(body, expect_phrase_hits=False)
    assert body["risk_classification"]["risk_category"] == "异地大额异常转账"
    assert body["risk_classification"]["risk_level"] == "medium"
    assert body["risk_classification"]["matched_keywords"]
    assert "异地" in body["risk_classification"]["matched_keywords"]


def test_secondary_check_police_reply_blocks_with_red_flags() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json=_build_payload(
                payee_name="小c",
                amount=8000,
                city="北京",
                semantic_summary="用户在异地发起大额转账。",
                input_pause_count=6,
                input_duration_ms=9000,
                extra_signals={"app_switch_count": 2},
            ),
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "警察让我转的，说现在就要打款。",
                "context": {
                    "session_id": "risk-scenario-secondary-police",
                    "device_id": "risk-test-device",
                    "platform": "pytest",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()

    assert body["secondary_decision"] == "block_secondary"
    assert body["final_risk_after_secondary"] >= 0.9
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=True)
    assert "司法机关要求转账" in body["semantic_red_flags"]
    assert "无法继续" in body["assistant_message"]


def test_secondary_check_refund_verification_blocks_with_red_flags() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json=_build_payload(
                payee_name="小c",
                amount=8000,
                city="北京",
                semantic_summary="用户在异地发起大额转账。",
                input_pause_count=6,
                input_duration_ms=9000,
                extra_signals={"app_switch_count": 2},
            ),
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "客服说验证资金后退款，还要我先刷流水。",
                "context": {
                    "session_id": "risk-scenario-secondary-refund",
                    "device_id": "risk-test-device",
                    "platform": "pytest",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()

    assert body["secondary_decision"] == "block_secondary"
    assert any("高风险语义" in reason for reason in body["reasons"])
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=True)
    assert "客服要求验证资金" in body["semantic_red_flags"]


def test_secondary_check_irrelevant_reply_stays_in_interrogate() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json=_build_payload(
                payee_name="小d",
                amount=6000,
                city="西安",
                semantic_summary="对方说临时借钱让我马上转。",
            ),
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "我就是想转账。",
                "context": {
                    "session_id": "risk-scenario-secondary-irrelevant",
                    "device_id": "risk-test-device",
                    "platform": "pytest",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()

    assert body["secondary_decision"] == "interrogate"
    assert body["secondary_decision"] != "pass_secondary"
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=False)
    assert any("关键核验点" in reason or "直接相关" in reason for reason in body["reasons"])
