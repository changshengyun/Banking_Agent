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
)
from .risk_engine import RiskAssessment, RiskEngine, RiskInput


class BankHostService:
    def __init__(self, repository: BankingRepository | None = None) -> None:
        self.repository = repository or BankingRepository()
        self.risk_engine = RiskEngine()

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
            demo_tip="演示模式已开启：异地、大额、首次收款人会触发 Agent 风控确认。",
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
        assessment = self.risk_engine.assess(
            RiskInput(
                payee_name=request.payee_name,
                amount=request.amount,
                current_city=request.context.current_city,
                is_known_payee=payee is not None,
                common_cities=common_cities,
                recent_transfer_count=self.repository.recent_outgoing_transfer_count(),
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
            reasons=assessment.reasons,
        )
        return TransferPrecheckResponse(
            decision=assessment.decision,
            risk_level=assessment.risk_level,
            reasons=assessment.reasons,
            confirmation_token=token,
            assistant_message=assistant_message,
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
            assistant_message="转账已完成，模拟账户余额和交易记录已同步更新。",
            cash_balance=account["cash_balance"],
            wealth_balance=account["wealth_balance"],
            total_assets=round(account["cash_balance"] + account["wealth_balance"], 2),
            latest_transaction=latest_transaction,
        )

    def explain_last_risk_event(self) -> str:
        event = self.repository.get_latest_risk_event()
        if event is None:
            return "当前没有最近的风控记录，系统将继续监测地点、金额与收款人变化。"
        reasons = "；".join(event["reasons"])
        return (
            f"最近一次风控事件发生在 {event['city']}，风险等级为 {event['risk_level']}。"
            f"系统给出的原因是：{reasons}"
        )

    def build_bill_summary(self) -> str:
        summary = self.repository.get_spending_summary()
        if not summary:
            return "最近暂无支出记录。"
        parts = [f"{item['category']} {item['total_amount']:.2f} 元" for item in summary]
        return "近期待支出主要集中在：" + "，".join(parts) + "。"

    def _build_transfer_message(
        self, request: TransferPrecheckRequest, assessment: RiskAssessment
    ) -> str:
        if assessment.decision == "pass":
            return (
                f"已完成转账预检。收款人 {request.payee_name}、金额 {request.amount:.2f} 元"
                " 未触发高风险规则，可直接执行模拟转账。"
            )
        reasons_text = "；".join(assessment.reasons)
        return (
            f"本次转账需要二次确认。系统检测到：{reasons_text}"
            "。如果这确实是你本人操作，可点击确认继续。"
        )


@lru_cache(maxsize=1)
def get_bank_host_service() -> BankHostService:
    return BankHostService()

