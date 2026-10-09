"""超图只读快照。JSON 用 node_id / edge_id；表主键列名是 id。快照内没有 verdict。"""

from pydantic import BaseModel


class FieldNodeOut(BaseModel):
    node_id: int
    case_id: int
    document_id: int | None = None
    field_name: str
    field_value: str | None = None


class HyperedgeMemberOut(BaseModel):
    edge_id: int
    node_id: int
    slot_name: str


class HyperedgeOut(BaseModel):
    edge_id: int
    case_id: int
    constraint_type: str
    rule_id: str
    members: list[HyperedgeMemberOut]


class HypergraphOut(BaseModel):
    case_id: int
    nodes: list[FieldNodeOut]
    edges: list[HyperedgeOut]
