# 技术选型说明：关务慧眼｜出口货物海关申报自查系统

> 依据：[@docs/handoff.md](handoff.md)、[@docs/architecture.md](architecture.md)、[@docs/requirement-spec.md](requirement-spec.md)。  
> 本文只锁定框架 / 数据库 / 中间件，**不含 API 定义、不含业务实现代码**。  
> 约束：前后端分离；FastAPI 纯 API；后端同进程模块化单体；超图只表达单据字段勾稽；规则引擎判定；模拟数据。

---

## 1. 选型总览

| 分类 | MVP 采用 | 明确不采用（本次） |
| --- | --- | --- |
| 后端框架 / 库 | Python 3、FastAPI、Uvicorn、Pydantic、PaddleOCR、OpenAI 兼容客户端、NumPy | Django 全栈模板、Spring Cloud、第二套 OCR |
| 前端框架 / 库 | Nuxt 3、Element Plus、Axios | 原生 App、Next.js 替代 API、Supabase 替流水线 |
| 数据库 | SQLite（业务 + 超图实例）；JSON 文件（勾稽模板、RAG 切片与向量） | PostgreSQL / MySQL（可未来迁移）、Neo4j、Milvus |
| 中间件 | 开发：FastAPI CORSMiddleware；竞赛演示：Nginx 反代 | Redis、Milvus、Neo4j、Kafka、RabbitMQ、Celery、K8s |

系统形态回顾（详见 [@docs/architecture.md](architecture.md) §3）：**Nuxt 3 独立前端 → HTTP `/api` → FastAPI 单进程 → 内部模块 + SQLite / JSON**。微服务不落地。

---

## 2. 后端框架与库

| 选型 | 用途 | 选择理由 |
| --- | --- | --- |
| Python 3 | 后端运行时 | 与 PaddleOCR 同语言，避免再包一层 RPC；竞赛环境安装成本低。 |
| FastAPI | 纯 HTTP JSON API | 交接允许前后端自选且要求轻量；适合文件上传与 OpenAPI 自描述；**不**用它渲染业务页面。 |
| Uvicorn | ASGI 进程 | FastAPI 标准运行方式；开发与兜底演示直接 `uvicorn` 即可。 |
| Pydantic | 请求 / 领域结构校验 | 与 FastAPI 一体；强制对齐、报告等结构不含「模型自由判定」字段。 |
| python-multipart | 单据 / 现场照片上传 | 上传是 P0 输入通路。 |
| PaddleOCR | 唯一 OCR 引擎 | [@docs/handoff.md](handoff.md) 指定开源 OCR；禁止再引 EasyOCR / Tesseract 等第二引擎。权重缺失时仿真案例可读预置 JSON，`source=fixture`。 |
| OpenAI 兼容 HTTP 客户端 | 语义对齐；P1 辩论可选第二端点 | LLM **只做理解**，不写 `verdict`。无密钥时走仿真映射，保证演示可跑。 |
| NumPy（或等价向量点积） | RAG 进程内余弦检索 | 法规切片规模小，不必上向量中间件。 |

后端内部：OCR、对齐、超图、RAG、规则引擎、辩论、报告均为 **同一进程内 Python 模块**，模块间函数调用，不开新端口。

**本次不用的后端框架：** Django 模板单体（与前后端分离冲突）；Flask 可替换但已锁定 FastAPI；Spring Boot / Node 会迫使 Paddle 另起进程，增加部署，不采用。

---

## 3. 前端框架与库

| 选型 | 用途 | 选择理由 |
| --- | --- | --- |
| Nuxt 3 | 独立前端工程 | 相对纯 Vite SPA 更接近 2026 常见 Vue 全栈形态；竞赛用静态生成，**不**用 Nuxt 服务端去跑 OCR。 |
| Element Plus | 表格、上传、步骤条、结果展示 | 换 Nuxt 后仍用这套，避免重做演示页。 |
| Axios | 调用 FastAPI | 开发基址 `http://127.0.0.1:8000/api`，演示 / 兜底用相对路径 `/api`。 |

不做：原生 App、Uni-app 独立发行包、Vue Router 多业务站点（单页三个分区即可，不新增页面产品）。

---

## 4. 数据库

MVP **两个落盘面**：SQLite 管「这一票自查的业务与超图实例」；JSON 文件管「只读模板与法规向量」。**存储方案不变**（JSON 向量 + SQLite）。业务单证为仿真样本；法规为海外政府官方公开文本快照。

### 4.1 SQLite（业务模拟库 + 超图实例）

| 项 | 说明 |
| --- | --- |
| 文件 | 建议 `data/app.db`，单机文件库 |
| 访问 | Python 标准库 `sqlite3`，**不引入 SQLAlchemy**。Pydantic 只校验接口入参 / 出参，不做 ORM |
| 用途 | **业务表 + 超图实例三张表**（不是「全库只有三张表」） |
| 选择理由 | 表少、拷目录即可答辩；零安装数据库服务 |
| 不用 SQLite 做的事 | 不存企业关系网；不当向量库；不替代法规原文文件 |

**业务表（模拟数据，不是监管库）**

| 表 | 用途 |
| --- | --- |
| `cases` | 一票模拟出口自查 |
| `documents` | 报关单 / 增值税发票 / 装箱单 / 出口合同 |
| `photos` | 现场唛头 / 箱单照片及 OCR 来源 |
| `check_reports` | 体检报告头 |
| `risk_items` | 规则引擎写出的风险明细（含 `rule_id`、`edge_id`、`chunk_id`） |

**超图如何用 SQLite 三张表持久化（只表达单据字段勾稽）**

超图 = 顶点（某张单据上的一个字段取值）+ 超边（一条勾稽约束，可连接 ≥2 个顶点）+ 成员（超边包含哪些顶点）。这不是企业—企业图。

| 表 | 图论角色 | 关键字段 | 持久化含义 |
| --- | --- | --- | --- |
| `field_nodes` | 顶点 | `node_id`, `case_id`, `document_id`, `field_name`, `field_value` | 例如：发票.数量=113000；箱单.件数=100；箱单.每箱数=300 |
| `hyperedges` | 超边 | `edge_id`, `case_id`, `constraint_type`, `rule_id` | 例如类型 `qty_identity`，绑定规则 `R-QTY` |
| `hyperedge_members` | 关联 | `edge_id`, `node_id`, `slot_name` | 把多个字段顶点挂到同一条超边上（四点数量勾稽即四行成员） |

数量勾稽示例（一次 INSERT 一条超边 + 四条成员，**不是**四家企业互连）：

```text
hyperedges:  e_qty | qty_identity | R-QTY
members:     e_qty → invoice.qty
             e_qty → packing.pkgs
             e_qty → packing.per_pkg
             e_qty → declaration.qty
constraint:  invoice.qty == pkgs * per_pkg  AND invoice.qty == declaration.qty
```

勾稽**模板**（有哪些约束、槽位名、表达式）不放 SQLite，见下一节 JSON，避免把规则硬编码进库结构。每次 `/run` 按模板物化实例行，报告用 `edge_id` 追溯。

### 4.2 本地 JSON（模板 + RAG 向量库）

| 文件 | 用途 | 选择理由 |
| --- | --- | --- |
| `data/hypergraph/constraint_templates.json` | 品名 / 主体 / 数量 / 金额 / 唛头批号件数等勾稽模板 | 答辩时可打开给评委看约束白名单；禁止出现企业关联类型 |
| `data/knowledge/hs_tariff_chunks.json` | 海外各国政府**官方公开渠道**发布的进口商品法律法规快照（非涉密） | 交接要求 RAG 给依据；体积控制在女裤演示可讲解规模；**不上 Milvus，仍为本地 JSON** |
| `data/knowledge/embeddings.json` | 与 `chunk_id` 一一对应的预计算向量 | **RAG 向量不进 SQLite、不上 Milvus**；进程启动载入内存，NumPy 余弦检索 |

每条法规切片字段（检索返回必须带出来源，禁止无出处条文）：

| 字段 | 含义 |
| --- | --- |
| `chunk_id` | 切片编号 |
| `title` / `regulation_name` | 法规名称 |
| `publish_date` | 发布日期 |
| `source_url` | 官方公开来源链接 |
| `hs_code` | 相关税号（如有） |
| `text` | 公开原文摘录 |
| `issuing_body` | 发布机关（政府官方机构名称） |

对应向量仍只存在 `embeddings.json`，与 `chunk_id` 对齐。

检索流程：品名 + 成分 + 申报 HS → 向量检索 JSON 中的 chunk → 将 `text`、`regulation_name`、`publish_date`、`source_url` 交给规则引擎与报告。未命中返回空列表，禁止模型编造条文或假链接。

业务侧：`cases` / `documents` / `photos` 仅为模拟仿真样本，**禁止**把真实企业报关单写入 SQLite 或演示目录。

---

## 5. 中间件

这里的「中间件」指进程外的代理、缓存、队列、专用数据库插件。MVP 尽量少用。

### 5.1 本次使用

| 中间件 | 使用场景 | 不使用的场景 |
| --- | --- | --- |
| FastAPI `CORSMiddleware` | **仅开发调试模式**：白名单 `http://127.0.0.1:3000` 与 `http://localhost:3000` | Nginx 演示与无 Nginx 兜底均为同源，不依赖 CORS |
| Nginx | **仅竞赛演示反向代理**：`/` → Nuxt 静态产出；`/api/` → FastAPI | **开发环境不需要、不启动 Nginx**。开发 = Nuxt + FastAPI 两进程 + CORS |

Nginx 不是业务中间件，不承担鉴权中台、WAF、负载集群。赛场没有 Nginx 时走架构中的兜底：FastAPI 挂载 `dist`，仍不启用 Redis 等。

### 5.2 MVP 明确不使用的中间件（及原因）

| 不使用 | 常见误用方式 | 本次不选用的原因 | 缺了它如何工作 |
| --- | --- | --- | --- |
| Redis | 会话、缓存、队列 | 无登录系统、无高并发、无分布式锁需求；多一个进程违背轻量化 | 状态在 SQLite 与请求内内存 |
| Milvus / Chroma / Pinecone | RAG 向量库 | 法规切片只有演示级条数；交接未要求独立向量服务；部署重 | 本地 `embeddings.json` + 内存余弦 |
| Neo4j / 其他图数据库 | 把超图做成「图谱产品」 | 超图是字段勾稽，不是企业团伙网；用图库容易在答辩中滑向监管风控叙事 | SQLite 三张表表达超边 |
| Kafka / RabbitMQ | 异步流水线 | 单票同步自查即可；拆队列等于预埋微服务 | FastAPI 进程内 pipeline 顺序 / 并行函数调用 |
| Celery 等任务队列 | OCR 后台任务 | 演示要同步出报告；再依赖 Broker（通常又是 Redis） | 请求内调用 Paddle 或 fixture |
| Elasticsearch | 全文搜税则 | 演示检索以向量 + HS 过滤足够 | JSON 扫描 / 余弦 Top-K |
| Docker Compose 强制依赖 / K8s / API 网关 | 生产编排 | 交接：不做完整生产级部署 | 本机两个进程（开发）或 Nginx+API（演示） |
| MinIO / 云对象存储 | 单证影像 | 仿真图片放本地目录即可 | 文件系统路径写入 `documents` / `photos` |

禁止借「以后要用图数据库」把表结构改成企业关联边。

---

## 6. 未来生产环境可迁移备选（本次不落地）

只允许在**不改变产品定位**（企业自查、非监管、字段超图、规则引擎判定）的前提下替换组件。

| MVP | 生产可迁移 | 迁移时仍须遵守 |
| --- | --- | --- |
| SQLite | PostgreSQL（业务表结构可几乎平移） | 仍是模拟或企业自有单证，不接海关涉密库 |
| JSON 向量 | PostgreSQL `pgvector`，或独立 Milvus | 仍只存官方公开进口法规快照（需定期同步）；检索结果仍交规则引擎 |
| SQLite 超图表 | 仍建议关系表；若查询复杂可考虑专用图库 **仅存字段顶点与勾稽超边** | **不得**迁移成企业团伙 / 股权图谱 |
| CORS + Nuxt / Nginx 反代 | 企业网关或 Ingress 同源反代 | 前端仍调纯 API；后端可不拆微服务 |
| 单进程模块 | 仅当 OCR / RAG 成为瓶颈时再拆独立进程 | 拆分不等于上微服务全家桶；辩论仍不得变主流程 |
| 可选 Redis | 缓存税则向量或限流 | 不作为风险结论存储 |
| PaddleOCR 本机 | GPU 推理服务 | 仍是唯一 OCR 引擎 |

本次竞赛工程 **不预埋** 上述生产组件的依赖与配置。

---

## 7. 运行环境与 Nginx 边界（重申）

| 环境 | 前端 | 后端 | Nginx | 跨域 |
| --- | --- | --- | --- | --- |
| 开发调试 | Nuxt `:3000` | Uvicorn / FastAPI `:8000` | **不需要** | CORS 白名单 |
| 竞赛演示 | Nginx 托管 `dist` | FastAPI 只服务 `/api` | **仅此模式使用**，做静态 + `/api` 反代 | 无（同源） |
| 无 Nginx 兜底 | FastAPI 挂载 `dist` | 同进程 `/api` | 不使用 | 无（同源） |

开发者日常：只开 Nuxt 与 FastAPI。不要为了「完整中间件」在开发机启动 Nginx、Redis、Milvus、Neo4j。

建议端口（可改，不改变功能）：Nuxt `3000`，FastAPI `8000`，竞赛 Nginx `80` 或 `8080`。

---

## 8. 与交接约束的对照

| 交接要求 | 本选型如何落实 |
| --- | --- |
| OCR = PaddleOCR | 后端唯一 OCR 库 |
| RAG 存海外政府公开进口法规快照 | `hs_tariff_chunks.json`（含来源链接、法规名称、发布日期）+ `embeddings.json` |
| 超图 = 字段勾稽，不是团伙网 | SQLite 三张表 + 模板 JSON 白名单 |
| 规则引擎判定，LLM 不做最终结论 | LLM 客户端只给对齐 / 辩论材料 |
| 轻量化、非生产部署 | SQLite + JSON；不用 Redis / 图库 / 向量集群 |
| 前端后端自选 | Nuxt 3 独立 + FastAPI 纯 API（不用 Next.js 替换 OCR 流水线） |

---

## 9. 配套清单收口（相对「仅超图三表 / 法规勾稽」那份草稿的修正）

单机一票仿真、最小外部依赖。PaddleOCR 与 FastAPI **同一 Python 进程**。不引入高并发、分布式、账号中间件。

**不要把核心业务写成「OCR + 超图 + 法规勾稽」。** 产品主线是单单相符、单证相符（R-HS-CN / R-HS-DEST）、单货相符；超图只做字段约束；法规走 RAG；**判定只出规则引擎**。OCR 是输入手段。

| 层 | 采用 | 备选（本次不换） |
| --- | --- | --- |
| 前端 | Nuxt 3、Element Plus、Axios、`nuxi generate`；D3 可选可删 | Nuxt UI（要重做三块分区） |
| 后端 | FastAPI、Uvicorn、Pydantic、PaddleOCR、NumPy 余弦 | Flask / Django |
| LLM | OpenAI 兼容客户端**只做对齐**；有密钥才联网，无密钥或失败用预置映射；辩论默认关 | 答辩强制永不联网（更稳，但看不到真对齐） |
| 数据库 | `sqlite3` 读写：业务表（`cases` / `documents` / `photos` / `check_reports` / `risk_items`）+ 超图三表；模板与法规向量仍是本地 JSON | SQLAlchemy；PostgreSQL / pgvector / Milvus |
| 开发中间件 | CORSMiddleware，白名单 3000 两个 origin | 开发机开 Nginx |
| 演示中间件 | 主：Nginx 静态 + `/api` 反代；兜底：FastAPI 挂 Nuxt 静态 | Redis 等禁止清单见 §5.2 |

禁止引入：Redis、Milvus、Pinecone、Qdrant、Neo4j、Kafka、Celery、Clerk、Stripe、Supabase，以及用 Next.js API / Firebase 替换 FastAPI 流水线。

工具不进运行时：GitHub、Bruno / Postman、TablePlus。

`POST /cases/load-demo` 约定见 [@docs/architecture.md](architecture.md) §4.0.1，代码待仓库就绪再写。

---

## 10. 下一步

技术栈与 `load-demo` 约定已可开发。当前工作区仍无 FastAPI / Nuxt 工程。

请指定下一步（只选一项再做）：实现 `backend` 骨架 + `POST /cases/load-demo`；或补其余资源接口字段表；或搭 `frontend` Nuxt 空壳。
