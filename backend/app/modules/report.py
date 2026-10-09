"""报告汇编。只折叠规则引擎已经写出的 verdict，不重新比较字段。"""

from __future__ import annotations

from app.modules.types import RuleVerdict


def summary_verdict(verdicts: list[RuleVerdict]) -> str:
    if not verdicts:
        raise RuntimeError("规则引擎未给出结论")
    verdicts_only = {item.verdict for item in verdicts}
    if "fail" in verdicts_only:
        return "fail"
    if "warning" in verdicts_only:
        return "warning"
    return "pass"
