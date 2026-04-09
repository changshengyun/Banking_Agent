from __future__ import annotations


def test_risk_report_is_not_available_before_secondary_check() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-report-missing",
                    "device_id": "android-report",
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

        report = client.get(f"/api/v1/transfers/{token}/risk-report")
        assert report.status_code == 404
        assert "未找到对应的风险报告" in report.json()["detail"]


def test_secondary_check_generates_persisted_risk_report() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-report-generated",
                    "device_id": "android-report",
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
                    "session_id": "session-report-generated",
                    "device_id": "android-report",
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

        report = client.get(f"/api/v1/transfers/{token}/risk-report")
        assert report.status_code == 200
        body = report.json()

    assert body["confirmation_token"] == token
    assert body["headline"]
    assert body["overall_risk_level"] in {"low", "medium", "high"}
    assert body["risk_summary"]
    assert isinstance(body["risk_factors"], list)
    assert body["recommended_action"]
    assert isinstance(body["evidence"], list)
    assert body["generated_at"]


def test_secondary_check_trace_includes_risk_report_event() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小d",
                "amount": 6000,
                "context": {
                    "session_id": "session-report-trace",
                    "device_id": "android-report",
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
                    "session_id": "session-report-trace",
                    "device_id": "android-report",
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

    items = get_bank_host_service().repository.get_transfer_trace(token)
    assert "risk_report_generated" in [item["event_type"] for item in items]
