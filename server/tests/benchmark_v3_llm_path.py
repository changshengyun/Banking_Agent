from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean

import httpx


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


def _preflight_payload() -> dict:
    return {
        "model": settings.llm_model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": "你是测试助手。"},
            {"role": "user", "content": "只输出 JSON：{\"ok\": true}"},
        ],
    }


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

    try:
        with httpx.Client(timeout=_timeout()) as client:
            response = client.post(
                _endpoint(),
                headers=_headers(),
                json=_preflight_payload(),
            )
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

    try:
        body = response.json()
    except ValueError:
        return {
            "status": "failed",
            "failure_type": "model_or_route_error",
            "reason": "真实 LLM preflight 返回非 JSON。",
        }
    content = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not content:
        return {
            "status": "failed",
            "failure_type": "model_or_route_error",
            "reason": "真实 LLM preflight 返回空内容。",
        }
    return {"status": "ok"}


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

    service = AgentService()
    timings: list[float] = []
    rounds = 5

    try:
        for _ in range(rounds):
            system_prompt = service._build_secondary_system_prompt()
            user_prompt = service._build_secondary_user_prompt(
                user_reply="对方说是同事介绍的熟人，我知道要转账，但现在还没有完全说清用途。",
                semantic_summary="用户在中风险场景下提交解释，希望系统继续判断。",
                risk_category="熟人借款风险",
                risk_level="medium",
                matched_keywords=["借钱", "周转"],
                matched_scenarios=["冒充熟人借钱"],
                follow_up_questions=["你是否线下认识对方？", "是否有共同联系人可确认？"],
                verification_points=["是否已视频核验对方身份", "是否有共同联系人可再次确认"],
            )
            start = time.perf_counter()
            with httpx.Client(timeout=_timeout()) as client:
                response = client.post(
                    _endpoint(),
                    headers=_headers(),
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.1,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
            content = _extract_content_or_raise(response)
            _extract_json_content(content)
            timings.append((time.perf_counter() - start) * 1000)
    except httpx.TimeoutException:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "failure_type": "timeout",
                    "reason": "真实 LLM benchmark 调用超时。",
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
                    "reason": f"真实 LLM benchmark 网络失败：{error}",
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
                "benchmark_timeout_seconds": settings.llm_benchmark_timeout_seconds,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
