"""把 sqlite3.Row 转成接口模型。不写库。"""

from __future__ import annotations

import json
import sqlite3

from app.schemas.case import CaseOut
from app.schemas.document import DocumentOut, OcrFields
from app.schemas.hypergraph import FieldNodeOut, HyperedgeMemberOut, HyperedgeOut, HypergraphOut
from app.schemas.photo import PhotoOut
from app.schemas.report import DISCLAIMER, HsRuleView, ReportDetail, ReportSummary, RiskItemOut


def case_from_row(row: sqlite3.Row) -> CaseOut:
    return CaseOut(
        id=row["id"],
        case_no=row["case_no"],
        remark=row["remark"],
        status=row["status"],
        is_demo=bool(row["is_demo"]),
        demo_type=row["demo_type"],
        destination_country=row["destination_country"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_ocr_fields(raw: str | None) -> OcrFields | None:
    if raw is None or raw == "":
        return None
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return None
    return OcrFields.model_validate(payload)


def document_from_row(row: sqlite3.Row) -> DocumentOut:
    return DocumentOut(
        id=row["id"],
        case_id=row["case_id"],
        doc_type=row["doc_type"],
        filename=row["filename"],
        storage_path=row["storage_path"],
        ocr_source=row["ocr_source"],
        ocr_fields=parse_ocr_fields(row["ocr_fields"]),
        created_at=row["created_at"],
    )


def _evidence(raw: str | None) -> dict | None:
    if raw is None or raw == "":
        return None
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return None
    return payload


def risk_from_row(row: sqlite3.Row) -> RiskItemOut:
    return RiskItemOut(
        id=row["id"],
        case_id=row["case_id"],
        report_id=row["report_id"],
        rule_id=row["rule_id"],
        verdict=row["verdict"],
        rule_outcome=row["rule_outcome"],
        risk_level=row["risk_level"],
        description=row["description"],
        evidence=_evidence(row["evidence"]),
        edge_id=row["edge_id"],
        chunk_id=row["chunk_id"],
        jurisdiction=row["jurisdiction"],
        regulation_name=row["regulation_name"],
        publish_date=row["publish_date"],
        source_url=row["source_url"],
        excerpt=row["excerpt"],
    )


def hs_from_row(row: sqlite3.Row) -> HsRuleView:
    return HsRuleView(
        rule_id=row["rule_id"],
        verdict=row["verdict"],
        rule_outcome=row["rule_outcome"],
        description=row["description"],
        risk_level=row["risk_level"],
        regulation_name=row["regulation_name"],
        publish_date=row["publish_date"],
        source_url=row["source_url"],
        excerpt=row["excerpt"],
        chunk_id=row["chunk_id"],
        jurisdiction=row["jurisdiction"],
        edge_id=row["edge_id"],
    )


def report_from_row(row: sqlite3.Row, hs_rows: list[sqlite3.Row]) -> ReportSummary:
    by_rule = {item["rule_id"]: item for item in hs_rows}
    return ReportSummary(
        id=row["id"],
        case_id=row["case_id"],
        status=row["status"],
        summary_verdict=row["summary_verdict"],
        debate_triggered=bool(row["debate_triggered"]),
        created_at=row["created_at"],
        hs_cn=hs_from_row(by_rule["R-HS-CN"]) if "R-HS-CN" in by_rule else None,
        hs_dest=hs_from_row(by_rule["R-HS-DEST"]) if "R-HS-DEST" in by_rule else None,
    )


def report_detail_from_row(row: sqlite3.Row, hs_rows: list[sqlite3.Row]) -> ReportDetail:
    summary = report_from_row(row, hs_rows)
    return ReportDetail(
        **summary.model_dump(),
        disclaimer=DISCLAIMER,
    )


def hypergraph_from_rows(
    case_id: int,
    nodes: list[sqlite3.Row],
    edges: list[sqlite3.Row],
    members: list[sqlite3.Row],
) -> HypergraphOut:
    grouped: dict[int, list[HyperedgeMemberOut]] = {}
    for member in members:
        grouped.setdefault(member["edge_id"], []).append(
            HyperedgeMemberOut(
                edge_id=member["edge_id"],
                node_id=member["node_id"],
                slot_name=member["slot_name"],
            )
        )
    return HypergraphOut(
        case_id=case_id,
        nodes=[
            FieldNodeOut(
                node_id=node["id"],
                case_id=node["case_id"],
                document_id=node["document_id"],
                field_name=node["field_name"],
                field_value=node["field_value"],
            )
            for node in nodes
        ],
        edges=[
            HyperedgeOut(
                edge_id=edge["id"],
                case_id=edge["case_id"],
                constraint_type=edge["constraint_type"],
                rule_id=edge["rule_id"],
                members=grouped.get(edge["id"], []),
            )
            for edge in edges
        ],
    )


def photo_from_row(row: sqlite3.Row) -> PhotoOut:
    return PhotoOut(
        id=row["id"],
        case_id=row["case_id"],
        kind=row["kind"],
        filename=row["filename"],
        storage_path=row["storage_path"],
        ocr_source=row["ocr_source"],
        ocr_fields=parse_ocr_fields(row["ocr_fields"]),
        created_at=row["created_at"],
    )
