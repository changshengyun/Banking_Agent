from __future__ import annotations

from functools import lru_cache

from ..schemas.external_intelligence import ExternalIntelligenceReport
from ..schemas.report import RiskReportGovernancePayload
from ..schemas.report import RiskReportPayload
from ..schemas.risk import RiskClassificationPayload
from ..schemas.transfer import ExplainPack
from .llm_gateway import LLMGateway


class RiskReportService:
    REPORT_VERSION = "v2"

    def __init__(self, llm_gateway: LLMGateway | None = None) -> None:
        self.llm_gateway = llm_gateway or LLMGateway()

    def generate_report(
        self,
        *,
        confirmation_token: str,
        user_profile: dict,
        pending_transfer: dict,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
        explain_pack: ExplainPack,
        policy_version: str,
        generated_at: str,
    ) -> RiskReportPayload:
        try:
            payload = self.llm_gateway.generate_json_sync(
                system_prompt=self._build_system_prompt(),
                user_prompt=self._build_user_prompt(
                    user_profile=user_profile,
                    pending_transfer=pending_transfer,
                    risk_classification=risk_classification,
                    secondary_decision=secondary_decision,
                    semantic_red_flags=semantic_red_flags,
                    external_intelligence=external_intelligence,
                    explain_pack=explain_pack,
                    policy_version=policy_version,
                ),
                temperature=0.1,
            )
            return self._parse_payload(
                confirmation_token=confirmation_token,
                payload=payload,
                policy_version=policy_version,
                secondary_decision=secondary_decision,
                risk_category=risk_classification.risk_category,
                external_intelligence_level=external_intelligence.max_risk_level,
                generated_at=generated_at,
            )
        except ValueError:
            return self._build_fallback_report(
                confirmation_token=confirmation_token,
                user_profile=user_profile,
                pending_transfer=pending_transfer,
                risk_classification=risk_classification,
                secondary_decision=secondary_decision,
                semantic_red_flags=semantic_red_flags,
                external_intelligence=external_intelligence,
                explain_pack=explain_pack,
                policy_version=policy_version,
                generated_at=generated_at,
            )

    def _build_system_prompt(self) -> str:
        return (
            "你是银行风控风险报告 Agent。"
            "你只负责生成结构化风险报告，不负责业务裁决。"
            "必须输出严格 JSON，不允许输出额外文本。"
        )

    def _build_user_prompt(
        self,
        *,
        user_profile: dict,
        pending_transfer: dict,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
        explain_pack: ExplainPack,
        policy_version: str,
    ) -> str:
        return (
            "请根据下面的用户画像、交易文本、风险分类和二次校验结果，生成结构化风险报告。"
            "返回 JSON：\n"
            "{"
            '"headline":"报告标题",'
            '"overall_risk_level":"low|medium|high",'
            '"risk_summary":"简短总结",'
            '"risk_factors":["因子1","因子2"],'
            '"recommended_action":"建议动作",'
            '"evidence":["证据1","证据2"],'
            '"review_checkpoints":["复核点1","复核点2"]'
            "}\n"
            "要求：报告必须引用真实风险依据，不允许输出空泛结论。"
            "复核点要指向人工复核时最该核实的对象、关系、用途或外部情报。"
            f"策略版本：{policy_version}\n"
            f"用户画像：姓名 {user_profile.get('name', '未知')}，常驻城市 {user_profile.get('home_city', '未知')}，风险偏好 {user_profile.get('risk_preference', '未知')}。\n"
            f"交易文本：{pending_transfer.get('semantic_summary', '')}\n"
            f"用户二次回复：{pending_transfer.get('secondary_reply', '')}\n"
            f"风险分类：{risk_classification.risk_category} / {risk_classification.risk_level}\n"
            f"命中关键词：{'、'.join(risk_classification.matched_keywords) if risk_classification.matched_keywords else '无'}\n"
            f"命中场景：{'；'.join(risk_classification.matched_scenarios) if risk_classification.matched_scenarios else '无'}\n"
            f"二次结果：{secondary_decision}\n"
            f"语义红旗：{'；'.join(semantic_red_flags) if semantic_red_flags else '无'}\n"
            f"外部情报：{external_intelligence.summary}\n"
            f"解释包标题：{explain_pack.headline}\n"
            f"解释建议：{explain_pack.recommended_action}\n"
        )

    def _parse_payload(
        self,
        *,
        confirmation_token: str,
        payload: dict,
        policy_version: str,
        secondary_decision: str,
        risk_category: str,
        external_intelligence_level: str,
        generated_at: str,
    ) -> RiskReportPayload:
        headline = str(payload.get("headline", "")).strip()
        overall_risk_level = str(payload.get("overall_risk_level", "")).strip().lower()
        risk_summary = str(payload.get("risk_summary", "")).strip()
        recommended_action = str(payload.get("recommended_action", "")).strip()
        if not headline or overall_risk_level not in {"low", "medium", "high"}:
            raise ValueError("risk report payload invalid")
        if not risk_summary or not recommended_action:
            raise ValueError("risk report payload incomplete")

        risk_factors = [
            str(item).strip()
            for item in payload.get("risk_factors", [])
            if str(item).strip()
        ]
        evidence = [
            str(item).strip()
            for item in payload.get("evidence", [])
            if str(item).strip()
        ]
        review_checkpoints = [
            str(item).strip()
            for item in payload.get("review_checkpoints", [])
            if str(item).strip()
        ]
        return RiskReportPayload(
            confirmation_token=confirmation_token,
            headline=headline,
            overall_risk_level=overall_risk_level,
            risk_summary=risk_summary,
            risk_factors=risk_factors,
            recommended_action=self._merge_recommended_action(
                recommended_action=recommended_action,
                review_checkpoints=review_checkpoints,
            ),
            evidence=evidence,
            governance=self._build_governance(
                policy_version=policy_version,
                generation_mode="llm",
                secondary_decision=secondary_decision,
                risk_category=risk_category,
                external_intelligence_level=external_intelligence_level,
            ),
            generated_at=generated_at,
        )

    def _build_fallback_report(
        self,
        *,
        confirmation_token: str,
        user_profile: dict,
        pending_transfer: dict,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
        explain_pack: ExplainPack,
        policy_version: str,
        generated_at: str,
    ) -> RiskReportPayload:
        overall_risk_level = self._overall_risk_level(
            risk_level=risk_classification.risk_level,
            secondary_decision=secondary_decision,
            semantic_red_flags=semantic_red_flags,
            external_intelligence=external_intelligence,
        )
        headline = (
            "高风险转账报告"
            if overall_risk_level == "high"
            else "交易复核报告"
            if overall_risk_level == "medium"
            else "低风险转账说明"
        )
        risk_factors = self._risk_factors(
            risk_classification=risk_classification,
            semantic_red_flags=semantic_red_flags,
            external_intelligence=external_intelligence,
        )
        evidence = self._evidence(
            user_profile=user_profile,
            pending_transfer=pending_transfer,
            risk_classification=risk_classification,
            secondary_decision=secondary_decision,
            explain_pack=explain_pack,
            external_intelligence=external_intelligence,
        )
        risk_summary = (
            f"用户 {user_profile.get('name', '未知用户')} 发起向 {pending_transfer.get('payee_name', '未知收款人')} "
            f"转账 {float(pending_transfer.get('amount') or 0):.2f} 元，"
            f"当前风险分类为 {risk_classification.risk_category}，二次校验结果为 {secondary_decision}。"
        )
        return RiskReportPayload(
            confirmation_token=confirmation_token,
            headline=headline,
            overall_risk_level=overall_risk_level,
            risk_summary=risk_summary,
            risk_factors=risk_factors,
            recommended_action=self._merge_recommended_action(
                recommended_action=explain_pack.recommended_action,
                review_checkpoints=self._review_checkpoints(
                    risk_classification=risk_classification,
                    secondary_decision=secondary_decision,
                    semantic_red_flags=semantic_red_flags,
                    external_intelligence=external_intelligence,
                ),
            ),
            evidence=evidence,
            governance=self._build_governance(
                policy_version=policy_version,
                generation_mode="fallback",
                secondary_decision=secondary_decision,
                risk_category=risk_classification.risk_category,
                external_intelligence_level=external_intelligence.max_risk_level,
            ),
            generated_at=generated_at,
        )

    def _overall_risk_level(
        self,
        *,
        risk_level: str,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
    ) -> str:
        if secondary_decision == "block_secondary" or semantic_red_flags:
            return "high"
        if external_intelligence.max_risk_level == "high":
            return "high"
        if secondary_decision == "interrogate":
            return "medium"
        return risk_level if risk_level in {"low", "medium", "high"} else "medium"

    def _risk_factors(
        self,
        *,
        risk_classification: RiskClassificationPayload,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
    ) -> list[str]:
        factors: list[str] = []
        factors.extend(semantic_red_flags[:3])
        factors.extend(risk_classification.matched_scenarios[:2])
        factors.extend(risk_classification.matched_keywords[:3])
        if external_intelligence.status == "hit":
            factors.extend(hit.summary for hit in external_intelligence.hits[:2])
        deduped: list[str] = []
        seen: set[str] = set()
        for item in factors:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped[:6]

    def _evidence(
        self,
        *,
        user_profile: dict,
        pending_transfer: dict,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        explain_pack: ExplainPack,
        external_intelligence: ExternalIntelligenceReport,
    ) -> list[str]:
        evidence = [
            f"用户画像：常驻城市 {user_profile.get('home_city', '未知')}，风险偏好 {user_profile.get('risk_preference', '未知')}",
            f"交易语义：{pending_transfer.get('semantic_summary', '无')}",
            f"二次回复：{pending_transfer.get('secondary_reply', '无')}",
            f"风险分类：{risk_classification.risk_category} / {risk_classification.risk_level}",
            f"二次结果：{secondary_decision}",
            f"外部情报：{external_intelligence.summary}",
            f"解释建议：{explain_pack.recommended_action}",
        ]
        return [item for item in evidence if item.strip()]

    def _review_checkpoints(
        self,
        *,
        risk_classification: RiskClassificationPayload,
        secondary_decision: str,
        semantic_red_flags: list[str],
        external_intelligence: ExternalIntelligenceReport,
    ) -> list[str]:
        checkpoints: list[str] = []
        if semantic_red_flags:
            checkpoints.append(f"核实语义红旗：{'；'.join(semantic_red_flags[:2])}")
        if risk_classification.matched_scenarios:
            checkpoints.append(
                f"核实风险场景：{'；'.join(risk_classification.matched_scenarios[:2])}"
            )
        if external_intelligence.status == "hit":
            checkpoints.append("核实外部情报命中对象与收款人关系是否真实。")
        if secondary_decision == "block_secondary":
            checkpoints.append("二次说明未通过，需人工复核转账用途与沟通来源。")
        elif secondary_decision == "interrogate":
            checkpoints.append("二次说明仍不足，需补充关系、用途和资金去向证明。")
        else:
            checkpoints.append("虽已放行，但仍建议核实收款人身份与转账用途一致性。")
        return checkpoints[:4]

    def _merge_recommended_action(
        self,
        *,
        recommended_action: str,
        review_checkpoints: list[str],
    ) -> str:
        if not review_checkpoints:
            return recommended_action
        joined = "；".join(review_checkpoints[:2])
        return f"{recommended_action} 重点复核：{joined}"

    def _build_governance(
        self,
        *,
        policy_version: str,
        generation_mode: str,
        secondary_decision: str,
        risk_category: str,
        external_intelligence_level: str,
    ) -> RiskReportGovernancePayload:
        return RiskReportGovernancePayload(
            report_version=self.REPORT_VERSION,
            policy_version=policy_version,
            generation_mode=generation_mode,
            source_stage="secondary-check",
            secondary_decision=secondary_decision,
            risk_category=risk_category,
            external_intelligence_level=external_intelligence_level,
            trace_events=["secondary_decided", "risk_report_generated"],
        )


@lru_cache(maxsize=1)
def get_risk_report_service() -> RiskReportService:
    return RiskReportService()
