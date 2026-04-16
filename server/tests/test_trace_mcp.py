from __future__ import annotations


def test_trace_records_precheck_and_cancel_flow_and_mcp_matches_repo() -> None:
    from fastapi.testclient import TestClient

    from mcp_servers import bank_server
    from server.app.main import app
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-trace-cancel",
                    "device_id": "android-trace",
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

    repo_items = get_bank_host_service().repository.get_transfer_trace(token)
    mcp_payload = bank_server.get_transfer_trace(token)
    mcp_items = mcp_payload["items"]

    assert [item["event_type"] for item in repo_items] == [
        "precheck_started",
        "precheck_decided",
        "transfer_cancelled",
    ]
    precheck_payload = repo_items[1]["payload"]
    assert "timing_total_ms" in precheck_payload
    assert "timing_classification_ms" in precheck_payload
    assert "timing_engine_ms" in precheck_payload
    assert precheck_payload["timing_total_ms"] >= 0
    assert repo_items[-1]["payload"]["cancel_stage"] == "after_precheck"
    assert mcp_payload["count"] == len(repo_items)
    assert mcp_items == repo_items


def test_trace_records_secondary_flow() -> None:
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
                    "session_id": "session-trace-secondary",
                    "device_id": "android-trace",
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
                    "session_id": "session-trace-secondary",
                    "device_id": "android-trace",
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

    items = get_bank_host_service().repository.get_transfer_trace(token)
    assert [item["event_type"] for item in items] == [
        "precheck_started",
        "precheck_decided",
        "secondary_submitted",
        "secondary_decided",
        "risk_report_generated",
    ]
    assert items[-2]["decision"] == "interrogate"
    secondary_payload = items[-2]["payload"]
    assert "timing_total_ms" in secondary_payload
    assert "timing_classification_ms" in secondary_payload
    assert "timing_persistence_ms" in secondary_payload
    assert secondary_payload["timing_total_ms"] >= 0
    assert items[-1]["payload"]["headline"]


def test_repeated_cancel_is_rejected_and_traced() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-trace-repeat-cancel",
                    "device_id": "android-trace",
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

        first_cancel = client.post(
            "/api/v1/transfers/cancel",
            json={"confirmation_token": token},
        )
        assert first_cancel.status_code == 200

        second_cancel = client.post(
            "/api/v1/transfers/cancel",
            json={"confirmation_token": token},
        )
        assert second_cancel.status_code == 400
        assert "无法取消" in second_cancel.json()["detail"]

    items = get_bank_host_service().repository.get_transfer_trace(token)
    assert items[-1]["event_type"] == "transfer_rejected"
    assert items[-1]["stage"] == "cancel"
    assert items[-1]["payload"]["reason"] == "non_pending_status"


def test_confirm_after_cancel_is_rejected_and_traced() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        precheck = client.post(
            "/api/v1/transfers/precheck",
            json={
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": "session-trace-confirm-after-cancel",
                    "device_id": "android-trace",
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

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 400

    items = get_bank_host_service().repository.get_transfer_trace(token)
    assert items[-1]["event_type"] == "transfer_rejected"
    assert items[-1]["stage"] == "confirm"
    assert items[-1]["payload"]["reason"] == "non_pending_status"


def test_confirm_after_interrogate_secondary_is_rejected_with_reason_trace() -> None:
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
                    "session_id": "session-trace-confirm-after-secondary-interrogate",
                    "device_id": "android-trace",
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
                    "session_id": "session-trace-confirm-after-secondary-interrogate",
                    "device_id": "android-trace",
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

    items = get_bank_host_service().repository.get_transfer_trace(token)
    assert items[-1]["event_type"] == "transfer_rejected"
    assert items[-1]["stage"] == "confirm"
    assert items[-1]["payload"]["reason"] == "secondary_not_passed"
    assert items[-1]["payload"]["secondary_decision"] == "interrogate"


def test_list_transfer_traces_returns_latest_trace_summaries() -> None:
    from mcp_servers import bank_server

    payload = bank_server.list_transfer_traces(limit=5)

    assert payload["count"] <= 5
    assert isinstance(payload["items"], list)
    if payload["items"]:
        item = payload["items"][0]
        assert "confirmation_token" in item
        assert "event_type" in item
        assert "payload" in item
