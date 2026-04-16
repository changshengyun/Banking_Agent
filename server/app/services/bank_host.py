from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import time

from ..errors import NotFoundError
from ..repositories.banking import BankingRepository
from ..schemas.common import SpendingCategory, TransactionItem
from ..schemas.dashboard import DashboardResponse, TransactionsResponse
from ..schemas.external_intelligence import ExternalIntelligenceReport
from ..schemas.manual_review import ManualReviewCreateRequest
from ..schemas.manual_review import ManualReviewDetailPayload
from ..schemas.manual_review import ManualReviewListResponsePayload
from ..schemas.manual_review import ManualReviewQueueItemPayload
from ..schemas.manual_review import ManualReviewQueueResponsePayload
from ..schemas.manual_review import ManualReviewSnapshotPayload
from ..schemas.manual_review import ManualReviewSummaryPayload
from ..schemas.manual_review import ManualReviewUpdateRequest
from ..schemas.report import RiskReportListItemPayload
from ..schemas.report import RiskReportListResponsePayload
from ..schemas.report import RiskReportGovernancePayload
from ..schemas.report import RiskReportPayload
from ..schemas.risk import RiskClassificationPayload
from ..schemas.transfer import (
    TransferCancelRequest,
    TransferCancelResponse,
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
from .pii_masker import PiiMasker
from ..utils.executor_utils import get_global_executor
from .risk_report_service import get_risk_report_service
from .risk_engine import RiskAssessment, RiskEngine, RiskInput
from .risk_knowledge_base import get_risk_knowledge_base_service


class BankHostService:
    REASON_NON_PENDING_STATUS = "non_pending_status"
    REASON_PRECHECK_BLOCKED = "precheck_blocked"
    REASON_SECONDARY_NOT_PASSED = "secondary_not_passed"
    REASON_DUPLICATE_SECONDARY_SUBMISSION = "duplicate_secondary_submission"

    ERROR_SECONDARY_SINGLE_ROUND = "二次质询本轮仅允许一次提交，请重新发起转账或取消交易。"
    ERROR_CONFIRM_SECONDARY_NOT_PASSED = "该转账尚未通过二次校验，无法继续确认。"

    # HIRD-D: 治理层，负责装配银行宿主所需的数据仓库、评分引擎和外部情报能力。
    def __init__(self, repository: BankingRepository | None = None) -> None:
        self.repository = repository or BankingRepository()
        self.risk_engine = RiskEngine()
        self.risk_knowledge = get_risk_knowledge_base_service()
        self.risk_report_service = get_risk_report_service()
        self.external_intelligence = get_external_intelligence_service()
        self._executor = get_global_executor()

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
        total_started_at = time.perf_counter()
        common_cities = self._common_cities()
        payee = self.repository.find_payee(request.payee_name)
        is_known_payee = payee is not None
        # 演示环境：小a-小f 是模拟的已知/未知收款人，部分强制设定为已知以测试特定路径
        if request.payee_name in {"小a", "小b", "小c"}:
            is_known_payee = True

        confirmation_token = self.repository.build_confirmation_token()
        self._write_trace_event(
            confirmation_token=confirmation_token,
            event_type="precheck_started",
            stage="precheck",
            decision="pending",
            risk_level="pending",
            final_risk=0.0,
            payload={
                "payee_name": request.payee_name,
                "amount": request.amount,
                "current_city": request.context.current_city,
                "recent_page": request.context.recent_page,
                "last_action": request.context.last_action,
                "semantic_summary": PiiMasker.mask_text(request.context.semantic_summary),
                "perception_snapshot": self._build_perception_snapshot(
                    current_city=request.context.current_city,
                    recent_page=request.context.recent_page,
                    last_action=request.context.last_action,
                    semantic_summary=request.context.semantic_summary,
                    input_pause_count=request.context.input_pause_count,
                    input_duration_ms=request.context.input_duration_ms,
                    extra_signals=request.context.extra_signals,
                    external_intelligence=None,
                    is_known_payee=is_known_payee,
                ),
            },
        )
        external_started_at = time.perf_counter()
        # Parallelize external intelligence screening and risk classification
        future_external = self._executor.submit(self._call_with_timing, self.screen_external_intelligence, request.payee_name)
        future_classification = self._executor.submit(
            self._call_with_timing,
            self.risk_knowledge.classify_text,
            text=self._build_classification_text(
                payee_name=request.payee_name,
                semantic_summary=request.context.semantic_summary,
                recent_page=request.context.recent_page,
                last_action=request.context.last_action,
            ),
            amount=request.amount,
            current_city=request.context.current_city,
            common_cities=common_cities,
            is_known_payee=is_known_payee,
        )

        external_intelligence, external_intelligence_ms = future_external.result()
        risk_classification, classification_ms = future_classification.result()

        c_match = self._derive_c_match(risk_classification)
        engine_started_at = time.perf_counter()
        assessment = self.risk_engine.assess(
            RiskInput(
                payee_name=request.payee_name,
                amount=request.amount,
                current_city=request.context.current_city,
                is_known_payee=is_known_payee,
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
                c_match=c_match,
            )
        )
        engine_ms = self._elapsed_ms(engine_started_at)
        assistant_message = self._build_transfer_message(request, assessment)
        persistence_started_at = time.perf_counter()
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
            confirmation_token=confirmation_token,
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
        persistence_ms = self._elapsed_ms(persistence_started_at)
        timing_total_ms = self._elapsed_ms(total_started_at)
        self._write_trace_event(
            confirmation_token=token,
            event_type="precheck_decided",
            stage="precheck",
            decision=assessment.decision,
            risk_level=assessment.risk_level,
            final_risk=assessment.final_risk,
            payload={
                "risk_category": risk_classification.risk_category,
                "classification_risk_level": risk_classification.risk_level,
                "matched_keywords": risk_classification.matched_keywords,
                "matched_scenarios": risk_classification.matched_scenarios,
                "external_intelligence_status": external_intelligence.status,
                "external_intelligence_hits": [
                    hit.summary for hit in external_intelligence.hits
                ],
                "reasons": assessment.reasons,
                "perception_snapshot": self._build_perception_snapshot(
                    current_city=request.context.current_city,
                    recent_page=request.context.recent_page,
                    last_action=request.context.last_action,
                    semantic_summary=request.context.semantic_summary,
                    input_pause_count=request.context.input_pause_count,
                    input_duration_ms=request.context.input_duration_ms,
                    extra_signals=request.context.extra_signals,
                    external_intelligence=external_intelligence,
                    is_known_payee=is_known_payee,
                ),
                "timing_total_ms": timing_total_ms,
                "timing_external_intelligence_ms": external_intelligence_ms,
                "timing_classification_ms": classification_ms,
                "timing_engine_ms": engine_ms,
                "timing_persistence_ms": persistence_ms,
            },
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
        transfer = self.repository.get_transfer_record(request.confirmation_token)
        if transfer is None:
            raise ValueError("未找到待确认转账，或该转账已处理完成。")
        if transfer["status"] != "pending":
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="confirm",
                decision=transfer.get("decision"),
                risk_level=transfer.get("risk_level"),
                final_risk=float(transfer.get("final_risk") or 0.0),
                payload={
                    "reason": self.REASON_NON_PENDING_STATUS,
                    "status": transfer["status"],
                },
            )
            raise ValueError("未找到待确认转账，或该转账已处理完成。")
        if transfer["decision"] == "block":
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="confirm",
                decision=transfer["decision"],
                risk_level=transfer["risk_level"],
                final_risk=float(transfer["final_risk"]),
                payload={"reason": self.REASON_PRECHECK_BLOCKED},
            )
            raise ValueError("该转账已被风控拦截，无法继续确认。")
        if (
            transfer["decision"] == "interrogate"
            and transfer.get("secondary_decision") != "pass_secondary"
        ):
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="confirm",
                decision=transfer.get("secondary_decision") or transfer["decision"],
                risk_level=transfer["risk_level"],
                final_risk=float(transfer.get("secondary_risk") or transfer["final_risk"]),
                payload={
                    "reason": self.REASON_SECONDARY_NOT_PASSED,
                    "secondary_decision": transfer.get("secondary_decision"),
                },
            )
            raise ValueError(self.ERROR_CONFIRM_SECONDARY_NOT_PASSED)
        payload = self.repository.commit_transfer(request.confirmation_token)
        self._write_trace_event(
            confirmation_token=request.confirmation_token,
            event_type="transfer_confirmed",
            stage="confirm",
            decision=transfer.get("secondary_decision") or transfer["decision"],
            risk_level=transfer["risk_level"],
            final_risk=float(transfer.get("secondary_risk") or transfer["final_risk"]),
            payload={
                "payee_name": transfer["payee_name"],
                "amount": float(transfer["amount"]),
                "status": "committed",
            },
        )
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

    # HIRD-E: 业务执行层，负责显式取消待确认交易，避免与普通关闭弹窗混淆。
    def cancel_transfer(
        self, request: TransferCancelRequest
    ) -> TransferCancelResponse:
        transfer = self.repository.get_transfer_record(request.confirmation_token)
        if transfer is None:
            raise ValueError("未找到对应转账记录。")
        if transfer["status"] != "pending":
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="cancel",
                decision=transfer.get("decision"),
                risk_level=transfer.get("risk_level"),
                final_risk=float(transfer.get("final_risk") or 0.0),
                payload={
                    "reason": self.REASON_NON_PENDING_STATUS,
                    "status": transfer["status"],
                },
            )
            raise ValueError("该转账已非待确认状态，无法取消。")
        payload = self.repository.cancel_pending_transfer(request.confirmation_token)
        self._write_trace_event(
            confirmation_token=request.confirmation_token,
            event_type="transfer_cancelled",
            stage="cancel",
            decision=transfer["decision"],
            risk_level=transfer["risk_level"],
            final_risk=float(transfer["final_risk"]),
            payload={
                "payee_name": transfer["payee_name"],
                "amount": float(transfer["amount"]),
                "cancel_stage": self._cancel_stage(transfer),
                "secondary_decision": transfer.get("secondary_decision"),
                "status": "cancelled",
            },
        )
        return TransferCancelResponse(
            success=True,
            status=payload["status"],
            confirmation_token=payload["confirmation_token"],
            assistant_message=(
                f"已取消向 {payload['payee_name']} 转账 {payload['amount']:.2f} 元的待确认交易。"
            ),
        )

    # HIRD-D: 治理层，负责执行二次质询、落库审计信息并返回复核结果。
    def secondary_check_transfer(
        self, request: TransferSecondaryCheckRequest
    ) -> TransferSecondaryCheckResponse:
        total_started_at = time.perf_counter()
        transfer_status = self.repository.get_transfer_status(request.confirmation_token)
        if transfer_status is None:
            raise ValueError("未找到对应转账记录。")
        transfer = self.repository.get_transfer_record(request.confirmation_token)
        if transfer_status != "pending":
            if transfer is not None:
                self._write_trace_event(
                    confirmation_token=request.confirmation_token,
                    event_type="transfer_rejected",
                    stage="secondary-check",
                    decision=transfer.get("decision"),
                    risk_level=transfer.get("risk_level"),
                    final_risk=float(transfer.get("final_risk") or 0.0),
                    payload={
                        "reason": self.REASON_NON_PENDING_STATUS,
                        "status": transfer_status,
                    },
                )
            raise ValueError("该转账已非待确认状态，无法执行二次校验。")

        pending = self.repository.get_pending_transfer(request.confirmation_token)
        if pending.get("secondary_decision") not in {None, "", "pending"}:
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="secondary-check",
                decision=pending.get("secondary_decision") or pending["decision"],
                risk_level=pending["risk_level"],
                final_risk=float(pending.get("secondary_risk") or pending["final_risk"]),
                payload={
                    "reason": self.REASON_DUPLICATE_SECONDARY_SUBMISSION,
                    "secondary_decision": pending.get("secondary_decision"),
                },
            )
            raise ValueError(self.ERROR_SECONDARY_SINGLE_ROUND)
        if pending["decision"] == "block":
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="transfer_rejected",
                stage="secondary-check",
                decision=pending["decision"],
                risk_level=pending["risk_level"],
                final_risk=float(pending["final_risk"]),
                payload={"reason": self.REASON_PRECHECK_BLOCKED},
            )
            raise ValueError("该转账已被预检拦截，无需执行二次校验。")

        self._write_trace_event(
            confirmation_token=request.confirmation_token,
            event_type="secondary_submitted",
            stage="secondary-check",
            decision=pending["decision"],
            risk_level=pending["risk_level"],
            final_risk=float(pending["final_risk"]),
            payload={
                "user_reply": PiiMasker.mask_text(request.user_reply),
                "semantic_summary": PiiMasker.mask_text(pending["semantic_summary"]),
                "perception_snapshot": self._build_perception_snapshot(
                    current_city=pending["city"],
                    recent_page=pending["recent_page"],
                    last_action="secondary_check",
                    semantic_summary=pending["semantic_summary"],
                    extra_signals={"reply_length": len(request.user_reply)},
                    external_intelligence=None,
                    is_known_payee=self.repository.find_payee(pending["payee_name"]) is not None,
                ),
            },
        )

        policy_version = "secondary_policy_v1"

        if pending["decision"] == "pass":
            common_cities = self._common_cities()
            is_known_payee = self.repository.find_payee(pending["payee_name"]) is not None

            external_future = self._executor.submit(
                self._call_with_timing,
                self.screen_external_intelligence,
                pending["payee_name"],
            )
            classification_future = self._executor.submit(
                self._call_with_timing,
                self.risk_knowledge.classify_text,
                text=pending["semantic_summary"],
                amount=float(pending["amount"]),
                current_city=pending["city"],
                common_cities=common_cities,
                is_known_payee=is_known_payee,
            )
            external_intelligence, external_intelligence_ms = external_future.result()
            risk_classification, classification_ms = classification_future.result()

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
            persistence_started_at = time.perf_counter()
            self.repository.update_secondary_check(
                confirmation_token=request.confirmation_token,
                secondary_decision="pass_secondary",
                secondary_risk=float(pending["final_risk"]),
                secondary_reasons=["该交易为放行路径，无需二次质询。"],
                secondary_question="放行路径无需二次质询。",
                secondary_reply=request.user_reply,
                policy_version=policy_version,
            )
            persistence_ms = self._elapsed_ms(persistence_started_at)
            self._write_trace_event(
                confirmation_token=request.confirmation_token,
                event_type="secondary_decided",
                stage="secondary-check",
                decision="pass_secondary",
                risk_level=pending["risk_level"],
                final_risk=float(pending["final_risk"]),
                payload={
                    "risk_category": risk_classification.risk_category,
                    "risk_level": risk_classification.risk_level,
                    "policy_version": policy_version,
                    "semantic_red_flags": [],
                    "timing_total_ms": self._elapsed_ms(total_started_at),
                    "timing_external_intelligence_ms": external_intelligence_ms,
                    "timing_classification_ms": classification_ms,
                    "timing_persistence_ms": persistence_ms,
                },
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

        common_cities = self._common_cities()
        is_known_payee = self.repository.find_payee(pending["payee_name"]) is not None

        anchor_started_at = time.perf_counter()
        anchor_classification = self.risk_knowledge.classify_text(
            text=pending["semantic_summary"],
            amount=float(pending["amount"]),
            current_city=pending["city"],
            common_cities=common_cities,
            is_known_payee=is_known_payee,
        )
        anchor_classification_ms = self._elapsed_ms(anchor_started_at)
        secondary_question = self._select_secondary_question(
            anchor_classification.follow_up_questions
        )

        classification_future = self._executor.submit(
            self._call_with_timing,
            self.risk_knowledge.classify_text,
            text=f"{pending['semantic_summary']} {request.user_reply}".strip(),
            amount=float(pending["amount"]),
            current_city=pending["city"],
            common_cities=common_cities,
            is_known_payee=is_known_payee,
        )
        external_future = self._executor.submit(
            self._call_with_timing,
            self.screen_external_intelligence,
            pending["payee_name"],
        )
        result = get_agent_service().evaluate_secondary_intercept(
            user_reply=request.user_reply,
            semantic_summary=pending["semantic_summary"],
            risk_category=anchor_classification.risk_category,
            risk_level=anchor_classification.risk_level,
            matched_keywords=anchor_classification.matched_keywords,
            matched_scenarios=anchor_classification.matched_scenarios,
            follow_up_questions=anchor_classification.follow_up_questions,
        )
        risk_classification, additional_classification_ms = classification_future.result()
        external_intelligence, external_intelligence_ms = external_future.result()

        classification_ms = round(
            anchor_classification_ms + additional_classification_ms,
            2,
        )

        persistence_started_at = time.perf_counter()
        self.repository.update_secondary_check(
            confirmation_token=request.confirmation_token,
            secondary_decision=result.decision,
            secondary_risk=result.risk,
            secondary_reasons=result.reasons,
            secondary_question=secondary_question,
            secondary_reply=request.user_reply,
            policy_version=policy_version,
        )
        self.repository.create_risk_event(
            payee_name=pending["payee_name"],
            amount=pending["amount"],
            city=pending["city"],
            device_id=request.context.device_id,
            risk_level="high" if result.decision == "block_secondary" else "medium",
            decision=result.decision,
            flag_s=float(pending["flag_s"]),
            g_behavior=float(pending["g_behavior"]),
            g_dynamic=float(pending["g_dynamic"]),
            final_risk=float(pending["final_risk"]),
            reasons=result.reasons,
            secondary_decision=result.decision,
            secondary_risk=result.risk,
            secondary_reply=request.user_reply,
            policy_version=policy_version,
        )
        persistence_ms = self._elapsed_ms(persistence_started_at)
        explain_pack = self._build_secondary_explain_pack(
            flag_s=float(pending["flag_s"]),
            g_behavior=float(pending["g_behavior"]),
            g_dynamic=float(pending["g_dynamic"]),
            final_risk=result.risk,
            decision=result.decision,
            reasons=result.reasons,
            risk_category=risk_classification.risk_category,
            risk_level=risk_classification.risk_level,
            external_intelligence=external_intelligence,
        )
        risk_report = self._generate_and_store_risk_report(
            confirmation_token=request.confirmation_token,
            pending_transfer={
                **pending,
                "secondary_reply": request.user_reply,
                "secondary_decision": result.decision,
                "secondary_risk": result.risk,
            },
            risk_classification=risk_classification,
            secondary_decision=result.decision,
            semantic_red_flags=result.semantic_red_flags,
            external_intelligence=external_intelligence,
            explain_pack=explain_pack,
            policy_version=policy_version,
        )
        self._write_trace_event(
            confirmation_token=request.confirmation_token,
            event_type="secondary_decided",
            stage="secondary-check",
            decision=result.decision,
            risk_level="high" if result.decision == "block_secondary" else "medium",
            final_risk=result.risk,
            payload={
                "semantic_red_flags": result.semantic_red_flags,
                "risk_category": risk_classification.risk_category,
                "risk_level": risk_classification.risk_level,
                "policy_version": policy_version,
                "perception_snapshot": self._build_perception_snapshot(
                    current_city=pending["city"],
                    recent_page=pending["recent_page"],
                    last_action="secondary_check",
                    semantic_summary=pending["semantic_summary"],
                    extra_signals={"reply_length": len(request.user_reply)},
                    external_intelligence=external_intelligence,
                    is_known_payee=is_known_payee,
                ),
                "risk_report_headline": risk_report.headline,
                "risk_report_level": risk_report.overall_risk_level,
                "risk_report_version": risk_report.governance.report_version,
                "timing_total_ms": self._elapsed_ms(total_started_at),
                "timing_classification_ms": classification_ms,
                "timing_external_intelligence_ms": external_intelligence_ms,
                "timing_persistence_ms": persistence_ms,
                **(
                    {"timing_llm_ms": result.llm_elapsed_ms}
                    if result.used_llm and result.llm_elapsed_ms is not None
                    else {}
                ),
            },
        )
        self._write_risk_report_generated_event(
            confirmation_token=request.confirmation_token,
            secondary_decision=result.decision,
            final_risk=result.risk,
            report=risk_report,
        )
        return TransferSecondaryCheckResponse(
            secondary_decision=result.decision,
            reasons=result.reasons,
            final_risk_after_secondary=round(result.risk, 4),
            assistant_message=result.assistant_message,
            semantic_red_flags=result.semantic_red_flags,
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

    def get_transfer_risk_report(self, confirmation_token: str) -> RiskReportPayload:
        payload = self.repository.get_risk_report(confirmation_token)
        if payload is None:
            raise NotFoundError("未找到对应的风险报告。")
        return RiskReportPayload(**payload)

    def list_high_risk_reports(self, limit: int = 20) -> RiskReportListResponsePayload:
        items = [
            RiskReportListItemPayload(**item)
            for item in self.repository.list_high_risk_reports(limit=limit)
        ]
        return RiskReportListResponsePayload(items=items)

    def create_manual_review(
        self,
        *,
        confirmation_token: str,
        payload: ManualReviewCreateRequest,
    ) -> ManualReviewSummaryPayload:
        transfer = self.repository.get_transfer_record(confirmation_token)
        if transfer is None:
            raise NotFoundError("未找到对应转账记录。")
        report_payload = self.repository.get_risk_report(confirmation_token)
        if report_payload is None:
            raise NotFoundError("该转账尚未生成风险报告，无法申请人工复核。")
        report = RiskReportPayload(**report_payload)
        if report.overall_risk_level.lower() != "high":
            raise ValueError("仅高风险报告支持申请人工复核。")
        existing = self.repository.get_open_manual_review_by_confirmation_token(
            confirmation_token
        )
        if existing is not None:
            raise ValueError("该风险报告已有进行中的人工复核单。")

        created = self.repository.create_manual_review_case(
            review_id=self.repository.build_manual_review_id(),
            confirmation_token=confirmation_token,
            request_reason=payload.request_reason.strip(),
            request_snapshot=self._build_manual_review_snapshot(report).model_dump(),
        )
        self._write_trace_event(
            confirmation_token=confirmation_token,
            event_type="manual_review_requested",
            stage="manual-review",
            decision=transfer.get("secondary_decision") or transfer.get("decision"),
            risk_level=report.overall_risk_level,
            final_risk=float(transfer.get("secondary_risk") or transfer.get("final_risk") or 0.0),
            payload={
                "review_id": created["review_id"],
                "status": created["status"],
                "request_reason": PiiMasker.mask_text(created["request_reason"]),
            },
        )
        return ManualReviewSummaryPayload(**created)

    def list_manual_reviews(
        self,
        *,
        limit: int = 20,
        status: str = "all",
    ) -> ManualReviewListResponsePayload:
        if status not in {"all", "submitted", "in_review", "closed"}:
            raise ValueError("manual review status 参数无效。")
        items = [
            ManualReviewSummaryPayload(**item)
            for item in self.repository.list_manual_reviews(
                limit=limit,
                status=None if status == "all" else status,
            )
        ]
        return ManualReviewListResponsePayload(items=items)

    def get_manual_review(self, review_id: str) -> ManualReviewDetailPayload:
        payload = self.repository.get_manual_review_case(review_id)
        if payload is None:
            raise NotFoundError("未找到对应人工复核单。")
        return ManualReviewDetailPayload(**payload)

    def list_manual_review_queue(self) -> ManualReviewQueueResponsePayload:
        items = [
            ManualReviewQueueItemPayload(**item)
            for item in self.repository.list_manual_review_queue()
        ]
        return ManualReviewQueueResponsePayload(items=items)

    def update_manual_review(
        self,
        *,
        review_id: str,
        payload: ManualReviewUpdateRequest,
    ) -> ManualReviewDetailPayload:
        current = self.repository.get_manual_review_case(review_id)
        if current is None:
            raise NotFoundError("未找到对应人工复核单。")
        if payload.status == "in_review":
            if current["status"] != "submitted":
                raise ValueError("当前复核单无法进入处理中状态。")
            updated = self.repository.update_manual_review_case(
                review_id=review_id,
                status="in_review",
                outcome=None,
                review_note=current.get("review_note"),
                reviewer_id=payload.reviewer_id or "demo-reviewer",
                in_review_at=current.get("in_review_at") or self.repository._now(),
            )
            self._write_trace_event(
                confirmation_token=current["confirmation_token"],
                event_type="manual_review_started",
                stage="manual-review",
                decision=None,
                risk_level=updated["overall_risk_level"],
                final_risk=0.0,
                payload={
                    "review_id": updated["review_id"],
                    "status": updated["status"],
                    "reviewer_id": updated.get("reviewer_id") or "",
                },
            )
            return ManualReviewDetailPayload(**updated)

        if payload.status == "closed":
            if current["status"] != "in_review":
                raise ValueError("当前复核单尚未进入处理中状态，无法关闭。")
            if payload.outcome not in {"upheld", "advisory"}:
                raise ValueError("关闭复核单时必须提供有效 outcome。")
            review_note = (payload.review_note or "").strip()
            if not review_note:
                raise ValueError("关闭复核单时必须填写 review_note。")
            updated = self.repository.update_manual_review_case(
                review_id=review_id,
                status="closed",
                outcome=payload.outcome,
                review_note=review_note,
                reviewer_id=payload.reviewer_id or current.get("reviewer_id") or "demo-reviewer",
                in_review_at=current.get("in_review_at"),
            )
            self._write_trace_event(
                confirmation_token=current["confirmation_token"],
                event_type="manual_review_closed",
                stage="manual-review",
                decision=None,
                risk_level=updated["overall_risk_level"],
                final_risk=0.0,
                payload={
                    "review_id": updated["review_id"],
                    "status": updated["status"],
                    "outcome": updated.get("outcome") or "",
                    "reviewer_id": updated.get("reviewer_id") or "",
                    "review_note": PiiMasker.mask_text(updated.get("review_note") or ""),
                },
            )
            return ManualReviewDetailPayload(**updated)

        raise ValueError("仅支持将人工复核单更新为 in_review 或 closed。")

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

    def _generate_and_store_risk_report(
        self,
        *,
        confirmation_token: str,
        pending_transfer: dict,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
        explain_pack: ExplainPack,
        policy_version: str,
    ) -> RiskReportPayload:
        generated_at = self.repository._now()
        report = self.risk_report_service.generate_report(
            confirmation_token=confirmation_token,
            user_profile=self.repository.get_user_profile(),
            pending_transfer=pending_transfer,
            risk_classification=risk_classification,
            secondary_decision=secondary_decision,
            semantic_red_flags=semantic_red_flags,
            external_intelligence=external_intelligence,
            explain_pack=explain_pack,
            policy_version=policy_version,
            generated_at=generated_at,
        )
        self.repository.upsert_risk_report(report=report)
        return report

    def _write_risk_report_generated_event(
        self,
        *,
        confirmation_token: str,
        secondary_decision: str,
        final_risk: float,
        report: RiskReportPayload,
    ) -> None:
        self._write_trace_event(
            confirmation_token=confirmation_token,
            event_type="risk_report_generated",
            stage="risk-report",
            decision=secondary_decision,
            risk_level=report.overall_risk_level,
            final_risk=final_risk,
            payload={
                "headline": report.headline,
                "overall_risk_level": report.overall_risk_level,
                "report_version": report.governance.report_version,
                "generation_mode": report.governance.generation_mode,
                "policy_version": report.governance.policy_version,
                "risk_factors": report.risk_factors,
                "generated_at": report.generated_at,
            },
        )

    def _build_manual_review_snapshot(
        self,
        report: RiskReportPayload,
    ) -> ManualReviewSnapshotPayload:
        governance = report.governance
        if not isinstance(governance, RiskReportGovernancePayload):
            governance = RiskReportGovernancePayload(**governance)
        return ManualReviewSnapshotPayload(
            headline=report.headline,
            overall_risk_level=report.overall_risk_level,
            risk_summary=report.risk_summary,
            risk_category=report.governance.risk_category,
            policy_version=report.governance.policy_version,
            generation_mode=report.governance.generation_mode,
            generated_at=report.generated_at,
            evidence=report.evidence,
            governance=governance,
        )

    def _build_perception_snapshot(
        self,
        *,
        current_city: str,
        recent_page: str,
        last_action: str,
        semantic_summary: str,
        input_pause_count: int | None = None,
        input_duration_ms: int | None = None,
        extra_signals: dict | None = None,
        external_intelligence: ExternalIntelligenceReport | None = None,
        is_known_payee: bool = False,
    ) -> dict[str, object]:
        snapshot = {
            "current_city": current_city,
            "recent_page": recent_page,
            "last_action": last_action,
            "semantic_summary": PiiMasker.mask_text(semantic_summary),
            "input_pause_count": input_pause_count,
            "input_duration_ms": input_duration_ms,
            "is_known_payee": is_known_payee,
            "extra_signals": extra_signals or {},
        }
        if external_intelligence is not None:
            snapshot["external_intelligence_status"] = external_intelligence.status
            snapshot["external_intelligence_level"] = external_intelligence.max_risk_level
        return snapshot

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

    def _derive_c_match(self, classification: RiskClassificationPayload) -> float:
        base_map = {"high": 0.3, "medium": 0.2, "low": 0.1}
        base = base_map.get(classification.risk_level.lower(), 0.2)
        high_phrase_bonus = min(len(classification.high_risk_phrase_hits) * 0.25, 0.7)
        block_hint_boost = 0.4 if classification.block_hint else 0.0
        base = min(base + high_phrase_bonus + block_hint_boost, 1.0)
        if classification.block_hint:
            base = max(base, 0.7)
        return base

    def _cancel_stage(self, transfer: dict) -> str:
        secondary_decision = transfer.get("secondary_decision")
        if secondary_decision not in {None, "", "pending"}:
            return "after_secondary_check"
        return "after_precheck"

    def _write_trace_event(
        self,
        *,
        confirmation_token: str,
        event_type: str,
        stage: str,
        decision: str | None,
        risk_level: str | None,
        final_risk: float,
        payload: dict,
    ) -> None:
        self.repository.create_trace_event(
            trace_id=confirmation_token,
            confirmation_token=confirmation_token,
            event_type=event_type,
            stage=stage,
            decision=decision,
            risk_level=risk_level,
            final_risk=final_risk,
            payload=payload,
        )

    def _call_with_timing(self, func, /, *args, **kwargs):
        started_at = time.perf_counter()
        value = func(*args, **kwargs)
        return value, self._elapsed_ms(started_at)

    def _elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 2)


# HIRD-D: 治理层，负责提供银行宿主服务的单例入口。
@lru_cache(maxsize=1)
def get_bank_host_service() -> BankHostService:
    return BankHostService()
