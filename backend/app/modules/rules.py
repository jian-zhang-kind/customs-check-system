"""规则引擎。唯一写出 verdict / rule_outcome 的模块。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.modules.types import AlignedSlot, EvidenceChunk, HypergraphInstance, RuleVerdict

_VERDICT = {
    "matched": "pass",
    "conflict": "fail",
    "hard": "warning",
    "insufficient_evidence": "warning",
}
_LEVEL = {
    "matched": "low",
    "conflict": "high",
    "hard": "medium",
    "insufficient_evidence": "low",
}


def judge(
    slots: list[AlignedSlot],
    graph: HypergraphInstance,
    chunks: list[EvidenceChunk],
    destination_country: str | None,
) -> list[RuleVerdict]:
    declared_hs = _declared_hs(slots)
    return [
        _identity("R-NAME", "品名", graph),
        _identity("R-PARTY", "主体", graph),
        _quantity(graph),
        _identity("R-AMT", "金额", graph),
        _hs_cn(declared_hs, chunks),
        _hs_dest(destination_country, chunks),
        _mark(graph),
    ]


def _identity(rule_id: str, label: str, graph: HypergraphInstance) -> RuleVerdict:
    values = graph.values_for(rule_id)
    evidence = _evidence(values)
    if len(values) < 2:
        return _item(rule_id, "insufficient_evidence", f"{label}字段不足，无法勾稽", evidence)
    if len(set(values.values())) == 1:
        return _item(rule_id, "matched", f"{label}在已抽取单据间一致", evidence)
    return _item(rule_id, "conflict", f"{label}在单据间不一致", evidence)


def _quantity(graph: HypergraphInstance) -> RuleVerdict:
    values = graph.values_for("R-QTY")
    evidence = _evidence(values)
    needed = ("invoice.qty", "packing.pkgs", "packing.per_pkg", "declaration.qty")
    if any(key not in values for key in needed):
        return _item("R-QTY", "insufficient_evidence", "数量勾稽字段不足", evidence)
    try:
        invoice_qty = _number(values["invoice.qty"])
        packages = _number(values["packing.pkgs"])
        per_package = _number(values["packing.per_pkg"])
        declaration_qty = _number(values["declaration.qty"])
    except InvalidOperation:
        return _item("R-QTY", "insufficient_evidence", "数量字段无法换算", evidence)
    if invoice_qty == packages * per_package and invoice_qty == declaration_qty:
        return _item("R-QTY", "matched", "发票数量、箱数乘每箱数与报关数量一致", evidence)
    return _item("R-QTY", "conflict", "发票数量与箱数×每箱数或报关数量不一致", evidence)


def _mark(graph: HypergraphInstance) -> RuleVerdict:
    values = graph.values_for("R-MARK")
    evidence = _evidence(values)
    groups = {
        "唛头": [key for key in values if key.endswith(".mark")],
        "批号": [key for key in values if key.endswith(".lot_no")],
        "件数": [key for key in values if key.endswith(".pkgs")],
    }
    comparable = [keys for keys in groups.values() if len(keys) >= 2]
    if not comparable:
        return _item("R-MARK", "insufficient_evidence", "唛头、批号或件数字段不足", evidence)
    for keys in comparable:
        if len({values[key] for key in keys}) > 1:
            return _item("R-MARK", "conflict", "唛头、批号或件数与申报数据不一致", evidence)
    return _item("R-MARK", "matched", "唛头、批号和件数在已抽取来源间一致", evidence)


def _hs_cn(declared_hs: list[str], chunks: list[EvidenceChunk]) -> RuleVerdict:
    cn_chunks = [chunk for chunk in chunks if chunk.jurisdiction == "CN"]
    if not declared_hs or not cn_chunks:
        return _item(
            "R-HS-CN",
            "insufficient_evidence",
            "缺少申报 HS 或中国公开税则摘录",
            {"declared_hs": declared_hs},
        )
    cited = cn_chunks[0]
    candidate_codes = {chunk.hs_code for chunk in cn_chunks if chunk.hs_code}
    if len(candidate_codes) > 1:
        return _cite(
            "R-HS-CN",
            "hard",
            "中国公开税则摘录出现多个候选子目",
            {"declared_hs": declared_hs, "candidate_hs": sorted(candidate_codes)},
            cited,
            "CN",
        )
    if any(code != cited.hs_code for code in declared_hs):
        return _cite(
            "R-HS-CN",
            "conflict",
            "申报 HS 与中国公开税则摘录不一致",
            {"declared_hs": declared_hs, "candidate_hs": cited.hs_code},
            cited,
            "CN",
        )
    return _cite(
        "R-HS-CN",
        "matched",
        "申报 HS 与中国公开税则摘录一致",
        {"declared_hs": declared_hs, "candidate_hs": cited.hs_code},
        cited,
        "CN",
    )


def _hs_dest(destination_country: str | None, chunks: list[EvidenceChunk]) -> RuleVerdict:
    destination = (destination_country or "").strip().upper()
    if not destination:
        return _item(
            "R-HS-DEST",
            "insufficient_evidence",
            "未填写目的国，不能核对目的国进口规则",
            {},
        )
    matched = [chunk for chunk in chunks if chunk.jurisdiction == destination]
    if destination not in {"CN", "VN"} or not matched:
        return _item(
            "R-HS-DEST",
            "insufficient_evidence",
            "没有该目的国的公开进口规则摘录",
            {"destination_country": destination},
        )
    cited = matched[0]
    ids = {chunk.chunk_id for chunk in matched}
    conflicting = [chunk for chunk in matched if ids.intersection(chunk.conflicts_with)]
    if len(conflicting) >= 2:
        return _cite(
            "R-HS-DEST",
            "hard",
            "目的国公开进口规则存在互相冲突的条文",
            {"destination_country": destination, "chunk_ids": [chunk.chunk_id for chunk in conflicting]},
            cited,
            destination,
        )
    return _cite(
        "R-HS-DEST",
        "matched",
        "目的国公开进口规则摘录未显示额外冲突",
        {"destination_country": destination, "chunk_ids": [chunk.chunk_id for chunk in matched]},
        cited,
        destination,
    )


def _declared_hs(slots: list[AlignedSlot]) -> list[str]:
    found: list[str] = []
    for slot in slots:
        if slot.field_name == "hs_code" and slot.field_value not in found:
            found.append(slot.field_value)
    return found


def _item(
    rule_id: str,
    outcome: str,
    description: str,
    evidence: dict[str, object],
) -> RuleVerdict:
    return RuleVerdict(
        rule_id=rule_id,
        verdict=_VERDICT[outcome],
        rule_outcome=outcome,
        risk_level=_LEVEL[outcome],
        description=description,
        evidence=evidence,
    )


def _cite(
    rule_id: str,
    outcome: str,
    description: str,
    evidence: dict[str, object],
    chunk: EvidenceChunk,
    jurisdiction: str,
) -> RuleVerdict:
    item = _item(rule_id, outcome, description, evidence)
    return RuleVerdict(
        rule_id=item.rule_id,
        verdict=item.verdict,
        rule_outcome=item.rule_outcome,
        risk_level=item.risk_level,
        description=item.description,
        evidence=item.evidence,
        chunk_id=chunk.chunk_id,
        jurisdiction=jurisdiction,
        regulation_name=chunk.regulation_name,
        publish_date=chunk.publish_date,
        source_url=chunk.source_url,
        excerpt=chunk.excerpt,
    )


def _evidence(values: dict[str, str]) -> dict[str, object]:
    return {key: _as_json(value) for key, value in values.items()}


def _as_json(value: str) -> object:
    try:
        number = _number(value)
    except InvalidOperation:
        return value
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def _number(value: str) -> Decimal:
    return Decimal(value.strip())
