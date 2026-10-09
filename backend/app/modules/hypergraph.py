"""超图勾稽。只按模板把字段收成顶点和超边，不判断是否相符。"""

from __future__ import annotations

import json

from app.config import TEMPLATE_PATH
from app.modules.types import AlignedSlot, HyperEdge, HyperMember, HyperNode, HypergraphInstance

_RULE_IDS = {"R-NAME", "R-PARTY", "R-QTY", "R-AMT", "R-MARK"}


def build(slots: list[AlignedSlot]) -> HypergraphInstance:
    templates = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    by_slot = {slot.slot_name: slot for slot in slots}
    nodes: dict[str, HyperNode] = {}
    edges: list[HyperEdge] = []
    for template in templates:
        rule_id = str(template["rule_id"])
        if rule_id not in _RULE_IDS:
            raise ValueError(f"未知勾稽规则 {rule_id}")
        members: list[HyperMember] = []
        for slot_name in template.get("slots", []):
            slot = by_slot.get(slot_name)
            if slot is None:
                continue
            nodes.setdefault(
                slot.node_key,
                HyperNode(
                    node_key=slot.node_key,
                    document_id=slot.document_id,
                    field_name=slot.field_name,
                    field_value=slot.field_value,
                ),
            )
            members.append(HyperMember(node_key=slot.node_key, slot_name=slot.slot_name))
        if len(members) < 2:
            continue
        edges.append(
            HyperEdge(
                constraint_type=str(template["constraint_type"]),
                rule_id=rule_id,
                members=members,
            )
        )
    return HypergraphInstance(nodes=list(nodes.values()), edges=edges)
