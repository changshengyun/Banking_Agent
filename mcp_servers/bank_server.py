from __future__ import annotations

from typing import Any

from server.app.db import get_connection
from server.app.repositories.banking import BankingRepository
from server.app.schemas.common import ClientContext
from server.app.schemas.transfer import TransferConfirmRequest, TransferPrecheckRequest
from server.app.services.bank_host import get_bank_host_service

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None


bank_mcp = FastMCP(name="bank-demo-server") if FastMCP is not None else None


def _load_static_profile(user_id: str = "小a") -> dict[str, Any]:
    repository = BankingRepository(user_id=user_id)
    profile = repository.get_user_profile()
    common_locations = repository.get_common_locations()

    fallback = {
        "user_id": user_id,
        "flag_s": 0.2,
        "scenario": "normal_activity",
        "relation_level_b": 0.85,
        "blacklist_hit": False,
        "common_device": True,
        "home_city": profile.get("home_city"),
        "common_location_count": len(
            [item for item in common_locations if int(item.get("is_common", 0)) == 1]
        ),
        "source": "fallback_profile",
    }

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT user_id, flag_s, scenario, relation_level_b,
                       blacklist_hit, common_device
                FROM risk_profiles
                WHERE user_id = ?
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
    except Exception:
        return fallback

    if row is None:
        return fallback

    payload = dict(row)
    payload["blacklist_hit"] = bool(payload.get("blacklist_hit", 0))
    payload["common_device"] = bool(payload.get("common_device", 1))
    payload["home_city"] = profile.get("home_city")
    payload["common_location_count"] = len(
        [item for item in common_locations if int(item.get("is_common", 0)) == 1]
    )
    payload["source"] = "risk_profiles"
    return payload


if bank_mcp is not None:

    @bank_mcp.tool()
    def get_account_summary() -> dict:
        return get_bank_host_service().get_dashboard().model_dump()


    @bank_mcp.tool()
    def list_transactions(limit: int = 10) -> dict:
        return get_bank_host_service().list_transactions(limit=limit).model_dump()


    @bank_mcp.tool()
    def get_user_profile() -> dict:
        return get_bank_host_service().get_user_profile()


    @bank_mcp.tool()
    def get_static_profile(user_id: str = "小a") -> dict:
        return _load_static_profile(user_id=user_id)


    @bank_mcp.tool()
    def get_common_locations() -> list[dict]:
        return get_bank_host_service().get_common_locations()


    @bank_mcp.tool()
    def classify_transfer_risk(
        payee_name: str,
        amount: float,
        current_city: str,
        device_id: str = "mcp-device-demo",
        recent_page: str = "home",
        last_action: str = "mcp_classify",
        semantic_summary: str = "User requests risk classification via MCP demo.",
        input_pause_count: int | None = None,
        input_duration_ms: int | None = None,
    ) -> dict:
        payload = TransferPrecheckRequest(
            payee_name=payee_name,
            amount=amount,
            context=ClientContext(
                device_id=device_id,
                current_city=current_city,
                recent_page=recent_page,
                last_action=last_action,
                semantic_summary=semantic_summary,
                input_pause_count=input_pause_count,
                input_duration_ms=input_duration_ms,
            ),
        )
        return get_bank_host_service().classify_transfer_risk(payload).model_dump()


    @bank_mcp.tool()
    def precheck_transfer_risk(
        payee_name: str,
        amount: float,
        current_city: str,
        device_id: str = "mcp-device-demo",
        recent_page: str = "home",
        last_action: str = "mcp_precheck",
        semantic_summary: str = "User initiates transfer precheck via MCP demo.",
        input_pause_count: int | None = None,
        input_duration_ms: int | None = None,
    ) -> dict:
        payload = TransferPrecheckRequest(
            payee_name=payee_name,
            amount=amount,
            context=ClientContext(
                device_id=device_id,
                current_city=current_city,
                recent_page=recent_page,
                last_action=last_action,
                semantic_summary=semantic_summary,
                input_pause_count=input_pause_count,
                input_duration_ms=input_duration_ms,
            ),
        )
        response = get_bank_host_service().precheck_transfer(payload).model_dump()
        response["risk_breakdown"] = {
            "flag_s": response.get("flag_s"),
            "g_behavior": response.get("g_behavior"),
            "g_dynamic": response.get("g_dynamic"),
            "final_risk": response.get("final_risk"),
        }
        response["risk_classification"] = response.get("risk_classification", {})
        return response


    @bank_mcp.tool()
    def screen_external_intelligence(payee_name: str) -> dict:
        return get_bank_host_service().screen_external_intelligence(payee_name).model_dump()


    @bank_mcp.tool()
    def commit_transfer(confirmation_token: str) -> dict:
        payload = TransferConfirmRequest(confirmation_token=confirmation_token)
        return get_bank_host_service().confirm_transfer(payload).model_dump()


if __name__ == "__main__":
    if bank_mcp is None:
        raise SystemExit("The mcp package is not installed.")
    bank_mcp.run(transport="streamable-http")
