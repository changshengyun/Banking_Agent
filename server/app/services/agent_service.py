from __future__ import annotations

from functools import lru_cache

from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.common import SuggestedAction, ToolUsage
from .bank_host import BankHostService, get_bank_host_service
from .llm_gateway import LLMGateway
from .risk_knowledge_base import (
    RiskKnowledgeBaseService,
    get_risk_knowledge_base_service,
)


class AgentService:
    def __init__(
        self,
        bank_host: BankHostService | None = None,
        llm_gateway: LLMGateway | None = None,
        risk_knowledge: RiskKnowledgeBaseService | None = None,
    ) -> None:
        self.bank_host = bank_host or get_bank_host_service()
        self.llm_gateway = llm_gateway or LLMGateway()
        self.risk_knowledge = risk_knowledge or get_risk_knowledge_base_service()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        latest_message = request.messages[-1].content.strip()
        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "user",
            latest_message,
        )

        response = await self._live_chat_response(
            latest_message=latest_message,
            current_city=request.context.current_city,
        )

        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "assistant",
            response.assistant_message,
        )
        return response

    def evaluate_secondary_intercept(
        self,
        *,
        user_reply: str,
        semantic_summary: str,
        risk_category: str,
        risk_level: str,
        matched_keywords: list[str],
        follow_up_questions: list[str],
    ) -> tuple[str, float, list[str], str]:
        system_prompt = (
            "你是银行风控二次质询模型。"
            "你只能在 pass_secondary 和 block_secondary 两种结果中选择一种。"
            "必须输出严格 JSON，不允许输出额外解释。"
        )
        user_prompt = (
            "请根据预检摘要、知识库风险分类、命中关键词和用户解释，"
            "判断本次转账是否允许继续。返回 JSON：\n"
            "{"
            '"secondary_decision":"pass_secondary 或 block_secondary",'
            '"final_risk_after_secondary":0到1之间小数,'
            '"reasons":["原因1","原因2"],'
            '"assistant_message":"给用户的简短结论"'
            "}\n"
            f"预检语义摘要：{semantic_summary}\n"
            f"知识库风险分类：{risk_category}\n"
            f"知识库风险等级：{risk_level}\n"
            f"命中关键词：{'、'.join(matched_keywords) if matched_keywords else '无'}\n"
            f"建议追问点：{'；'.join(follow_up_questions) if follow_up_questions else '无'}\n"
            f"用户二次解释：{user_reply.strip()}"
        )
        payload = self.llm_gateway.generate_json_sync(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        return self._parse_secondary_json(payload)

    async def _live_chat_response(
        self,
        *,
        latest_message: str,
        current_city: str,
    ) -> ChatResponse:
        dashboard = self.bank_host.get_dashboard()
        bill_summary = self.bank_host.build_bill_summary()
        risk_summary = self.bank_host.explain_last_risk_event()
        classification = self.risk_knowledge.classify_text(
            text=latest_message,
            amount=0.0,
            current_city=current_city,
            common_cities=[current_city],
            is_known_payee=True,
        )

        system_prompt = (
            "你是手机银行内的风控助手。"
            "只能基于提供的银行上下文和风险分类结果回答。"
            "回答要简洁、明确、可执行，不要杜撰没有提供的账户事实。"
            "必须输出严格 JSON，不要输出额外文本。"
        )
        user_prompt = (
            "请根据下面上下文回答用户问题，并生成建议动作。返回 JSON：\n"
            "{"
            '"assistant_message":"给用户的回复",'
            '"suggested_actions":[{"label":"按钮文案","action":"动作标识"}]'
            "}\n"
            f"账户摘要：活期 {dashboard.cash_balance:.2f} 元，理财 {dashboard.wealth_balance:.2f} 元，总资产 {dashboard.total_assets:.2f} 元。\n"
            f"账单摘要：{bill_summary}\n"
            f"最近风控：{risk_summary}\n"
            f"风险分类：{classification.risk_category} / {classification.risk_level}\n"
            f"分类分析：{classification.analysis}\n"
            f"建议追问：{'；'.join(classification.follow_up_questions) if classification.follow_up_questions else '无'}\n"
            f"用户问题：{latest_message}"
        )
        payload = await self.llm_gateway.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        assistant_message = str(payload.get("assistant_message", "")).strip()
        if not assistant_message:
            raise ValueError("在线模型返回格式异常，缺少 assistant_message。")

        actions_raw = payload.get("suggested_actions", [])
        suggested_actions = self._parse_suggested_actions(actions_raw)
        if not suggested_actions:
            suggested_actions = [
                SuggestedAction(label="返回首页", action="refresh_dashboard")
            ]

        used_tools = [
            ToolUsage(name="bank_context_pack", summary="聚合账户、账单和最近风控摘要"),
        ]
        if classification.risk_category != "正常转账":
            used_tools.append(
                ToolUsage(
                    name="risk_scene_classifier",
                    summary=f"匹配风险分类 {classification.risk_category}",
                )
            )

        return ChatResponse(
            assistant_message=assistant_message,
            used_tools=used_tools,
            suggested_actions=suggested_actions,
        )

    def _parse_suggested_actions(self, actions_raw) -> list[SuggestedAction]:
        actions: list[SuggestedAction] = []
        if not isinstance(actions_raw, list):
            return actions
        for item in actions_raw[:3]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            action = str(item.get("action", "")).strip()
            if not label or not action:
                continue
            actions.append(SuggestedAction(label=label, action=action))
        return actions

    def _parse_secondary_json(
        self,
        payload: dict,
    ) -> tuple[str, float, list[str], str]:
        decision = str(payload.get("secondary_decision", "")).strip()
        if decision not in {"pass_secondary", "block_secondary"}:
            raise ValueError("二次校验返回缺少有效 secondary_decision。")

        try:
            risk = float(payload.get("final_risk_after_secondary", 1.0))
        except (TypeError, ValueError) as error:
            raise ValueError("二次校验返回的风险分值无效。") from error

        reasons_raw = payload.get("reasons", [])
        reasons = [str(item).strip() for item in reasons_raw if str(item).strip()]
        if not reasons:
            reasons = ["模型未返回详细原因。"]

        assistant_message = str(payload.get("assistant_message", "")).strip()
        if not assistant_message:
            assistant_message = "二次校验已完成。"

        return (
            decision,
            max(0.0, min(1.0, risk)),
            reasons,
            assistant_message,
        )


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService()
