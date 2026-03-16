from __future__ import annotations

from server.app.schemas.common import ClientContext
from server.app.schemas.transfer import TransferConfirmRequest, TransferPrecheckRequest
from server.app.services.bank_host import get_bank_host_service

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None


bank_mcp = FastMCP(name="bank-demo-server") if FastMCP is not None else None


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
    def get_common_locations() -> list[dict]:
        return get_bank_host_service().get_common_locations()


    @bank_mcp.tool()
    def precheck_transfer_risk(
        payee_name: str,
        amount: float,
        current_city: str,
        device_id: str = "mcp-device-demo",
        recent_page: str = "home",
        last_action: str = "mcp_precheck",
        semantic_summary: str = "用户通过 MCP 演示入口发起转账预检。",
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
            ),
        )
        return get_bank_host_service().precheck_transfer(payload).model_dump()


    @bank_mcp.tool()
    def commit_transfer(confirmation_token: str) -> dict:
        payload = TransferConfirmRequest(confirmation_token=confirmation_token)
        return get_bank_host_service().confirm_transfer(payload).model_dump()


if __name__ == "__main__":
    if bank_mcp is None:
        raise SystemExit("The mcp package is not installed.")
    bank_mcp.run(transport="streamable-http")
