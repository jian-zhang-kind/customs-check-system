"""统一响应、分页与枚举。取值以 docs/api.md §1.4 为准。"""

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class CaseStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Verdict(str, Enum):
    """前端风险档 pass / warning / fail。只能由规则引擎经 run / load-demo 写入。"""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class RuleOutcome(str, Enum):
    matched = "matched"
    conflict = "conflict"
    hard = "hard"
    insufficient_evidence = "insufficient_evidence"


class DemoType(str, Enum):
    battery_vietnam = "battery-vietnam"


class DocType(str, Enum):
    declaration = "declaration"
    invoice = "invoice"
    packing = "packing"
    contract = "contract"


class PhotoKind(str, Enum):
    mark = "mark"
    packing = "packing"


class OcrSource(str, Enum):
    paddle = "paddle"
    fixture = "fixture"


class RuleId(str, Enum):
    name = "R-NAME"
    party = "R-PARTY"
    qty = "R-QTY"
    amt = "R-AMT"
    hs_cn = "R-HS-CN"
    hs_dest = "R-HS-DEST"
    mark = "R-MARK"


class Jurisdiction(str, Enum):
    cn = "CN"
    vn = "VN"


class ApiResponse(BaseModel, Generic[T]):
    """成功：code=0 且 HTTP 200。失败：code 与 HTTP 状态码相同。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    """列表字段名是 list，不是 items。"""

    list: list[T]
    total: int = 0
    page: int = 1
    page_size: int = 20


class PageQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
