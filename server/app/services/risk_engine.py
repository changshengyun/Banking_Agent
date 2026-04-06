from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class RiskInput:
    payee_name: str
    amount: float
    current_city: str
    is_known_payee: bool
    common_cities: list[str]
    recent_transfer_count: int
    recent_page: str
    last_action: str
    semantic_summary: str
    classification_risk_level: Optional[str] = None
    classification_category: Optional[str] = None
    classification_block_hint: bool = False
    classification_keywords: Optional[list[str]] = None
    classification_scenarios: Optional[list[str]] = None
    input_pause_count: Optional[int] = None
    input_duration_ms: Optional[int] = None
    extra_signals: Optional[dict[str, Union[float, int, str, bool]]] = None


@dataclass(frozen=True)
class RiskAssessment:
    decision: str
    risk_level: str
    reasons: list[str]
    score: int
    flag_s: float
    g_behavior: float
    g_dynamic: float
    final_risk: float


class RiskEngine:
    BEHAVIOR_RISK_ACTION_HINTS = (
        "paste",
        "copy",
        "external",
        "deeplink",
        "scan",
        "qr",
        "share",
        "粘贴",
        "复制",
        "外部",
        "扫码",
        "分享",
    )
    BEHAVIOR_RISK_PAGE_HINTS = {
        "chat",
        "notification",
        "message",
        "sms",
        "聊天",
        "通知",
        "消息",
        "短信",
    }

    def assess(self, payload: RiskInput) -> RiskAssessment:
        reasons: list[str] = []

        flag_s = self._calculate_static_score(payload, reasons)
        g_behavior = self._calculate_behavior_score(payload)
        g_dynamic, hard_block = self._calculate_dynamic_score(payload, reasons)
        final_risk = self._calculate_final_risk(
            flag_s=flag_s,
            g_behavior=g_behavior,
            g_dynamic=g_dynamic,
            hard_block=hard_block,
        )

        decision = self._resolve_decision(final_risk)
        risk_level = self._resolve_risk_level(final_risk)

        if decision == "block" and not any("拦截" in reason for reason in reasons):
            reasons.append("风险评分达到拦截阈值，本次转账已被拦截。")
        if decision == "interrogate" and not any("补充确认" in reason for reason in reasons):
            reasons.append("风险评分处于补充确认区间，需要进一步核验。")
        if decision == "pass" and not reasons:
            reasons.append("未命中高风险规则，本次转账可放行。")

        return RiskAssessment(
            decision=decision,
            risk_level=risk_level,
            reasons=reasons,
            score=int(round(final_risk * 100)),
            flag_s=round(flag_s, 4),
            g_behavior=round(g_behavior, 4),
            g_dynamic=round(g_dynamic, 4),
            final_risk=round(final_risk, 4),
        )

    def _calculate_static_score(self, payload: RiskInput, reasons: list[str]) -> float:
        score = 0.05

        normalized_city = payload.current_city.strip()
        if normalized_city not in payload.common_cities:
            score += 0.35
            reasons.append(f"当前城市为 {normalized_city}，不在常用地点名单中。")

        if payload.amount >= 20000:
            score += 0.55
            reasons.append(f"转账金额 {payload.amount:.2f} 元，属于超高金额区间。")
        elif payload.amount >= 10000:
            score += 0.40
            reasons.append(f"转账金额 {payload.amount:.2f} 元，属于高金额区间。")
        elif payload.amount >= 5000:
            score += 0.28
            reasons.append(f"转账金额 {payload.amount:.2f} 元，超过演示环境常见阈值。")
        elif payload.amount >= 2000:
            score += 0.15
            reasons.append(f"转账金额 {payload.amount:.2f} 元，属于中高金额区间。")

        if not payload.is_known_payee:
            score += 0.22
            reasons.append(f"收款人 {payload.payee_name} 为新增收款人。")

        if payload.recent_transfer_count >= 3:
            score += 0.22
            reasons.append("近期转出频率偏高。")
        elif payload.recent_transfer_count >= 2:
            score += 0.14
            reasons.append("近期转出频率触发关注。")

        return self._clamp(score)

    def _calculate_behavior_score(self, payload: RiskInput) -> float:
        score = 0.10

        if payload.recent_page.strip().lower() in self.BEHAVIOR_RISK_PAGE_HINTS:
            score += 0.25

        action = payload.last_action.strip().lower()
        if any(hint in action for hint in self.BEHAVIOR_RISK_ACTION_HINTS):
            score += 0.25

        if payload.recent_transfer_count >= 2:
            score += 0.20

        if not payload.is_known_payee and payload.amount >= 5000:
            score += 0.20

        if payload.input_pause_count is not None:
            if payload.input_pause_count >= 8:
                score += 0.30
            elif payload.input_pause_count >= 4:
                score += 0.18

        if payload.input_duration_ms is not None:
            if payload.input_duration_ms <= 1500:
                score += 0.18
            elif payload.input_duration_ms >= 45000:
                score += 0.12

        paste_count = self._signal_value(payload.extra_signals, "paste_count")
        if paste_count is not None and paste_count >= 1:
            score += 0.20

        app_switch_count = self._signal_value(payload.extra_signals, "app_switch_count")
        if app_switch_count is None:
            app_switch_count = self._signal_value(payload.extra_signals, "switch_app_count")
        if app_switch_count is not None and app_switch_count >= 2:
            score += 0.15

        focus_lost_count = self._signal_value(payload.extra_signals, "focus_lost_count")
        if focus_lost_count is not None and focus_lost_count >= 3:
            score += 0.12

        return self._clamp(score)

    def _signal_value(
        self, signals: dict[str, float | int | str | bool] | None, key: str
    ) -> float | None:
        if not signals or key not in signals:
            return None
        value = signals[key]
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return float(raw)
            except ValueError:
                return None
        return None

    def _calculate_dynamic_score(
        self, payload: RiskInput, reasons: list[str]
    ) -> tuple[float, bool]:
        classification_level = (payload.classification_risk_level or "").strip().lower()
        classification_category = (payload.classification_category or "").strip()
        matched_keywords = payload.classification_keywords or []

        if not classification_level or not classification_category:
            return 0.2, False

        keywords_text = "、".join(matched_keywords[:4]) if matched_keywords else "知识库风险信号"
        if classification_level == "high":
            reasons.append(
                f"知识库匹配到高风险场景“{classification_category}”，命中信号：{keywords_text}。"
            )
            return 1.0 if payload.classification_block_hint else 0.85, (
                payload.classification_block_hint
            )

        if classification_level == "medium":
            reasons.append(
                f"知识库匹配到中风险场景“{classification_category}”，命中信号：{keywords_text}。"
            )
            return 0.65, False

        if classification_category == "正常转账":
            return 0.15, False

        reasons.append(f"知识库提供了辅助风险线索：{classification_category}。")
        return 0.3, False

    def _calculate_final_risk(
        self,
        *,
        flag_s: float,
        g_behavior: float,
        g_dynamic: float,
        hard_block: bool,
    ) -> float:
        if hard_block:
            return 1.0
        weighted = (0.5 * flag_s) + (0.2 * g_behavior) + (0.3 * g_dynamic)
        return self._clamp(weighted)

    def _resolve_decision(self, final_risk: float) -> str:
        if final_risk >= 0.80:
            return "block"
        if final_risk >= 0.45:
            return "interrogate"
        return "pass"

    def _resolve_risk_level(self, final_risk: float) -> str:
        if final_risk >= 0.75:
            return "high"
        if final_risk >= 0.40:
            return "medium"
        return "low"

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
