from __future__ import annotations

from functools import lru_cache

from ..config import settings
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.common import SuggestedAction, ToolUsage
from .bank_host import BankHostService, get_bank_host_service
from .outdoor_knowledge import OutdoorKnowledgeService


class AgentService:
    def __init__(
        self,
        bank_host: BankHostService | None = None,
        outdoor_knowledge: OutdoorKnowledgeService | None = None,
    ) -> None:
        self.bank_host = bank_host or get_bank_host_service()
        self.outdoor_knowledge = outdoor_knowledge or OutdoorKnowledgeService()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        latest_message = request.messages[-1].content.strip()
        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "user",
            latest_message,
        )

        if not settings.mock_llm:
            live_response = await self._try_live_langchain_response(latest_message)
            if live_response is not None:
                self.bank_host.repository.add_chat_message(
                    request.context.session_id,
                    "assistant",
                    live_response.assistant_message,
                )
                return live_response

        response = self._mock_chat_response(latest_message)
        self.bank_host.repository.add_chat_message(
            request.context.session_id,
            "assistant",
            response.assistant_message,
        )
        return response

    def _mock_chat_response(self, latest_message: str) -> ChatResponse:
        lower_text = latest_message.lower()
        used_tools: list[ToolUsage] = []
        suggested_actions: list[SuggestedAction] = []

        if any(keyword in latest_message for keyword in ("余额", "资产", "账户")):
            dashboard = self.bank_host.get_dashboard()
            used_tools.append(
                ToolUsage(name="get_account_summary", summary="读取模拟账户余额与资产信息")
            )
            suggested_actions.append(
                SuggestedAction(label="发起转账", action="open_transfer")
            )
            return ChatResponse(
                assistant_message=(
                    f"当前可用余额为 {dashboard.cash_balance:.2f} 元，理财余额为 "
                    f"{dashboard.wealth_balance:.2f} 元，总资产为 {dashboard.total_assets:.2f} 元。"
                ),
                used_tools=used_tools,
                suggested_actions=suggested_actions,
            )

        if any(keyword in latest_message for keyword in ("账单", "消费", "流水", "交易")):
            bill_summary = self.bank_host.build_bill_summary()
            used_tools.append(
                ToolUsage(name="list_transactions", summary="读取最近交易与消费分类摘要")
            )
            suggested_actions.append(
                SuggestedAction(label="查看首页", action="refresh_dashboard")
            )
            return ChatResponse(
                assistant_message=bill_summary,
                used_tools=used_tools,
                suggested_actions=suggested_actions,
            )

        if any(keyword in latest_message for keyword in ("风险", "风控", "为什么", "拦截", "提醒")):
            used_tools.append(
                ToolUsage(name="precheck_transfer_risk", summary="解释最近一次风控事件")
            )
            suggested_actions.append(
                SuggestedAction(label="再次确认", action="open_transfer")
            )
            return ChatResponse(
                assistant_message=self.bank_host.explain_last_risk_event(),
                used_tools=used_tools,
                suggested_actions=suggested_actions,
            )

        if any(keyword in latest_message for keyword in ("露营", "徒步", "登山", "户外")) or any(
            keyword in lower_text for keyword in ("camp", "hiking", "outdoor")
        ):
            answer = self.outdoor_knowledge.answer(latest_message)
            used_tools.append(
                ToolUsage(
                    name="answer_outdoor_question",
                    summary="调用轻量户外知识库回答演示问题",
                )
            )
            return ChatResponse(
                assistant_message=answer,
                used_tools=used_tools,
                suggested_actions=[
                    SuggestedAction(label="继续提问", action="stay_in_chat")
                ],
            )

        return ChatResponse(
            assistant_message=(
                "我是演示版银行 AI 助手。你可以问我余额、账单、最近一次风控原因，"
                "也可以顺带问露营或徒步的基础知识。"
            ),
            used_tools=[
                ToolUsage(name="demo_router", summary="根据意图选择银行或户外演示工具")
            ],
            suggested_actions=[
                SuggestedAction(label="查余额", action="ask_balance"),
                SuggestedAction(label="查风控", action="ask_risk_reason"),
            ],
        )

    async def _try_live_langchain_response(
        self, latest_message: str
    ) -> ChatResponse | None:
        if not settings.llm_api_key or not settings.llm_model:
            return None

        try:
            from langchain_openai import ChatOpenAI
        except Exception:
            return None

        dashboard = self.bank_host.get_dashboard()
        bill_summary = self.bank_host.build_bill_summary()
        risk_summary = self.bank_host.explain_last_risk_event()
        prompt = (
            "你是银行 App 内的演示版智能助手。请基于已知上下文，简洁、专业地回答用户。\n"
            f"账户余额：活期 {dashboard.cash_balance:.2f} 元，理财 {dashboard.wealth_balance:.2f} 元。\n"
            f"账单摘要：{bill_summary}\n"
            f"最近风控：{risk_summary}\n"
            f"用户问题：{latest_message}"
        )
        try:
            client = ChatOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url or None,
                model=settings.llm_model,
                temperature=0.2,
            )
            result = await client.ainvoke(prompt)
        except Exception:
            return None

        return ChatResponse(
            assistant_message=str(getattr(result, "content", "")).strip() or "暂时未获取到模型回复。",
            used_tools=[
                ToolUsage(name="langchain_chat", summary="通过 LangChain 调用兼容模型接口")
            ],
            suggested_actions=[SuggestedAction(label="返回首页", action="refresh_dashboard")],
        )


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService()
