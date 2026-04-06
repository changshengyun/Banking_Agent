from __future__ import annotations

from functools import lru_cache

from ..repositories.banking import BankingRepository
from ..schemas.common import SpendingCategory, TransactionItem
from ..schemas.dashboard import DashboardResponse, TransactionsResponse
from ..schemas.external_intelligence import ExternalIntelligenceReport
from ..schemas.transfer import (
    ExplainNode,
    ExplainPack,
    ExplainScoreBreakdown,
    TransferConfirmRequest,
    TransferConfirmResponse,
    TransferPrecheckRequest,
    TransferPrecheckResponse,
    TransferSecondaryCheckRequest,
    TransferSecondaryCheckResponse,
)
from .external_intelligence import get_external_intelligence_service
from .risk_engine import RiskAssessment, RiskEngine, RiskInput
from .risk_knowledge_base import get_risk_knowledge_base_service


class BankHostService:
    # HIRD-D: 治理层，负责装配银行宿主所需的数据仓库、评分引擎和外部情报能力。
    def __init__(self, repository: BankingRepository | None = None) -> None:
        self.repository = repository or BankingRepository()
        self.risk_engine = RiskEngine()
        self.risk_knowledge = get_risk_knowledge_base_service()
        self.external_intelligence = get_external_intelligence_service()

    # HIRD-H: 感知层，负责聚合首页资产、账单和提示信息。
    def get_dashboard(self) -> DashboardResponse:
        account = self.repository.get_account()
        profile = self.repository.get_user_profile()
        transactions = self.list_transactions(limit=6)
        spending_summary = [
            SpendingCategory(**item) for item in self.repository.get_spending_summary()
        ]
        return DashboardResponse(
            user_name=profile["name"],
            cash_balance=account["cash_balance"],
            wealth_balance=account["wealth_balance"],
            total_assets=round(account["cash_balance"] + account["wealth_balance"], 2),
            currency=account["currency"],
            recent_transactions=transactions.items,
            spending_summary=spending_summary,
            demo_tip="演示模式已开启：系统会重点监测异地、大额与新增收款人等风险特征。",
        )

    # HIRD-H: 感知层，负责读取交易列表与消费分类汇总。
    def list_transactions(self, limit: int = 20) -> TransactionsResponse:
        items = [
            TransactionItem(
                **{
                    **item,
                    "is_income": bool(item["is_income"]),
                }
            )
            for item in self.repository.list_transactions(limit=limit)
        ]
        spending_summary = [
            SpendingCategory(**item) for item in self.repository.get_spending_summary()
        ]
        return TransactionsResponse(items=items, spending_summary=spending_summary)

    # HIRD-H: 感知层，负责读取当前用户画像。
    def get_user_profile(self) -> dict:
        return self.repository.get_user_profile()

    # HIRD-H: 感知层，负责读取常用地理位置画像。
    def get_common_locations(self) -> list[dict]:
        return self.repository.get_common_locations()

    # HIRD-D: 治理层，负责执行预检、落库待确认转账并返回风控解释。
    def precheck_transfer(
        self, request: TransferPrecheckRequest
    ) -> TransferPrecheckResponse:
        common_cities = self._common_cities()
        payee = self.repository.find_payee(request.payee_name)
        external_intelligence = self.screen_external_intelligence(request.payee_name)
        risk_classification = self.risk_knowledge.classify_text(
            text=self._build_classification_text(
                payee_name=request.payee_name,
                semantic_summary=request.context.semantic_summary,
                recent_page=request.context.recent_page,
                last_action=request.context.last_action,
            ),
            amount=request.amount,
            current_city=request.context.current_city,
            common_cities=common_cities,
            is_known_payee=payee is not None,
        )
        assessment = self.risk_engine.assess(
            RiskInput(
                payee_name=request.payee_name,
                amount=request.amount,
                current_city=request.context.current_city,
                is_known_payee=payee is not None,
                common_cities=common_cities,
                recent_transfer_count=self.repository.recent_outgoing_transfer_count(),
                recent_page=request.context.recent_page,
                last_action=request.context.last_action,
                semantic_summary=request.context.semantic_summary,
                classification_risk_level=risk_classification.risk_level,
                classification_category=risk_classification.risk_category,
                classification_block_hint=risk_classification.block_hint,
                classification_keywords=risk_classification.matched_keywords,
                classification_scenarios=risk_classification.matched_scenarios,
                external_intelligence_risk_level=external_intelligence.max_risk_level,
                external_intelligence_hits=[
                    hit.summary for hit in external_intelligence.hits
                ],
                external_intelligence_block_hint=any(
                    hit.block_hint for hit in external_intelligence.hits
                ),
                input_pause_count=request.context.input_pause_count,
                input_duration_ms=request.context.input_duration_ms,
                extra_signals=request.context.extra_signals,
            )
        )
        assistant_message = self._build_transfer_message(request, assessment)
        token = self.repository.create_pending_transfer(
            payee_name=request.payee_name,
            amount=request.amount,
            city=request.context.current_city,
            device_id=request.context.device_id,
            recent_page=request.context.recent_page,
            last_action=request.context.last_action,
            semantic_summary=request.context.semantic_summary,
            risk_level=assessment.risk_level,
            decision=assessment.decision,
            flag_s=assessment.flag_s,
            g_behavior=assessment.g_behavior,
            g_dynamic=assessment.g_dynamic,
            final_risk=assessment.final_risk,
            reasons=assessment.reasons,
            assistant_message=assistant_message,
        )
        self.repository.create_risk_event(
            payee_name=request.payee_name,
            amount=request.amount,
            city=request.context.current_city,
            device_id=request.context.device_id,
            risk_level=assessment.risk_level,
            decision=assessment.decision,
            flag_s=assessment.flag_s,
            g_behavior=assessment.g_behavior,
            g_dynamic=assessment.g_dynamic,
            final_risk=assessment.final_risk,
            reasons=assessment.reasons,
        )
        explain_pack = self._build_precheck_explain_pack(
            assessment=assessment,
            risk_category=risk_classification.risk_category,
            risk_level=risk_classification.risk_level,
            decision=assessment.decision,
            reasons=assessment.reasons,
            external_intelligence=external_intelligence,
        )
        return TransferPrecheckResponse(
            decision=assessment.decision,
            risk_level=assessment.risk_level,
            flag_s=assessment.flag_s,
            g_behavior=assessment.g_behavior,
            g_dynamic=assessment.g_dynamic,
            final_risk=assessment.final_risk,
            reasons=assessment.reasons,
            confirmation_token=token,
            assistant_message=assistant_message,
            risk_classification=risk_classification,
            external_intelligence=external_intelligence,
            explain_pack=explain_pack,
        )

    # HIRD-D: 治理层，负责真正提交已通过风控门禁的转账。
    def confirm_transfer(
        self, request: TransferConfirmRequest
    ) -> TransferConfirmResponse:
        payload = self.repository.commit_transfer(request.confirmation_token)
        account = payload["account"]
        latest_transaction = TransactionItem(
            **{
                **payload["transaction"],
                "is_income": bool(payload["transaction"]["is_income"]),
            }
        )
        return TransferConfirmResponse(
            success=True,
            assistant_message="转账已完成，余额与交易记录已更新。",
            cash_balance=account["cash_balance"],
            wealth_balance=account["wealth_balance"],
            total_assets=round(account["cash_balance"] + account["wealth_balance"], 2),
            latest_transaction=latest_transaction,
        )

    # HIRD-D: 治理层，负责执行二次质询、落库审计信息并返回复核结果。
    def secondary_check_transfer(
        self, request: TransferSecondaryCheckRequest
    ) -> TransferSecondaryCheckResponse:
        pending = self.repository.get_pending_transfer(request.confirmation_token)
        if pending["decision"] == "block":
            raise ValueError("该转账已被预检拦截，无需执行二次校验。")

        if pending["decision"] == "pass":
            external_intelligence = self.screen_external_intelligence(
                pending["payee_name"]
            )
            risk_classification = self.risk_knowledge.classify_text(
                text=pending["semantic_summary"],
                amount=float(pending["amount"]),
                current_city=pending["city"],
                common_cities=self._common_cities(),
                is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
            )
            explain_pack = self._build_secondary_explain_pack(
                flag_s=float(pending["flag_s"]),
                g_behavior=float(pending["g_behavior"]),
                g_dynamic=float(pending["g_dynamic"]),
                final_risk=float(pending["final_risk"]),
                decision="pass_secondary",
                reasons=["该交易为放行路径，无需二次质询。"],
                risk_category=risk_classification.risk_category,
                risk_level=risk_classification.risk_level,
                external_intelligence=external_intelligence,
            )
            return TransferSecondaryCheckResponse(
                secondary_decision="pass_secondary",
                reasons=["该交易为放行路径，无需二次质询。"],
                final_risk_after_secondary=float(pending["final_risk"]),
                assistant_message="当前交易已处于放行状态，可直接确认转账。",
                semantic_red_flags=[],
                risk_classification=risk_classification,
                external_intelligence=external_intelligence,
                explain_pack=explain_pack,
            )

        from .agent_service import get_agent_service

        policy_version = "secondary_policy_v1"
        anchor_classification = self.risk_knowledge.classify_text(
            text=pending["semantic_summary"],
            amount=float(pending["amount"]),
            current_city=pending["city"],
            common_cities=self._common_cities(),
            is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
        )
        secondary_question = self._select_secondary_question(
            anchor_classification.follow_up_questions
        )
        risk_classification = self.risk_knowledge.classify_text(
            text=f"{pending['semantic_summary']} {request.user_reply}".strip(),
            amount=float(pending["amount"]),
            current_city=pending["city"],
            common_cities=self._common_cities(),
            is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
        )
        external_intelligence = self.screen_external_intelligence(pending["payee_name"])
        (
            secondary_decision,
            secondary_risk,
            secondary_reasons,
            assistant_message,
            semantic_red_flags,
        ) = get_agent_service().evaluate_secondary_intercept(
            user_reply=request.user_reply,
            semantic_summary=pending["semantic_summary"],
            risk_category=anchor_classification.risk_category,
            risk_level=anchor_classification.risk_level,
            matched_keywords=anchor_classification.matched_keywords,
            matched_scenarios=anchor_classification.matched_scenarios,
            follow_up_questions=anchor_classification.follow_up_questions,
        )

        self.repository.update_secondary_check(
            confirmation_token=request.confirmation_token,
            secondary_decision=secondary_decision,
            secondary_risk=secondary_risk,
            secondary_reasons=secondary_reasons,
            secondary_question=secondary_question,
            secondary_reply=request.user_reply,
            policy_version=policy_version,
        )
        self.repository.create_risk_event(
            payee_name=pending["payee_name"],
            amount=pending["amount"],
            city=pending["city"],
            device_id=request.context.device_id,
            risk_level="high" if secondary_decision == "block_secondary" else "medium",
            decision=secondary_decision,
            flag_s=float(pending["flag_s"]),
            g_behavior=float(pending["g_behavior"]),
            g_dynamic=float(pending["g_dynamic"]),
            final_risk=float(pending["final_risk"]),
            reasons=secondary_reasons,
            secondary_decision=secondary_decision,
            secondary_risk=secondary_risk,
            secondary_reply=request.user_reply,
            policy_version=policy_version,
        )
        explain_pack = self._build_secondary_explain_pack(
            flag_s=float(pending["flag_s"]),
            g_behavior=float(pending["g_behavior"]),
            g_dynamic=float(pending["g_dynamic"]),
            final_risk=secondary_risk,
            decision=secondary_decision,
            reasons=secondary_reasons,
            risk_category=risk_classification.risk_category,
            risk_level=risk_classification.risk_level,
            external_intelligence=external_intelligence,
        )
        return TransferSecondaryCheckResponse(
            secondary_decision=secondary_decision,
            reasons=secondary_reasons,
            final_risk_after_secondary=round(secondary_risk, 4),
            assistant_message=assistant_message,
            semantic_red_flags=semantic_red_flags,
            risk_classification=risk_classification,
            external_intelligence=external_intelligence,
            explain_pack=explain_pack,
        )

    # HIRD-I: 识别层，负责提供独立的风险分类接口结果。
    def classify_transfer_risk(self, request: TransferPrecheckRequest):
        payee = self.repository.find_payee(request.payee_name)
        return self.risk_knowledge.classify_text(
            text=self._build_classification_text(
                payee_name=request.payee_name,
                semantic_summary=request.context.semantic_summary,
                recent_page=request.context.recent_page,
                last_action=request.context.last_action,
            ),
            amount=request.amount,
            current_city=request.context.current_city,
            common_cities=self._common_cities(),
            is_known_payee=payee is not None,
        )

    # HIRD-H: 感知层，负责筛查收款人的外部情报名单命中。
    def screen_external_intelligence(
        self,
        payee_name: str,
    ) -> ExternalIntelligenceReport:
        return self.external_intelligence.screen_payee(payee_name=payee_name)

    # HIRD-R: 推理层，负责把最近风控事件汇总为可读说明。
    def explain_last_risk_event(self) -> str:
        event = self.repository.get_latest_risk_event()
        if event is None:
            return "近期暂无风控事件，系统监测正常进行中。"
        reasons = "；".join(event["reasons"])
        risk_level = self._risk_level_label(event["risk_level"])
        return (
            f"最近一次风控事件发生在 {event['city']}，风险等级为 {risk_level}，"
            f"综合风险分 {event['final_risk']:.2f}。触发原因：{reasons}"
        )

    # HIRD-H: 感知层，负责生成账单摘要供聊天与前端展示使用。
    def build_bill_summary(self) -> str:
        summary = self.repository.get_spending_summary()
        if not summary:
            return "近期暂无消费记录。"
        category_labels = {
            "food": "餐饮",
            "transport": "交通",
            "shopping": "购物",
            "transfer": "转账",
            "income": "收入",
        }
        parts = [
            f"{category_labels.get(item['category'], item['category'])} {item['total_amount']:.2f} 元"
            for item in summary
        ]
        return "近期消费主要集中在：" + "；".join(parts) + "。"

    # HIRD-D: 治理层，负责把预检决策翻译成用户可读的提示文案。
    def _build_transfer_message(
        self, request: TransferPrecheckRequest, assessment: RiskAssessment
    ) -> str:
        if assessment.decision == "pass":
            return (
                f"预检完成：收款人 {request.payee_name}，金额 {request.amount:.2f} 元。"
                "当前未命中高风险规则，可继续转账。"
            )
        if assessment.decision == "interrogate":
            reasons_text = "；".join(assessment.reasons)
            return (
                f"本次转账需要补充确认。识别到的风险信号：{reasons_text}。"
                "请核实收款人身份与转账用途。"
            )
        reasons_text = "；".join(assessment.reasons)
        return (
            f"本次转账已被拦截。识别到的风险信号：{reasons_text}。"
            "如需继续，请联系人工客服进行核验。"
        )

    # HIRD-R: 推理层，负责将风险等级代码转换成可读标签。
    def _risk_level_label(self, risk_level: str) -> str:
        mapping = {
            "high": "高风险",
            "medium": "中风险",
            "low": "低风险",
        }
        return mapping.get(risk_level.lower(), "未知风险")

    # HIRD-H: 感知层，负责提取用户常用城市清单。
    def _common_cities(self) -> list[str]:
        common_locations = self.repository.get_common_locations()
        return [item["city"] for item in common_locations if int(item["is_common"]) == 1]

    # HIRD-R: 推理层，负责从场景追问列表中选择当前二次质询使用的主问题。
    def _select_secondary_question(self, follow_up_questions: list[str]) -> str:
        if follow_up_questions:
            return follow_up_questions[0]
        return "请说明你与收款人的关系及本次转账的具体用途。"

    # HIRD-R: 推理层，负责构建预检解释包供前端展示。
    def _build_precheck_explain_pack(
        self,
        *,
        assessment: RiskAssessment,
        risk_category: str,
        risk_level: str,
        decision: str,
        reasons: list[str],
        external_intelligence: ExternalIntelligenceReport,
    ) -> ExplainPack:
        headline = (
            f"风险分类：{risk_category}（{self._risk_level_label(risk_level)}）"
            if risk_category
            else "风险分类：待补充判断"
        )
        return ExplainPack(
            headline=headline,
            recommended_action=self._recommended_action(decision),
            score_breakdown=ExplainScoreBreakdown(
                flag_s=assessment.flag_s,
                g_behavior=assessment.g_behavior,
                g_dynamic=assessment.g_dynamic,
                final_risk=assessment.final_risk,
            ),
            nodes=self._build_explain_nodes(
                flag_s=assessment.flag_s,
                g_behavior=assessment.g_behavior,
                g_dynamic=assessment.g_dynamic,
                final_risk=assessment.final_risk,
                decision=decision,
                reasons=reasons,
                risk_category=risk_category,
                external_intelligence=external_intelligence,
            ),
        )

    # HIRD-R: 推理层，负责构建二次校验解释包供前端展示。
    def _build_secondary_explain_pack(
        self,
        *,
        flag_s: float,
        g_behavior: float,
        g_dynamic: float,
        final_risk: float,
        decision: str,
        reasons: list[str],
        risk_category: str,
        risk_level: str,
        external_intelligence: ExternalIntelligenceReport,
    ) -> ExplainPack:
        headline = (
            f"二次校验：{risk_category}（{self._risk_level_label(risk_level)}）"
            if risk_category
            else "二次校验：风险复核完成"
        )
        return ExplainPack(
            headline=headline,
            recommended_action=self._recommended_action(decision),
            score_breakdown=ExplainScoreBreakdown(
                flag_s=round(flag_s, 4),
                g_behavior=round(g_behavior, 4),
                g_dynamic=round(g_dynamic, 4),
                final_risk=round(final_risk, 4),
            ),
            nodes=self._build_explain_nodes(
                flag_s=flag_s,
                g_behavior=g_behavior,
                g_dynamic=g_dynamic,
                final_risk=final_risk,
                decision=decision,
                reasons=reasons,
                risk_category=risk_category,
                external_intelligence=external_intelligence,
            ),
        )

    # HIRD-R: 推理层，负责把评分、原因和情报命中组装成解释节点。
    def _build_explain_nodes(
        self,
        *,
        flag_s: float,
        g_behavior: float,
        g_dynamic: float,
        final_risk: float,
        decision: str,
        reasons: list[str],
        risk_category: str,
        external_intelligence: ExternalIntelligenceReport,
    ) -> list[ExplainNode]:
        reason_summary = "；".join(reasons[:3]) if reasons else "未命中显著风险原因。"
        return [
            ExplainNode(
                id="static",
                title="静态风险",
                level=self._score_level(flag_s),
                summary="常用地、金额与收款人画像判断。",
                detail=reason_summary,
                score=round(flag_s, 4),
            ),
            ExplainNode(
                id="behavior",
                title="行为风险",
                level=self._score_level(g_behavior),
                summary="基于页面、操作轨迹与输入行为信号评估。",
                detail="结合 recent_page、last_action、输入停顿与输入时长等信号综合判断。",
                score=round(g_behavior, 4),
            ),
            ExplainNode(
                id="semantic",
                title="语义风险",
                level=self._score_level(g_dynamic),
                summary=f"基于知识库场景匹配：{risk_category or '正常转账'}。",
                detail="结合风险关键词、场景标签、追问建议与补充说明进行识别。",
                score=round(g_dynamic, 4),
            ),
            self._build_external_intelligence_node(external_intelligence),
            ExplainNode(
                id="decision",
                title="最终决策",
                level=self._decision_level(decision, final_risk),
                summary=f"当前决策：{decision}。",
                detail=self._recommended_action(decision),
                score=round(final_risk, 4),
            ),
        ]

    # HIRD-H: 感知层，负责把外部情报命中转换成解释节点。
    def _build_external_intelligence_node(
        self,
        external_intelligence: ExternalIntelligenceReport,
    ) -> ExplainNode:
        if external_intelligence.status != "hit":
            return ExplainNode(
                id="external_intelligence",
                title="外部情报",
                level="low",
                summary="未命中外部名单或负面情报。",
                detail="当前未发现需要额外升级的外部背景调查信号。",
                score=0.0,
            )

        top_hit = external_intelligence.hits[0]
        detail = "；".join(hit.detail for hit in external_intelligence.hits[:2])
        return ExplainNode(
            id="external_intelligence",
            title="外部情报",
            level=external_intelligence.max_risk_level,
            summary=top_hit.summary,
            detail=detail,
            score=round(external_intelligence.max_score, 4),
        )

    # HIRD-D: 治理层，负责把决策代码映射成操作建议。
    def _recommended_action(self, decision: str) -> str:
        if decision in {"pass", "pass_secondary"}:
            return "可继续确认转账"
        if decision in {"interrogate", "review"}:
            return "请完成补充说明后再确认"
        return "建议中止转账并联系人工客服核验"

    # HIRD-R: 推理层，负责把分值区间映射为风险等级。
    def _score_level(self, score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"

    # HIRD-D: 治理层，负责把最终决策映射为解释面板中的风险等级。
    def _decision_level(self, decision: str, final_risk: float) -> str:
        if decision in {"block", "block_secondary"}:
            return "high"
        if decision in {"interrogate", "review"}:
            return "medium"
        return self._score_level(final_risk)

    # HIRD-I: 识别层，负责为风险知识分类提取可用于语义识别的用户说明文本。
    def _build_classification_text(
        self,
        *,
        payee_name: str,
        semantic_summary: str,
        recent_page: str,
        last_action: str,
    ) -> str:
        return semantic_summary.strip()


# HIRD-D: 治理层，负责提供银行宿主服务的单例入口。
@lru_cache(maxsize=1)
def get_bank_host_service() -> BankHostService:
    return BankHostService()

