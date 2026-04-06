from __future__ import annotations


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
        assert body["risk_classification"]["risk_category"]
        assert body["risk_classification"]["risk_level"] in {"low", "medium", "high"}
        assert "analysis" in body["risk_classification"]


def test_classify_risk_endpoint() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transfers/classify-risk",
            json={
                "payee_name": "小f",
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
        assert body["risk_category"] == "客服退款诈骗"
        assert body["risk_level"] == "high"
        assert any(keyword for keyword in body["matched_keywords"])


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
