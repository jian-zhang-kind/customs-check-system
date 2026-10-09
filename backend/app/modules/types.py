"""流水线模块之间传递的结构。不含 verdict。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceRecord:
    target: str
    record_id: int
    doc_type: str | None = None
    photo_kind: str | None = None


@dataclass(frozen=True)
class OcrExtract:
    source: SourceRecord
    ocr_source: str
    fields: dict[str, str]


@dataclass(frozen=True)
class AlignedSlot:
    slot_name: str
    document_id: int | None
    field_name: str
    field_value: str
    node_key: str


@dataclass(frozen=True)
class HyperMember:
    node_key: str
    slot_name: str


@dataclass
class HyperNode:
    node_key: str
    document_id: int | None
    field_name: str
    field_value: str


@dataclass
class HyperEdge:
    constraint_type: str
    rule_id: str
    members: list[HyperMember] = field(default_factory=list)


@dataclass
class HypergraphInstance:
    nodes: list[HyperNode]
    edges: list[HyperEdge]

    def values_for(self, rule_id: str) -> dict[str, str]:
        for edge in self.edges:
            if edge.rule_id == rule_id:
                found: dict[str, str] = {}
                nodes = {node.node_key: node for node in self.nodes}
                for member in edge.members:
                    node = nodes.get(member.node_key)
                    if node is not None:
                        found[member.slot_name] = node.field_value
                return found
        return {}


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    jurisdiction: str
    hs_code: str | None
    regulation_name: str
    publish_date: str | None
    source_url: str | None
    excerpt: str
    conflicts_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleVerdict:
    rule_id: str
    verdict: str
    rule_outcome: str
    risk_level: str | None
    description: str
    evidence: dict[str, object]
    chunk_id: str | None = None
    jurisdiction: str | None = None
    regulation_name: str | None = None
    publish_date: str | None = None
    source_url: str | None = None
    excerpt: str | None = None
