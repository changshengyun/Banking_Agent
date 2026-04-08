from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean

from fastapi.testclient import TestClient

# 支持直接执行 python server/tests/benchmark_v3_baseline.py
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.app.main import app


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = int(round((len(ordered) - 1) * p))
    return ordered[rank]


def _build_context(*, session_id: str, city: str, semantic_summary: str) -> dict:
    coordinates = {
        "上海": (31.2304, 121.4737),
        "北京": (39.9042, 116.4074),
    }
    lat, lng = coordinates.get(city, (31.2304, 121.4737))
    return {
        "session_id": session_id,
        "device_id": "bench-device",
        "platform": "benchmark",
        "current_city": city,
        "lat": lat,
        "lng": lng,
        "recent_page": "home",
        "last_action": "tap_transfer",
        "semantic_summary": semantic_summary,
    }


def run_precheck_benchmark(*, client: TestClient, rounds: int = 50) -> dict[str, float]:
    timings: list[float] = []
    for idx in range(rounds):
        payload = {
            "payee_name": "小b",
            "amount": 300,
            "context": _build_context(
                session_id=f"bench-precheck-{idx}",
                city="上海",
                semantic_summary="收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。",
            ),
        }
        start = time.perf_counter()
        response = client.post("/api/v1/transfers/precheck", json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        timings.append(elapsed_ms)
    return {
        "avg_ms": round(mean(timings), 2),
        "p95_ms": round(_percentile(timings, 0.95), 2),
    }


def run_secondary_benchmark(*, client: TestClient, rounds: int = 30) -> dict[str, float]:
    timings: list[float] = []
    for idx in range(rounds):
        precheck_payload = {
            "payee_name": "小c",
            "amount": 8000,
            "context": _build_context(
                session_id=f"bench-secondary-{idx}",
                city="北京",
                semantic_summary="普通转账需求。",
            ),
        }
        precheck = client.post("/api/v1/transfers/precheck", json=precheck_payload)
        assert precheck.status_code == 200
        token = precheck.json()["confirmation_token"]
        secondary_payload = {
            "confirmation_token": token,
            "user_reply": "收款人是我朋友，这次是还款，不涉及验证码、安全账户或屏幕共享。",
            "context": {
                **_build_context(
                    session_id=f"bench-secondary-{idx}",
                    city="北京",
                    semantic_summary="用户提交补充说明。",
                ),
                "recent_page": "transfer",
                "last_action": "secondary_check",
            },
        }
        start = time.perf_counter()
        secondary = client.post("/api/v1/transfers/secondary-check", json=secondary_payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert secondary.status_code == 200
        timings.append(elapsed_ms)
    return {
        "avg_ms": round(mean(timings), 2),
        "p95_ms": round(_percentile(timings, 0.95), 2),
    }


def main() -> None:
    with TestClient(app) as client:
        precheck = run_precheck_benchmark(client=client)
        secondary = run_secondary_benchmark(client=client)
    result = {
        "precheck": precheck,
        "secondary_check": secondary,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
