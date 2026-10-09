"""单据读写。只保存上传记录，不写 OCR 结果，不改票次状态。"""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.db.clock import utc_now
from app.schemas.common import DocType

_DOCUMENT_COLUMNS = (
    "id, case_id, doc_type, filename, storage_path, ocr_source, ocr_fields, created_at"
)


def insert_document(
    conn: sqlite3.Connection,
    *,
    case_id: int,
    doc_type: DocType,
    filename: str,
    storage_path: str,
) -> sqlite3.Row:
    cursor = conn.execute(
        """
        INSERT INTO documents (
            case_id, doc_type, filename, storage_path, ocr_source, ocr_fields, created_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, ?)
        """,
        (case_id, doc_type.value, filename, storage_path, utc_now()),
    )
    return require_document(conn, int(cursor.lastrowid))


def require_document(conn: sqlite3.Connection, document_id: int) -> sqlite3.Row:
    row = conn.execute(
        f"SELECT {_DOCUMENT_COLUMNS} FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="单据不存在")
    return row


def list_documents(
    conn: sqlite3.Connection,
    *,
    case_id: int,
    doc_type: DocType | None,
    page: int,
    page_size: int,
) -> tuple[list[sqlite3.Row], int]:
    clauses = ["case_id = ?"]
    params: list[object] = [case_id]
    if doc_type is not None:
        clauses.append("doc_type = ?")
        params.append(doc_type.value)
    where = " AND ".join(clauses)
    total = int(
        conn.execute(
            f"SELECT COUNT(*) AS n FROM documents WHERE {where}",
            params,
        ).fetchone()["n"]
    )
    rows = conn.execute(
        f"""
        SELECT {_DOCUMENT_COLUMNS}
        FROM documents
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return list(rows), total
