from __future__ import annotations

CUSTOMER_SERVICE_FRAUD_CATEGORY = "客服退款诈骗"
SAFE_ACCOUNT_FRAUD_CATEGORY = "安全账户诈骗"
REMOTE_LARGE_TRANSFER_CATEGORY = "异地大额异常转账"


def _assert_risk_classification_contract(
    classification: dict,
    *,
    expect_phrase_hits: bool | None = None,
) -> None:
    assert set(classification.keys()) == {
        "risk_category",
        "risk_level",
        "block_hint",
        "matched_keywords",
        "high_risk_phrase_hits",
        "matched_scenarios",
        "analysis",
        "follow_up_questions",
        "suggested_reply_examples",
    }
    assert classification["risk_category"]
    assert classification["risk_level"] in {"low", "medium", "high"}
    assert isinstance(classification["block_hint"], bool)
    assert classification["analysis"]
    for key in (
        "matched_keywords",
        "high_risk_phrase_hits",
        "matched_scenarios",
        "follow_up_questions",
        "suggested_reply_examples",
    ):
        assert isinstance(classification[key], list)
        assert all(isinstance(item, str) for item in classification[key])
    if expect_phrase_hits is True:
        assert classification["high_risk_phrase_hits"]
    elif expect_phrase_hits is False:
        assert classification["high_risk_phrase_hits"] == []


def _assert_secondary_semantic_red_flags_contract(
    body: dict,
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


def _assert_explain_pack_contract(body: dict) -> None:
    assert "explain_pack" in body
    explain_pack = body["explain_pack"]
    assert set(explain_pack.keys()) == {
        "headline",
        "recommended_action",
        "score_breakdown",
        "nodes",
    }
    assert explain_pack["headline"]
    assert explain_pack["recommended_action"]

    score_breakdown = explain_pack["score_breakdown"]
    assert set(score_breakdown.keys()) == {
        "flag_s",
        "g_behavior",
        "g_dynamic",
        "final_risk",
    }
    for value in score_breakdown.values():
        assert 0.0 <= float(value) <= 1.0

    nodes = explain_pack["nodes"]
    assert len(nodes) == 5
    assert [node["id"] for node in nodes] == [
        "static",
        "behavior",
        "semantic",
        "external_intelligence",
        "decision",
    ]
    for node in nodes:
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


def _assert_external_intelligence_contract(body: dict) -> None:
    assert "external_intelligence" in body
    external = body["external_intelligence"]
    assert set(external.keys()) == {
        "status",
        "screened_entity",
        "summary",
        "max_risk_level",
        "max_score",
        "hits",
    }
    assert external["status"] in {"clear", "hit"}
    assert external["max_risk_level"] in {"low", "medium", "high"}
    assert 0.0 <= float(external["max_score"]) <= 1.0
    for hit in external["hits"]:
        assert set(hit.keys()) == {
            "provider",
            "list_name",
            "risk_level",
            "summary",
            "detail",
            "tags",
            "score",
            "block_hint",
        }
        assert hit["risk_level"] in {"low", "medium", "high"}
        assert 0.0 <= float(hit["score"]) <= 1.0
        assert isinstance(hit["block_hint"], bool)


def test_dashboard_endpoint() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["cash_balance"] >= 0
        assert len(body["recent_transactions"]) >= 1


def test_transfer_precheck_mvp_flow() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-test",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 6,
                    "input_duration_ms": 9000,
                    "extra_signals": {"app_switch_count": 2},
                },
            },
        )
        assert precheck.status_code == 200
        body = precheck.json()

        assert body["decision"] in {"pass", "interrogate", "block"}
        assert body["confirmation_token"]
        for key in ("flag_s", "g_behavior", "g_dynamic", "final_risk"):
            assert key in body
            assert 0.0 <= float(body[key]) <= 1.0
        _assert_risk_classification_contract(body["risk_classification"])
        _assert_external_intelligence_contract(body)
        _assert_explain_pack_contract(body)


def test_classify_risk_endpoint() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/classify-risk",
            json={
                "payee_name": "陌生客服",
                "amount": 8000,
                "context": {
                    "session_id": "session-classify",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "对方说自己是客服，要我关闭百万保障并转账验证。",
                },
            },
        )
        assert response.status_code == 200
        body = response.json()
        _assert_risk_classification_contract(body, expect_phrase_hits=False)
        assert body["risk_category"] == CUSTOMER_SERVICE_FRAUD_CATEGORY
        assert body["risk_level"] == "high"
        assert any(keyword for keyword in body["matched_keywords"])


def test_classify_risk_returns_high_risk_phrase_hits_for_phrase_only_input() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/classify-risk",
            json={
                "payee_name": "陌生账户A",
                "amount": 3000,
                "context": {
                    "session_id": "session-phrase-only",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "message",
                    "last_action": "copy_paste",
                    "semantic_summary": "对方让我转到安全账户，资金清查完成后返还。",
                },
            },
        )
        assert response.status_code == 200
        body = response.json()
        _assert_risk_classification_contract(body, expect_phrase_hits=True)
        assert body["risk_category"] == SAFE_ACCOUNT_FRAUD_CATEGORY
        assert body["risk_level"] == "high"
        assert "转到安全账户" in body["high_risk_phrase_hits"]
        assert body["block_hint"] is True


def test_classify_risk_negated_high_risk_terms_do_not_create_phrase_hits() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/classify-risk",
            json={
                "payee_name": "朋友小a",
                "amount": 1200,
                "context": {
                    "session_id": "session-negated-high-risk-terms",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": (
                        "收款人是我朋友，这次是还款，"
                        "不涉及验证码、安全账户或屏幕共享。"
                    ),
                },
            },
        )
        assert response.status_code == 200
        body = response.json()

    _assert_risk_classification_contract(body, expect_phrase_hits=False)
    assert body["risk_category"] == "正常转账"
    assert body["high_risk_phrase_hits"] == []
    assert "验证码" not in body["matched_keywords"]
    assert "安全账户" not in body["matched_keywords"]
    assert "屏幕共享" not in body["matched_keywords"]


def test_classify_risk_uses_contextual_fallback_for_empty_summary() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/classify-risk",
            json={
                "payee_name": "陌生账户B",
                "amount": 8000,
                "context": {
                    "session_id": "session-empty-summary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "",
                },
            },
        )
        assert response.status_code == 200
        body = response.json()
        _assert_risk_classification_contract(body, expect_phrase_hits=False)
        assert body["risk_category"] == REMOTE_LARGE_TRANSFER_CATEGORY
        assert body["risk_level"] == "medium"
        assert body["matched_keywords"]
        assert body["matched_scenarios"]


def test_precheck_returns_external_intelligence_report() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小e",
                "amount": 300,
                "context": {
                    "session_id": "session-external-hit",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "正常生活转账。",
                },
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["decision"] == "block"
        _assert_risk_classification_contract(body["risk_classification"])
        _assert_external_intelligence_contract(body)
        assert body["external_intelligence"]["status"] == "hit"
        assert body["external_intelligence"]["max_risk_level"] == "high"
        assert body["explain_pack"]["nodes"][3]["id"] == "external_intelligence"
        assert body["explain_pack"]["nodes"][3]["level"] == "high"


def test_block_cannot_confirm() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小e",
                "amount": 20000,
                "context": {
                    "session_id": "session-test",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "message",
                    "last_action": "copy_paste",
                    "semantic_summary": "请立刻转到安全账户，并把验证码发给我。",
                },
            },
        )
        assert precheck.status_code == 200
        body = precheck.json()
        assert body["decision"] == "block"
        _assert_risk_classification_contract(
            body["risk_classification"],
            expect_phrase_hits=True,
        )
        assert "转到安全账户" in body["risk_classification"]["high_risk_phrase_hits"]
        _assert_external_intelligence_contract(body)

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": body["confirmation_token"]},
        )
        assert confirm.status_code == 400


def test_secondary_check_returns_explain_pack_on_pass_path() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小b",
                "amount": 200,
                "context": {
                    "session_id": "session-secondary-pass",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "日常还款转账。",
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "pass"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "收款人是小b，日常还款。",
                "context": {
                    "session_id": "session-secondary-pass",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户主动补充说明。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()
        assert body["secondary_decision"] == "pass_secondary"
        _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=False)
        _assert_risk_classification_contract(
            body["risk_classification"],
            expect_phrase_hits=False,
        )
        _assert_external_intelligence_contract(body)
        _assert_explain_pack_contract(body)
        assert body["explain_pack"]["recommended_action"] == "可继续确认转账"


def test_secondary_check_returns_explain_pack_on_block_path(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.agent_service import get_agent_service

    def fake_secondary_check(**kwargs):
        from server.app.services.agent_service import SecondaryResult
        return SecondaryResult(
            decision="block_secondary",
            risk=0.92,
            reasons=["命中高危关键词", "用户说明与风险场景不一致"],
            assistant_message="二次校验未通过，请停止转账。",
            semantic_red_flags=["安全账户/资金清查"],
        )

    monkeypatch.setattr(
        get_agent_service(),
        "evaluate_secondary_intercept",
        fake_secondary_check,
    )

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-secondary-block",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 6,
                    "input_duration_ms": 9000,
                    "extra_signals": {"app_switch_count": 2},
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "对方让我把钱转到安全账户，并把验证码发给他。",
                "context": {
                    "session_id": "session-secondary-block",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交高风险补充说明。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()
        assert body["secondary_decision"] == "block_secondary"
        _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=True)
        _assert_risk_classification_contract(
            body["risk_classification"],
            expect_phrase_hits=True,
        )
        assert "转到安全账户" in body["risk_classification"]["high_risk_phrase_hits"]
        _assert_external_intelligence_contract(body)
        _assert_explain_pack_contract(body)


def test_secondary_check_persists_dynamic_follow_up_question(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.agent_service import get_agent_service
    from server.app.services.bank_host import get_bank_host_service

    captured: dict = {}

    def fake_secondary_check(**kwargs):
        from server.app.services.agent_service import SecondaryResult
        captured.update(kwargs)
        return SecondaryResult(
            decision="pass_secondary",
            risk=0.36,
            reasons=["用户说明覆盖了当前核验点"],
            assistant_message="二次校验通过，可继续转账。",
            semantic_red_flags=[],
        )

    monkeypatch.setattr(
        get_agent_service(),
        "evaluate_secondary_intercept",
        fake_secondary_check,
    )

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-dynamic-question",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 5,
                    "input_duration_ms": 8000,
                    "extra_signals": {"app_switch_count": 1},
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "收款人是同事，本次转账用于酒店押金。",
                "context": {
                    "session_id": "session-dynamic-question",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户补充了关系和用途。",
                },
            },
        )
        assert secondary.status_code == 200
        body = secondary.json()

    pending = get_bank_host_service().repository.get_pending_transfer(
        precheck_body["confirmation_token"]
    )
    assert pending["secondary_question"] == precheck_body["risk_classification"]["follow_up_questions"][0]
    assert captured["matched_scenarios"] == precheck_body["risk_classification"]["matched_scenarios"]
    assert captured["follow_up_questions"] == precheck_body["risk_classification"]["follow_up_questions"]
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=False)


class _FakeLlmGateway:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    def generate_json_sync(self, *, system_prompt: str, user_prompt: str, temperature: float):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return {
            "secondary_decision": "block_secondary",
            "final_risk_after_secondary": 0.91,
            "reasons": ["需要继续核验"],
            "assistant_message": "二次校验未通过。",
        }


class _FailingLlmGateway:
    def generate_json_sync(self, *, system_prompt: str, user_prompt: str, temperature: float):
        raise ValueError("在线模型调用失败")


def test_secondary_intercept_prompt_includes_police_verification_points() -> None:
    from server.app.services.agent_service import AgentService

    fake_gateway = _FakeLlmGateway()
    service = AgentService(llm_gateway=fake_gateway)

    result = service.evaluate_secondary_intercept(
        user_reply="对方说自己是公安，让我配合处理。",
        semantic_summary="对方自称公安，要求我配合线上做笔录。",
        risk_category="冒充公检法",
        risk_level="high",
        matched_keywords=["公安", "线上做笔录"],
        matched_scenarios=["冒充公安检法办案"],
        follow_up_questions=["你是否通过官方公开电话核实过对方身份和案号？"],
    )

    assert result.decision == "block_secondary"
    assert 0.0 <= result.risk <= 1.0
    assert result.reasons
    assert result.assistant_message
    assert result.semantic_red_flags == []
    assert "官方电话核实案号或身份" in fake_gateway.user_prompt
    assert "是否被要求转账核验资金" in fake_gateway.user_prompt
    assert "冒充公安检法办案" in fake_gateway.user_prompt
    assert "你是否通过官方公开电话核实过对方身份和案号？" in fake_gateway.user_prompt


def test_secondary_intercept_negation_reply_does_not_trigger_red_flags() -> None:
    from server.app.services.agent_service import AgentService

    service = AgentService(llm_gateway=_FailingLlmGateway())
    result = service.evaluate_secondary_intercept(
        user_reply="收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。",
        semantic_summary="用户补充解释。",
        risk_category="异地大额异常转账",
        risk_level="medium",
        matched_keywords=["异地", "大额"],
        matched_scenarios=["异地大额转账风险"],
        follow_up_questions=["请说明你与收款人的关系。", "请说明本次转账用途。"],
    )

    assert result.decision == "pass_secondary"
    assert result.semantic_red_flags == []
    assert result.risk < 0.3


def test_secondary_intercept_same_sentence_negation_conflict_is_not_flagged() -> None:
    from server.app.services.agent_service import AgentService

    service = AgentService(llm_gateway=_FailingLlmGateway())
    result = service.evaluate_secondary_intercept(
        user_reply=(
            "收款人是我同事，这次是还款，"
            "不涉及验证码但只是提醒不要泄露验证码，不涉及安全账户或屏幕共享。"
        ),
        semantic_summary="用户补充解释。",
        risk_category="异地大额异常转账",
        risk_level="medium",
        matched_keywords=["异地", "大额"],
        matched_scenarios=["异地大额转账风险"],
        follow_up_questions=["请说明你与收款人的关系。", "请说明本次转账用途。"],
    )

    assert result.decision == "pass_secondary"
    assert result.semantic_red_flags == []
    assert result.risk < 0.3


def test_secondary_intercept_cross_sentence_positive_hit_is_still_blocked() -> None:
    from server.app.services.agent_service import AgentService

    service = AgentService(llm_gateway=_FailingLlmGateway())
    result = service.evaluate_secondary_intercept(
        user_reply=(
            "收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。"
            "但对方现在让我把验证码发给他并共享屏幕。"
        ),
        semantic_summary="用户补充解释。",
        risk_category="异地大额异常转账",
        risk_level="medium",
        matched_keywords=["异地", "大额"],
        matched_scenarios=["异地大额转账风险"],
        follow_up_questions=["请说明你与收款人的关系。", "请说明本次转账用途。"],
    )

    assert result.decision == "block_secondary"
    assert "验证码/屏幕共享" in result.semantic_red_flags


def test_secondary_intercept_returns_interrogate_when_llm_unavailable() -> None:
    from server.app.services.agent_service import AgentService

    service = AgentService(llm_gateway=_FailingLlmGateway())
    result = service.evaluate_secondary_intercept(
        user_reply="收款人是同事，我已视频确认身份，请继续处理。",
        semantic_summary="用户补充解释。",
        risk_category="熟人借款风险",
        risk_level="medium",
        matched_keywords=["借钱", "周转"],
        matched_scenarios=["冒充熟人借钱"],
        follow_up_questions=["你是否线下认识对方？", "是否有共同联系人可确认？"],
    )

    assert result.decision == "interrogate"
    assert result.semantic_red_flags == []
    assert "系统正在忙" in result.assistant_message


def test_secondary_check_blocks_police_instruction_and_returns_red_flags() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-police-red-flag",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 6,
                    "input_duration_ms": 9000,
                    "extra_signals": {"app_switch_count": 2},
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "警察让我转的，说现在就要打款。",
                "context": {
                    "session_id": "session-police-red-flag",
                    "device_id": "android-test",
                    "platform": "android",
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
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=True)
    assert "司法机关要求转账" in body["semantic_red_flags"]


def test_secondary_check_blocks_refund_verification_and_returns_red_flags() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-refund-red-flag",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 6,
                    "input_duration_ms": 9000,
                    "extra_signals": {"app_switch_count": 2},
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "客服说验证资金后退款，还要我先刷流水。",
                "context": {
                    "session_id": "session-refund-red-flag",
                    "device_id": "android-test",
                    "platform": "android",
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
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=True)
    assert "客服要求验证资金" in body["semantic_red_flags"]


def test_secondary_check_irrelevant_reply_does_not_pass() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-irrelevant-reply",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "对方说临时借钱让我马上转。",
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "我就是想转账，别问了。",
                "context": {
                    "session_id": "session-irrelevant-reply",
                    "device_id": "android-test",
                    "platform": "android",
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
    _assert_secondary_semantic_red_flags_contract(body, expect_non_empty=False)
    assert body["secondary_decision"] != "pass_secondary"
    assert any("关键核验点" in reason or "直接相关" in reason for reason in body["reasons"])


def test_secondary_check_allows_only_single_submission_per_transfer() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-single-secondary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "对方说临时借钱让我马上转。",
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        first_secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "我就是想转账，别问了。",
                "context": {
                    "session_id": "session-single-secondary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert first_secondary.status_code == 200
        assert first_secondary.json()["secondary_decision"] == "interrogate"

        second_secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "再次补充说明。",
                "context": {
                    "session_id": "session-single-secondary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户再次提交补充说明。",
                },
            },
        )
        assert second_secondary.status_code == 400
        assert "本轮仅允许一次提交" in second_secondary.json()["detail"]


def test_confirm_is_rejected_after_single_round_interrogate_result() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-interrogate-stop",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "西安",
                    "lat": 34.3416,
                    "lng": 108.9398,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "对方说临时借钱让我马上转。",
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "我就是想转账，别问了。",
                "context": {
                    "session_id": "session-interrogate-stop",
                    "device_id": "android-test",
                    "platform": "android",
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
        assert secondary.json()["secondary_decision"] == "interrogate"

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 400
        assert "尚未通过二次校验" in confirm.json()["detail"]


def test_cancel_pending_transfer_is_explicit_business_action() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-cancel-transfer",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                    "input_pause_count": 6,
                    "input_duration_ms": 9000,
                    "extra_signals": {"app_switch_count": 2},
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        cancel = client.post(
            "/api/v1/transfers/cancel",
            json={"confirmation_token": token},
        )
        assert cancel.status_code == 200
        cancel_body = cancel.json()
        assert cancel_body["success"] is True
        assert cancel_body["status"] == "cancelled"
        assert cancel_body["confirmation_token"] == token
        assert "已取消" in cancel_body["assistant_message"]

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 400
        assert "未找到待确认转账" in confirm.json()["detail"]


def test_secondary_check_rejects_cancelled_transfer() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-secondary-after-cancel",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                },
            },
        )
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]

        cancel = client.post(
            "/api/v1/transfers/cancel",
            json={"confirmation_token": token},
        )
        assert cancel.status_code == 200

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "补充说明",
                "context": {
                    "session_id": "session-secondary-after-cancel",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert secondary.status_code == 400
        assert "非待确认状态" in secondary.json()["detail"]


def test_secondary_check_rejects_committed_transfer() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小b",
                "amount": 300,
                "context": {
                    "session_id": "session-secondary-after-confirm",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "日常生活转账。",
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "pass"
        token = precheck_body["confirmation_token"]

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 200

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "补充说明",
                "context": {
                    "session_id": "session-secondary-after-confirm",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交补充说明。",
                },
            },
        )
        assert secondary.status_code == 400
        assert "非待确认状态" in secondary.json()["detail"]
