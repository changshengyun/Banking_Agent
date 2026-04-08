from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.app.config import settings
from server.app.services.agent_service import AgentService


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = int(round((len(ordered) - 1) * p))
    return ordered[rank]


def main() -> None:
    if not settings.llm_api_key:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "LLM_API_KEY 未配置，无法执行真实 LLM 路径基准。",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    service = AgentService()
    timings: list[float] = []
    rounds = 5

    for _ in range(rounds):
        start = time.perf_counter()
        service.llm_gateway.generate_json_sync(
            system_prompt=service._build_secondary_system_prompt(),
            user_prompt=service._build_secondary_user_prompt(
                user_reply="对方说是同事介绍的熟人，我知道要转账，但现在还没有完全说清用途。",
                semantic_summary="用户在中风险场景下提交解释，希望系统继续判断。",
                risk_category="熟人借款风险",
                risk_level="medium",
                matched_keywords=["借钱", "周转"],
                matched_scenarios=["冒充熟人借钱"],
                follow_up_questions=["你是否线下认识对方？", "是否有共同联系人可确认？"],
                verification_points=["是否已视频核验对方身份", "是否有共同联系人可再次确认"],
            ),
            temperature=0.1,
        )
        timings.append((time.perf_counter() - start) * 1000)

    print(
        json.dumps(
            {
                "status": "ok",
                "rounds": rounds,
                "avg_ms": round(mean(timings), 2),
                "p95_ms": round(_percentile(timings, 0.95), 2),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
