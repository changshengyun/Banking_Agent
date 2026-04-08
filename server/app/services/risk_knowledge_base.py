from __future__ import annotations

from collections import OrderedDict
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Optional, Any

from ..db import get_connection
from ..schemas.risk import RiskClassificationPayload
from .embedding_service import get_embedding_service, normalize_text
from ..utils import nlp_utils

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
    target_user_profiles: tuple[str, ...]

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
                " ".join(self.target_user_profiles),
            )
        )


DEFAULT_RISK_SCENARIOS: tuple[RiskScenario, ...] = (
    RiskScenario(
        scenario_id="normal_transfer",
        risk_category="正常转账",
        title="正常转账",
        description="转账关系清晰、用途明确，且不涉及验证码、安全账户、屏幕共享等高危指令。",
        risk_level="low",
        keywords=(
            "房租", "工资", "还款", "学费", "生活费", "餐费", "aa", "物业费",
            "水电费", "燃气费", "押金", "朋友", "同事", "家人", "父母", "房东",
            "日常生活转账", "普通还款", "日常转账", "生活转账",
        ),
        high_risk_phrases=(),
        suspicious_behaviors=("用途明确", "关系可核验", "无验证码", "无屏幕共享"),
        follow_up_questions=(
            "请说明你与收款人的关系。",
            "请说明本次转账的具体用途。",
        ),
        suggested_reply_examples=(
            "收款人是小b，是我线下认识的朋友，这次转账用于归还借款，不涉及验证码或安全账户。",
            "收款人是小c，是房东，本次转账是本月房租，没有客服、公检法或陌生人要求我操作。",
        ),
        target_user_profiles=("普通薪资用户", "家庭日常转账用户"),
    ),
    RiskScenario(
        scenario_id="customer_service_fraud",
        risk_category="客服退款诈骗",
        title="客服退款/保障关闭诈骗",
        description="对方冒充平台客服、保险客服或支付客服，以关闭保障、退款退费、验证资金为由要求转账。",
        risk_level="high",
        keywords=(
            "客服", "退款", "退费", "关闭百万保障", "百万保障", "保险服务",
            "支付客服", "验证资金", "退保", "刷流水",
        ),
        high_risk_phrases=(
            "验证资金后退款", "先刷流水", "客服让我转账验证",
            "退款验证",
        ),
        suspicious_behaviors=("冒充客服", "要求转账验证", "要求刷流水", "诱导脱离官方渠道"),
        follow_up_questions=(
            "你是否通过官方 App、官网或官方客服入口核实过对方身份？",
            "对方是否要求你转账验证资金、提供验证码或开启屏幕共享？",
        ),
        suggested_reply_examples=(
            "对方自称客服，说要关闭百万保障并让我转账验证资金，我怀疑是诈骗。",
            "如果真是官方客服，我只会通过官方 App 核实，不会向陌生账户转账。",
        ),
        target_user_profiles=("普通支付用户", "保险服务用户", "中老年用户"),
    ),
    RiskScenario(
        scenario_id="safe_account_fraud",
        risk_category="安全账户诈骗",
        title="安全账户/监管账户诈骗",
        description="对方要求把资金转入所谓安全账户、监管账户或验资账户，并配合资金清查、验证码核验。",
        risk_level="high",
        keywords=(
            "安全账户", "监管账户", "资金清查", "验资", "冻结前转账",
            "verificationcode", "safeaccount", "验证码", "核验资金",
        ),
        high_risk_phrases=(
            "转到安全账户", "转入监管账户", "资金清查完成后返还", "提供verificationcode",
            "提供验证码", "安全账户转账", "safeaccount", "verificationcode",
        ),
        suspicious_behaviors=("转移资金", "要求验证码", "要求屏幕共享", "冒充安全核验"),
        follow_up_questions=(
            "对方是否明确要求你把钱转到安全账户、监管账户或验资账户？",
            "对方是否要求你提供验证码、密码或共享屏幕？",
        ),
        suggested_reply_examples=(
            "对方要求我转到安全账户并提供验证码，这明显不是正常银行流程。",
            "任何要求我转入监管账户做资金清查的说法，我都会停止操作并联系银行。",
        ),
        target_user_profiles=("中老年用户", "风控敏感用户"),
    ),
    RiskScenario(
        scenario_id="borrow_money_impersonation",
        risk_category="熟人借款风险",
        title="冒充熟人借钱",
        description="对方以换号、住院、出事、周转等理由突然借钱，并要求快速转账或保密。",
        risk_level="medium",
        keywords=(
            "借钱", "周转", "急用钱", "手头紧", "帮我付一下", "先转我", "住院",
            "手术", "出车祸", "救急", "学费", "马上转",
        ),
        high_risk_phrases=(
            "猜猜我是谁", "我是新号", "先别告诉别人", "先转我救急", "借我周转一下", "borrow money",
        ),
        suspicious_behaviors=("突然联系", "要求保密", "拒绝视频核验", "持续催促"),
        follow_up_questions=(
            "你是否与对方线下认识，能否视频核验身份？",
            "这笔钱是否能通过共同联系人再次确认？",
        ),
        suggested_reply_examples=(
            "收款人是小d，是我线下认识的同事，我已经电话核实身份，这次转账用于短期周转。",
            "收款人是小e，是共同朋友介绍的熟人，我已通过视频核验，不存在催促或保密要求。",
        ),
        target_user_profiles=("学生用户", "年轻白领", "熟人社交频繁用户"),
    ),
    RiskScenario(
        scenario_id="impersonate_police",
        risk_category="冒充公检法",
        title="冒充公安检法办案",
        description="对方冒充公安、检察院或法院，以涉案、洗钱、冻结资产等理由要求配合操作。",
        risk_level="high",
        keywords=(
            "公安", "警察", "检察院", "法院", "涉案", "洗钱", "笔录", "冻结资产",
            "通缉令", "案件", "反诈中心", "police",
        ),
        high_risk_phrases=(
            "线上做笔录", "涉嫌洗钱", "安全审查", "办案账户", "冻结前先转账", "保密办案", "case investigation",
            "转到安全账户", "安全账户转账",
        ),
        suspicious_behaviors=("要求下载软件", "要求保密", "要求转账核验", "要求屏幕共享"),
        follow_up_questions=(
            "对方是否要求你转账核验资金、提供验证码或共享屏幕？",
            "你是否接到了自称‘公检法’工作人员要求你转移资金到‘安全账户’的电话？",
        ),
        suggested_reply_examples=(
            "对方冒充警官让我把钱转到安全账户进行核验，这显然是诈骗。",
            "对方说我涉嫌洗钱，要求我下载屏幕共享软件做线上笔录并转账，我怀疑是冒充公检法。",
        ),
        target_user_profiles=("中老年用户", "财务人员", "学生用户"),
    ),
    RiskScenario(
        scenario_id="remote_large_transfer",
        risk_category="异地大额异常转账",
        title="异地大额转账风险",
        description="在非常驻城市发起的、远超日常水平的大额转账请求。",
        risk_level="medium",
        keywords=("大额", "异地", "异常", "突然", "large amount", "remote city"),
        high_risk_phrases=(),
        suspicious_behaviors=("地点跨度大", "金额突增", "环境陌生"),
        follow_up_questions=(
            "你目前是否在非经常居住城市，本次大额转账是否为你本人意愿？",
            "收款人是否为你线下熟识，能否确认对方身份？",
        ),
        suggested_reply_examples=(
            "我目前在出差，这是正常的业务转账，收款人是我长期合作的供应商。",
            "我在外地旅游，这笔转账是用于支付预定的酒店套餐，收款人是酒店官方账户。",
        ),
        target_user_profiles=("高净值用户", "商旅频繁用户"),
    ),
    RiskScenario(
        scenario_id="investment_fraud",
        risk_category="投资理财诈骗",
        title="虚假投资理财诈骗",
        description="对方以'高额回报'、'内部消息'为诱饵，诱导用户在虚假平台上投资、转账。",
        risk_level="high",
        keywords=("投资", "理财", "回报", "利息", "带单", "赚钱", "内部消息", "高收益", "打新股", "跟单"),
        high_risk_phrases=("高收益低风险", "老师带单", "内部渠道", "赚钱不麻烦", "稳赚不赔", "今晚拉升"),
        suspicious_behaviors=("下载非主流金融App", "在微信群/QQ群跟单", "初期小额提现诱导", "要求转账至私人账户"),
        follow_up_questions=(
            "该投资项目是否来自正规金融机构？是否要求你将资金转入私人账户？",
            "你是否加入了所谓的‘投资交流群’并按照‘导师’的要求进行操作？",
        ),
        suggested_reply_examples=(
            "我加入了一个理财群，老师说有内部消息能稳赚不赔，让我转账到一个私人账户去建仓。",
            "这是一个高收益理财项目，但我发现它要求我把资金转给个人而不是平台公户，我怀疑是诈骗。",
        ),
        target_user_profiles=("中老年用户", "急于理财的年轻人", "企业财务"),
    ),
    RiskScenario(
        scenario_id="romance_scam",
        risk_category="情感诈骗",
        title="'杀猪盘'情感诈骗",
        description="对方通过网络社交建立虚假恋爱关系，随后以投资、生病、借钱等名义骗取财物。",
        risk_level="high",
        keywords=("网恋", "交友", "对象", "彩票", "漏洞", "结婚", "买礼物", "周转", "杀猪盘", "机票"),
        high_risk_phrases=("我们的未来", "发现系统漏洞", "帮我操作账号", "为了我们的家", "转账后就来见你"),
        suspicious_behaviors=("拒绝线下见面", "人设完美", "突然提到赚钱门路", "要求大额转账证明心意"),
        follow_up_questions=(
            "你是否与该网友见过面？对方是否在建立感情联系后突然要求你参与投资或博彩？",
            "对方是否以‘为了未来’为名义，诱导你查看或操作所谓的‘盈利软件’？",
        ),
        suggested_reply_examples=(
            "我在社交软件认识的对象，虽然没见过面但感情很好，他最近让我帮他在一个彩票网站投注。",
            "对方自称是我的‘另一半’，现在因为家里出事急需一笔钱周转，但我其实从未见过他本人。",
        ),
        target_user_profiles=("单心适龄男女", "独居中老年人"),
    ),
    RiskScenario(
        scenario_id="part_time_fraud",
        risk_category="刷单兼职诈骗",
        title="兼职刷单返佣诈骗",
        description='对方以"高佣金"、"操作简单"为名招募刷单兼职，先返小利，后以任务卡住为由骗取大额资金。',
        risk_level="high",
        keywords=("刷单", "兼职", "返利", "佣金", "做任务", "垫付", "关注公众号", "提现失败", "返现"),
        high_risk_phrases=("足不出户", "日入过千", "先垫付后返还", "先垫付后返现", "任务还没做完", "连续单", "再做一单"),
        suspicious_behaviors=("要求先垫资", "通过聊天软件私聊派单", "提现时要求继续充值", "拒绝走正规电商平台"),
        follow_up_questions=(
            "该兼职是否要求你先垫付资金购买商品或虚拟卡？",
            "你是否通过官方平台接单，还是通过聊天软件私下联系？",
        ),
        suggested_reply_examples=(
            "如果兼职要求我先垫付资金或继续做单才能提现，我会立即停止操作。",
            "我不会通过聊天软件接刷单任务，也不会为了返佣继续转账。",
        ),
        target_user_profiles=("学生用户", "兼职求职用户", "宝妈用户"),
    ),
)


class RiskKnowledgeBaseService:
    def __init__(self) -> None:
        self.embedding_service = get_embedding_service()
        self._seeded = False
        self._seed_lock = Lock()
        self._scenarios_cache: list[dict] | None = None
        self._classification_cache: OrderedDict[tuple, RiskClassificationPayload] = (
            OrderedDict()
        )
        self._classification_cache_lock = Lock()
        self._classification_cache_max_size = 256

    def ensure_seeded(self) -> None:
        """确保知识库已初始化并同步。支持幂等更新。"""
        if self._seeded:
            return
        with self._seed_lock:
            if self._seeded:
                return
            with get_connection() as connection:
                # 批量获取嵌入，避免每次请求都重新计算。
                embeddings = self.embedding_service.batch_get_embeddings(
                    [s.embedding_text for s in DEFAULT_RISK_SCENARIOS]
                )

                for scenario, vector in zip(DEFAULT_RISK_SCENARIOS, embeddings):
                    connection.execute(
                        """
                        INSERT INTO risk_scene_knowledge
                        (scenario_id, risk_category, title, description, risk_level, keywords_json,
                         high_risk_phrases_json, suspicious_behaviors_json, follow_up_questions_json,
                         suggested_reply_examples_json, target_user_profile_json, embedding_text,
                         vector_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        ON CONFLICT(scenario_id) DO UPDATE SET
                            risk_category=excluded.risk_category,
                            title=excluded.title,
                            description=excluded.description,
                            risk_level=excluded.risk_level,
                            keywords_json=excluded.keywords_json,
                            high_risk_phrases_json=excluded.high_risk_phrases_json,
                            suspicious_behaviors_json=excluded.suspicious_behaviors_json,
                            follow_up_questions_json=excluded.follow_up_questions_json,
                            suggested_reply_examples_json=excluded.suggested_reply_examples_json,
                            target_user_profile_json=excluded.target_user_profile_json,
                            embedding_text=excluded.embedding_text,
                            vector_json=excluded.vector_json,
                            updated_at=datetime('now')
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
                            json.dumps(scenario.suggested_reply_examples, ensure_ascii=False),
                            json.dumps(scenario.target_user_profiles, ensure_ascii=False),
                            scenario.embedding_text,
                            json.dumps(vector),
                        ),
                    )
            self._seeded = True
            self._scenarios_cache = None
            with self._classification_cache_lock:
                self._classification_cache.clear()

    def prewarm(self) -> None:
        """在应用启动阶段完成知识库种子和场景向量装载。"""
        self.ensure_seeded()
        self._load_scenarios_with_vectors()

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
        normalized_text = normalize_text(text)
        scenarios = self._load_scenarios_with_vectors()
        cache_key = (
            normalized_text,
            round(amount, 2),
            current_city,
            tuple(sorted(common_cities)),
            bool(is_known_payee),
        )

        if not normalized_text:
            return self._build_contextual_fallback(
                amount=amount, current_city=current_city,
                common_cities=common_cities, is_known_payee=is_known_payee,
            )

        with self._classification_cache_lock:
            cached = self._classification_cache.get(cache_key)
            if cached is not None:
                self._classification_cache.move_to_end(cache_key)
                return self._clone_payload(cached)

        # 1. 向量语义检索 (Recall)
        text_vector = self.embedding_service.get_embedding(normalized_text)
        vector_matches = self._vector_recall(text_vector, scenarios)

        # 2. 评分与过滤
        scored_matches: list[dict] = []
        for scenario_data in scenarios:
            scenario = scenario_data["scenario"]
            is_recalled = scenario.scenario_id in vector_matches
            scored = self._score_scenario(
                scenario=scenario,
                normalized_text=normalized_text,
                amount=amount,
                current_city=current_city,
                common_cities=common_cities,
                is_known_payee=is_known_payee,
                vector_recall_bonus=1.0 if is_recalled else 0.0,
            )
            if scored["score"] > 0 or is_recalled:
                scored_matches.append(scored)

        if not scored_matches:
            return self._build_contextual_fallback(
                amount=amount, current_city=current_city,
                common_cities=common_cities, is_known_payee=is_known_payee,
            )

        # 语义匹配优先原则
        explicit_semantic_matches = [
            item for item in scored_matches
            if item["scenario"].scenario_id != "remote_large_transfer"
            and item["semantic_match_count"] > 0
        ]
        if explicit_semantic_matches:
            scored_matches = explicit_semantic_matches

        # 排序：总分 -> 高危命中 -> 风险等级
        scored_matches.sort(
            key=lambda item: (
                item["score"],
                len(item["high_risk_phrase_hits"]),
                self._risk_level_rank(item["effective_risk_level"]),
            ),
            reverse=True,
        )

        top_match = scored_matches[0]
        top_scenario: RiskScenario = top_match["scenario"]

        # 组装结果
        analysis_parts = [
            f"知识库匹配到风险分类「{top_scenario.risk_category}」",
            f"关键词命中：{'、'.join(top_match['matched_keywords'][:6]) or '无'}",
        ]
        if top_match["high_risk_phrase_hits"]:
            analysis_parts.append(f"高危短语命中：{'、'.join(top_match['high_risk_phrase_hits'])}")

        if top_scenario.scenario_id == "remote_large_transfer":
            analysis_parts.append(f"当前城市 {current_city} 与常用地点、金额 {amount:.2f} 元共同构成异常转账信号。")
        else:
            analysis_parts.append(top_scenario.description)

        result = RiskClassificationPayload(
            risk_category=top_scenario.risk_category,
            risk_level=str(top_match["effective_risk_level"]),
            block_hint=(
                top_match["effective_risk_level"] == "high"
                or (top_scenario.risk_level == "high" and bool(top_match["high_risk_phrase_hits"]))
            ),
            matched_keywords=top_match["matched_keywords"][:8],
            high_risk_phrase_hits=top_match["high_risk_phrase_hits"][:6],
            matched_scenarios=[item["scenario"].title for item in scored_matches[:3]],
            analysis="；".join(analysis_parts),
            follow_up_questions=self._unique(
                q for item in scored_matches[:2] for q in item["scenario"].follow_up_questions
            )[:4],
            suggested_reply_examples=list(top_scenario.suggested_reply_examples[:2]),
        )
        self._store_classification_cache(cache_key, result)
        return self._clone_payload(result)

    def _load_scenarios_with_vectors(self) -> list[dict]:
        """从数据库加载场景及其向量。"""
        if self._scenarios_cache is not None:
            return self._scenarios_cache
        with get_connection() as connection:
            rows = connection.execute("SELECT * FROM risk_scene_knowledge").fetchall()
            scenarios = []
            for row in rows:
                scenario = RiskScenario(
                    scenario_id=row["scenario_id"],
                    risk_category=row["risk_category"],
                    title=row["title"],
                    description=row["description"],
                    risk_level=row["risk_level"],
                    keywords=tuple(json.loads(row["keywords_json"])),
                    high_risk_phrases=tuple(json.loads(row["high_risk_phrases_json"])),
                    suspicious_behaviors=tuple(json.loads(row["suspicious_behaviors_json"])),
                    follow_up_questions=tuple(json.loads(row["follow_up_questions_json"])),
                    suggested_reply_examples=tuple(json.loads(row["suggested_reply_examples_json"])),
                    target_user_profiles=tuple(json.loads(row["target_user_profile_json"])),
                )
                try:
                    vector = json.loads(row["vector_json"])
                except (TypeError, ValueError, json.JSONDecodeError):
                    vector = []
                scenarios.append({"scenario": scenario, "vector": vector})
            self._scenarios_cache = scenarios
            return scenarios

    def _vector_recall(self, text_vector: list[float], scenarios: list[dict]) -> list[str]:
        """执行向量召回。"""
        if not text_vector:
            return []
        similarities = []
        for s in scenarios:
            if s["vector"]:
                sim = self.embedding_service.cosine_similarity(text_vector, s["vector"])
                similarities.append((s["scenario"].scenario_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [sid for sid, sim in similarities[:3] if sim > 0.35]

    def _score_scenario(self, **kwargs) -> dict:
        """核心评分逻辑。"""
        scenario: RiskScenario = kwargs["scenario"]
        text: str = kwargs["normalized_text"]
        amount: float = kwargs["amount"]
        is_recalled = kwargs.get("vector_recall_bonus", 0) > 0

        matched_keywords = self._affirmative_matches(text, scenario.keywords)
        high_risk_hits = self._affirmative_matches(text, scenario.high_risk_phrases)
        negated_keywords = self._negated_matches(text, scenario.keywords)
        negated_high_risk_hits = self._negated_matches(text, scenario.high_risk_phrases)
        semantic_match_count = len(matched_keywords) + len(high_risk_hits)

        score = (
            len(matched_keywords) * 1.5
            + len(high_risk_hits) * 3.0
            + kwargs.get("vector_recall_bonus", 0)
        )
        score -= len(negated_keywords) * 1.0
        score -= len(negated_high_risk_hits) * 2.0
        if scenario.scenario_id == "normal_transfer":
            score += self._count_negated_high_risk_signals(text) * 0.1
        score = max(0.0, score)

        # 远程大额场景特殊处理
        if scenario.scenario_id == "remote_large_transfer":
            if kwargs["current_city"] not in kwargs["common_cities"]:
                score += 2.0
            if amount >= 5000:
                score += 2.0
            if not kwargs["is_known_payee"]:
                score += 1.0

        base_rank = self._risk_level_rank(scenario.risk_level)
        if high_risk_hits:
            effective_risk_level = "high"
        elif score > 10:
            derived_rank = 3
            level_map = {1: "low", 2: "medium", 3: "high"}
            effective_risk_level = level_map[derived_rank]
        elif score > 5:
            derived_rank = 2
            level_map = {1: "low", 2: "medium", 3: "high"}
            effective_risk_level = level_map[max(base_rank, derived_rank)]
        else:
            derived_rank = 1
            if semantic_match_count > 0:
                effective_risk_level = "medium" if base_rank >= 2 else "low"
            elif scenario.scenario_id == "remote_large_transfer" and score >= 3.5:
                effective_risk_level = "medium"
            else:
                effective_risk_level = "low"

        return {
            "scenario": scenario,
            "score": score,
            "matched_keywords": matched_keywords,
            "high_risk_phrase_hits": high_risk_hits,
            "semantic_match_count": semantic_match_count,
            "effective_risk_level": effective_risk_level,
        }

    def _store_classification_cache(
        self,
        cache_key: tuple,
        payload: RiskClassificationPayload,
    ) -> None:
        with self._classification_cache_lock:
            self._classification_cache[cache_key] = self._clone_payload(payload)
            self._classification_cache.move_to_end(cache_key)
            while len(self._classification_cache) > self._classification_cache_max_size:
                self._classification_cache.popitem(last=False)

    def _clone_payload(
        self,
        payload: RiskClassificationPayload,
    ) -> RiskClassificationPayload:
        if hasattr(payload, "model_copy"):
            return payload.model_copy(deep=True)
        return payload.copy(deep=True)

    def _affirmative_matches(self, text: str, terms: tuple[str, ...]) -> list[str]:
        return [
            term
            for term in terms
            if nlp_utils.contains_affirmative(text, term)
        ]

    def _negated_matches(self, text: str, terms: tuple[str, ...]) -> list[str]:
        return [
            term
            for term in terms
            if nlp_utils.contains_negated(text, term)
        ]

    def _count_negated_high_risk_signals(self, text: str) -> int:
        high_risk_signals = (
            "验证码",
            "verificationcode",
            "安全账户",
            "safeaccount",
            "监管账户",
            "验资",
            "资金清查",
            "屏幕共享",
            "共享屏幕",
            "远程控制",
            "远程协助",
        )
        return sum(
            1
            for term in high_risk_signals
            if nlp_utils.contains_negated(text, term)
        )

    def _unique(self, items) -> list[str]:
        seen = set()
        res = []
        for i in items:
            if i not in seen:
                seen.add(i)
                res.append(i)
        return res

    def _risk_level_rank(self, level: str) -> int:
        return {"low": 1, "medium": 2, "high": 3}.get(level.lower(), 0)

    def _build_contextual_fallback(self, **kwargs) -> RiskClassificationPayload:
        amount = kwargs["amount"]
        current_city = kwargs["current_city"]
        common_cities = kwargs["common_cities"]
        is_remote = current_city not in common_cities

        if is_remote and amount >= 5000:
            return RiskClassificationPayload(
                risk_category="异地大额异常转账",
                risk_level="medium",
                block_hint=False,
                matched_keywords=["异地", "大额"],
                high_risk_phrase_hits=[],
                matched_scenarios=["remote_large_transfer"],
                analysis=f"当前城市 {current_city} 不在常用地点，金额 {amount:.2f} 元超过阈值，触发异地大额预警。",
                follow_up_questions=["请确认收款人身份和转账用途。", "你目前是否在非经常居住城市？"],
                suggested_reply_examples=["收款人是我朋友。"],
            )

        return RiskClassificationPayload(
            risk_category="待质询转账",
            risk_level="medium" if amount > 5000 else "low",
            block_hint=False,
            matched_keywords=[],
            high_risk_phrase_hits=[],
            matched_scenarios=["未知场景"],
            analysis="未匹配到明确风险模板，基于金额和地点进行初步风险评估。",
            follow_up_questions=["请确认收款人身份和转账用途。"],
            suggested_reply_examples=["收款人是我朋友。"],
        )


@lru_cache(maxsize=1)
def get_risk_knowledge_base_service() -> RiskKnowledgeBaseService:
    return RiskKnowledgeBaseService()
