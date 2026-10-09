"""把流水线结果写入既有表。不新增字段。"""

from __future__ import annotations

import json
import sqlite3

from app.db.clock import utc_now
from app.modules.types import HypergraphInstance, OcrExtract, RuleVerdict

_REPORT_COLUMNS = (
    "id, case_id, status, summary_verdict, debate_triggered, created_at"
)
_RISK_COLUMNS = (
    "id, case_id, report_id, rule_id, verdict, rule_outcome, risk_level, description, "
    "evidence, edge_id, chunk_id, jurisdiction, regulation_name, publish_date, source_url, excerpt"
)


def list_source_records(conn: sqlite3.Connection, case_id: int) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    documents = conn.execute(
        "SELECT id, doc_type, filename FROM documents WHERE case_id = ? ORDER BY id",
        (case_id,),
    ).fetchall()
    photos = conn.execute(
        "SELECT id, kind, filename FROM photos WHERE case_id = ? ORDER BY id",
        (case_id,),
    ).fetchall()
    return list(documents), list(photos)


def material_count(conn: sqlite3.Connection, case_id: int) -> int:
    documents, photos = list_source_records(conn, case_id)
    return len(documents) + len(photos)


def set_case_status(conn: sqlite3.Connection, case_id: int, status: str) -> None:
    conn.execute(
        "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?",
        (status, utc_now(), case_id),
    )


def clear_case_results(conn: sqlite3.Connection, case_id: int) -> None:
    conn.execute("DELETE FROM risk_items WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM hyperedge_members WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM hyperedges WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM field_nodes WHERE case_id = ?", (case_id,))
    conn.execute("DELETE FROM check_reports WHERE case_id = ?", (case_id,))


def save_ocr(conn: sqlite3.Connection, extracts: list[OcrExtract]) -> None:
    for extract in extracts:
        payload = json.dumps(extract.fields, ensure_ascii=False) if extract.fields else None
        table = "documents" if extract.source.target == "document" else "photos"
        conn.execute(
            f"UPDATE {table} SET ocr_source = ?, ocr_fields = ? WHERE id = ?",
            (extract.ocr_source, payload, extract.source.record_id),
        )


def save_hypergraph(conn: sqlite3.Connection, case_id: int, graph: HypergraphInstance) -> dict[str, int]:
    node_ids: dict[str, int] = {}
    for node in graph.nodes:
        cursor = conn.execute(
            """
            INSERT INTO field_nodes (case_id, document_id, field_name, field_value)
            VALUES (?, ?, ?, ?)
            """,
            (case_id, node.document_id, node.field_name, node.field_value),
        )
        node_ids[node.node_key] = int(cursor.lastrowid)
    rule_edges: dict[str, int] = {}
    for edge in graph.edges:
        cursor = conn.execute(
            """
            INSERT INTO hyperedges (case_id, constraint_type, rule_id)
            VALUES (?, ?, ?)
            """,
            (case_id, edge.constraint_type, edge.rule_id),
        )
        edge_id = int(cursor.lastrowid)
        rule_edges[edge.rule_id] = edge_id
        for member in edge.members:
            conn.execute(
                """
                INSERT INTO hyperedge_members (case_id, edge_id, node_id, slot_name)
                VALUES (?, ?, ?, ?)
                """,
                (case_id, edge_id, node_ids[member.node_key], member.slot_name),
            )
    return rule_edges


def save_report(
    conn: sqlite3.Connection,
    case_id: int,
    summary: str,
    verdicts: list[RuleVerdict],
    rule_edges: dict[str, int],
) -> sqlite3.Row:
    cursor = conn.execute(
        """
        INSERT INTO check_reports (case_id, status, summary_verdict, debate_triggered, created_at)
        VALUES (?, 'completed', ?, 0, ?)
        """,
        (case_id, summary, utc_now()),
    )
    report_id = int(cursor.lastrowid)
    for item in verdicts:
        conn.execute(
            f"""
            INSERT INTO risk_items (
                case_id, report_id, rule_id, verdict, rule_outcome, risk_level, description,
                evidence, edge_id, chunk_id, jurisdiction, regulation_name, publish_date,
                source_url, excerpt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                report_id,
                item.rule_id,
                item.verdict,
                item.rule_outcome,
                item.risk_level,
                item.description,
                json.dumps(item.evidence, ensure_ascii=False),
                rule_edges.get(item.rule_id),
                item.chunk_id,
                item.jurisdiction,
                item.regulation_name,
                item.publish_date,
                item.source_url,
                item.excerpt,
            ),
        )
    row = conn.execute(
        f"SELECT {_REPORT_COLUMNS} FROM check_reports WHERE id = ?",
        (report_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("报告未写入")
    return row


def get_report_row(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {_REPORT_COLUMNS} FROM check_reports WHERE case_id = ?",
        (case_id,),
    ).fetchone()


def list_risk_rows(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    rule_id: str | None,
    verdict: str | None,
    page: int,
    page_size: int,
) -> tuple[list[sqlite3.Row], int]:
    clauses = ["case_id = ?"]
    params: list[object] = [case_id]
    if rule_id is not None:
        clauses.append("rule_id = ?")
        params.append(rule_id)
    if verdict is not None:
        clauses.append("verdict = ?")
        params.append(verdict)
    where = " AND ".join(clauses)
    total = int(
        conn.execute(f"SELECT COUNT(*) AS n FROM risk_items WHERE {where}", params).fetchone()["n"]
    )
    rows = conn.execute(
        f"""
        SELECT {_RISK_COLUMNS}
        FROM risk_items
        WHERE {where}
        ORDER BY id
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return list(rows), total


def risk_rows_for_rules(conn: sqlite3.Connection, case_id: int, rule_ids: tuple[str, ...]) -> list[sqlite3.Row]:
    marks = ",".join("?" for _ in rule_ids)
    return list(
        conn.execute(
            f"""
            SELECT {_RISK_COLUMNS}
            FROM risk_items
            WHERE case_id = ? AND rule_id IN ({marks})
            ORDER BY id
            """,
            [case_id, *rule_ids],
        ).fetchall()
    )


def load_hypergraph_rows(
    conn: sqlite3.Connection, case_id: int
) -> tuple[list[sqlite3.Row], list[sqlite3.Row], list[sqlite3.Row]]:
    nodes = conn.execute(
        """
        SELECT id, case_id, document_id, field_name, field_value
        FROM field_nodes
        WHERE case_id = ?
        ORDER BY id
        """,
        (case_id,),
    ).fetchall()
    edges = conn.execute(
        """
        SELECT id, case_id, constraint_type, rule_id
        FROM hyperedges
        WHERE case_id = ?
        ORDER BY id
        """,
        (case_id,),
    ).fetchall()
    members = conn.execute(
        """
        SELECT edge_id, node_id, slot_name
        FROM hyperedge_members
        WHERE case_id = ?
        ORDER BY id
        """,
        (case_id,),
    ).fetchall()
    return list(nodes), list(edges), list(members)
