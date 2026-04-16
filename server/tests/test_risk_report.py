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
    assert body["governance"]["report_version"] == "v2"
    assert body["governance"]["policy_version"] == "secondary_policy_v1"
    assert body["governance"]["source_stage"] == "secondary-check"
    assert "risk_report_generated" in body["governance"]["trace_events"]
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
    report_event = next(
        item for item in items if item["event_type"] == "risk_report_generated"
    )
    assert report_event["payload"]["report_version"] == "v2"
    assert report_event["payload"]["policy_version"] == "secondary_policy_v1"


def test_high_risk_report_list_returns_latest_high_risk_only() -> None:
    from fastapi.testclient import TestClient

    from server.app.main import app
    from server.app.schemas.report import RiskReportGovernancePayload
    from server.app.schemas.report import RiskReportPayload
    from server.app.services.bank_host import get_bank_host_service

    with TestClient(app) as client:
        repository = get_bank_host_service().repository
        repository.upsert_risk_report(
            report=RiskReportPayload(
                confirmation_token="report-high-new",
                headline="高风险转账报告-新",
                overall_risk_level="high",
                risk_summary="新的高风险报告",
                risk_factors=["语义红旗"],
                recommended_action="人工复核",
                evidence=["证据A"],
                governance=RiskReportGovernancePayload(
                    report_version="v2",
                    policy_version="secondary_policy_v1",
                    generation_mode="fallback",
                    source_stage="secondary-check",
                    secondary_decision="block_secondary",
                    risk_category="safe_account_scam",
                    external_intelligence_level="high",
                    trace_events=["secondary_decided", "risk_report_generated"],
                ),
                generated_at="2099-04-10T12:00:00Z",
            )
        )
        repository.upsert_risk_report(
            report=RiskReportPayload(
                confirmation_token="report-medium-ignore",
                headline="中风险报告",
                overall_risk_level="medium",
                risk_summary="不应出现在高风险列表中",
                risk_factors=["中风险因子"],
                recommended_action="继续观察",
                evidence=["证据B"],
                governance=RiskReportGovernancePayload(
                    report_version="v2",
                    policy_version="secondary_policy_v1",
                    generation_mode="fallback",
                    source_stage="secondary-check",
                    secondary_decision="interrogate",
                    risk_category="remote_large_transfer",
                    external_intelligence_level="medium",
                    trace_events=["secondary_decided", "risk_report_generated"],
                ),
                generated_at="2099-04-10T11:00:00Z",
            )
        )
        repository.upsert_risk_report(
            report=RiskReportPayload(
                confirmation_token="report-high-old",
                headline="高风险转账报告-旧",
                overall_risk_level="high",
                risk_summary="旧的高风险报告",
                risk_factors=["外部情报"],
                recommended_action="人工复核",
                evidence=["证据C"],
                governance=RiskReportGovernancePayload(
                    report_version="v2",
                    policy_version="secondary_policy_v1",
                    generation_mode="llm",
                    source_stage="secondary-check",
                    secondary_decision="block_secondary",
                    risk_category="loan_scam",
                    external_intelligence_level="high",
                    trace_events=["secondary_decided", "risk_report_generated"],
                ),
                generated_at="2099-04-10T10:00:00Z",
            )
        )
        response = client.get("/api/v1/transfers/risk-reports")
        assert response.status_code == 200
        body = response.json()

    tokens = [item["confirmation_token"] for item in body["items"]]
    assert "report-medium-ignore" not in tokens
    assert tokens.index("report-high-new") < tokens.index("report-high-old")
    first_item = next(
        item for item in body["items"] if item["confirmation_token"] == "report-high-new"
    )
    assert first_item["risk_category"] == "safe_account_scam"
    assert first_item["policy_version"] == "secondary_policy_v1"
    assert first_item["generation_mode"] == "fallback"
