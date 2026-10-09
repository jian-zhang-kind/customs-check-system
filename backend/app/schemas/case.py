"""票次、演示加载与 run 的请求 / 响应。id 按 schema.sql 为整数，示例里的 c_001 只是示意。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import CaseStatus, DemoType
from app.schemas.report import ReportSummary


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_no: str = Field(min_length=1)
    remark: str | None = None
    title: str | None = None
    destination_country: str | None = None

    @field_validator("case_no")
    @classmethod
    def case_no_not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("case_no 不能为空")
        return text


class CaseOut(BaseModel):
    """is_demo 在接口里是布尔；库内是 0/1。本模型只描述 JSON。"""

    id: int
    case_no: str
    remark: str | None = None
    status: CaseStatus
    is_demo: bool
    demo_type: DemoType | None = None
    destination_country: str | None = None
    title: str | None = None
    created_at: str
    updated_at: str


class LoadDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demo_type: str | None = None

    @field_validator("demo_type")
    @classmethod
    def only_battery_vietnam(cls, value: str | None) -> str:
        if value is None or value == "":
            return DemoType.battery_vietnam.value
        if value != DemoType.battery_vietnam.value:
            raise ValueError("未知 demo_type")
        return value


class LoadDemoData(BaseModel):
    case_id: int
    case: CaseOut
    report: ReportSummary


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False


class RunData(BaseModel):
    case_id: int
    status: CaseStatus
    report: ReportSummary
