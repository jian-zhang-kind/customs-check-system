"""Document 资源。上传只落盘并写入 documents，不触发 run，不写 OCR。"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.errors import DOC_SUFFIXES
from app.config import DOCUMENT_UPLOAD_DIR
from app.db.cases import require_case
from app.db.connection import get_db
from app.db.documents import insert_document, list_documents as query_documents, require_document
from app.db.rows import document_from_row
from app.schemas.common import ApiResponse, DocType, PageData
from app.schemas.document import DocumentOut
from app.storage import remove_stored, save_upload

router = APIRouter(tags=["documents"])


@router.get(
    "/cases/{case_id}/documents",
    response_model=ApiResponse[PageData[DocumentOut]],
    summary="票次单据列表",
)
def list_documents(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    doc_type: Annotated[DocType | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[DocumentOut]]:
    require_case(db, case_id)
    rows, total = query_documents(
        db,
        case_id=case_id,
        doc_type=doc_type,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageData(
            list=[document_from_row(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/documents/{id}", response_model=ApiResponse[DocumentOut], summary="单据详情")
def get_document(
    id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[DocumentOut]:
    return ApiResponse(data=document_from_row(require_document(db, id)))


@router.post(
    "/cases/{case_id}/documents",
    response_model=ApiResponse[DocumentOut],
    summary="上传单据",
)
async def upload_document(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    doc_type: Annotated[DocType, Form()],
    file: Annotated[UploadFile, File()],
) -> ApiResponse[DocumentOut]:
    """pdf / png / jpg。写入文件和 documents 行。ocr_source、ocr_fields 保持为空。"""
    require_case(db, case_id)
    filename, storage_path = await save_upload(file, DOCUMENT_UPLOAD_DIR, DOC_SUFFIXES)
    try:
        row = insert_document(
            db,
            case_id=case_id,
            doc_type=doc_type,
            filename=filename,
            storage_path=storage_path,
        )
    except Exception:
        remove_stored(storage_path)
        raise
    return ApiResponse(data=document_from_row(row))
