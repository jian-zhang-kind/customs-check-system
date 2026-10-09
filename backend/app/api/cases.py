"""Case 资源。空票走 insert_case；演示票走 demo_seed，两条链路不互相调用。"""

import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.db.cases import insert_case, list_cases as query_cases, require_case
from app.db.connection import get_db
from app.db.demo_seed import insert_demo_case, seed_demo_records
from app.db.pipeline_store import clear_case_results, load_hypergraph_rows, material_count, set_case_status
from app.db.rows import case_from_row, hypergraph_from_rows
from app.schemas.case import CaseCreate, CaseOut, LoadDemoData, LoadDemoRequest, RunData, RunRequest
from app.schemas.common import ApiResponse, CaseStatus, PageData
from app.schemas.hypergraph import HypergraphOut
from app.services.case_pipeline import execute_case_pipeline

logger = logging.getLogger("app")

router = APIRouter(tags=["cases"])


@router.post("/cases", response_model=ApiResponse[CaseOut], summary="创建空票次")
def create_case(
    body: CaseCreate,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[CaseOut]:
    """插入一行 pending、is_demo=false 的 cases。不上传文件，不跑流水线。"""
    return ApiResponse(data=case_from_row(insert_case(db, body)))


@router.get("/cases", response_model=ApiResponse[PageData[CaseOut]], summary="分页查询票次")
def list_cases(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    is_demo: Annotated[bool | None, Query()] = None,
    status: Annotated[CaseStatus | None, Query()] = None,
) -> ApiResponse[PageData[CaseOut]]:
    rows, total = query_cases(
        db,
        page=page,
        page_size=page_size,
        is_demo=is_demo,
        status=status,
    )
    return ApiResponse(
        data=PageData(
            list=[case_from_row(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/cases/{id}", response_model=ApiResponse[CaseOut], summary="票次基础详情")
def get_case(
    id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[CaseOut]:
    """只返回 cases 一行。单据、照片、报告走子资源。"""
    return ApiResponse(data=case_from_row(require_case(db, id)))


@router.get(
    "/cases/{id}/hypergraph",
    response_model=ApiResponse[HypergraphOut],
    summary="超图只读快照",
)
def get_hypergraph(
    id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[HypergraphOut]:
    """只读。未跑过流水线时节点和超边为空数组。"""
    require_case(db, id)
    nodes, edges, members = load_hypergraph_rows(db, id)
    return ApiResponse(data=hypergraph_from_rows(id, nodes, edges, members))


@router.post(
    "/cases/load-demo",
    response_model=ApiResponse[LoadDemoData],
    summary="一键加载演示票",
)
async def load_demo(
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    body: Annotated[LoadDemoRequest | None, Body()] = None,
) -> ApiResponse[LoadDemoData]:
    """自建演示票并调用 execute_case_pipeline。不调用 POST /cases。"""
    payload = body or LoadDemoRequest()
    case = insert_demo_case(db, payload.demo_type or "battery-vietnam")
    case_id = int(case["id"])
    db.commit()
    try:
        seed_demo_records(db, case_id)
        db.commit()
    except Exception:
        logger.exception("演示种子写入失败 case_id=%s", case_id)
        db.rollback()
        clear_case_results(db, case_id)
        set_case_status(db, case_id, "failed")
        db.commit()
        raise HTTPException(status_code=500, detail="流水线异常") from None
    report = await execute_case_pipeline(db, case_id)
    return ApiResponse(
        data=LoadDemoData(
            case_id=case_id,
            case=case_from_row(require_case(db, case_id)),
            report=report,
        )
    )


@router.post("/cases/{id}/run", response_model=ApiResponse[RunData], summary="触发校验流水线")
async def run_case(
    id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    body: Annotated[RunRequest | None, Body()] = None,
) -> ApiResponse[RunData]:
    """状态校验后调用与 load-demo 相同的 execute_case_pipeline。"""
    case = require_case(db, id)
    force = body.force if body is not None else False
    if case["status"] == "running":
        raise HTTPException(status_code=400, detail="票次正在校验，不能重复触发")
    if case["status"] == "completed" and not force:
        raise HTTPException(status_code=400, detail="已完成的票次需 force=true 才能重跑")
    if material_count(db, id) == 0:
        raise HTTPException(status_code=400, detail="无可校验材料")
    report = await execute_case_pipeline(db, id)
    return ApiResponse(
        data=RunData(
            case_id=id,
            status=CaseStatus.completed,
            report=report,
        )
    )
