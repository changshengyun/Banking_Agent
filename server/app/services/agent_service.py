from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.common import SuggestedAction, ToolUsage


def _normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "")


@dataclass(frozen=True)
class SecondaryResult:
    decision: str
    risk: float
    reasons: list[str]
    assistant_message: str
    semantic_red_flags: list[str]


from .bank_host import BankHostService, get_bank_host_service
from .llm_gateway import LLMGateway
from .pii_masker import PiiMasker
from .risk_engine import Decision
from .risk_knowledge_base import (
    RiskKnowledgeBaseService,
    get_risk_knowledge_base_service,
)

SEMANTIC_RED_FLAG_RULES: dict[str, tuple[str, ...]] = {
    "司法机关要求转账": (
        "公安让我转",
        "警察让我转",
        "检察院让我转",
        "法院让我转",
        "公安要求转账",
        "警察要求转账",
        "配合办案转账",
    ),
    "安全账户/资金清查": (
        "安全账户",
        "监管账户",
        "资金清查",
        "冻结前转账",
        "验资",
    ),
    "客服要求验证资金": (
        "验证资金",
        "刷流水",
        "退款后返还",
        "验证后退款",
        "百万保障",
    ),
    "验证码/屏幕共享": (
        "验证码",
        "屏幕共享",
        "共享屏幕",
        "远程控制",
        "远程协助",
    ),
    "投资收益诱导": (
        "稳赚",
        "稳赚不赔",
        "内部消息",
        "跟单收益",
        "保本收益",
        "老师带单",
    ),
}

GENERIC_EVASIVE_PATTERNS: tuple[str, ...] = (
    "我就是想转账",
    "就是想转账",
    "正常转账",
    "帮我通过",
    "赶紧通过",
    "没什么",
    "没事",
    "不用问",
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
        matched_scenarios: list[str],
        follow_up_questions: list[str],
    ) -> SecondaryResult:
        # HIRD-G: 治理层，进入二次拦截逻辑前强制对摘要脱敏
        semantic_summary = PiiMasker.mask_text(semantic_summary)
        user_reply = PiiMasker.mask_text(user_reply)

        verification_points = self._secondary_verification_points(
            risk_category=risk_category,
            matched_scenarios=matched_scenarios,
            follow_up_questions=follow_up_questions,
        )
        semantic_red_flags = self._detect_semantic_red_flags(user_reply)
        if semantic_red_flags:
            return self._build_red_flag_block_result(semantic_red_flags)

        if self._is_irrelevant_reply(
            user_reply=user_reply,
            risk_category=risk_category,
            verification_points=verification_points,
        ):
            return SecondaryResult(
                decision=Decision.INTERROGATE,
                risk=0.72,
                reasons=["用户回复未覆盖当前风险场景的关键核验点", "需要继续补充与风险问题直接相关的说明"],
                assistant_message="当前说明与核验问题不匹配，请继续补充与风险问题直接相关的解释。",
                semantic_red_flags=[],
            )

        system_prompt = self._build_secondary_system_prompt()
        user_prompt = self._build_secondary_user_prompt(
            user_reply=user_reply,
            semantic_summary=semantic_summary,
            risk_category=risk_category,
            risk_level=risk_level,
            matched_keywords=matched_keywords,
            matched_scenarios=matched_scenarios,
            follow_up_questions=follow_up_questions,
            verification_points=verification_points,
        )
        payload = self.llm_gateway.generate_json_sync(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        result = self._parse_secondary_json(payload)
        if result.semantic_red_flags and result.decision != "block_secondary":
            return self._build_red_flag_block_result(result.semantic_red_flags)
        return result

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

    def _build_secondary_system_prompt(self) -> str:
        return (
            "你是手机银行二次拦截风控 Agent。"
            f"你只能输出 {Decision.PASS_SECONDARY}、{Decision.INTERROGATE} 或 {Decision.BLOCK_SECONDARY} 三种结果之一。"
            "必须输出严格 JSON，不允许输出额外解释。"
            f"若用户回复出现高风险语义模式，必须输出 {Decision.BLOCK_SECONDARY}。"
            f"若用户回复与当前追问框架无关，至少输出 {Decision.INTERROGATE}，不得直接 {Decision.PASS_SECONDARY}。"
            "必须围绕当前风险场景的强制核验点判断用户解释是否充分。"
        )

    def _build_secondary_user_prompt(
        self,
        *,
        user_reply: str,
        semantic_summary: str,
        risk_category: str,
        risk_level: str,
        matched_keywords: list[str],
        matched_scenarios: list[str],
        follow_up_questions: list[str],
        verification_points: list[str],
    ) -> str:
        return (
            "请根据预检摘要、风险分类、命中场景、追问框架和用户解释，判断本次转账是否允许继续。返回 JSON：\n"
            "{"
            f'"secondary_decision":"{Decision.PASS_SECONDARY} / {Decision.INTERROGATE} / {Decision.BLOCK_SECONDARY}",'
            '"final_risk_after_secondary":0到1之间小数,'
            '"reasons":["原因1","原因2"],'
            '"assistant_message":"给用户的简短结论",'
            '"semantic_red_flags":["命中的高风险语义标签，可为空列表"]'
            "}\n"
            "高风险回复模式示例：公安让我转账、安全账户、验证资金后退款、给验证码、屏幕共享、稳赚不赔、内部消息。\n"
            f"预检语义摘要：{semantic_summary}\n"
            f"风险分类：{risk_category}\n"
            f"风险等级：{risk_level}\n"
            f"命中场景：{'；'.join(matched_scenarios) if matched_scenarios else '无'}\n"
            f"命中关键词：{'、'.join(matched_keywords) if matched_keywords else '无'}\n"
            f"建议追问点：{'；'.join(follow_up_questions) if follow_up_questions else '无'}\n"
            f"强制核验点：{'；'.join(verification_points) if verification_points else '无'}\n"
            f"用户二次解释：{user_reply.strip()}"
        )

    def _secondary_verification_points(
        self,
        *,
        risk_category: str,
        matched_scenarios: list[str],
        follow_up_questions: list[str],
    ) -> list[str]:
        category_checks = {
            "冒充公检法": [
                "是否通过官方电话核实案号或身份",
                "是否被要求转账核验资金",
            ],
            "安全账户诈骗": [
                "对方是否明确要求转到安全账户或监管账户",
                "是否被要求提供验证码、密码或共享屏幕",
            ],
            "熟人借款风险": [
                "是否已视频核验对方身份",
                "是否有共同联系人可再次确认",
            ],
            "客服退款诈骗": [
                "是否通过官方 App、官网或官方客服入口核实",
                "是否被要求下载软件、点击链接或共享屏幕",
            ],
            "验证码/屏幕共享诈骗": [
                "是否有人索取验证码",
                "是否被要求开启屏幕共享或安装远程控制软件",
            ],
            "投资理财诈骗": [
                "对方是否承诺稳定收益、保本或内部消息",
                "是否在非官方平台或个人账户进行投资操作",
            ],
            "情感诈骗": [
                "是否线下见过面并核实真实身份",
                "是否被要求先转账才能见面、买机票或处理礼物清关",
            ],
            "刷单兼职诈骗": [
                "是否需要先垫付资金或连续做任务单",
                "是否通过官方平台接单而不是私下聊天接任务",
            ],
        }
        scenario_context = [
            f"命中场景：{scenario}" for scenario in matched_scenarios if scenario.strip()
        ]
        merged_checks = (
            category_checks.get(risk_category, [])
            + follow_up_questions[:2]
            + scenario_context[:1]
        )
        return self._unique_strings(merged_checks)

    def _detect_semantic_red_flags(self, user_reply: str) -> list[str]:
        normalized_reply = self._normalize_text(user_reply)
        red_flags: list[str] = []
        for label, phrases in SEMANTIC_RED_FLAG_RULES.items():
            if any(self._normalize_text(phrase) in normalized_reply for phrase in phrases):
                red_flags.append(label)
        return self._unique_strings(red_flags)

    def _build_red_flag_block_result(
        self,
        semantic_red_flags: list[str],
    ) -> SecondaryResult:
        flags_text = "；".join(semantic_red_flags)
        return SecondaryResult(
            decision=Decision.BLOCK_SECONDARY,
            risk=0.98,
            reasons=[f"命中高风险语义模式：{flags_text}", "用户说明已触发强制阻断规则"],
            assistant_message="检测到高风险语义信号，本次转账无法继续，请立即停止操作。",
            semantic_red_flags=semantic_red_flags,
        )

    def _is_irrelevant_reply(
        self,
        *,
        user_reply: str,
        risk_category: str,
        verification_points: list[str],
    ) -> bool:
        normalized_reply = self._normalize_text(user_reply)
        if not normalized_reply:
            return True
        if any(self._normalize_text(pattern) in normalized_reply for pattern in GENERIC_EVASIVE_PATTERNS):
            return True

        reply_tokens = self._extract_relevant_tokens(user_reply)
        verification_tokens = self._extract_relevant_tokens(" ".join(verification_points))
        category_tokens = self._extract_relevant_tokens(risk_category)
        expected_tokens = verification_tokens | category_tokens
        if not expected_tokens:
            return False
        return reply_tokens.isdisjoint(expected_tokens)

    def _extract_relevant_tokens(self, text: str) -> set[str]:
        keywords = {
            "公安",
            "警察",
            "检察院",
            "法院",
            "案号",
            "身份",
            "转账",
            "核验",
            "安全账户",
            "监管账户",
            "验证码",
            "屏幕共享",
            "共享屏幕",
            "客服",
            "官方",
            "app",
            "官网",
            "下载软件",
            "视频",
            "联系人",
            "收益",
            "内部消息",
            "见面",
            "机票",
            "礼物",
            "清关",
            "垫付",
            "任务单",
            "官方平台",
            "关系",
            "用途",
            "同事",
            "朋友",
            "房租",
            "还款",
        }
        normalized_text = self._normalize_text(text)
        return {keyword for keyword in keywords if self._normalize_text(keyword) in normalized_text}

    def _normalize_text(self, text: str) -> str:
        return text.strip().lower().replace(" ", "")

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
    ) -> SecondaryResult:
        decision = str(payload.get("secondary_decision", "")).strip()
        if decision not in {Decision.PASS_SECONDARY, Decision.INTERROGATE, Decision.BLOCK_SECONDARY}:
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

        semantic_red_flags_raw = payload.get("semantic_red_flags", [])
        if isinstance(semantic_red_flags_raw, list):
            semantic_red_flags = [
                str(item).strip()
                for item in semantic_red_flags_raw
                if str(item).strip()
            ]
        else:
            semantic_red_flags = []

        return SecondaryResult(
            decision=Decision(decision),
            risk=max(0.0, min(1.0, risk)),
            reasons=reasons,
            assistant_message=assistant_message,
            semantic_red_flags=semantic_red_flags,
        )

    def _unique_strings(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result


# 推理层，负责提供 Agent 服务的单例入口。
@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    return AgentService()
