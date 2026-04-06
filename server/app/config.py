from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_files(repo_root: Path) -> None:
    for path in (repo_root / ".env", repo_root / "server" / ".env"):
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_first_non_empty(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


@dataclass(frozen=True)
class Settings:
    app_env: str
    sqlite_path: Path
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_api_name: str
    mcp_bank_enabled: bool


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    _load_env_files(repo_root)
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
        llm_api_key=_get_first_non_empty(
            "LLM_API_KEY",
            "ARK_API_KEY",
            "DEEPSEEK_API_KEY",
        ),
        llm_base_url=_get_first_non_empty(
            "LLM_BASE_URL",
            "ARK_BASE_URL",
            "DEEPSEEK_BASE_URL",
            default="https://ark.cn-beijing.volces.com/api/v3",
        ),
        llm_model=_get_first_non_empty(
            "LLM_MODEL",
            "ARK_MODEL",
            "DEEPSEEK_MODEL",
            default="deepseek-v3-2-251201",
        ),
        llm_api_name=_get_first_non_empty("LLM_API_NAME", "ARK_API_NAME"),
        mcp_bank_enabled=_get_bool("MCP_BANK_ENABLED", True),
    )


settings = load_settings()
