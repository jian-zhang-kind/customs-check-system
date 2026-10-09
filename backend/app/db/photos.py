"""现场照片读写。只保存上传记录，不写 OCR 结果，不改票次状态。"""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.db.clock import utc_now
from app.schemas.common import PhotoKind

_PHOTO_COLUMNS = (
    "id, case_id, kind, filename, storage_path, ocr_source, ocr_fields, created_at"
)


def insert_photo(
    conn: sqlite3.Connection,
    *,
    case_id: int,
    kind: PhotoKind,
    filename: str,
    storage_path: str,
) -> sqlite3.Row:
    cursor = conn.execute(
        """
        INSERT INTO photos (
            case_id, kind, filename, storage_path, ocr_source, ocr_fields, created_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, ?)
        """,
        (case_id, kind.value, filename, storage_path, utc_now()),
    )
    return require_photo(conn, int(cursor.lastrowid))


def require_photo(conn: sqlite3.Connection, photo_id: int) -> sqlite3.Row:
    row = conn.execute(
        f"SELECT {_PHOTO_COLUMNS} FROM photos WHERE id = ?",
        (photo_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="照片不存在")
    return row


def list_photos(
    conn: sqlite3.Connection,
    *,
    case_id: int,
    kind: PhotoKind | None,
    page: int,
    page_size: int,
) -> tuple[list[sqlite3.Row], int]:
    clauses = ["case_id = ?"]
    params: list[object] = [case_id]
    if kind is not None:
        clauses.append("kind = ?")
        params.append(kind.value)
    where = " AND ".join(clauses)
    total = int(
        conn.execute(
            f"SELECT COUNT(*) AS n FROM photos WHERE {where}",
            params,
        ).fetchone()["n"]
    )
    rows = conn.execute(
        f"""
        SELECT {_PHOTO_COLUMNS}
        FROM photos
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return list(rows), total
