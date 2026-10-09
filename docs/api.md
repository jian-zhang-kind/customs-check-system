# 接口设计：关务慧眼｜出口货物海关申报自查系统

> 依据：[@docs/tech-stack.md](tech-stack.md)、[@docs/architecture.md](architecture.md)。  
> **只做契约，不搭建工程、不写业务代码。**  
> `verdict` 只能由规则引擎经 `run` / `load-demo` 写入，没有任何 PATCH 判定接口。  
> 超图三表无 CRUD。无聊天、出口管制、登录、支付接口。

---

## 0. 相对你原文的改进（请知悉）

未机械照抄你列的枚举，原因如下。若你要改回原文取值，实现前说一声即可。

| 你的原文 | 本文采用 | 原因 |
| --- | --- | --- |
| `Verdict`: pass / warning / fail | **保留这三档给前端展示**，另加只读 `rule_outcome`：`matched` / `conflict` / `hard` / `insufficient_evidence` | 辩论触发靠 `hard`；RAG 未命中靠 `insufficient_evidence`。三档不够支撑已锁定规则引擎 |
| `GET /cases/{id}` 基础详情 | **只返回 Case 行**，单据/照片/报告走子资源 | 避免一个接口塞全库，和资源模型一致 |
| `POST /cases/{id}/run` 只返回执行状态 | 流水线是**同步**的，返回 `status` + `report` 摘要 | 否则前端还要再拉一次报告，答辩一键路径更脆 |
| 错误码只写 400/404/500 | HTTP 用这三档；`code` 与 HTTP 相同 | 竞赛够用，去掉 40001 这类多余编号 |
| 列表字段名 `items` | 按你的要求改为 **`list`** + `total` / `page` / `page_size` | 与前端分页更直观 |
| `CaseStatus` 用 pending | 采用 **pending / running / completed / failed** | 替代旧稿 `draft` |

---

## 1. 全局约定

### 1.1 基址

所有路径相对 **`/api`**。

| 环境 | 示例 |
| --- | --- |
| 开发 | `http://127.0.0.1:8000/api/cases/load-demo` |
| Nginx 演示 / 兜底 | `/api/cases/load-demo` |

JSON：`application/json`。上传：`multipart/form-data`。

### 1.2 统一响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

- 成功：`code = 0`，HTTP 200。
- 失败：HTTP 400 / 404 / 500，`code` 与 HTTP 状态码相同，`data` 可为 `null` 或 `{ "detail": "..." }`。

列表 `data`：

```json
{
  "list": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

查询参数：`page`（默认 1）、`page_size`（默认 20，最大 100）。

### 1.3 错误码

| HTTP / code | 含义 |
| --- | --- |
| 400 | 参数错误（含未知 `demo_type`、缺文件、类型不支持） |
| 404 | Case / Document / Photo / Report 不存在 |
| 500 | 服务错误（流水线异常）。**不得**因此写 `verdict=pass` |

无 401/403：MVP 无登录。

### 1.4 枚举

| 名 | 取值 | 说明 |
| --- | --- | --- |
| `CaseStatus` | `pending` / `running` / `completed` / `failed` | 票次生命周期。**不含** `insufficient_evidence`（那是 `RuleOutcome`，不是票状态） |
| `Verdict` | `pass` / `warning` / `fail` | 给前端的风险档，由规则引擎映射，接口不可改 |
| `RuleOutcome` | `matched` / `conflict` / `hard` / `insufficient_evidence` | 规则内部结果；`hard` 才允许辩论 |
| `DemoType` | `battery-vietnam` | MVP 唯一种子 |
| `DocType` | `declaration` / `invoice` / `packing` / `contract` | 与 `documents.doc_type` 对应 |
| `PhotoKind` | `mark` / `packing` | 唛头 / 现场箱单 |
| `OcrSource` | `paddle` / `fixture` | |
| `RuleId` | `R-NAME` / `R-PARTY` / `R-QTY` / `R-AMT` / `R-HS-CN` / `R-HS-DEST` / `R-MARK` | |
| `Jurisdiction` | `CN` / `VN` | |

映射：`matched`→`pass`；`conflict`→`fail`；`hard` 与 `insufficient_evidence`→`warning`。

### 1.5 演示专用 vs 业务接口

| 标记 | 接口 |
| --- | --- |
| **演示专用** | `POST /cases/load-demo`（一步：建票 + 种子 + run） |
| **业务接口** | `POST /cases` 建空票 → 上传单据/照片 → `POST /cases/{id}/run` → 看报告 |

---

## 2. 字段与表对应（Pydantic 风格）

无 SQLAlchemy。超图无增删改；仅提供 `GET /cases/{id}/hypergraph` 只读快照。

**cases：** `id`, `case_no`, `remark`, `status`, `is_demo`, `demo_type`, `destination_country`, `title`, `created_at`, `updated_at`

**documents：** `id`, `case_id`, `doc_type`, `filename`, `storage_path`, `ocr_source`, `ocr_fields`, `created_at`

**photos：** `id`, `case_id`, `kind`, `filename`, `storage_path`, `ocr_source`, `ocr_fields`, `created_at`

**check_reports：** `id`, `case_id`, `status`, `summary_verdict`, `debate_triggered`, `created_at`

**risk_items：** `id`, `case_id`, `report_id`, `rule_id`, `verdict`, `rule_outcome`, `risk_level`, `description`, `evidence`, `edge_id`, `chunk_id`, `jurisdiction`, `regulation_name`, `publish_date`, `source_url`, `excerpt`

`ocr_fields` 槽位：`product_name`, `party_seller`, `qty`, `amount`, `hs_code`, `material`, `mark`, `lot_no`, `pkgs`, `per_pkg`。缺字段保持缺省，禁止补造。

`destination_country` 为空时：规则引擎对 **R-HS-DEST** 必须写 `rule_outcome=insufficient_evidence`（展示 `verdict=warning`），`source_url` / `excerpt` 为空，**禁止编造**目的国条文。票次 `status` 仍按流水线是否跑完取值（一般为 `completed`），不要把 `insufficient_evidence` 做成第四种 CaseStatus。

---

## 3. Case 票次资源

两条互不耦合的路径：

- **业务：** `POST /cases`（空票、`pending`、`is_demo=false`）→ 上传 Document/Photo → `POST /cases/{id}/run`
- **演示：** `POST /cases/load-demo`（一步到位，不调用 `POST /cases`）

### 3.0 创建空票次

- **路径：** `/cases`
- **方法：** `POST`
- **类型：** 业务接口
- **功能：** 只插入一行 `cases`：`status=pending`，`is_demo=false`，无报告、无 `verdict`。**禁止**在本接口上传文件、隐式 `run`、直接写判定。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| case_no | string | 是 | 业务票号，全表唯一 |
| remark | string | 否 | 备注 |
| title | string | 否 | 展示标题；缺省可用 `case_no` |
| destination_country | string | 否 | 非演示票的目的国；缺省不填则 R-HS-DEST 应为 `insufficient_evidence` |

```json
{
  "case_no": "CK-2026-0001",
  "remark": "手工上传待核"
}
```

**响应 data**

```json
{
  "id": "c_001",
  "case_no": "CK-2026-0001",
  "remark": "手工上传待核",
  "is_demo": false,
  "status": "pending",
  "demo_type": null,
  "destination_country": null,
  "title": "CK-2026-0001",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**错误码：** 400 `case_no` 缺失或重复。

**不做：** 请求体带单据文件、带风险结论、隐式 `run`。

### 3.1 分页查询票次列表

- **路径：** `/cases`
- **方法：** `GET`
- **类型：** 业务接口
- **功能：** 分页列出票次，可按演示标记与状态筛选。

**请求参数（query）**

| 名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| page | int | 否 | 默认 1 |
| page_size | int | 否 | 默认 20 |
| is_demo | bool | 否 | 只看演示票 / 非演示票 |
| status | CaseStatus | 否 | |

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "c_demo_001",
        "case_no": "DEMO-BAT-VN-001",
        "status": "completed",
        "is_demo": true,
        "demo_type": "battery-vietnam",
        "destination_country": "VN",
        "title": "锂电池出口越南（演示）",
        "created_at": "2026-10-09T10:00:00+08:00",
        "updated_at": "2026-10-09T10:00:08+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**错误码：** 400 查询参数非法。

---

### 3.2 查询单条票次基础详情

- **路径：** `/cases/{id}`
- **方法：** `GET`
- **类型：** 业务接口
- **功能：** 只返回 `cases` 一行。单据、照片、报告请调子资源。

**请求参数：** 路径 `id`。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "c_demo_001",
    "case_no": "DEMO-BAT-VN-001",
    "status": "completed",
    "is_demo": true,
    "demo_type": "battery-vietnam",
    "destination_country": "VN",
    "title": "锂电池出口越南（演示）",
    "created_at": "2026-10-09T10:00:00+08:00",
    "updated_at": "2026-10-09T10:00:08+08:00"
  }
}
```

**错误码：** 404 票次不存在。

---

### 3.2.1 超图只读快照

- **路径：** `/cases/{id}/hypergraph`
- **方法：** `GET`
- **类型：** 业务接口（Case 子资源，只读）
- **功能：** 返回本票随 `run` / `load-demo` 落库的 `field_nodes`、`hyperedges`、`hyperedge_members` 完整快照，供电脑端 D3。无 POST/PATCH/DELETE。未 run 过则 `nodes/edges` 为空数组，不是 404（票存在即可）。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "case_id": "c_demo_001",
    "nodes": [
      {
        "node_id": "n1",
        "case_id": "c_demo_001",
        "document_id": "d_inv",
        "field_name": "qty",
        "field_value": "1000"
      }
    ],
    "edges": [
      {
        "edge_id": "e_qty",
        "case_id": "c_demo_001",
        "constraint_type": "qty_identity",
        "rule_id": "R-QTY",
        "members": [
          { "edge_id": "e_qty", "node_id": "n1", "slot_name": "invoice.qty" }
        ]
      }
    ]
  }
}
```

快照里**没有** `verdict`。对错只在 `risk_items`。

**错误码：** 404 票次不存在。

---

### 3.3 一键加载演示票

- **路径：** `/cases/load-demo`
- **方法：** `POST`
- **说明补记：** 本接口**不调用** `POST /cases`；自建 Case 时必须写入演示 `case_no`。
- **类型：** **演示专用**
- **功能：** 创建 `is_demo=true` 的普通 Case，预置锂电池出口越南单据与照片，**同一请求内**跑完整 Pipeline（OCR → 对齐 → 超图勾稽 ∥ RAG → 规则引擎）。辩论默认关。不做管制/危化。

**请求体**

```json
{
  "demo_type": "battery-vietnam"
}
```

| 字段 | 规则 |
| --- | --- |
| demo_type | 可选。缺省或 `null` / `""` → `battery-vietnam`。其它字符串 → **400** |
| 其它字段 | 禁止携带真实报关单内容 |

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "case_id": "c_demo_001",
    "case": {
      "id": "c_demo_001",
      "case_no": "DEMO-BAT-VN-001",
      "status": "completed",
      "is_demo": true,
      "demo_type": "battery-vietnam",
      "destination_country": "VN",
      "title": "锂电池出口越南（演示）",
      "created_at": "2026-10-09T10:00:00+08:00",
      "updated_at": "2026-10-09T10:00:08+08:00"
    },
    "report": {
      "id": "r_001",
      "case_id": "c_demo_001",
      "status": "completed",
      "summary_verdict": "fail",
      "debate_triggered": false,
      "hs_cn": {
        "rule_id": "R-HS-CN",
        "verdict": "fail",
        "rule_outcome": "conflict",
        "source_url": "https://example.gov/cn-tariff-public",
        "regulation_name": "中华人民共和国进出口税则（公开摘录）",
        "publish_date": "2025-01-01"
      },
      "hs_dest": {
        "rule_id": "R-HS-DEST",
        "verdict": "warning",
        "rule_outcome": "hard",
        "source_url": "https://example.gov.vn/import-public",
        "regulation_name": "越南进口税则公开摘录",
        "publish_date": "2024-06-01"
      },
      "created_at": "2026-10-09T10:00:08+08:00"
    }
  }
}
```

`hs_cn` / `hs_dest` 中的法规字段来自 RAG 切片，不是模型生成。示例 URL 为占位，实现时换成真实官方公开链接。

**错误码：** 400 未知 `demo_type`；500 种子缺失或流水线失败（不写通过结论）。OCR 无权重时 `ocr_source=fixture`。

API **不** HTTP 重定向；前端用返回的 `case_id` 自行打开该票。

---

### 3.4 手动触发校验流水线

- **路径：** `/cases/{id}/run`
- **方法：** `POST`
- **类型：** 业务接口
- **功能：** 对已有票跑与 `load-demo` **同一条** Pipeline。上传单据/照片**不会**自动调用本接口。

**请求参数：** 路径 `id`。请求体可空，或 `{"force": true}` 允许对 `completed` 重跑。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "case_id": "c_001",
    "status": "completed",
    "report": {
      "id": "r_002",
      "case_id": "c_001",
      "status": "completed",
      "summary_verdict": "warning",
      "debate_triggered": false,
      "created_at": "2026-10-09T11:00:00+08:00"
    }
  }
}
```

**错误码：** 404 无此票；400 无可校验材料；500 流水线异常。`status=running` 时重复调用视为 400（单机同步，不排队）。

每次成功 run 覆盖本票超图三表与 `risk_items`。接口不能只改 `verdict`。

---

## 4. Document 单据资源

### 4.1 查询票次下单据列表

- **路径：** `/cases/{case_id}/documents`
- **方法：** `GET`
- **类型：** 业务接口

**请求参数：** 路径 `case_id`；query：`doc_type`、`page`、`page_size`。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "d_001",
        "case_id": "c_demo_001",
        "doc_type": "declaration",
        "filename": "declaration.json",
        "storage_path": "data/samples/case_battery_vn/declaration.json",
        "ocr_source": "fixture",
        "ocr_fields": { "product_name": "锂离子蓄电池", "hs_code": "85076000", "qty": 1000 },
        "created_at": "2026-10-09T10:00:01+08:00"
      }
    ],
    "total": 4,
    "page": 1,
    "page_size": 20
  }
}
```

**错误码：** 404 票次不存在。

---

### 4.2 查询单据详情（含 OCR 字段）

- **路径：** `/documents/{id}`
- **方法：** `GET`
- **类型：** 业务接口
- **功能：** 返回 `documents` 行 + `ocr_fields`。不返回文件二进制。

**响应示例：** 单条 `Document` 对象包在 `data` 中（字段同列表元素）。

**错误码：** 404。

---

### 4.3 上传单据

- **路径：** `/cases/{case_id}/documents`
- **方法：** `POST`
- **类型：** 业务接口
- **Content-Type：** `multipart/form-data`

**表单字段**

| 名 | 必填 | 说明 |
| --- | --- | --- |
| doc_type | 是 | `DocType` 之一 |
| file | 是 | pdf / png / jpg，建议 ≤ 8MB |

**响应示例：** `data` 为新建 `Document`（`ocr_fields` 可在 run 前为空）。

**错误码：** 400 缺字段或类型不支持；404 无此票。

上传后**不**自动 `run`。禁止真实企业涉密单证。

---

## 5. Photo 现场照片资源

### 5.1 查询票次下照片列表

- **路径：** `/cases/{case_id}/photos`
- **方法：** `GET`
- **类型：** 业务接口

**请求参数：** 路径 `case_id`；query：`kind`、`page`、`page_size`。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "p_001",
        "case_id": "c_demo_001",
        "kind": "mark",
        "filename": "mark.jpg",
        "storage_path": "data/samples/case_battery_vn/mark.jpg",
        "ocr_source": "fixture",
        "ocr_fields": { "mark": "VN-BAT-2026", "lot_no": "LOT-A", "pkgs": 10 },
        "created_at": "2026-10-09T10:00:02+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

**错误码：** 404。

---

### 5.2 查询照片详情与识别信息

- **路径：** `/photos/{id}`
- **方法：** `GET`
- **类型：** 业务接口

**响应：** `data` 为单条 `Photo`（含 `ocr_fields`）。只涉及唛头、批号、件数。

**错误码：** 404。

---

### 5.3 上传现场照片

- **路径：** `/cases/{case_id}/photos`
- **方法：** `POST`
- **类型：** 业务接口
- **Content-Type：** `multipart/form-data`

**表单：** `kind`（`mark`|`packing`，必填）、`file`（png/jpg，必填）。

**错误码：** 400 / 404。不自动 `run`。不做危化/残损鉴定。

---

## 6. Report 与 RiskItem

### 6.1 校验报告总览（含 HS 双结论）

- **路径：** `/cases/{case_id}/report`
- **方法：** `GET`
- **类型：** 业务接口
- **功能：** 读 `check_reports`，并嵌 **R-HS-CN**、**R-HS-DEST** 两条规则项（来自 `risk_items`，不是模型另写一段）。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "r_001",
    "case_id": "c_demo_001",
    "status": "completed",
    "summary_verdict": "fail",
    "debate_triggered": false,
    "disclaimer": "本系统为竞赛演示工具，输出不构成法律意见或正式归类裁定。",
    "hs_cn": {
      "rule_id": "R-HS-CN",
      "verdict": "fail",
      "rule_outcome": "conflict",
      "description": "申报 HS 与中国公开税则摘录不一致",
      "regulation_name": "中华人民共和国进出口税则（公开摘录）",
      "publish_date": "2025-01-01",
      "source_url": "https://example.gov/cn-tariff-public",
      "excerpt": "……",
      "chunk_id": "cn_8507_01"
    },
    "hs_dest": {
      "rule_id": "R-HS-DEST",
      "verdict": "warning",
      "rule_outcome": "hard",
      "description": "目的国公开进口规则存在相邻冲突条文",
      "regulation_name": "越南进口税则公开摘录",
      "publish_date": "2024-06-01",
      "source_url": "https://example.gov.vn/import-public",
      "excerpt": "……",
      "chunk_id": "vn_8507_02",
      "jurisdiction": "VN"
    },
    "created_at": "2026-10-09T10:00:08+08:00"
  }
}
```

**错误码：** 404 无此票或尚未 run。

免责声明为服务端常量。未命中法规时 `rule_outcome=insufficient_evidence`，`source_url` 为空，禁止填假链接。

---

### 6.2 风险项明细

- **路径：** `/cases/{case_id}/risk-items`
- **方法：** `GET`
- **类型：** 业务接口
- **功能：** 分页列出 `risk_items`。勾稽项带 `edge_id`（指向 `hyperedges`，无超图 CRUD）。HS 项带法规来源链接。

**请求参数：** 路径 `case_id`；query：`rule_id`、`verdict`、`page`、`page_size`。

**响应示例**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      {
        "id": "ri_qty",
        "case_id": "c_demo_001",
        "report_id": "r_001",
        "rule_id": "R-QTY",
        "verdict": "fail",
        "rule_outcome": "conflict",
        "risk_level": "high",
        "description": "发票数量与箱数×每箱数不一致",
        "evidence": { "invoice.qty": 1000, "packing.pkgs": 10, "packing.per_pkg": 50 },
        "edge_id": "e_qty",
        "chunk_id": null,
        "source_url": null
      }
    ],
    "total": 6,
    "page": 1,
    "page_size": 20
  }
}
```

**错误码：** 404。

不提供 `PATCH /risk-items/{id}`。

---

## 7. 明确不提供的接口

- 超图三表的任何增删改（只读 `GET /cases/{id}/hypergraph` 除外）  
- `/chat`、知识库写入、登录注册、支付  
- 出口管制、危化 UN 编号鉴定  
- 直接修改 `verdict` 的接口  

---

## 8. 与流水线的关系

```text
POST /cases/load-demo  ─┐
                        ├─ 同一 Pipeline ─► cases/documents/photos
POST /cases/{id}/run  ─┘                   check_reports / risk_items
                                           超图三表（仅落库，无 REST）
```
