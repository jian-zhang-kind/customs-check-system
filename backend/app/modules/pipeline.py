"""编排：OCR → 对齐 →（超图与 RAG 并行）→ 规则引擎 → 报告摘要。

HTTP 会等本函数结束再返回报告。并行的是超图和法规检索，不是把请求改成后台任务。
"""

from __future__ import annotations

import asyncio

from app.modules.align import align
from app.modules.hypergraph import build as build_hypergraph
from app.modules.ocr import extract
from app.modules.rag import retrieve
from app.modules.report import summary_verdict
from app.modules.rules import judge
from app.modules.types import (
    HypergraphInstance,
    OcrExtract,
    RuleVerdict,
    SourceRecord,
)


async def run_pipeline(
    records: list[SourceRecord],
    destination_country: str | None,
) -> tuple[list[OcrExtract], HypergraphInstance, list[RuleVerdict], str]:
    extracts = await asyncio.to_thread(extract, records)
    aligned = align(extracts)
    graph, chunks = await asyncio.gather(
        asyncio.to_thread(build_hypergraph, aligned),
        asyncio.to_thread(retrieve, aligned, destination_country),
    )
    verdicts = judge(aligned, graph, chunks, destination_country)
    return extracts, graph, verdicts, summary_verdict(verdicts)
