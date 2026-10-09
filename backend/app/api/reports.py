"""Report / RiskItem 只读。结论来自已落库的规则结果，没有修改 verdict 的接口。"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.cases import require_case
from app.db.connection import get_db
from app.db.pipeline_store import get_report_row, list_risk_rows, risk_rows_for_rules
from app.db.rows import report_detail_from_row, risk_from_row
from app.schemas.common import ApiResponse, PageData, RuleId, Verdict
from app.schemas.report import ReportDetail, RiskItemOut

router = APIRouter(tags=["reports"])


@router.get(
    "/cases/{case_id}/report",
    response_model=ApiResponse[ReportDetail],
    summary="校验报告总览",
)
def get_report(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> ApiResponse[ReportDetail]:
    require_case(db, case_id)
    row = get_report_row(db, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="尚未生成报告")
    hs_rows = risk_rows_for_rules(db, case_id, ("R-HS-CN", "R-HS-DEST"))
    return ApiResponse(data=report_detail_from_row(row, hs_rows))


@router.get(
    "/cases/{case_id}/risk-items",
    response_model=ApiResponse[PageData[RiskItemOut]],
    summary="风险项明细",
)
def list_risk_items(
    case_id: int,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
    rule_id: Annotated[RuleId | None, Query()] = None,
    verdict: Annotated[Verdict | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PageData[RiskItemOut]]:
    require_case(db, case_id)
    rows, total = list_risk_rows(
        db,
        case_id,
        rule_id=rule_id.value if rule_id is not None else None,
        verdict=verdict.value if verdict is not None else None,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageData(
            list=[risk_from_row(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )
