"""Photo 资源。上传只落盘并写入 photos，不触发 run，不写 OCR。"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.errors import PHOTO_SUFFIXES
from app.config import PHOTO_UPLOAD_DIR
from app.db.cases import require_case
from app.db.connection import get_db
from app.db.photos import insert_photo, list_photos as query_photos, require_photo
from app.db.rows import photo_from_row
from app.schemas.common import ApiResponse, PageData, PhotoKind
from app.schemas.photo import PhotoOut
from app.storage import remove_stored, save_upload

router = APIRouter(tags=["photos"])


@router.get(
    "/cases/{case_id}/photos",
    response_model=ApiResponse[PageData[PhotoOut]],
    summary="票次照片列表",
)
def list_photos(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    kind: Annotated[PhotoKind | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[PhotoOut]]:
    require_case(db, case_id)
    rows, total = query_photos(
        db,
        case_id=case_id,
        kind=kind,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageData(
            list=[photo_from_row(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/photos/{id}", response_model=ApiResponse[PhotoOut], summary="照片详情")
def get_photo(
    id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[PhotoOut]:
    return ApiResponse(data=photo_from_row(require_photo(db, id)))


@router.post(
    "/cases/{case_id}/photos",
    response_model=ApiResponse[PhotoOut],
    summary="上传现场照片",
)
async def upload_photo(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    kind: Annotated[PhotoKind, Form()],
    file: Annotated[UploadFile, File()],
) -> ApiResponse[PhotoOut]:
    """png / jpg。写入文件和 photos 行。ocr_source、ocr_fields 保持为空。"""
    require_case(db, case_id)
    filename, storage_path = await save_upload(file, PHOTO_UPLOAD_DIR, PHOTO_SUFFIXES)
    try:
        row = insert_photo(
            db,
            case_id=case_id,
            kind=kind,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        remove_stored(storage_path)
        raise
    return ApiResponse(data=photo_from_row(row))
