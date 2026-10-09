"""字段对齐。把抽取结果收成统一槽位，不写 verdict，不编造缺槽。"""

from __future__ import annotations

from app.modules.types import AlignedSlot, OcrExtract


def align(extracts: list[OcrExtract]) -> list[AlignedSlot]:
    slots: list[AlignedSlot] = []
    for extract in extracts:
        source = extract.source
        prefix = "photo" if source.target == "photo" else (source.doc_type or "")
        document_id = source.record_id if source.target == "document" else None
        for field_name, field_value in extract.fields.items():
            slots.append(
                AlignedSlot(
                    slot_name=f"{prefix}.{field_name}",
                    document_id=document_id,
                    field_name=field_name,
                    field_value=field_value,
                    node_key=f"{source.target}:{source.record_id}:{field_name}",
                )
            )
    return slots
