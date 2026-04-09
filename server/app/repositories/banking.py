from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ..db import get_connection
from ..schemas.report import RiskReportPayload


class BankingRepository:
    def __init__(self, user_id: str = "小a") -> None:
        self.user_id = user_id

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    def build_confirmation_token(self) -> str:
        return f"confirm-{uuid4().hex}"

    def get_user_profile(self) -> dict:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, name, home_city, risk_preference FROM users WHERE id = ?",
                (self.user_id,),
            ).fetchone()
        if row is None:
            raise ValueError("未找到演示用户，请先初始化种子数据。")
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
            raise ValueError("未找到演示账户，请先初始化种子数据。")
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
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime(
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
        flag_s: float,
        g_behavior: float,
        g_dynamic: float,
        final_risk: float,
        reasons: list[str],
        assistant_message: str,
        confirmation_token: str | None = None,
    ) -> str:
        pending_id = confirmation_token or self.build_confirmation_token()
        created_at = self._now()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO pending_transfers
                (id, user_id, payee_name, amount, city, device_id, recent_page, last_action,
                 semantic_summary, risk_level, decision, flag_s, g_behavior, g_dynamic, final_risk,
                 reasons_json, assistant_message, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
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
                    flag_s,
                    g_behavior,
                    g_dynamic,
                    final_risk,
                    json.dumps(reasons, ensure_ascii=False),
                    assistant_message,
                    created_at,
                ),
            )
        return pending_id

    def get_transfer_record(self, confirmation_token: str) -> dict | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM pending_transfers
                WHERE id = ? AND user_id = ?
                """,
                (confirmation_token, self.user_id),
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["reasons"] = json.loads(payload.pop("reasons_json"))
        secondary_reasons = payload.pop("secondary_reasons_json", None)
        payload["secondary_reasons"] = (
            json.loads(secondary_reasons) if secondary_reasons else []
        )
        return payload

    def get_pending_transfer(self, confirmation_token: str) -> dict:
        payload = self.get_transfer_record(confirmation_token)
        if payload is None or payload["status"] != "pending":
            raise ValueError("未找到待确认转账，或该转账已处理完成。")
        return payload

    def get_transfer_status(self, confirmation_token: str) -> str | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT status
                FROM pending_transfers
                WHERE id = ? AND user_id = ?
                """,
                (confirmation_token, self.user_id),
            ).fetchone()
        if row is None:
            return None
        return str(row["status"])

    def create_risk_event(
        self,
        *,
        payee_name: str,
        amount: float,
        city: str,
        device_id: str,
        risk_level: str,
        decision: str,
        flag_s: float,
        g_behavior: float,
        g_dynamic: float,
        final_risk: float,
        reasons: list[str],
        secondary_decision: str | None = None,
        secondary_risk: float = 0.0,
        secondary_reply: str | None = None,
        policy_version: str | None = None,
    ) -> str:
        risk_event_id = f"risk-{uuid4().hex}"
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO risk_events
                (id, user_id, payee_name, amount, city, device_id, risk_level, decision,
                 flag_s, g_behavior, g_dynamic, final_risk, secondary_decision, secondary_risk,
                 secondary_reply, policy_version, reasons_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    flag_s,
                    g_behavior,
                    g_dynamic,
                    final_risk,
                    secondary_decision,
                    secondary_risk,
                    secondary_reply,
                    policy_version,
                    json.dumps(reasons, ensure_ascii=False),
                    self._now(),
                ),
            )
        return risk_event_id

    def create_trace_event(
        self,
        *,
        trace_id: str,
        confirmation_token: str,
        event_type: str,
        stage: str,
        decision: str | None,
        risk_level: str | None,
        final_risk: float,
        payload: dict,
    ) -> str:
        trace_event_id = f"trace-{uuid4().hex}"
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO trace_events
                (id, trace_id, confirmation_token, user_id, event_type, stage, decision,
                 risk_level, final_risk, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_event_id,
                    trace_id,
                    confirmation_token,
                    self.user_id,
                    event_type,
                    stage,
                    decision,
                    risk_level,
                    final_risk,
                    json.dumps(payload, ensure_ascii=False),
                    self._now(),
                ),
            )
        return trace_event_id

    def get_transfer_trace(self, confirmation_token: str) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT trace_id, confirmation_token, event_type, stage, decision,
                       risk_level, final_risk, payload_json, created_at
                FROM trace_events
                WHERE confirmation_token = ? AND user_id = ?
                ORDER BY rowid ASC
                """,
                (confirmation_token, self.user_id),
            ).fetchall()
        result: list[dict] = []
        for row in rows:
            payload = dict(row)
            payload["payload"] = json.loads(payload.pop("payload_json"))
            result.append(payload)
        return result

    def list_transfer_traces(self, limit: int = 20) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                WITH ranked AS (
                    SELECT trace_id, confirmation_token, event_type, stage, decision,
                           risk_level, final_risk, payload_json, created_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY confirmation_token
                               ORDER BY rowid DESC
                           ) AS rn
                    FROM trace_events
                    WHERE user_id = ?
                )
                SELECT trace_id, confirmation_token, event_type, stage, decision,
                       risk_level, final_risk, payload_json, created_at
                FROM ranked
                WHERE rn = 1
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self.user_id, limit),
            ).fetchall()
        result: list[dict] = []
        for row in rows:
            payload = dict(row)
            payload["payload"] = json.loads(payload.pop("payload_json"))
            result.append(payload)
        return result

    def update_secondary_check(
        self,
        *,
        confirmation_token: str,
        secondary_decision: str,
        secondary_risk: float,
        secondary_reasons: list[str],
        secondary_question: str,
        secondary_reply: str,
        policy_version: str,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE pending_transfers
                SET secondary_decision = ?,
                    secondary_risk = ?,
                    secondary_reasons_json = ?,
                    secondary_question = ?,
                    secondary_reply = ?,
                    secondary_checked_at = ?,
                    policy_version = ?
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (
                    secondary_decision,
                    secondary_risk,
                    json.dumps(secondary_reasons, ensure_ascii=False),
                    secondary_question,
                    secondary_reply,
                    self._now(),
                    policy_version,
                    confirmation_token,
                    self.user_id,
                ),
            )

    def get_latest_risk_event(self) -> dict | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT payee_name, amount, city, risk_level, decision,
                       flag_s, g_behavior, g_dynamic, final_risk,
                       reasons_json, created_at
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
        if pending["decision"] == "block":
            raise ValueError("该转账已被风控拦截，无法继续确认。")
        if (
            pending["decision"] == "interrogate"
            and pending.get("secondary_decision") != "pass_secondary"
        ):
            raise ValueError("该转账尚未通过二次校验，无法继续确认。")

        account = self.get_account()
        if pending["amount"] > account["cash_balance"]:
            raise ValueError("余额不足，无法完成本次转账。")

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
                    "经智能体风控确认后执行",
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

    def cancel_pending_transfer(self, confirmation_token: str) -> dict:
        pending = self.get_pending_transfer(confirmation_token)
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE pending_transfers
                SET status = 'cancelled'
                WHERE id = ? AND user_id = ? AND status = 'pending'
                """,
                (confirmation_token, self.user_id),
            )
        return {
            "confirmation_token": confirmation_token,
            "status": "cancelled",
            "payee_name": pending["payee_name"],
            "amount": float(pending["amount"]),
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

    def upsert_risk_report(
        self,
        *,
        report: RiskReportPayload,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO risk_reports
                (confirmation_token, user_id, headline, overall_risk_level, risk_summary,
                 risk_factors_json, recommended_action, evidence_json, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(confirmation_token) DO UPDATE SET
                    headline = excluded.headline,
                    overall_risk_level = excluded.overall_risk_level,
                    risk_summary = excluded.risk_summary,
                    risk_factors_json = excluded.risk_factors_json,
                    recommended_action = excluded.recommended_action,
                    evidence_json = excluded.evidence_json,
                    generated_at = excluded.generated_at
                """,
                (
                    report.confirmation_token,
                    self.user_id,
                    report.headline,
                    report.overall_risk_level,
                    report.risk_summary,
                    json.dumps(report.risk_factors, ensure_ascii=False),
                    report.recommended_action,
                    json.dumps(report.evidence, ensure_ascii=False),
                    report.generated_at,
                ),
            )

    def get_risk_report(self, confirmation_token: str) -> dict | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT confirmation_token, headline, overall_risk_level, risk_summary,
                       risk_factors_json, recommended_action, evidence_json, generated_at
                FROM risk_reports
                WHERE confirmation_token = ? AND user_id = ?
                """,
                (confirmation_token, self.user_id),
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["risk_factors"] = json.loads(payload.pop("risk_factors_json"))
        payload["evidence"] = json.loads(payload.pop("evidence_json"))
        return payload

