from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutdoorKnowledgeService:
    _knowledge_base: tuple[tuple[str, str], ...] = (
        ("露营", "露营前优先确认天气、饮水点、撤离路线，并准备应急照明和保暖层。"),
        ("徒步", "徒步建议采用分层穿衣，控制配速，并在出发前共享行程和预计返回时间。"),
        ("登山", "登山时注意海拔变化、补水频率和落石风险，尽量避免单人夜间上山。"),
    )

    def answer(self, question: str) -> str:
        for keyword, answer in self._knowledge_base:
            if keyword in question:
                return answer
        return "户外知识库当前支持露营、徒步和登山类基础问答，可继续追问装备或安全建议。"

