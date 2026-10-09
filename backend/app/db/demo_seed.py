"""演示票种子。只插入 cases / documents / photos，不调用业务建票，不写 verdict。"""

from __future__ import annotations

import sqlite3

from app.db.cases import require_case
from app.db.clock import utc_now

DEMO_TITLE = "锂电池出口越南（演示）"
DEMO_REMARK = "演示种子，非真实报关单"
DEMO_DESTINATION = "VN"
FIXTURE_STORAGE_PATH = "data/fixtures/ocr_simulation.json"

_DOCUMENTS = (
    ("declaration", "declaration.jpg"),
    ("invoice", "invoice.jpg"),
    ("packing", "packing.png"),
    ("contract", "contract.pdf"),
)
_PHOTOS = (
    ("mark", "mark.png"),
    ("packing", "packing-photo.png"),
)


def insert_demo_case(conn: sqlite3.Connection, demo_type: str) -> sqlite3.Row:
    """直接插入 running 的演示票。不经过 insert_case，因此不会变成 pending 业务票。"""
    now = utc_now()
    cursor = conn.execute(
        """
        INSERT INTO cases (
            case_no, title, remark, status, is_demo, demo_type,
            destination_country, created_at, updated_at
        ) VALUES (?, ?, ?, 'running', 1, ?, ?, ?, ?)
        """,
        (
            _next_case_no(conn),
            DEMO_TITLE,
            DEMO_REMARK,
            demo_type,
            DEMO_DESTINATION,
            now,
            now,
        ),
    )
    return require_case(conn, int(cursor.lastrowid))


def seed_demo_records(conn: sqlite3.Connection, case_id: int) -> None:
    """单据和照片只登记路径。字段由现有 fixture OCR 在流水线里填写。"""
    now = utc_now()
    for doc_type, filename in _DOCUMENTS:
        conn.execute(
            """
            INSERT INTO documents (
                case_id, doc_type, filename, storage_path, ocr_source, ocr_fields, created_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, ?)
            """,
            (case_id, doc_type, filename, FIXTURE_STORAGE_PATH, now),
        )
    for kind, filename in _PHOTOS:
        conn.execute(
            """
            INSERT INTO photos (
                case_id, kind, filename, storage_path, ocr_source, ocr_fields, created_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, ?)
            """,
            (case_id, kind, filename, FIXTURE_STORAGE_PATH, now),
        )


def _next_case_no(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT case_no FROM cases WHERE case_no LIKE 'DEMO-BAT-VN-%'"
    ).fetchall()
    numbers = []
    for row in rows:
        suffix = str(row["case_no"]).rsplit("-", 1)[-1]
        if suffix.isdigit():
            numbers.append(int(suffix))
    nxt = (max(numbers) if numbers else 0) + 1
    return f"DEMO-BAT-VN-{nxt:03d}"
