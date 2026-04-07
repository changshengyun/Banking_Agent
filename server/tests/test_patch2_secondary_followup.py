from __future__ import annotations

from dataclasses import dataclass

from server.app.db import init_database
from server.app.repositories.banking import BankingRepository
from server.app.schemas.common import ClientContext
from server.app.schemas.external_intelligence import ExternalIntelligenceReport
from server.app.schemas.risk import RiskClassificationPayload
from server.app.schemas.transfer import TransferSecondaryCheckRequest
from server.app.seed import seed_demo_data
from server.app.services.agent_service import AgentService, SecondaryResult
from server.app.services.bank_host import BankHostService


class _FakeGateway:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    def generate_json_sync(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return {
            "secondary_decision": "block_secondary",
            "final_risk_after_secondary": 0.88,
            "reasons": ["未完成关键核验点"],
            "assistant_message": "请停止当前转账并进一步核验。",
        }


@dataclass
class _FakeSecondaryAgent:
    calls: list[dict]

    def evaluate_secondary_intercept(self, **kwargs) -> SecondaryResult:
        self.calls.append(kwargs)
        return SecondaryResult(
            decision="block_secondary",
            risk=0.91,
            reasons=["命中场景化追问核验失败"],
            assistant_message="二次校验未通过，请停止转账。",
            semantic_red_flags=[],
        )


def _clear_external_intelligence(payee_name: str) -> ExternalIntelligenceReport:
    return ExternalIntelligenceReport(
        status="clear",
        screened_entity=payee_name,
        summary="未命中外部名单或负面情报。",
        max_risk_level="low",
        max_score=0.0,
        hits=[],
    )


def _police_classification() -> RiskClassificationPayload:
    return RiskClassificationPayload(
        risk_category="冒充公检法",
        risk_level="high",
        block_hint=True,
        matched_keywords=["公安", "转账核验"],
        high_risk_phrase_hits=[],
        matched_scenarios=["冒充公安检法办案"],
        analysis="对方以涉案理由要求配合转账核验。",
        follow_up_questions=[
            "你是否通过官方公开电话核实过对方身份和案号？",
            "对方是否要求你转账核验资金、提供验证码或共享屏幕？",
        ],
        suggested_reply_examples=[
            "如涉及公检法事项，我只会主动拨打官方电话核验，不会向陌生账户转账。",
        ],
    )


def test_agent_service_injects_police_verification_points_into_prompt() -> None:
    gateway = _FakeGateway()
    service = AgentService(llm_gateway=gateway)

    result = service.evaluate_secondary_intercept(
        user_reply="对方说是公安，让我配合核验。",
        semantic_summary="对方自称公安，要求线上做笔录并转账核验。",
        risk_category="冒充公检法",
        risk_level="high",
        matched_keywords=["公安", "转账核验"],
        matched_scenarios=["冒充公安检法办案"],
        follow_up_questions=[
            "你是否通过官方公开电话核实过对方身份和案号？",
            "对方是否要求你转账核验资金、提供验证码或共享屏幕？",
        ],
    )

    assert result.decision == "block_secondary"
    assert 0.0 <= result.risk <= 1.0
    assert result.reasons
    assert result.assistant_message
    assert "强制核验点" in gateway.user_prompt
    assert "是否通过官方电话核实案号或身份" in gateway.user_prompt
    assert "是否被要求转账核验资金" in gateway.user_prompt
    assert "命中场景：冒充公安检法办案" in gateway.user_prompt


def test_secondary_check_uses_first_follow_up_question_and_passes_scenarios(
    monkeypatch,
) -> None:
    from server.app.services import agent_service as agent_service_module

    init_database()
    seed_demo_data()

    repository = BankingRepository()
    service = BankHostService(repository=repository)
    token = repository.create_pending_transfer(
        payee_name="陌生收款人甲",
        amount=6800,
        city="北京",
        device_id="patch2-device",
        recent_page="transfer",
        last_action="secondary_check",
        semantic_summary="对方自称公安，要求我配合核验资金。",
        risk_level="medium",
        decision="interrogate",
        flag_s=0.41,
        g_behavior=0.22,
        g_dynamic=0.67,
        final_risk=0.58,
        reasons=["存在可疑执法话术"],
        assistant_message="请补充说明后再继续。",
    )
    fake_agent = _FakeSecondaryAgent(calls=[])

    monkeypatch.setattr(
        service.risk_knowledge,
        "classify_text",
        lambda **kwargs: _police_classification(),
    )
    monkeypatch.setattr(
        service,
        "screen_external_intelligence",
        _clear_external_intelligence,
    )
    monkeypatch.setattr(
        agent_service_module,
        "get_agent_service",
        lambda: fake_agent,
    )

    response = service.secondary_check_transfer(
        TransferSecondaryCheckRequest(
            confirmation_token=token,
            user_reply="我还没有通过官方电话核实。",
            context=ClientContext(
                session_id="patch2-session",
                device_id="patch2-device",
                platform="pytest",
                current_city="北京",
                lat=39.9042,
                lng=116.4074,
                recent_page="transfer",
                last_action="secondary_check",
                semantic_summary="用户提交二次解释。",
            ),
        )
    )

    pending = repository.get_pending_transfer(token)
    assert response.secondary_decision == "block_secondary"
    assert pending["secondary_question"] == "你是否通过官方公开电话核实过对方身份和案号？"
    assert fake_agent.calls
    assert fake_agent.calls[0]["matched_scenarios"] == ["冒充公安检法办案"]
    assert fake_agent.calls[0]["follow_up_questions"][0] == pending["secondary_question"]
