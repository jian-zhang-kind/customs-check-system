# 流程图（Mermaid）

依据：[@docs/api.md](../api.md)、[@docs/architecture.md](../architecture.md)。  
只描述约定，不实现代码。可直接在支持 Mermaid 的 Markdown 里渲染。

## 已拍板的画法

1. **「活动图」**：Mermaid 没有标准 UML Activity，用 `flowchart` 表达流水线。
2. **时序图**：业务 + 演示两张都保留。
3. **状态机**：允许 `completed`/`failed` 经 `POST /run`（含 force/重试）回到 `running`。
4. **`load-demo` 与 `pending`**：客户端几乎看不到 `pending`；图中 `[*] --> running` 表示演示入口，业务入口仍是 `[*] --> pending`。

模块边界（图中已遵守）：超图/RAG/OCR **不写** `verdict`；只有规则引擎出判定。

---

## 1. 时序图

### 1.1 业务链路：建票 → 上传 → run → 报告

```mermaid
sequenceDiagram
  participant FE as NuxtFrontend
  participant API as FastAPI
  participant OCR as OCR
  participant Align as Align
  participant HG as Hypergraph
  participant RAG as RAG
  participant RE as RuleEngine
  participant DB as SQLite

  FE->>API: POST /cases case_no
  API->>DB: INSERT cases pending is_demo false
  API-->>FE: id status pending

  FE->>API: POST /cases/id/documents
  API->>DB: INSERT documents
  API-->>FE: Document
  FE->>API: POST /cases/id/photos
  API->>DB: INSERT photos
  API-->>FE: Photo

  FE->>API: POST /cases/id/run
  API->>DB: UPDATE status running
  API->>OCR: extract fields
  OCR-->>API: ocr_fields no verdict
  API->>Align: map slots
  Align-->>API: aligned fields no verdict
  par structure only
    API->>HG: instantiate edges
    HG-->>API: nodes edges members
    API->>RAG: retrieve chunks
    RAG-->>API: texts source_url
  end
  API->>RE: judge aligned plus graph plus chunks
  RE-->>API: verdicts rule_outcome
  API->>DB: UPSERT report risk_items hypergraph
  API->>DB: UPDATE status completed or failed
  API-->>FE: status plus report summary
  FE->>API: GET /cases/id/report
  API-->>FE: hs_cn hs_dest
  FE->>API: GET /cases/id/hypergraph
  API-->>FE: snapshot read only
```

### 1.2 演示链路：仅 `POST /cases/load-demo`（不调用 `POST /cases`）

```mermaid
sequenceDiagram
  participant FE as NuxtFrontend
  participant API as FastAPI
  participant Seed as DemoSeed
  participant Pipe as Pipeline
  participant RE as RuleEngine
  participant DB as SQLite

  FE->>API: POST /cases/load-demo demo_type
  alt unknown demo_type
    API-->>FE: 400
  else battery-vietnam or default
    API->>DB: INSERT cases is_demo true case_no DEMO
    API->>Seed: load battery vietnam files
    Seed->>DB: INSERT documents photos fixture
    API->>Pipe: same Pipeline as run
    Pipe->>RE: only engine writes verdict
    RE-->>Pipe: verdicts
    Pipe->>DB: report risk_items hypergraph completed
    API-->>FE: case_id plus full report
  end
```

---

## 2. 流水线活动（flowchart，非 UML Activity）

`destination_country` 为空时，规则引擎对 R-HS-DEST 给出 `insufficient_evidence`，不编造条文。整票 `status` 仍可以是 `completed`。

```mermaid
flowchart TB
  startNode[Start_run_or_load_demo] --> ocr[OCR_structured_fields]
  ocr --> align[Align_slots]
  align --> split[Fan_out]
  split --> hg[Hypergraph_structure_only]
  split --> rag[RAG_statutes_only]
  hg --> joinNode[Fan_in]
  rag --> joinNode
  joinNode --> re[RuleEngine_verdicts]
  re --> destEmpty{Dest_country_empty}
  destEmpty -->|yes| destSkip[R_HS_DEST_insufficient_evidence]
  destEmpty -->|no| destRule[R_HS_DEST_vs_VN_chunks]
  destSkip --> writeDb[Write_report_risk_hypergraph]
  destRule --> writeDb
  writeDb --> ok{Pipeline_ok}
  ok -->|yes| done[Case_completed]
  ok -->|no| fail[Case_failed_no_fake_pass]
```

---

## 3. Case 状态机

票状态只有四档：`pending` / `running` / `completed` / `failed`。  
`insufficient_evidence` 不是票状态，只出现在 `risk_items.rule_outcome`。

```mermaid
stateDiagram-v2
  [*] --> pending: POST_cases_business
  pending --> running: POST_run
  running --> completed: pipeline_success
  running --> failed: pipeline_exception
  completed --> running: POST_run_force
  failed --> running: POST_run_retry

  [*] --> running: POST_load_demo_internal
```

上传单据/照片 **不改变** `status`（仍为 `pending`，直到 `run`）。
