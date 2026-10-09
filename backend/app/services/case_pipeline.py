"""已有票次的校验执行。/run 与 load-demo 都走这里，不另写规则。"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import HTTPException

from app.db.pipeline_store import (
    clear_case_results,
    list_source_records,
    risk_rows_for_rules,
    save_hypergraph,
    save_ocr,
    save_report,
    set_case_status,
)
from app.db.rows import report_from_row
from app.db.cases import require_case
from app.modules.pipeline import run_pipeline
from app.modules.types import SourceRecord
from app.schemas.report import ReportSummary

logger = logging.getLogger("app")


async def execute_case_pipeline(conn: sqlite3.Connection, case_id: int) -> ReportSummary:
    """把票次置为 running，调用同一条流水线，成功后返回报告。失败则标为 failed。"""
    case = require_case(conn, case_id)
    documents, photos = list_source_records(conn, case_id)
    records = [
        SourceRecord(target="document", record_id=row["id"], doc_type=row["doc_type"])
        for row in documents
    ] + [
        SourceRecord(target="photo", record_id=row["id"], photo_kind=row["kind"])
        for row in photos
    ]
    set_case_status(conn, case_id, "running")
    conn.commit()
    try:
        extracts, graph, verdicts, summary = await run_pipeline(
            records,
            case["destination_country"],
        )
        clear_case_results(conn, case_id)
        save_ocr(conn, extracts)
        rule_edges = save_hypergraph(conn, case_id, graph)
        report_row = save_report(conn, case_id, summary, verdicts, rule_edges)
        set_case_status(conn, case_id, "completed")
        conn.commit()
    except Exception:
        logger.exception("流水线失败 case_id=%s", case_id)
        conn.rollback()
        clear_case_results(conn, case_id)
        set_case_status(conn, case_id, "failed")
        conn.commit()
        raise HTTPException(status_code=500, detail="流水线异常") from None

    hs_rows = risk_rows_for_rules(conn, case_id, ("R-HS-CN", "R-HS-DEST"))
    return report_from_row(report_row, hs_rows)
