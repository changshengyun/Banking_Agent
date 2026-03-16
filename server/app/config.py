from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    sqlite_path: Path
    mock_llm: bool
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    mcp_bank_enabled: bool
    mcp_outdoor_enabled: bool


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    sqlite_path = Path(
        os.getenv(
            "SQLITE_PATH",
            str(repo_root / "server" / "data" / "banking_ai_demo.db"),
        )
    )
    if not sqlite_path.is_absolute():
        sqlite_path = repo_root / sqlite_path
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        sqlite_path=sqlite_path,
        mock_llm=_get_bool("MOCK_LLM", True),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_model=os.getenv("LLM_MODEL", ""),
        mcp_bank_enabled=_get_bool("MCP_BANK_ENABLED", True),
        mcp_outdoor_enabled=_get_bool("MCP_OUTDOOR_ENABLED", True),
    )


settings = load_settings()

