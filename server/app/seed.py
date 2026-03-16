from __future__ import annotations

from .db import get_connection


def seed_demo_data() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO users (id, name, home_city, risk_preference, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("user-demo", "谢小璞", "上海", "balanced", "2026-03-01T09:00:00"),
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
                "user-demo",
                12500.00,
                18000.00,
                "CNY",
                "2026-03-16T09:00:00",
            ),
        )
        location_rows = (
            ("user-demo", "上海", 31.2304, 121.4737, 0.98, "2026-03-15T19:00:00", 1),
            ("user-demo", "苏州", 31.2989, 120.5853, 0.72, "2026-03-10T10:00:00", 1),
            ("user-demo", "北京", 39.9042, 116.4074, 0.25, "2026-01-15T12:00:00", 0),
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
            ("payee-zhangsan", "user-demo", "张三", "上海", 5, "2026-03-10T10:30:00"),
            ("payee-water", "user-demo", "水电缴费", "上海", 12, "2026-03-12T08:00:00"),
        )
        for row in payee_rows:
            connection.execute(
                """
                INSERT OR IGNORE INTO payees
                (id, user_id, name, last_city, transfer_count, last_transfer_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )

        transaction_rows = (
            (
                "txn-salary",
                "user-demo",
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
                "user-demo",
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
                "user-demo",
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
                "user-demo",
                "转账给 张三",
                "实时转账",
                520.00,
                0,
                "transfer",
                "上海",
                "张三",
                "2026-03-10T10:30:00",
                "posted",
            ),
            (
                "txn-shopping",
                "user-demo",
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
                INSERT OR IGNORE INTO transactions
                (id, user_id, title, subtitle, amount, is_income, category, city, payee_name, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
