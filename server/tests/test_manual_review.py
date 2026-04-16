from __future__ import annotations


def _create_high_risk_report(client, *, token: str = "confirm-review-demo") -> str:
    from server.app.schemas.report import RiskReportGovernancePayload
    from server.app.schemas.report import RiskReportPayload
    from server.app.services.bank_host import get_bank_host_service

    precheck = client.post(
        "/api/v1/transfers/precheck",
        json={
            "payee_name": "小d",
            "amount": 3200,
            "context": {
                "session_id": f"session-{token}",
                "device_id": "android-review",
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
    generated_token = precheck.json()["confirmation_token"]
    get_bank_host_service().repository.upsert_risk_report(
        report=RiskReportPayload(
            confirmation_token=generated_token,
            headline="高风险人工复核样例",
            overall_risk_level="high",
            risk_summary="该交易已命中高风险语义和复核要点。",
            risk_factors=["异地大额", "新增收款人", "高风险用途说明"],
            recommended_action="建议人工复核，不改变原有业务裁决。",
            evidence=["收款人关系不清晰", "用途说明与风险模板一致"],
            governance=RiskReportGovernancePayload(
                report_version="v2",
                policy_version="secondary_policy_v1",
                generation_mode="fallback",
                source_stage="secondary-check",
                secondary_decision="block_secondary",
                risk_category="safe_account_scam",
                external_intelligence_level="medium",
                trace_events=["secondary_decided", "risk_report_generated"],
            ),
            generated_at="2026-04-10T13:00:00Z",
        )
    )
    report = client.get(f"/api/v1/transfers/{generated_token}/risk-report")
    assert report.status_code == 200
    return generated_token


def test_manual_review_can_be_created_for_high_risk_report() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        token = _create_high_risk_report(client)
        response = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "这笔交易需要人工复核，因为对方身份和用途仍然可疑。"},
        )
        assert response.status_code == 200
        body = response.json()

    assert body["confirmation_token"] == token
    assert body["status"] == "submitted"
    assert body["headline"]
    assert body["overall_risk_level"] == "high"


def test_manual_review_rejects_duplicate_open_case() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        token = _create_high_risk_report(client)
        first = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "第一次提交人工复核申请，要求进一步确认收款方身份。"},
        )
        assert first.status_code == 200
        second = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "再次提交重复的人工复核申请，应该被拒绝。"},
        )
        assert second.status_code == 400
        assert "已有进行中的人工复核单" in second.json()["detail"]


def test_manual_review_queue_and_close_flow() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        token = _create_high_risk_report(client)
        created = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "需要人工复核对方是否真实存在，并核对风险证据。"},
        )
        assert created.status_code == 200
        review_id = created.json()["review_id"]

        queue = client.get("/api/v1/manual-reviews/queue")
        assert queue.status_code == 200
        queue_ids = [item["review_id"] for item in queue.json()["items"]]
        assert review_id in queue_ids

        started = client.patch(
            f"/api/v1/manual-reviews/{review_id}",
            json={"status": "in_review", "reviewer_id": "reviewer-demo"},
        )
        assert started.status_code == 200
        assert started.json()["status"] == "in_review"
        assert started.json()["in_review_at"]
        started_in_review_at = started.json()["in_review_at"]

        closed = client.patch(
            f"/api/v1/manual-reviews/{review_id}",
            json={
                "status": "closed",
                "outcome": "advisory",
                "review_note": "建议继续通过官方渠道核验收款方身份，不恢复原裁决。",
                "reviewer_id": "reviewer-demo",
            },
        )
        assert closed.status_code == 200
        body = closed.json()

    assert body["status"] == "closed"
    assert body["outcome"] == "advisory"
    assert body["in_review_at"] == started_in_review_at
    assert body["review_note"]
    assert body["request_snapshot"]["headline"]

    trace_items = get_bank_host_service().repository.get_transfer_trace(token)
    event_types = [item["event_type"] for item in trace_items]
    assert "manual_review_requested" in event_types
    assert "manual_review_started" in event_types
    assert "manual_review_closed" in event_types


def test_manual_review_detail_and_list_are_user_visible() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        token = _create_high_risk_report(client)
        created = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "需要保留复核记录，便于后续重复查看。"},
        )
        assert created.status_code == 200
        review_id = created.json()["review_id"]

        listing = client.get("/api/v1/manual-reviews")
        assert listing.status_code == 200
        list_body = listing.json()
        assert list_body["items"][0]["review_id"] == review_id

        detail = client.get(f"/api/v1/manual-reviews/{review_id}")
        assert detail.status_code == 200
        detail_body = detail.json()

    assert detail_body["confirmation_token"] == token
    assert detail_body["request_snapshot"]["overall_risk_level"] == "high"
    assert detail_body["request_snapshot"]["policy_version"] == "secondary_policy_v1"


def test_manual_review_list_supports_status_filter() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        token = _create_high_risk_report(client, token="confirm-review-filtered")
        created = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "需要通过状态筛选确认关闭后的复核单是否可见。"},
        )
        assert created.status_code == 200
        review_id = created.json()["review_id"]

        started = client.patch(
            f"/api/v1/manual-reviews/{review_id}",
            json={"status": "in_review", "reviewer_id": "reviewer-demo"},
        )
        assert started.status_code == 200
        closed = client.patch(
            f"/api/v1/manual-reviews/{review_id}",
            json={
                "status": "closed",
                "outcome": "upheld",
                "review_note": "维持原结论，用于测试 closed 筛选。",
                "reviewer_id": "reviewer-demo",
            },
        )
        assert closed.status_code == 200

        response = client.get("/api/v1/manual-reviews?status=closed")
        assert response.status_code == 200
        body = response.json()

    assert body["items"]
    assert all(item["status"] == "closed" for item in body["items"])
    assert any(item["review_id"] == review_id for item in body["items"])


def test_manual_review_and_risk_report_not_found_use_404() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        report = client.get("/api/v1/transfers/not-exists/risk-report")
        create_review = client.post(
            "/api/v1/transfers/not-exists/manual-review",
            json={"request_reason": "这是一个不存在 token 的人工复核申请。"},
        )
        detail = client.get("/api/v1/manual-reviews/review-not-exists")
        update = client.patch(
            "/api/v1/manual-reviews/review-not-exists",
            json={"status": "in_review", "reviewer_id": "reviewer-demo"},
        )

    assert report.status_code == 404
    assert create_review.status_code == 404
    assert detail.status_code == 404
    assert update.status_code == 404


def test_manual_review_invalid_transition_keeps_400() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app

    with TestClient(app) as client:
        token = _create_high_risk_report(client, token="confirm-review-invalid")
        created = client.post(
            f"/api/v1/transfers/{token}/manual-review",
            json={"request_reason": "需要测试非法状态流转时是否仍返回 400。"},
        )
        assert created.status_code == 200
        review_id = created.json()["review_id"]

        invalid = client.patch(
            f"/api/v1/manual-reviews/{review_id}",
            json={
                "status": "closed",
                "outcome": "upheld",
                "review_note": "未进入处理中前不允许关闭。",
                "reviewer_id": "reviewer-demo",
            },
        )

    assert invalid.status_code == 400
    assert "尚未进入处理中状态" in invalid.json()["detail"]
