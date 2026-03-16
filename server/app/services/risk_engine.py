from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskInput:
    payee_name: str
    amount: float
    current_city: str
    is_known_payee: bool
    common_cities: list[str]
    recent_transfer_count: int


@dataclass(frozen=True)
class RiskAssessment:
    decision: str
    risk_level: str
    reasons: list[str]
    score: int


class RiskEngine:
    def assess(self, payload: RiskInput) -> RiskAssessment:
        reasons: list[str] = []
        score = 0

        normalized_city = payload.current_city.strip()
        if normalized_city not in payload.common_cities:
            reasons.append(f"当前操作地点为 {normalized_city}，不在常用交易地点列表中。")
            score += 2

        if payload.amount >= 5000:
            reasons.append(f"本次转账金额为 {payload.amount:.2f} 元，超过演示系统的大额阈值。")
            score += 2
        elif payload.amount >= 2000:
            reasons.append(f"本次转账金额为 {payload.amount:.2f} 元，属于中高金额操作。")
            score += 1

        if not payload.is_known_payee:
            reasons.append(f"收款人 {payload.payee_name} 为首次出现的收款对象。")
            score += 1

        if payload.recent_transfer_count >= 2:
            reasons.append("近期已存在连续转账行为，本次操作触发频率监测。")
            score += 1

        if score >= 4:
            return RiskAssessment("review", "high", reasons, score)
        if score >= 2:
            return RiskAssessment("review", "medium", reasons, score)
        return RiskAssessment(
            "pass",
            "low",
            reasons or ["未命中异常地点、异常金额或新收款人规则。"],
            score,
        )

