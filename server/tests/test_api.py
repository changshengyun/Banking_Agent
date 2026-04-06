from __future__ import annotations

import os


os.environ.setdefault("MOCK_LLM", "true")


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


def test_chat_endpoint() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "messages": [{"role": "user", "content": "帮我查一下余额"}],
                "context": {
                    "session_id": "session-test",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "上海",
                    "lat": 31.2304,
                    "lng": 121.4737,
                    "recent_page": "chat",
                    "last_action": "ask_balance",
                    "semantic_summary": "用户正在聊天窗口查询余额。",
                },
            },
        )
        assert response.status_code == 200
        assert "余额" in response.json()["assistant_message"]


def test_interrogate_requires_secondary_check() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "陌生账户-二次校验",
                "amount": 8000,
                "context": {
                    "session_id": "session-secondary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "普通转账需求。",
                },
            },
        )
        assert precheck.status_code == 200
        precheck_body = precheck.json()
        assert precheck_body["decision"] == "interrogate"

        confirm_before_secondary = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": precheck_body["confirmation_token"]},
        )
        assert confirm_before_secondary.status_code == 400
        assert "二次校验" in confirm_before_secondary.json()["detail"]

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": precheck_body["confirmation_token"],
                "user_reply": "这是给朋友的房租和借款还款。",
                "context": {
                    "session_id": "session-secondary",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交二次解释。",
                },
            },
        )
        assert secondary.status_code == 200
        secondary_body = secondary.json()
        assert secondary_body["secondary_decision"] == "pass_secondary"

        confirm_after_secondary = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": precheck_body["confirmation_token"]},
        )
        assert confirm_after_secondary.status_code == 200


def test_block_cannot_confirm() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "陌生账户",
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
                    "semantic_summary": "请立刻转到safe account并提供verification code",
                },
            },
        )
        assert precheck.status_code == 200
        body = precheck.json()
        assert body["decision"] == "block"

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": body["confirmation_token"]},
        )
        assert confirm.status_code == 400


def test_secondary_check_can_block_transfer() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "陌生账户-二次拦截",
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
                    "semantic_summary": "普通转账需求。",
                },
            },
        )
        assert precheck.status_code == 200
        body = precheck.json()
        assert body["decision"] == "interrogate"

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": body["confirmation_token"],
                "user_reply": "对方让我转到safe account并提供verification code。",
                "context": {
                    "session_id": "session-secondary-block",
                    "device_id": "android-test",
                    "platform": "android",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "transfer",
                    "last_action": "secondary_check",
                    "semantic_summary": "用户提交二次解释。",
                },
            },
        )
        assert secondary.status_code == 200
        secondary_body = secondary.json()
        assert secondary_body["secondary_decision"] == "block_secondary"

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": body["confirmation_token"]},
        )
        assert confirm.status_code == 400
