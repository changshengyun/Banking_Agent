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


def test_transfer_review_flow() -> None:
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
                },
            },
        )
        assert precheck.status_code == 200
        body = precheck.json()
        assert body["decision"] == "review"
        assert body["confirmation_token"]


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
