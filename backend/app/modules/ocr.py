"""OCR 模拟。只按单据类型填字段，ocr_source 固定为 fixture。不读图片，不写 verdict。"""

from __future__ import annotations

import json

from app.config import OCR_FIXTURE_PATH
from app.modules.types import OcrExtract, SourceRecord

_SLOTS = (
    "product_name",
    "party_seller",
    "qty",
    "amount",
    "hs_code",
    "material",
    "mark",
    "lot_no",
    "pkgs",
    "per_pkg",
)


def extract(records: list[SourceRecord]) -> list[OcrExtract]:
    fixture = json.loads(OCR_FIXTURE_PATH.read_text(encoding="utf-8"))
    documents = fixture.get("documents", {})
    photos = fixture.get("photos", {})
    extracts: list[OcrExtract] = []
    for record in records:
        raw = {}
        if record.target == "document" and record.doc_type:
            raw = documents.get(record.doc_type, {})
        elif record.target == "photo" and record.photo_kind:
            raw = photos.get(record.photo_kind, {})
        extracts.append(
            OcrExtract(
                source=record,
                ocr_source="fixture",
                fields=_fields(raw if isinstance(raw, dict) else {}),
            )
        )
    return extracts


def _fields(raw: dict[str, object]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for key in _SLOTS:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parsed[key] = text
    return parsed
