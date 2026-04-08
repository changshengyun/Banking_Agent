from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from server.app.main import app


def _build_context(*, session_id: str, city: str, semantic_summary: str) -> dict[str, Any]:
    coordinates = {
        "上海": (31.2304, 121.4737),
        "北京": (39.9042, 116.4074),
        "西安": (34.3416, 108.9398),
    }
    lat, lng = coordinates.get(city, (31.2304, 121.4737))
    return {
        "session_id": session_id,
        "device_id": "integration-device",
        "platform": "pytest",
        "current_city": city,
        "lat": lat,
        "lng": lng,
        "recent_page": "home",
        "last_action": "tap_transfer",
        "semantic_summary": semantic_summary,
    }


def _start_interrogate_transfer(*, client: TestClient, session_id: str) -> str:
    response = client.post(
        "/api/v1/transfers/precheck",
        json={
            "payee_name": "小c",
            "amount": 8000,
            "context": _build_context(
                session_id=session_id,
                city="北京",
                semantic_summary="普通转账需求。",
            ),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "interrogate"
    return body["confirmation_token"]


def _secondary_context(*, session_id: str) -> dict[str, Any]:
    context = _build_context(
        session_id=session_id,
        city="北京",
        semantic_summary="用户提交补充说明。",
    )
    context["recent_page"] = "transfer"
    context["last_action"] = "secondary_check"
    return context


def test_v3_flow_interrogate_then_cancel() -> None:
    with TestClient(app) as client:
        token = _start_interrogate_transfer(client=client, session_id="v3-int-cancel")

        cancel = client.post(
            "/api/v1/transfers/cancel",
            json={"confirmation_token": token},
        )
        assert cancel.status_code == 200
        cancel_body = cancel.json()
        assert cancel_body["status"] == "cancelled"
        assert cancel_body["confirmation_token"] == token

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 400
        assert "未找到待确认转账" in confirm.json()["detail"]


def test_v3_flow_interrogate_then_pass_secondary_then_confirm() -> None:
    with TestClient(app) as client:
        token = _start_interrogate_transfer(client=client, session_id="v3-int-pass")

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。",
                "context": _secondary_context(session_id="v3-int-pass"),
            },
        )
        assert secondary.status_code == 200
        secondary_body = secondary.json()
        assert secondary_body["secondary_decision"] == "pass_secondary"
        assert secondary_body["semantic_red_flags"] == []

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 200
        assert confirm.json()["success"] is True


def test_v3_flow_interrogate_then_block_secondary_then_stop() -> None:
    with TestClient(app) as client:
        token = _start_interrogate_transfer(client=client, session_id="v3-int-block")

        secondary = client.post(
            "/api/v1/transfers/secondary-check",
            json={
                "confirmation_token": token,
                "user_reply": "警察让我转的，说现在就要打款。",
                "context": _secondary_context(session_id="v3-int-block"),
            },
        )
        assert secondary.status_code == 200
        secondary_body = secondary.json()
        assert secondary_body["secondary_decision"] == "block_secondary"
        assert "司法机关要求转账" in secondary_body["semantic_red_flags"]

        confirm = client.post(
            "/api/v1/transfers/confirm",
            json={"confirmation_token": token},
        )
        assert confirm.status_code == 400
        assert "尚未通过二次校验" in confirm.json()["detail"]
