"""单据。ocr_fields 只列约定槽位，缺槽保持缺省。"""

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DocType, OcrSource


class OcrFields(BaseModel):
    model_config = ConfigDict(extra="ignore")

    product_name: str | None = None
    party_seller: str | None = None
    qty: str | int | float | None = None
    amount: str | int | float | None = None
    hs_code: str | None = None
    material: str | None = None
    mark: str | None = None
    lot_no: str | None = None
    pkgs: str | int | float | None = None
    per_pkg: str | int | float | None = None


class DocumentOut(BaseModel):
    id: int
    case_id: int
    doc_type: DocType
    filename: str
    storage_path: str
    ocr_source: OcrSource | None = None
    ocr_fields: OcrFields | None = None
    created_at: str
