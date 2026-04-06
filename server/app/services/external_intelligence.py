from __future__ import annotations

from functools import lru_cache

from ..schemas.external_intelligence import (
    ExternalIntelligenceHit,
    ExternalIntelligenceReport,
)


WATCHLIST_FIXTURES: dict[str, list[ExternalIntelligenceHit]] = {
    "小e": [
        ExternalIntelligenceHit(
            provider="watchlist_adapter_demo",
            list_name="high_risk_payee_watchlist",
            risk_level="high",
            summary="外部名单命中高风险收款人。",
            detail="第三方风险名单显示该收款人关联安全账户/验证码转移投诉，需直接拦截。",
            tags=["watchlist_hit", "safe_account_ring", "suspected_mule"],
            score=1.0,
            block_hint=True,
        )
    ],
    "小f": [
        ExternalIntelligenceHit(
            provider="watchlist_adapter_demo",
            list_name="negative_signal_feed",
            risk_level="medium",
            summary="外部负面情报提示该收款人近期存在异常收款投诉。",
            detail="近 30 天命中过退款诱导/异常收款投诉，建议补充核验关系与用途。",
            tags=["negative_signal", "refund_pattern"],
            score=0.55,
            block_hint=False,
        )
    ],
}


class ExternalIntelligenceService:
    def screen_payee(self, *, payee_name: str) -> ExternalIntelligenceReport:
        normalized_name = payee_name.strip()
        hits = [hit.model_copy(deep=True) for hit in WATCHLIST_FIXTURES.get(normalized_name, [])]
        if not hits:
            return ExternalIntelligenceReport(
                status="clear",
                screened_entity=normalized_name,
                summary="未命中外部名单或负面情报。",
                max_risk_level="low",
                max_score=0.0,
                hits=[],
            )

        max_score = max(hit.score for hit in hits)
        max_risk_level = self._max_risk_level(hits)
        return ExternalIntelligenceReport(
            status="hit",
            screened_entity=normalized_name,
            summary=f"命中 {len(hits)} 条外部情报记录。",
            max_risk_level=max_risk_level,
            max_score=max_score,
            hits=hits,
        )

    def _max_risk_level(self, hits: list[ExternalIntelligenceHit]) -> str:
        ranking = {"low": 1, "medium": 2, "high": 3}
        highest = max(hits, key=lambda hit: ranking.get(hit.risk_level, 0))
        return highest.risk_level


@lru_cache(maxsize=1)
def get_external_intelligence_service() -> ExternalIntelligenceService:
    return ExternalIntelligenceService()
