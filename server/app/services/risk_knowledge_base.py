from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from ..db import get_connection
from ..schemas.risk import RiskClassificationPayload


@dataclass(frozen=True)
class RiskScenario:
    scenario_id: str
    risk_category: str
    title: str
    description: str
    risk_level: str
    keywords: tuple[str, ...]
    high_risk_phrases: tuple[str, ...]
    suspicious_behaviors: tuple[str, ...]
    follow_up_questions: tuple[str, ...]
    suggested_reply_examples: tuple[str, ...]

    @property
    def embedding_text(self) -> str:
        return " ".join(
            (
                self.risk_category,
                self.title,
                self.description,
                " ".join(self.keywords),
                " ".join(self.high_risk_phrases),
                " ".join(self.suspicious_behaviors),
            )
        )


DEFAULT_RISK_SCENARIOS: tuple[RiskScenario, ...] = (
    RiskScenario(
        scenario_id="normal_transfer",
        risk_category="正常转账",
        title="正常转账",
        description="用户与收款人关系清晰，转账用途明确，不涉及催促、验证码或安全账户。",
        risk_level="low",
        keywords=("房租", "工资", "还款", "学费", "生活费", "朋友", "同事", "房东"),
        high_risk_phrases=(),
        suspicious_behaviors=("用途明确", "关系可核验", "无验证码", "无屏幕共享"),
        follow_up_questions=(
            "请说明你与收款人的关系。",
            "请说明本次转账的具体用途。",
        ),
        suggested_reply_examples=(
            "收款人是小b，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码或安全账户。",
            "收款人是小c，是房东，本次转账是4月房租，没有任何客服或公检法联系我。",
        ),
    ),
    RiskScenario(
        scenario_id="borrow_money_impersonation",
        risk_category="熟人借款风险",
        title="冒充熟人借钱",
        description="对方突然借钱、催促转账、换号联系，且不愿视频核验身份。",
        risk_level="medium",
        keywords=("借钱", "急用钱", "换号", "转账", "帮我", "住院", "车祸", "急事"),
        high_risk_phrases=("猜猜我是谁", "先转给我", "我换号了", "最近出了点事", "borrow money"),
        suspicious_behaviors=("突然联系", "要求保密", "拒绝视频核验", "强烈催促"),
        follow_up_questions=(
            "你是否与对方线下认识，是否能视频核验身份？",
            "本次借款是否能通过共同联系人确认？",
        ),
        suggested_reply_examples=(
            "收款人是小d，是我线下认识的同事，我已电话核实身份，这次转账用于临时借款。",
            "收款人是小e，是家人介绍的朋友，我已经视频确认本人，没有被要求保密或快速转账。",
        ),
    ),
    RiskScenario(
        scenario_id="impersonate_police",
        risk_category="冒充公检法",
        title="冒充公安检法办案",
        description="对方冒充公安、检察或法院，以涉案、洗钱、通缉令等理由要求配合处理。",
        risk_level="high",
        keywords=("公安", "警察", "检察", "法院", "涉案", "洗钱", "通缉令", "笔录", "police"),
        high_risk_phrases=("线上做笔录", "涉案资金清查", "通缉令", "保密办案", "case investigation"),
        suspicious_behaviors=("要求下载软件", "要求保密", "要求转账核验", "要求屏幕共享"),
        follow_up_questions=(
            "对方是否要求你转账核验资金或提供验证码？",
            "你是否通过官方公开电话核实过对方身份和案号？",
        ),
        suggested_reply_examples=(
            "我并未通过任何官方电话核实，如果对方要求转账或屏幕共享，我会停止操作并报警。",
            "若涉及公检法事项，我会自行拨打官方电话核验，不会向陌生账户转账。",
        ),
    ),
    RiskScenario(
        scenario_id="safe_account_scam",
        risk_category="安全账户诈骗",
        title="转入安全账户",
        description="对方要求将资金转入所谓安全账户进行核验、清查或冻结处理。",
        risk_level="high",
        keywords=("安全账户", "清查", "冻结", "核验", "资金风险", "涉案账户", "safe account"),
        high_risk_phrases=("转入安全账户", "资金清查后返还", "冻结前先转账核验", "transfer to safe account"),
        suspicious_behaviors=("要求转到陌生账户", "要求提供验证码", "要求立即操作"),
        follow_up_questions=(
            "对方是否明确要求你把钱转到安全账户？",
            "对方是否要求你提供验证码、密码或屏幕共享？",
        ),
        suggested_reply_examples=(
            "如果对方要求转入安全账户，我不会继续转账，并会通过官方渠道核实。",
            "我不会向所谓安全账户转账，也不会提供验证码或开启屏幕共享。",
        ),
    ),
    RiskScenario(
        scenario_id="refund_customer_service",
        risk_category="客服退款诈骗",
        title="冒充客服退款或百万保障",
        description="冒充平台客服，称误开服务、需要退款或取消百万保障，诱导转账验证。",
        risk_level="high",
        keywords=("客服", "退款", "百万保障", "关闭服务", "取消", "验证资金", "刷流水", "customer service", "refund"),
        high_risk_phrases=("误开了百万保障", "转账验证后退款", "关闭服务前先操作资金", "refund after verification"),
        suspicious_behaviors=("要求下载软件", "要求点链接", "要求远程协助", "要求屏幕共享"),
        follow_up_questions=(
            "你是否已通过官方App或官网客服核实？",
            "对方是否要求你下载软件、共享屏幕或转账验证？",
        ),
        suggested_reply_examples=(
            "我只会通过官方App客服联系，不会根据陌生电话要求转账验证。",
            "如果是退款，我会在官方平台内核实，不会提供验证码或共享屏幕。",
        ),
    ),
    RiskScenario(
        scenario_id="otp_screen_share",
        risk_category="验证码/屏幕共享诈骗",
        title="验证码或屏幕共享诱导",
        description="对方要求提供验证码、安装会议软件或开启屏幕共享以指导操作。",
        risk_level="high",
        keywords=("验证码", "屏幕共享", "远程协助", "会议软件", "链接", "远程控制", "verification code", "screen share"),
        high_risk_phrases=("把验证码发给我", "开启屏幕共享", "我来远程指导你", "send me the verification code"),
        suspicious_behaviors=("索取验证码", "要求安装远程软件", "引导点击陌生链接"),
        follow_up_questions=(
            "对方是否向你索取验证码或要求开启屏幕共享？",
            "对方是否要求你安装会议软件或远程控制工具？",
        ),
        suggested_reply_examples=(
            "没有人向我索要验证码，也没有要求屏幕共享或安装远程控制软件。",
            "如果有人要求验证码或屏幕共享，我会立即停止操作。",
        ),
    ),
    RiskScenario(
        scenario_id="remote_large_transfer",
        risk_category="异地大额异常转账",
        title="异地大额异常转账",
        description="用户在非常用城市发起大额或高频转账，且收款人不熟悉或用途不明。",
        risk_level="medium",
        keywords=("异地", "大额", "马上转", "频繁转账", "不要告诉别人"),
        high_risk_phrases=("马上转", "不要告诉任何人", "转到陌生账户"),
        suspicious_behaviors=("非常驻地操作", "金额异常", "新增收款人", "高频转账"),
        follow_up_questions=(
            "本次转账用途是什么，是否线下认识收款人？",
            "是否有人催促你立刻完成转账或要求保密？",
        ),
        suggested_reply_examples=(
            "我现在在北京出差，收款人是小f，本次转账用于酒店押金，不涉及验证码或安全账户。",
            "我在西安出差，收款人是公司同事，本次转账用于垫付差旅费用，没有人催促或要求保密。",
        ),
    ),
)


class RiskKnowledgeBaseService:
    def ensure_seeded(self) -> None:
        with get_connection() as connection:
            for scenario in DEFAULT_RISK_SCENARIOS:
                connection.execute(
                    """
                    INSERT INTO risk_scene_knowledge
                    (scenario_id, risk_category, title, description, risk_level, keywords_json,
                     high_risk_phrases_json, suspicious_behaviors_json, follow_up_questions_json,
                     suggested_reply_examples_json, embedding_text, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(scenario_id) DO UPDATE SET
                        risk_category = excluded.risk_category,
                        title = excluded.title,
                        description = excluded.description,
                        risk_level = excluded.risk_level,
                        keywords_json = excluded.keywords_json,
                        high_risk_phrases_json = excluded.high_risk_phrases_json,
                        suspicious_behaviors_json = excluded.suspicious_behaviors_json,
                        follow_up_questions_json = excluded.follow_up_questions_json,
                        suggested_reply_examples_json = excluded.suggested_reply_examples_json,
                        embedding_text = excluded.embedding_text,
                        updated_at = excluded.updated_at
                    """,
                    (
                        scenario.scenario_id,
                        scenario.risk_category,
                        scenario.title,
                        scenario.description,
                        scenario.risk_level,
                        json.dumps(scenario.keywords, ensure_ascii=False),
                        json.dumps(scenario.high_risk_phrases, ensure_ascii=False),
                        json.dumps(scenario.suspicious_behaviors, ensure_ascii=False),
                        json.dumps(scenario.follow_up_questions, ensure_ascii=False),
                        json.dumps(
                            scenario.suggested_reply_examples,
                            ensure_ascii=False,
                        ),
                        scenario.embedding_text,
                    ),
                )

    def classify_text(
        self,
        *,
        text: str,
        amount: float,
        current_city: str,
        common_cities: list[str],
        is_known_payee: bool,
    ) -> RiskClassificationPayload:
        self.ensure_seeded()
        normalized_text = text.strip().lower()
        scenarios = self._load_scenarios()
        if not normalized_text:
            return self._build_normal_result(amount=amount, current_city=current_city)

        scored_matches: list[tuple[int, int, RiskScenario, list[str]]] = []
        for scenario in scenarios:
            direct_matches = self._collect_matches(
                normalized_text,
                scenario.keywords + scenario.high_risk_phrases,
            )
            matched_keywords = list(direct_matches)
            score = len(direct_matches) * 3
            context_boost = 0

            if scenario.scenario_id == "remote_large_transfer":
                if current_city not in common_cities:
                    context_boost += 2
                    matched_keywords.append("异地")
                if amount >= 5000:
                    context_boost += 2
                    matched_keywords.append("大额")
                if not is_known_payee:
                    context_boost += 1
                    matched_keywords.append("新增收款人")
                score += context_boost

            if score > 0:
                scored_matches.append(
                    (
                        score,
                        len(direct_matches),
                        scenario,
                        self._unique(matched_keywords),
                    )
                )

        if not scored_matches:
            return self._build_normal_result(amount=amount, current_city=current_city)

        scored_matches.sort(
            key=lambda item: (
                item[0],
                item[1],
                self._risk_level_rank(item[2].risk_level),
            ),
            reverse=True,
        )
        _, _, top_scenario, top_keywords = scored_matches[0]
        matched_scenarios = [item[2].title for item in scored_matches[:3]]
        follow_up_questions = self._unique(
            question
            for _, _, scenario, _ in scored_matches[:2]
            for question in scenario.follow_up_questions
        )[:4]
        suggested_reply_examples = list(top_scenario.suggested_reply_examples[:2])

        analysis_parts = [
            f"知识库匹配到风险分类“{top_scenario.risk_category}”",
            f"命中关键词：{'、'.join(top_keywords[:5])}",
        ]
        if top_scenario.scenario_id == "remote_large_transfer":
            analysis_parts.append(
                f"当前城市 {current_city} 与常用地点特征、金额 {amount:.2f} 元共同构成异常交易信号"
            )
        else:
            analysis_parts.append(top_scenario.description)

        return RiskClassificationPayload(
            risk_category=top_scenario.risk_category,
            risk_level=top_scenario.risk_level,
            block_hint=top_scenario.risk_level == "high",
            matched_keywords=top_keywords[:8],
            matched_scenarios=matched_scenarios,
            analysis="；".join(analysis_parts),
            follow_up_questions=follow_up_questions,
            suggested_reply_examples=suggested_reply_examples,
        )

    def _build_normal_result(
        self,
        *,
        amount: float,
        current_city: str,
    ) -> RiskClassificationPayload:
        return RiskClassificationPayload(
            risk_category="正常转账",
            risk_level="low",
            block_hint=False,
            matched_keywords=[],
            matched_scenarios=["正常转账"],
            analysis=f"当前未命中高风险知识库场景，交易位于 {current_city}，金额 {amount:.2f} 元。",
            follow_up_questions=[
                "请说明你与收款人的关系。",
                "请说明本次转账的具体用途。",
            ],
            suggested_reply_examples=[
                "收款人是小b，是我线下认识的朋友，这次转账用于归还借款。",
                "收款人是小c，是房东，本次转账是本月房租。",
            ],
        )

    def _load_scenarios(self) -> list[RiskScenario]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT scenario_id, risk_category, title, description, risk_level,
                       keywords_json, high_risk_phrases_json, suspicious_behaviors_json,
                       follow_up_questions_json, suggested_reply_examples_json
                FROM risk_scene_knowledge
                ORDER BY scenario_id
                """
            ).fetchall()

        scenarios: list[RiskScenario] = []
        for row in rows:
            payload = dict(row)
            scenarios.append(
                RiskScenario(
                    scenario_id=payload["scenario_id"],
                    risk_category=payload["risk_category"],
                    title=payload["title"],
                    description=payload["description"],
                    risk_level=payload["risk_level"],
                    keywords=tuple(json.loads(payload["keywords_json"])),
                    high_risk_phrases=tuple(
                        json.loads(payload["high_risk_phrases_json"])
                    ),
                    suspicious_behaviors=tuple(
                        json.loads(payload["suspicious_behaviors_json"])
                    ),
                    follow_up_questions=tuple(
                        json.loads(payload["follow_up_questions_json"])
                    ),
                    suggested_reply_examples=tuple(
                        json.loads(payload["suggested_reply_examples_json"])
                    ),
                )
            )
        return scenarios

    def _collect_matches(self, text: str, candidates: tuple[str, ...]) -> list[str]:
        matches: list[str] = []
        for candidate in candidates:
            if candidate and candidate.lower() in text:
                matches.append(candidate)
        return matches

    def _risk_level_rank(self, risk_level: str) -> int:
        mapping = {"low": 1, "medium": 2, "high": 3}
        return mapping.get(risk_level.lower(), 0)

    def _unique(self, values) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result


@lru_cache(maxsize=1)
def get_risk_knowledge_base_service() -> RiskKnowledgeBaseService:
    return RiskKnowledgeBaseService()
