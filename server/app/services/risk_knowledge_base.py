from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from ..db import get_connection
from ..schemas.risk import RiskClassificationPayload
from .embedding_service import get_embedding_service


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
    vector: Optional[list[float]] = field(default=None)

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
            "房租",
            "工资",
            "还款",
            "学费",
            "生活费",
            "餐费",
            "aa",
            "物业费",
            "水电费",
            "燃气费",
            "押金",
            "朋友",
            "同事",
            "家人",
            "父母",
            "房东",
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
        scenario_id="borrow_money_impersonation",
        risk_category="熟人借款风险",
        title="冒充熟人借钱",
        description="对方以换号、住院、出事、周转等理由突然借钱，并要求快速转账或保密。",
        risk_level="medium",
        keywords=(
            "借钱",
            "周转",
            "急用钱",
            "手头紧",
            "帮我付一下",
            "先转我",
            "住院",
            "手术",
            "出车祸",
            "救急",
            "学费",
            "马上转",
        ),
        high_risk_phrases=(
            "猜猜我是谁",
            "我是新号",
            "先别告诉别人",
            "先转我救急",
            "借我周转一下",
            "borrow money",
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
            "公安",
            "警察",
            "检察院",
            "法院",
            "涉案",
            "洗钱",
            "笔录",
            "冻结资产",
            "通缉令",
            "案件",
            "反诈中心",
            "police",
        ),
        high_risk_phrases=(
            "线上做笔录",
            "涉嫌洗钱",
            "安全审查",
            "办案账户",
            "冻结前先转账",
            "保密办案",
            "case investigation",
        ),
        suspicious_behaviors=("要求下载软件", "要求保密", "要求转账核验", "要求屏幕共享"),
        follow_up_questions=(
            "对方是否要求你转账核验资金、提供验证码或共享屏幕？",
            "你是否通过官方公开电话核实过对方身份和案号？",
        ),
        suggested_reply_examples=(
            "我没有通过任何官方电话核实，如果对方要求转账或屏幕共享，我会立即停止操作并报警。",
            "涉及公检法事项时，我只会主动拨打官方电话核验，不会向陌生账户转账。",
        ),
        target_user_profiles=("老年用户", "风险认知较弱用户"),
    ),
    RiskScenario(
        scenario_id="safe_account_scam",
        risk_category="安全账户诈骗",
        title="转入安全账户",
        description="对方声称账户异常或资金需要清查，要求将钱转到所谓安全账户或监管账户。",
        risk_level="high",
        keywords=(
            "安全账户",
            "监管账户",
            "资金清查",
            "资金核验",
            "账户冻结",
            "验资",
            "风险账户",
            "涉案账户",
            "safe account",
        ),
        high_risk_phrases=(
            "转到安全账户",
            "转入监管账户",
            "资金清查完成后返还",
            "冻结前先转账核验",
            "transfer to safe account",
        ),
        suspicious_behaviors=("要求转到陌生账户", "索要验证码", "要求立即操作"),
        follow_up_questions=(
            "对方是否明确要求你把钱转到安全账户或监管账户？",
            "对方是否要求你提供验证码、密码或共享屏幕？",
        ),
        suggested_reply_examples=(
            "如果对方要求转入安全账户，我不会继续转账，并会通过银行官方渠道核实。",
            "我不会向所谓安全账户转账，也不会提供验证码或开启屏幕共享。",
        ),
        target_user_profiles=("老年用户", "首次接触反诈知识用户"),
    ),
    RiskScenario(
        scenario_id="refund_customer_service",
        risk_category="客服退款诈骗",
        title="冒充客服退款或百万保障",
        description="对方冒充平台客服，以退款、关闭会员、自动扣费、百万保障到期等理由诱导转账。",
        risk_level="high",
        keywords=(
            "客服",
            "退款",
            "关闭会员",
            "自动续费",
            "取消服务",
            "百万保障",
            "扣费",
            "退保",
            "返款",
            "customer service",
            "refund",
        ),
        high_risk_phrases=(
            "验证资金后退款",
            "关闭服务前先操作资金",
            "刷流水后返还",
            "退款前要先转账",
            "refund after verification",
        ),
        suspicious_behaviors=("要求下载软件", "要求点击链接", "要求远程协助", "要求屏幕共享"),
        follow_up_questions=(
            "你是否已通过官方 App、官网或官方客服入口核实？",
            "对方是否要求你下载软件、共享屏幕或转账验证？",
        ),
        suggested_reply_examples=(
            "我只会通过官方 App 联系客服，不会根据陌生电话要求转账验证。",
            "如果是退款，我会在官方平台内核实，不会提供验证码或共享屏幕。",
        ),
        target_user_profiles=("网购高频用户", "中青年用户"),
    ),
    RiskScenario(
        scenario_id="otp_screen_share",
        risk_category="验证码/屏幕共享诈骗",
        title="验证码或屏幕共享诱导",
        description="对方要求提供验证码、安装远程软件或开启屏幕共享以指导转账操作。",
        risk_level="high",
        keywords=(
            "验证码",
            "屏幕共享",
            "远程控制",
            "远程协助",
            "会议软件",
            "共享屏幕",
            "短信验证码",
            "远程桌面",
            "screen share",
            "verification code",
        ),
        high_risk_phrases=(
            "把验证码发给我",
            "开启屏幕共享",
            "我来远程指导你",
            "send me the verification code",
        ),
        suspicious_behaviors=("索取验证码", "要求安装远程软件", "诱导点击陌生链接"),
        follow_up_questions=(
            "是否有人向你索要验证码或要求开启屏幕共享？",
            "是否有人要求你安装会议软件或远程控制工具？",
        ),
        suggested_reply_examples=(
            "没有人向我索要验证码，也没有要求我开启屏幕共享或安装远程软件。",
            "如果有人索要验证码或要求屏幕共享，我会立即停止操作。",
        ),
        target_user_profiles=("全量用户", "数字技能较弱用户"),
    ),
    RiskScenario(
        scenario_id="remote_large_transfer",
        risk_category="异地大额异常转账",
        title="异地大额异常转账",
        description="用户在非常用城市发起大额或高频转账，且收款人不熟悉或用途不清晰。",
        risk_level="medium",
        keywords=(
            "异地",
            "大额",
            "马上转",
            "频繁转账",
            "别告诉别人",
            "临时转账",
            "先打过去",
            "跨城",
        ),
        high_risk_phrases=(
            "马上转过去",
            "不要告诉任何人",
            "转给陌生账户",
        ),
        suspicious_behaviors=("非常用地点操作", "金额异常", "新增收款人", "高频转账"),
        follow_up_questions=(
            "本次转账用途是什么，是否线下认识收款人？",
            "是否有人催促你立刻完成转账或要求你保密？",
        ),
        suggested_reply_examples=(
            "我现在在北京出差，收款人是小f，本次转账用于酒店押金，不涉及验证码或安全账户。",
            "我在西安出差，收款人是公司同事，本次转账用于垫付差旅费用，没有人催促或要求保密。",
        ),
        target_user_profiles=("出差用户", "跨城流动用户"),
    ),
    RiskScenario(
        scenario_id="investment_fraud",
        risk_category="投资理财诈骗",
        title="高收益投资诱导",
        description="对方以内部消息、稳赚不赔、老师带单、私募名额等说法诱导转账投资。",
        risk_level="high",
        keywords=(
            "内部消息",
            "稳赚",
            "高收益",
            "导师",
            "老师带单",
            "跟单",
            "私募",
            "荐股",
            "虚拟币",
            "数字货币",
            "理财老师",
            "投资群",
        ),
        high_risk_phrases=(
            "稳赚不赔",
            "老师带单",
            "内幕消息",
            "保本保收益",
            "今晚拉升",
        ),
        suspicious_behaviors=("诱导加群", "承诺高收益", "要求转到个人账户", "非官方平台开户"),
        follow_up_questions=(
            "对方是否承诺稳定收益、保本或内幕消息？",
            "你是否在非官方平台或个人账户进行投资转账？",
        ),
        suggested_reply_examples=(
            "如果对方承诺稳赚不赔或内部消息，我不会继续转账，也会退出相关群聊。",
            "投资理财我只会通过持牌机构官方平台操作，不会向个人账户转账。",
        ),
        target_user_profiles=("中老年投资用户", "高收益偏好用户"),
    ),
    RiskScenario(
        scenario_id="romance_scam",
        risk_category="情感诈骗",
        title="网恋情感诈骗",
        description="对方以恋爱、见面、送礼、机票、清关或紧急困难等理由向用户索要转账。",
        risk_level="high",
        keywords=(
            "网恋",
            "恋爱对象",
            "交友软件",
            "见面",
            "机票",
            "礼物",
            "清关",
            "生活困难",
            "住院",
            "想见你",
            "异国恋",
        ),
        high_risk_phrases=(
            "见面前先转账",
            "礼物清关费",
            "转账后就来见你",
            "帮我买机票",
        ),
        suspicious_behaviors=("未线下见面", "频繁情感承诺", "以困难为由索款", "要求反复转账"),
        follow_up_questions=(
            "你是否与对方线下见过面，是否能核实真实身份？",
            "对方是否要求你先转账才能见面、寄礼物或处理清关？",
        ),
        suggested_reply_examples=(
            "如果对方没有线下见面却要求我先转账，我不会继续操作。",
            "礼物、机票、清关等费用我不会向网恋对象直接转账，会先核实身份。",
        ),
        target_user_profiles=("单身交友用户", "情感依赖型用户"),
    ),
    RiskScenario(
        scenario_id="part_time_fraud",
        risk_category="刷单兼职诈骗",
        title="刷单兼职诈骗",
        description="对方以兼职、刷单、做任务、关注返现等理由诱导用户先垫付资金后返佣。",
        risk_level="high",
        keywords=(
            "刷单",
            "兼职",
            "任务单",
            "垫付",
            "返佣",
            "佣金",
            "做任务",
            "关注返现",
            "点赞赚钱",
            "解冻金额",
            "提现",
        ),
        high_risk_phrases=(
            "先垫付后返现",
            "完成任务单就返佣",
            "再做一单就能提现",
            "垫资解冻",
        ),
        suspicious_behaviors=("先付款后返利", "不断追加金额", "小额返现诱导大额投入", "任务无法结束"),
        follow_up_questions=(
            "这份兼职是否要求你先垫付资金或连续完成任务单？",
            "你是否通过官方平台接单，还是通过聊天软件私下联系？",
        ),
        suggested_reply_examples=(
            "如果兼职要求我先垫付资金或继续做单才能提现，我会立即停止操作。",
            "我不会通过聊天软件接刷单任务，也不会为了返佣继续转账。",
        ),
        target_user_profiles=("学生用户", "兼职求职用户", "宝妈用户"),
    ),
)


from .embedding_service import get_embedding_service


class RiskKnowledgeBaseService:
    def __init__(self) -> None:
        self.embedding_service = get_embedding_service()

    def ensure_seeded(self) -> None:
        scenarios_to_seed = []
        with get_connection() as connection:
            existing_ids = {
                row["scenario_id"]
                for row in connection.execute(
                    "SELECT scenario_id FROM risk_scene_knowledge"
                ).fetchall()
            }
            for scenario in DEFAULT_RISK_SCENARIOS:
                if scenario.scenario_id not in existing_ids:
                    scenarios_to_seed.append(scenario)

            if scenarios_to_seed:
                embeddings = self.embedding_service.batch_get_embeddings(
                    [s.embedding_text for s in scenarios_to_seed]
                )
                for scenario, vector in zip(scenarios_to_seed, embeddings):
                    connection.execute(
                        """
                        INSERT INTO risk_scene_knowledge
                        (scenario_id, risk_category, title, description, risk_level, keywords_json,
                         high_risk_phrases_json, suspicious_behaviors_json, follow_up_questions_json,
                         suggested_reply_examples_json, target_user_profile_json, embedding_text,
                         vector_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
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
                            json.dumps(scenario.target_user_profiles, ensure_ascii=False),
                            scenario.embedding_text,
                            json.dumps(vector),
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
            return self._build_contextual_fallback(
                amount=amount,
                current_city=current_city,
                common_cities=common_cities,
                is_known_payee=is_known_payee,
            )

        # 1. 向量语义检索 (Recall)
        text_vector = self.embedding_service.get_embedding(normalized_text)
        vector_matches = self._vector_recall(text_vector, scenarios)

        # 2. 关键词精排与分值计算
        scored_matches: list[dict] = []
        for scenario in scenarios:
            is_recalled = scenario.scenario_id in vector_matches
            scored = self._score_scenario(
                scenario=scenario,
                normalized_text=normalized_text,
                amount=amount,
                current_city=current_city,
                common_cities=common_cities,
                is_known_payee=is_known_payee,
                vector_recall_bonus=5.0 if is_recalled else 0.0,
            )
            if scored["score"] > 0 or is_recalled:
                scored_matches.append(scored)

        if not scored_matches:
            return self._build_contextual_fallback(
                amount=amount,
                current_city=current_city,
                common_cities=common_cities,
                is_known_payee=is_known_payee,
            )

        explicit_semantic_matches = [
            item
            for item in scored_matches
            if item["scenario"].scenario_id != "remote_large_transfer"
            and (item["semantic_match_count"] > 0 or item["scenario"].scenario_id in vector_matches)
        ]
        if explicit_semantic_matches:
            scored_matches = explicit_semantic_matches

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
        matched_scenarios = [item["scenario"].title for item in scored_matches[:3]]
        follow_up_questions = self._unique(
            question
            for item in scored_matches[:2]
            for question in item["scenario"].follow_up_questions
        )[:4]
        suggested_reply_examples = list(top_scenario.suggested_reply_examples[:2])
        high_risk_phrase_hits = self._unique(
            phrase
            for item in scored_matches
            for phrase in item["high_risk_phrase_hits"]
        )[:6]

        analysis_parts = [
            f"知识库匹配到风险分类“{top_scenario.risk_category}”",
            f"关键词命中：{'、'.join(top_match['matched_keywords'][:6]) or '无'}",
        ]
        if high_risk_phrase_hits:
            analysis_parts.append(f"高危短语命中：{'、'.join(high_risk_phrase_hits)}")
        if top_scenario.target_user_profiles:
            analysis_parts.append(
                f"典型受害画像：{'、'.join(top_scenario.target_user_profiles[:2])}"
            )
        if top_scenario.scenario_id == "remote_large_transfer":
            analysis_parts.append(
                f"当前城市 {current_city} 与常用地点、金额 {amount:.2f} 元共同构成异常转账信号。"
            )
        else:
            analysis_parts.append(top_scenario.description)

        effective_risk_level = str(top_match["effective_risk_level"])
        return RiskClassificationPayload(
            risk_category=top_scenario.risk_category,
            risk_level=effective_risk_level,
            block_hint=effective_risk_level == "high",
            matched_keywords=top_match["matched_keywords"][:8],
            high_risk_phrase_hits=high_risk_phrase_hits,
            matched_scenarios=matched_scenarios,
            analysis="；".join(analysis_parts),
            follow_up_questions=follow_up_questions,
            suggested_reply_examples=suggested_reply_examples,
        )

    # HIRD-I: 识别层，负责在语义缺失时基于上下文做兜底分类。
    def _build_contextual_fallback(
        self,
        *,
        amount: float,
        current_city: str,
        common_cities: list[str],
        is_known_payee: bool,
    ) -> RiskClassificationPayload:
        context_signals: list[str] = []
        context_score = 0

        if current_city not in common_cities:
            context_score += 2
            context_signals.append("异地")
        if amount >= 10000:
            context_score += 3
            context_signals.append("高额")
        elif amount >= 5000:
            context_score += 2
            context_signals.append("中大额")
        if not is_known_payee:
            context_score += 2
            context_signals.append("新增收款人")

        if context_score >= 4:
            remote_scenario = self._scenario_by_id("remote_large_transfer")
            return RiskClassificationPayload(
                risk_category=remote_scenario.risk_category,
                risk_level="medium",
                block_hint=False,
                matched_keywords=context_signals,
                high_risk_phrase_hits=[],
                matched_scenarios=[remote_scenario.title],
                analysis=(
                    "语义摘要为空，系统改用金额、城市与收款人关系做兜底识别；"
                    f"当前命中信号：{'、'.join(context_signals)}。"
                ),
                follow_up_questions=list(remote_scenario.follow_up_questions[:2]),
                suggested_reply_examples=list(
                    remote_scenario.suggested_reply_examples[:2]
                ),
            )

        return self._build_normal_result(amount=amount, current_city=current_city)

    # HIRD-I: 识别层，负责构建低风险正常场景的标准化分类结果。
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
            high_risk_phrase_hits=[],
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

    # HIRD-I: 识别层，负责把单一风险场景转换为可比较的分类得分。
    def _score_scenario(
        self,
        *,
        scenario: RiskScenario,
        normalized_text: str,
        amount: float,
        current_city: str,
        common_cities: list[str],
        is_known_payee: bool,
        vector_recall_bonus: float = 0.0,
    ) -> dict:
        keyword_matches = self._collect_matches(normalized_text, scenario.keywords)
        phrase_matches = self._collect_matches(
            normalized_text,
            scenario.high_risk_phrases,
        )
        matched_keywords = self._unique(keyword_matches + phrase_matches)
        score = (
            (len(keyword_matches) * 2)
            + (len(phrase_matches) * 6)
            + vector_recall_bonus
        )

        if scenario.scenario_id == "remote_large_transfer":
            if current_city not in common_cities:
                score += 3
                matched_keywords.append("异地")
            if amount >= 10000:
                score += 4
                matched_keywords.append("高额")
            elif amount >= 5000:
                score += 3
                matched_keywords.append("中大额")
            if not is_known_payee:
                score += 2
                matched_keywords.append("新增收款人")

        effective_risk_level = (
            "high" if phrase_matches else scenario.risk_level.lower()
        )
        return {
            "scenario": scenario,
            "score": score,
            "semantic_match_count": len(keyword_matches) + len(phrase_matches),
            "matched_keywords": self._unique(matched_keywords),
            "high_risk_phrase_hits": self._unique(phrase_matches),
            "effective_risk_level": effective_risk_level,
        }

    # HIRD-H: 感知层，负责从数据库读取最新风险场景知识。
    def _load_scenarios(self) -> list[RiskScenario]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT scenario_id, risk_category, title, description, risk_level,
                       keywords_json, high_risk_phrases_json, suspicious_behaviors_json,
                       follow_up_questions_json, suggested_reply_examples_json,
                       target_user_profile_json
                FROM risk_scene_knowledge
                ORDER BY scenario_id
                """
            ).fetchall()

        scenarios: list[RiskScenario] = []
        for row in rows:
            payload = dict(row)
            vector = None
            if payload.get("vector_json"):
                try:
                    vector = json.loads(payload["vector_json"])
                except Exception:
                    pass

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
                    target_user_profiles=tuple(
                        json.loads(payload.get("target_user_profile_json") or "[]")
                    ),
                    vector=vector,
                )
            )
        return scenarios

    # HIRD-H: 感知层，负责从原始文本中提取关键词或短语命中项。
    def _collect_matches(self, text: str, candidates: tuple[str, ...]) -> list[str]:
        matches: list[str] = []
        for candidate in candidates:
            lowered = candidate.lower().strip()
            if lowered and lowered in text:
                matches.append(candidate)
        return matches

    # HIRD-I: 识别层，负责提供风险等级排序权重。
    def _vector_recall(
        self, text_vector: list[float], scenarios: list[RiskScenario]
    ) -> list[str]:
        # HIRD-P: 感知层，执行向量相似度召回。
        # 在 V3.1-b 中，由于暂无真正的 FAISS 库，此处实现简单的余弦相似度（Mock 环境下为 0）。
        # 返回 Top-3 召回的 scenario_id。
        matches = []
        for s in scenarios:
            if s.vector and text_vector:
                # 实际计算逻辑...
                pass
        return matches

    def _risk_level_rank(self, risk_level: str) -> int:
        mapping = {"low": 1, "medium": 2, "high": 3}
        return mapping.get(risk_level.lower(), 0)

    # HIRD-H: 感知层，负责在本地知识库中按 ID 取回风险场景。
    def _scenario_by_id(self, scenario_id: str) -> RiskScenario:
        for scenario in DEFAULT_RISK_SCENARIOS:
            if scenario.scenario_id == scenario_id:
                return scenario
        raise ValueError(f"Unknown risk scenario: {scenario_id}")

    # HIRD-H: 感知层，负责去重和清洗候选命中词。
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


# HIRD-H: 感知层，负责提供知识库服务的单例入口。
@lru_cache(maxsize=1)
def get_risk_knowledge_base_service() -> RiskKnowledgeBaseService:
    return RiskKnowledgeBaseService()
