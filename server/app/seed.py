from __future__ import annotations

from .db import get_connection
from .services.risk_knowledge_base import get_risk_knowledge_base_service


def seed_demo_data() -> None:
    with get_connection() as connection:
        # Backward-compatible migration: keep demo data usable even if local DB still has legacy IDs.
        connection.execute("UPDATE accounts SET user_id = '小a' WHERE user_id = 'user-demo'")
        connection.execute("UPDATE transactions SET user_id = '小a' WHERE user_id = 'user-demo'")
        connection.execute("UPDATE payees SET user_id = '小a' WHERE user_id = 'user-demo'")
        connection.execute(
            "UPDATE location_profiles SET user_id = '小a' WHERE user_id = 'user-demo'"
        )
        connection.execute("UPDATE risk_events SET user_id = '小a' WHERE user_id = 'user-demo'")
        connection.execute(
            "UPDATE pending_transfers SET user_id = '小a' WHERE user_id = 'user-demo'"
        )
        connection.execute(
            "UPDATE manual_review_cases SET user_id = '小a' WHERE user_id = 'user-demo'"
        )
        connection.execute("UPDATE chat_sessions SET user_id = '小a' WHERE user_id = 'user-demo'")
        connection.execute("DELETE FROM users WHERE id = 'user-demo'")
        connection.execute("DELETE FROM manual_review_cases WHERE user_id = '小a'")
        connection.execute("DELETE FROM payees WHERE id = 'payee-zhangsan'")
        connection.execute("DELETE FROM location_profiles WHERE user_id = '小a'")
        connection.execute(
            """
            DELETE FROM transactions
            WHERE user_id = '小a'
              AND id NOT IN ('txn-salary', 'txn-food', 'txn-commute', 'txn-transfer-friend', 'txn-shopping')
            """
        )
        connection.execute(
            """
            DELETE FROM payees
            WHERE user_id = '小a'
              AND id NOT IN ('小b', 'payee-water')
            """
        )

        connection.execute(
            """
            INSERT INTO users (id, name, home_city, risk_preference, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                home_city = excluded.home_city,
                risk_preference = excluded.risk_preference,
                created_at = excluded.created_at
            """,
            ("小a", "小a", "上海", "balanced", "2026-03-01T09:00:00"),
        )
        connection.execute(
            """
            INSERT INTO accounts (id, user_id, cash_balance, wealth_balance, currency, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = excluded.user_id,
                cash_balance = excluded.cash_balance,
                wealth_balance = excluded.wealth_balance,
                currency = excluded.currency,
                updated_at = excluded.updated_at
            """,
            (
                "acct-demo",
                "小a",
                12500.00,
                18000.00,
                "CNY",
                "2026-03-16T09:00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_profiles
            (user_id, flag_s, scenario, relation_level_b, common_device, blacklist_hit, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                flag_s = excluded.flag_s,
                scenario = excluded.scenario,
                relation_level_b = excluded.relation_level_b,
                common_device = excluded.common_device,
                blacklist_hit = excluded.blacklist_hit,
                updated_at = excluded.updated_at
            """,
            ("小a", 0.18, "normal_activity", 0.86, 1, 0, "2026-03-18T09:00:00"),
        )
        location_rows = (
            ("小a", "上海", 31.2304, 121.4737, 0.98, "2026-03-15T19:00:00", 1),
            ("小a", "苏州", 31.2989, 120.5853, 0.72, "2026-03-10T10:00:00", 1),
            ("小a", "北京", 39.9042, 116.4074, 0.25, "2026-01-15T12:00:00", 0),
        )
        for row in location_rows:
            connection.execute(
                """
                INSERT OR IGNORE INTO location_profiles
                (user_id, city, latitude, longitude, confidence, last_seen_at, is_common)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )

        payee_rows = (
            ("小b", "小a", "小b", "上海", 5, "2026-03-10T10:30:00"),
            ("payee-water", "小a", "水电缴费", "上海", 12, "2026-03-12T08:00:00"),
        )
        for row in payee_rows:
            connection.execute(
                """
                INSERT INTO payees
                (id, user_id, name, last_city, transfer_count, last_transfer_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id = excluded.user_id,
                    name = excluded.name,
                    last_city = excluded.last_city,
                    transfer_count = excluded.transfer_count,
                    last_transfer_at = excluded.last_transfer_at
                """,
                row,
            )

        transaction_rows = (
            (
                "txn-salary",
                "小a",
                "工资入账",
                "公司薪酬",
                12000.00,
                1,
                "income",
                "上海",
                None,
                "2026-03-14T09:00:00",
                "posted",
            ),
            (
                "txn-food",
                "小a",
                "餐饮消费",
                "上海静安",
                86.00,
                0,
                "food",
                "上海",
                "南京西路餐厅",
                "2026-03-15T19:20:00",
                "posted",
            ),
            (
                "txn-commute",
                "小a",
                "地铁出行",
                "上海地铁",
                4.00,
                0,
                "transport",
                "上海",
                "上海地铁",
                "2026-03-15T08:15:00",
                "posted",
            ),
            (
                "txn-transfer-friend",
                "小a",
                "转账给 小b",
                "实时转账",
                520.00,
                0,
                "transfer",
                "上海",
                "小b",
                "2026-03-10T10:30:00",
                "posted",
            ),
            (
                "txn-shopping",
                "小a",
                "线上购物",
                "电商平台",
                328.00,
                0,
                "shopping",
                "上海",
                "电商平台",
                "2026-03-09T20:00:00",
                "posted",
            ),
        )
        for row in transaction_rows:
            connection.execute(
                """
                INSERT INTO transactions
                (id, user_id, title, subtitle, amount, is_income, category, city, payee_name, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id = excluded.user_id,
                    title = excluded.title,
                    subtitle = excluded.subtitle,
                    amount = excluded.amount,
                    is_income = excluded.is_income,
                    category = excluded.category,
                    city = excluded.city,
                    payee_name = excluded.payee_name,
                    created_at = excluded.created_at,
                    status = excluded.status
                """,
                row,
            )

    get_risk_knowledge_base_service().ensure_seeded()
