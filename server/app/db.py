from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from .config import settings


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    home_city TEXT NOT NULL,
    risk_preference TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    cash_balance REAL NOT NULL,
    wealth_balance REAL NOT NULL,
    currency TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    amount REAL NOT NULL,
    is_income INTEGER NOT NULL,
    category TEXT NOT NULL,
    city TEXT NOT NULL,
    payee_name TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payees (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    last_city TEXT NOT NULL,
    transfer_count INTEGER NOT NULL DEFAULT 0,
    last_transfer_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS location_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    confidence REAL NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_common INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS risk_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    flag_s REAL NOT NULL,
    scenario TEXT NOT NULL,
    relation_level_b REAL NOT NULL,
    common_device INTEGER NOT NULL DEFAULT 1,
    blacklist_hit INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_scene_knowledge (
    scenario_id TEXT PRIMARY KEY,
    risk_category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    high_risk_phrases_json TEXT NOT NULL,
    suspicious_behaviors_json TEXT NOT NULL,
    follow_up_questions_json TEXT NOT NULL,
    suggested_reply_examples_json TEXT NOT NULL,
    target_user_profile_json TEXT NOT NULL DEFAULT '[]',
    embedding_text TEXT NOT NULL,
    vector_json TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    payee_name TEXT NOT NULL,
    amount REAL NOT NULL,
    city TEXT NOT NULL,
    device_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    decision TEXT NOT NULL,
    flag_s REAL NOT NULL DEFAULT 0.0,
    g_behavior REAL NOT NULL DEFAULT 0.0,
    g_dynamic REAL NOT NULL DEFAULT 0.0,
    final_risk REAL NOT NULL DEFAULT 0.0,
    secondary_decision TEXT,
    secondary_risk REAL NOT NULL DEFAULT 0.0,
    secondary_reply TEXT,
    policy_version TEXT,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_events (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    confirmation_token TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    decision TEXT,
    risk_level TEXT,
    final_risk REAL NOT NULL DEFAULT 0.0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_transfers (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    payee_name TEXT NOT NULL,
    amount REAL NOT NULL,
    city TEXT NOT NULL,
    device_id TEXT NOT NULL,
    recent_page TEXT NOT NULL,
    last_action TEXT NOT NULL,
    semantic_summary TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    decision TEXT NOT NULL,
    flag_s REAL NOT NULL DEFAULT 0.0,
    g_behavior REAL NOT NULL DEFAULT 0.0,
    g_dynamic REAL NOT NULL DEFAULT 0.0,
    final_risk REAL NOT NULL DEFAULT 0.0,
    secondary_decision TEXT NOT NULL DEFAULT 'pending',
    secondary_risk REAL NOT NULL DEFAULT 0.0,
    secondary_reasons_json TEXT,
    secondary_question TEXT,
    secondary_reply TEXT,
    secondary_checked_at TEXT,
    policy_version TEXT,
    reasons_json TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_reports (
    confirmation_token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    headline TEXT NOT NULL,
    overall_risk_level TEXT NOT NULL,
    risk_summary TEXT NOT NULL,
    risk_factors_json TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""


@contextmanager
def get_connection() -> sqlite3.Connection:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.sqlite_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(
    connection: sqlite3.Connection, table_name: str, column_name: str, column_ddl: str
) -> None:
    if column_name in _table_columns(connection, table_name):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}")


# HIRD-H: 感知层基础设施，负责为知识库与风控链路补齐运行时所需表结构。
def init_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)
        _ensure_column(
            connection,
            "risk_scene_knowledge",
            "target_user_profile_json",
            "target_user_profile_json TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            "risk_scene_knowledge",
            "vector_json",
            "vector_json TEXT",
        )
        _ensure_column(
            connection,
            "risk_events",
            "flag_s",
            "flag_s REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "risk_events",
            "g_behavior",
            "g_behavior REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "risk_events",
            "g_dynamic",
            "g_dynamic REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "risk_events",
            "final_risk",
            "final_risk REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "risk_events",
            "secondary_decision",
            "secondary_decision TEXT",
        )
        _ensure_column(
            connection,
            "risk_events",
            "secondary_risk",
            "secondary_risk REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "risk_events",
            "secondary_reply",
            "secondary_reply TEXT",
        )
        _ensure_column(
            connection,
            "risk_events",
            "policy_version",
            "policy_version TEXT",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "flag_s",
            "flag_s REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "g_behavior",
            "g_behavior REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "g_dynamic",
            "g_dynamic REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "final_risk",
            "final_risk REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_decision",
            "secondary_decision TEXT NOT NULL DEFAULT 'pending'",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_risk",
            "secondary_risk REAL NOT NULL DEFAULT 0.0",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_reasons_json",
            "secondary_reasons_json TEXT",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_question",
            "secondary_question TEXT",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_reply",
            "secondary_reply TEXT",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "secondary_checked_at",
            "secondary_checked_at TEXT",
        )
        _ensure_column(
            connection,
            "pending_transfers",
            "policy_version",
            "policy_version TEXT",
        )
