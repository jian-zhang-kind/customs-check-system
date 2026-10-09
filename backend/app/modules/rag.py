"""法规检索模拟。只返回本地摘录，不写是否错报，不使用向量库。"""

from __future__ import annotations

import json

from app.config import CHUNK_PATH
from app.modules.types import AlignedSlot, EvidenceChunk


def retrieve(slots: list[AlignedSlot], destination_country: str | None) -> list[EvidenceChunk]:
    query = " ".join(slot.field_value for slot in slots if slot.field_name in {"product_name", "material", "hs_code"})
    if not query.strip():
        return []
    destination = (destination_country or "").strip().upper()
    found: list[EvidenceChunk] = []
    for raw in json.loads(CHUNK_PATH.read_text(encoding="utf-8")):
        jurisdiction = str(raw.get("jurisdiction", "")).upper()
        if jurisdiction != "CN" and jurisdiction != destination:
            continue
        keywords = [str(item) for item in raw.get("keywords", [])]
        if keywords and not any(word and word in query for word in keywords):
            continue
        found.append(
            EvidenceChunk(
                chunk_id=str(raw["chunk_id"]),
                jurisdiction=jurisdiction,
                hs_code=raw.get("hs_code"),
                regulation_name=str(raw.get("regulation_name") or ""),
                publish_date=raw.get("publish_date"),
                source_url=raw.get("source_url"),
                excerpt=str(raw.get("text") or ""),
                conflicts_with=tuple(str(item) for item in raw.get("conflicts_with", [])),
            )
        )
    return found
