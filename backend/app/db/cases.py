"""票次读写。只插入空票和查询，不改状态、不写判定。"""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.db.clock import utc_now
from app.schemas.case import CaseCreate
from app.schemas.common import CaseStatus

_CASE_COLUMNS = (
    "id, case_no, title, remark, status, is_demo, demo_type, "
    "destination_country, created_at, updated_at"
)


def require_case(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row:
    row = conn.execute(
        f"SELECT {_CASE_COLUMNS} FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="票次不存在")
    return row


def insert_case(conn: sqlite3.Connection, body: CaseCreate) -> sqlite3.Row:
    now = utc_now()
    title = (body.title or "").strip() or body.case_no
    remark = (body.remark or "").strip() or None
    destination = (body.destination_country or "").strip() or None
    try:
        cursor = conn.execute(
            """
            INSERT INTO cases (
                case_no, title, remark, status, is_demo, demo_type,
                destination_country, created_at, updated_at
            ) VALUES (?, ?, ?, 'pending', 0, NULL, ?, ?, ?)
            """,
            (body.case_no, title, remark, destination, now, now),
        )
    except sqlite3.IntegrityError as exc:
        if "case_no" in str(exc):
            raise HTTPException(status_code=400, detail="case_no 重复") from exc
        raise
    return require_case(conn, int(cursor.lastrowid))


def list_cases(
    conn: sqlite3.Connection,
    *,
    page: int,
    page_size: int,
    is_demo: bool | None,
    status: CaseStatus | None,
) -> tuple[list[sqlite3.Row], int]:
    clauses: list[str] = []
    params: list[object] = []
    if is_demo is not None:
        clauses.append("is_demo = ?")
        params.append(1 if is_demo else 0)
    if status is not None:
        clauses.append("status = ?")
        params.append(status.value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = int(
        conn.execute(f"SELECT COUNT(*) AS n FROM cases {where}", params).fetchone()["n"]
    )
    rows = conn.execute(
        f"""
        SELECT {_CASE_COLUMNS}
        FROM cases
        {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return list(rows), total
