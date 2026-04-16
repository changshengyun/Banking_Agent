from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean

import httpx
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.app.config import settings
from server.app.main import app


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = int(round((len(ordered) - 1) * p))
    return ordered[rank]


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(settings.llm_benchmark_timeout_seconds)


def _endpoint() -> str:
    return settings.llm_base_url.rstrip("/") + "/chat/completions"


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    if settings.llm_api_name:
        headers["X-Api-Name"] = settings.llm_api_name
    return headers


def _classify_http_failure(status_code: int) -> str:
    if status_code in {401, 403}:
        return "auth_failure"
    if status_code in {400, 404, 422}:
        return "model_or_route_error"
    return "network_failure"


def _extract_content_or_raise(response: httpx.Response) -> str:
    if response.status_code >= 400:
        failure_type = _classify_http_failure(response.status_code)
        raise ValueError(f"{failure_type}: HTTP {response.status_code}")
    body = response.json()
    content = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        raise ValueError("model_or_route_error: empty content")
    return content


def _extract_json_content(content: str) -> dict:
    raw = content.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("model_or_route_error: json_not_found")
    return json.loads(raw[start : end + 1])


def _llm_preflight() -> dict:
    if not settings.llm_api_key:
        return {
            "status": "failed",
            "failure_type": "missing_key",
            "reason": "LLM_API_KEY 未配置。",
        }
    if not settings.llm_model:
        return {
            "status": "failed",
            "failure_type": "model_or_route_error",
            "reason": "LLM_MODEL 未配置。",
        }

    payload = {
        "model": settings.llm_model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": "你是测试助手。"},
            {"role": "user", "content": "只输出 JSON：{\"ok\": true}"},
        ],
    }
    try:
        with httpx.Client(timeout=_timeout()) as client:
            response = client.post(_endpoint(), headers=_headers(), json=payload)
    except httpx.TimeoutException:
        return {
            "status": "failed",
            "failure_type": "timeout",
            "reason": "真实 LLM preflight 超时。",
        }
    except httpx.TransportError as error:
        return {
            "status": "failed",
            "failure_type": "network_failure",
            "reason": f"真实 LLM preflight 网络失败：{error}",
        }

    if response.status_code >= 400:
        return {
            "status": "failed",
            "failure_type": _classify_http_failure(response.status_code),
            "reason": f"真实 LLM preflight HTTP {response.status_code}",
            "http_status": response.status_code,
        }
    return {"status": "ok"}


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
    preflight = _llm_preflight()
    if preflight["status"] != "ok":
        print(
            json.dumps(
                {"status": "failed", "preflight": preflight},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    timings: list[float] = []
    drifts = 0
    rounds = 5

    try:
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
                with httpx.Client(timeout=_timeout()) as llm_client:
                    response = llm_client.post(
                        _endpoint(),
                        headers=_headers(),
                        json={
                            "model": settings.llm_model,
                            "temperature": 0.1,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "你是手机银行风控影子评估 Agent，只做风险建议，不做执行。",
                                },
                                {
                                    "role": "user",
                                    "content": _shadow_prompt(
                                        payee_name=payload["payee_name"],
                                        amount=payload["amount"],
                                        current_city=payload["context"]["current_city"],
                                        summary=payload["context"]["semantic_summary"],
                                    ),
                                },
                            ],
                        },
                    )
                shadow_body = _extract_json_content(_extract_content_or_raise(response))
                timings.append((time.perf_counter() - start) * 1000)

                if shadow_body.get("decision") != baseline_body.get("decision"):
                    drifts += 1
    except httpx.TimeoutException:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "failure_type": "timeout",
                    "reason": "precheck all-Agent shadow benchmark 调用超时。",
                    "completed_rounds": len(timings),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    except httpx.TransportError as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "failure_type": "network_failure",
                    "reason": f"precheck all-Agent shadow benchmark 网络失败：{error}",
                    "completed_rounds": len(timings),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    except ValueError as error:
        message = str(error)
        failure_type = message.split(":", 1)[0] if ":" in message else "model_or_route_error"
        print(
            json.dumps(
                {
                    "status": "failed",
                    "failure_type": failure_type,
                    "reason": message,
                    "completed_rounds": len(timings),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(
        json.dumps(
            {
                "status": "ok",
                "rounds": rounds,
                "avg_ms": round(mean(timings), 2),
                "p95_ms": round(_percentile(timings, 0.95), 2),
                "decision_drift_count": drifts,
                "decision_drift_rate": round(drifts / rounds, 4),
                "benchmark_timeout_seconds": settings.llm_benchmark_timeout_seconds,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
