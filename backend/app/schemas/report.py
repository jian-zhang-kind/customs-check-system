"""报告与风险项。免责声明是服务端常量，不由模型改写。"""

from typing import Any

from pydantic import BaseModel

from app.schemas.common import CaseStatus, Jurisdiction, RuleId, RuleOutcome, Verdict

DISCLAIMER = "本系统为竞赛演示工具，输出不构成法律意见或正式归类裁定。"


class HsRuleView(BaseModel):
    rule_id: RuleId
    verdict: Verdict
    rule_outcome: RuleOutcome
    description: str | None = None
    risk_level: str | None = None
    regulation_name: str | None = None
    publish_date: str | None = None
    source_url: str | None = None
    excerpt: str | None = None
    chunk_id: str | None = None
    jurisdiction: Jurisdiction | None = None
    edge_id: int | None = None


class ReportSummary(BaseModel):
    id: int
    case_id: int
    status: CaseStatus
    summary_verdict: Verdict | None = None
    debate_triggered: bool
    created_at: str
    hs_cn: HsRuleView | None = None
    hs_dest: HsRuleView | None = None


class ReportDetail(ReportSummary):
    disclaimer: str = DISCLAIMER


class RiskItemOut(BaseModel):
    id: int
    case_id: int
    report_id: int
    rule_id: RuleId
    verdict: Verdict
    rule_outcome: RuleOutcome
    risk_level: str | None = None
    description: str | None = None
    evidence: dict[str, Any] | None = None
    edge_id: int | None = None
    chunk_id: str | None = None
    jurisdiction: Jurisdiction | None = None
    regulation_name: str | None = None
    publish_date: str | None = None
    source_url: str | None = None
    excerpt: str | None = None
