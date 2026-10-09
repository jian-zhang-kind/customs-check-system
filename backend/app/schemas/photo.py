"""现场照片。只涉及唛头、批号、件数。"""

from pydantic import BaseModel

from app.schemas.common import OcrSource, PhotoKind
from app.schemas.document import OcrFields


class PhotoOut(BaseModel):
    id: int
    case_id: int
    kind: PhotoKind
    filename: str
    storage_path: str
    ocr_source: OcrSource | None = None
    ocr_fields: OcrFields | None = None
    created_at: str
