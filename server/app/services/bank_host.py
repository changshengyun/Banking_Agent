from __future__ import annotations

from functools import lru_cache

from ..repositories.banking import BankingRepository
from ..schemas.common import SpendingCategory, TransactionItem
from ..schemas.dashboard import DashboardResponse, TransactionsResponse
from ..schemas.transfer import (
    TransferConfirmRequest,
    TransferConfirmResponse,
    TransferPrecheckRequest,
    TransferPrecheckResponse,
    TransferSecondaryCheckRequest,
    TransferSecondaryCheckResponse,
)
from .risk_knowledge_base import get_risk_knowledge_base_service
from .risk_engine import RiskAssessment, RiskEngine, RiskInput


class BankHostService:
    def __init__(self, repository: BankingRepository | None = None) -> None:
        self.repository = repository or BankingRepository()
        self.risk_engine = RiskEngine()
        self.risk_knowledge = get_risk_knowledge_base_service()

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

    def get_user_profile(self) -> dict:
        return self.repository.get_user_profile()

    def get_common_locations(self) -> list[dict]:
        return self.repository.get_common_locations()

    def precheck_transfer(
        self, request: TransferPrecheckRequest
    ) -> TransferPrecheckResponse:
        common_locations = self.repository.get_common_locations()
        common_cities = [
            item["city"] for item in common_locations if int(item["is_common"]) == 1
        ]
        payee = self.repository.find_payee(request.payee_name)
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
        )

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

    def secondary_check_transfer(
        self, request: TransferSecondaryCheckRequest
    ) -> TransferSecondaryCheckResponse:
        pending = self.repository.get_pending_transfer(request.confirmation_token)
        if pending["decision"] == "block":
            raise ValueError("该转账已被预检拦截，无需执行二次校验。")
        if pending["decision"] == "pass":
            risk_classification = self.risk_knowledge.classify_text(
                text=pending["semantic_summary"],
                amount=float(pending["amount"]),
                current_city=pending["city"],
                common_cities=self._common_cities(),
                is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
            )
            return TransferSecondaryCheckResponse(
                secondary_decision="pass_secondary",
                reasons=["该交易为放行路径，无需二次质询。"],
                final_risk_after_secondary=float(pending["final_risk"]),
                assistant_message="当前交易已处于放行状态，可直接确认转账。",
                risk_classification=risk_classification,
            )

        from .agent_service import get_agent_service

        policy_version = "secondary_policy_v1"
        secondary_question = "请说明你与收款人的关系及本次转账的具体用途。"
        risk_classification = self.risk_knowledge.classify_text(
            text=f"{pending['semantic_summary']} {request.user_reply}",
            amount=float(pending["amount"]),
            current_city=pending["city"],
            common_cities=self._common_cities(),
            is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
        )
        (
            secondary_decision,
            secondary_risk,
            secondary_reasons,
            assistant_message,
        ) = get_agent_service().evaluate_secondary_intercept(
            user_reply=request.user_reply,
            semantic_summary=pending["semantic_summary"],
            risk_category=risk_classification.risk_category,
            risk_level=risk_classification.risk_level,
            matched_keywords=risk_classification.matched_keywords,
            follow_up_questions=risk_classification.follow_up_questions,
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
        return TransferSecondaryCheckResponse(
            secondary_decision=secondary_decision,
            reasons=secondary_reasons,
            final_risk_after_secondary=round(secondary_risk, 4),
            assistant_message=assistant_message,
            risk_classification=risk_classification,
        )

    def classify_transfer_risk(
        self, request: TransferPrecheckRequest
    ):
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

    def explain_last_risk_event(self) -> str:
        event = self.repository.get_latest_risk_event()
        if event is None:
            return "近期暂无风控事件，系统监测正常进行中。"
        reasons = "；".join(event["reasons"])
        risk_level = self._risk_level_label(event["risk_level"])
        return (
            f"最近一次风控事件发生在 {event['city']}，风险等级为{risk_level}，"
            f"综合风险分 {event['final_risk']:.2f}。触发原因：{reasons}"
        )

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

    def _risk_level_label(self, risk_level: str) -> str:
        mapping = {
            "high": "高风险",
            "medium": "中风险",
            "low": "低风险",
        }
        return mapping.get(risk_level.lower(), "未知风险")

    def _common_cities(self) -> list[str]:
        common_locations = self.repository.get_common_locations()
        return [item["city"] for item in common_locations if int(item["is_common"]) == 1]

    def _build_classification_text(
        self,
        *,
        payee_name: str,
        semantic_summary: str,
        recent_page: str,
        last_action: str,
    ) -> str:
        return " ".join(
            (
                payee_name,
                semantic_summary,
                recent_page,
                last_action,
            )
        ).strip()


@lru_cache(maxsize=1)
def get_bank_host_service() -> BankHostService:
    return BankHostService()
