from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ..db import get_connection


class BankingRepository:
    def __init__(self, user_id: str = "user-demo") -> None:
        self.user_id = user_id

    def _now(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")

    def get_user_profile(self) -> dict:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, name, home_city, risk_preference FROM users WHERE id = ?",
                (self.user_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Demo user not found. Seed data is missing.")
        return dict(row)

    def get_account(self) -> dict:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, cash_balance, wealth_balance, currency, updated_at
                FROM accounts WHERE user_id = ?
                """,
                (self.user_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Demo account not found. Seed data is missing.")
        return dict(row)

    def list_transactions(self, limit: int = 20) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, subtitle, amount, is_income, category, city, created_at, status
                FROM transactions
                WHERE user_id = ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (self.user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_spending_summary(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT category, ROUND(SUM(amount), 2) AS total_amount
                FROM transactions
                WHERE user_id = ? AND is_income = 0
                GROUP BY category
                ORDER BY total_amount DESC
                LIMIT 4
                """,
                (self.user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_common_locations(self) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT city, latitude, longitude, confidence, last_seen_at, is_common
                FROM location_profiles
                WHERE user_id = ?
                ORDER BY is_common DESC, confidence DESC
                """,
                (self.user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def find_payee(self, name: str) -> dict | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, name, last_city, transfer_count, last_transfer_at
                FROM payees WHERE user_id = ? AND name = ?
                """,
                (self.user_id, name),
            ).fetchone()
        return dict(row) if row else None

    def recent_outgoing_transfer_count(self, minutes: int = 20) -> int:
        since = (datetime.now(UTC) - timedelta(minutes=minutes)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM transactions
                WHERE user_id = ?
                  AND is_income = 0
                  AND category = 'transfer'
                  AND datetime(created_at) >= datetime(?)
                """,
                (self.user_id, since),
            ).fetchone()
        return int(row["total"]) if row else 0

    def create_pending_transfer(
        self,
        *,
        payee_name: str,
        amount: float,
        city: str,
        device_id: str,
        recent_page: str,
        last_action: str,
        semantic_summary: str,
        risk_level: str,
        decision: str,
        reasons: list[str],
        assistant_message: str,
    ) -> str:
        pending_id = f"confirm-{uuid4().hex}"
        created_at = self._now()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO pending_transfers
                (id, user_id, payee_name, amount, city, device_id, recent_page, last_action,
                 semantic_summary, risk_level, decision, reasons_json, assistant_message, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    pending_id,
                    self.user_id,
                    payee_name,
                    amount,
                    city,
                    device_id,
                    recent_page,
                    last_action,
                    semantic_summary,
                    risk_level,
                    decision,
                    json.dumps(reasons, ensure_ascii=False),
                    assistant_message,
                    created_at,
                ),
            )
        return pending_id

    def get_pending_transfer(self, confirmation_token: str) -> dict:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM pending_transfers
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (confirmation_token, self.user_id),
            ).fetchone()
        if row is None:
            raise ValueError("Pending transfer not found or already completed.")
        payload = dict(row)
        payload["reasons"] = json.loads(payload.pop("reasons_json"))
        return payload

    def create_risk_event(
        self,
        *,
        payee_name: str,
        amount: float,
        city: str,
        device_id: str,
        risk_level: str,
        decision: str,
        reasons: list[str],
    ) -> str:
        risk_event_id = f"risk-{uuid4().hex}"
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO risk_events
                (id, user_id, payee_name, amount, city, device_id, risk_level, decision, reasons_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    risk_event_id,
                    self.user_id,
                    payee_name,
                    amount,
                    city,
                    device_id,
                    risk_level,
                    decision,
                    json.dumps(reasons, ensure_ascii=False),
                    self._now(),
                ),
            )
        return risk_event_id

    def get_latest_risk_event(self) -> dict | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT payee_name, amount, city, risk_level, decision, reasons_json, created_at
                FROM risk_events
                WHERE user_id = ?
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (self.user_id,),
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["reasons"] = json.loads(payload.pop("reasons_json"))
        return payload

    def commit_transfer(self, confirmation_token: str) -> dict:
        pending = self.get_pending_transfer(confirmation_token)
        account = self.get_account()
        if pending["amount"] > account["cash_balance"]:
            raise ValueError("Insufficient balance for demo transfer.")

        created_at = self._now()
        transaction_id = f"txn-{uuid4().hex}"
        payee_id = pending["payee_name"].encode("utf-8").hex()[:20]

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE accounts
                SET cash_balance = cash_balance - ?, updated_at = ?
                WHERE user_id = ?
                """,
                (pending["amount"], created_at, self.user_id),
            )
            connection.execute(
                """
                INSERT INTO transactions
                (id, user_id, title, subtitle, amount, is_income, category, city, payee_name, created_at, status)
                VALUES (?, ?, ?, ?, ?, 0, 'transfer', ?, ?, ?, 'posted')
                """,
                (
                    transaction_id,
                    self.user_id,
                    f"转账给 {pending['payee_name']}",
                    "AI Agent 风控确认后执行",
                    pending["amount"],
                    pending["city"],
                    pending["payee_name"],
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO payees (id, user_id, name, last_city, transfer_count, last_transfer_at)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_city = excluded.last_city,
                    transfer_count = payees.transfer_count + 1,
                    last_transfer_at = excluded.last_transfer_at
                """,
                (
                    f"payee-{payee_id}",
                    self.user_id,
                    pending["payee_name"],
                    pending["city"],
                    created_at,
                ),
            )
            connection.execute(
                """
                UPDATE pending_transfers
                SET status = 'committed'
                WHERE id = ?
                """,
                (confirmation_token,),
            )

        latest_transaction = self.list_transactions(limit=1)[0]
        latest_account = self.get_account()
        return {
            "transaction": latest_transaction,
            "account": latest_account,
        }

    def add_chat_message(self, session_id: str, role: str, content: str) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO chat_sessions (id, user_id, session_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"chat-{uuid4().hex}",
                    self.user_id,
                    session_id,
                    role,
                    content,
                    self._now(),
                ),
            )
