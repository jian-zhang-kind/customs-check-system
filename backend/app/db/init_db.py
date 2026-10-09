"""按 docs/sql/schema.sql 初始化 SQLite。只建表，不灌种子、不写判定。"""

from __future__ import annotations

import sqlite3

from app.config import DB_PATH, SCHEMA_PATH
from app.db.connection import connect

REQUIRED_TABLES = frozenset(
    {
        "cases",
        "documents",
        "photos",
        "field_nodes",
        "hyperedges",
        "hyperedge_members",
        "check_reports",
        "risk_items",
    }
)


def init_db() -> None:
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"缺少建表脚本: {SCHEMA_PATH}")

    conn = connect()
    try:
        existing = _user_tables(conn)
        if not existing:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            return
        missing = REQUIRED_TABLES - existing
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(
                f"数据库不完整，缺少表: {names}。请删除 {DB_PATH} 后重新初始化。"
            )
    finally:
        conn.close()


def _user_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    return {str(row["name"]) for row in rows}


if __name__ == "__main__":
    init_db()
