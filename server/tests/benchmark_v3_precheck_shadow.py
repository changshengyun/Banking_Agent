from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.app.config import settings
from server.app.main import app
from server.app.services.llm_gateway import LLMGateway


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = int(round((len(ordered) - 1) * p))
    return ordered[rank]


def _shadow_prompt(*, payee_name: str, amount: float, current_city: str, summary: str) -> str:
    return (
        "请根据转账上下文判断风险决策，只允许输出严格 JSON：\n"
        '{"decision":"pass|interrogate|block","risk_level":"low|medium|high","reasons":["原因"]}\n'
        f"收款人：{payee_name}\n"
        f"金额：{amount}\n"
        f"城市：{current_city}\n"
        f"语义摘要：{summary}\n"
        "不要输出任何额外文本。"
    )


def main() -> None:
    if not settings.llm_api_key:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "LLM_API_KEY 未配置，无法执行 precheck 全 Agent 影子基准。",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    gateway = LLMGateway()
    timings: list[float] = []
    drifts = 0
    rounds = 5

    with TestClient(app) as client:
        for idx in range(rounds):
            payload = {
                "payee_name": "小c",
                "amount": 8000,
                "context": {
                    "session_id": f"shadow-precheck-{idx}",
                    "device_id": "shadow-device",
                    "platform": "benchmark",
                    "current_city": "北京",
                    "lat": 39.9042,
                    "lng": 116.4074,
                    "recent_page": "home",
                    "last_action": "tap_transfer",
                    "semantic_summary": "用户在异地发起大额转账。",
                },
            }
            baseline = client.post("/api/v1/transfers/precheck", json=payload)
            baseline.raise_for_status()
            baseline_body = baseline.json()

            start = time.perf_counter()
            shadow_body = gateway.generate_json_sync(
                system_prompt="你是手机银行风控影子评估 Agent，只做风险建议，不做执行。",
                user_prompt=_shadow_prompt(
                    payee_name=payload["payee_name"],
                    amount=payload["amount"],
                    current_city=payload["context"]["current_city"],
                    summary=payload["context"]["semantic_summary"],
                ),
                temperature=0.1,
            )
            timings.append((time.perf_counter() - start) * 1000)

            if shadow_body.get("decision") != baseline_body.get("decision"):
                drifts += 1

    print(
        json.dumps(
            {
                "status": "ok",
                "rounds": rounds,
                "avg_ms": round(mean(timings), 2),
                "p95_ms": round(_percentile(timings, 0.95), 2),
                "decision_drift_count": drifts,
                "decision_drift_rate": round(drifts / rounds, 4),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
