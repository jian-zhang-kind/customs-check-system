# 前端转交说明：关务慧眼

> 给接下 `frontend/` 的人。日期：2026-10-09。  
> 产品是中小外贸企业**申报前自查**演示，不是海关监管系统。  
> 本文只交接前端任务和当前仓库事实，不新增功能、不改已锁定的技术选型。

---

## 1. 你要做的事

在仓库根目录新建独立前端工程 **`frontend/`**，用 Nuxt 3 做竞赛演示页，通过 HTTP 调已有 FastAPI。

当前仓库**没有** `frontend/`。后端代码在 `backend/`，但是骨架：路由已注册，业务没写。你可以按接口契约做页面和请求封装，不要在前端补规则判定。

建议先做这一截，再绑真实数据：

1. Nuxt 3 空壳能在 `http://127.0.0.1:3000` 跑起来。
2. 同一页三个分区：单单相符、单证相符（HS）、单货相符（现场拍照），加上「一键加载演示票」。
3. Axios 基址走环境变量。开发用 `http://127.0.0.1:8000/api`，演示 / 兜底用相对路径 `/api`。
4. 页面能发出 `POST /cases/load-demo`。空请求体即可。成功时响应里有 `case_id`、`case` 和 `report`，票次 `is_demo=true`、状态 `completed`。

后端流水线（OCR、对齐、超图、RAG、规则、报告）实现之前，用 `docs/api.md` 里的示例 JSON 做展示假数据即可。假数据只放前端，不要写进 SQLite，也不要伪造 `verdict` 的计算过程。

---

## 2. 先读这些，冲突时按这个顺序

| 顺序 | 文件 | 前端要拿走的内容 |
| --- | --- | --- |
| 1 | [handoff.md](handoff.md) | 只做 3 个 P0；禁止真实报关单；大模型不得直接出最终判定 |
| 2 | [tech-stack.md](tech-stack.md) §3、§5、§7 | Nuxt 3、Element Plus、Axios；开发不启 Nginx |
| 3 | [architecture.md](architecture.md) §3、§4.8、§10.1 | 三种运行模式、页面职责、文案禁区 |
| 4 | [api.md](api.md) | 路径、字段、枚举、统一响应。前端只打这些资源接口 |
| 5 | [process/flow-diagrams.md](process/flow-diagrams.md) | 业务链路和演示链路两张时序 |

[requirement-spec.md](requirement-spec.md) 里仍有「女裤」字样。演示主票已改为 **锂电池出口越南**，以 [architecture.md](architecture.md) §10.1 和 [api.md](api.md) 的 `battery-vietnam` 为准。

---

## 3. 仓库现在的事实

| 项 | 状态 |
| --- | --- |
| `frontend/` | 不存在 |
| `backend/` | FastAPI 已能启动。启动时按 [sql/schema.sql](sql/schema.sql) 建 `data/app.db` |
| 业务数据 | 票次、单据、照片的创建和查询已落库。上传文件在 `data/uploads/`，库里存相对路径。`ocr_source` / `ocr_fields` 上传后为空 |
| 校验流水线 | `POST /cases/{id}/run` 已用模拟 OCR、超图、法规摘录和规则引擎跑通。报告、风险项、超图快照可以查询。不接 PaddleOCR，不接向量库 |
| 一键演示 | `POST /cases/load-demo` 已可用。它自己建演示票，再走和 `run` 相同的流水线。上传仍然不会自动 `run` |
| 依赖与启动 | 本机用 Python 3.13 在 `backend/.venv` 装过依赖并跑通过骨架检查。默认的 `python` 是 MSYS2，没有 pip，不要用它 |

后端开发启动（在 `backend/` 目录）：

```text
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

开发态 CORS 只放行 `http://127.0.0.1:3000` 和 `http://localhost:3000`。Nuxt 不要改用别的端口，否则浏览器会被跨域拦住。`APP_ENV=development`（默认）才挂 CORS；演示同源时不要依赖 CORS。

OpenAPI 草稿：后端起来之后看 `http://127.0.0.1:8000/docs`。

---

## 4. 技术边界

| 采用 | 不要用 |
| --- | --- |
| Nuxt 3、Element Plus、Axios | Next.js、Nuxt 服务端跑 OCR、原生 App、Uni-app |
| 开发：Nuxt `:3000` + FastAPI `:8000` | 开发机启动 Nginx、Redis、Milvus、Neo4j |
| 竞赛：`nuxi generate` 出静态文件，由 Nginx 托管；`/api` 反代到 FastAPI | 把 SSR 接到 FastAPI；用 Next.js API / Supabase 替换后端 |
| 勾稽默认用 Element Plus 表格 | 手机拍照区画 D3 / WebGL 关系网 |
| D3 可选，只在电脑端画**当前这一票**的字段超图 | 画企业、团伙、股权关系 |

前端不调用 `backend/app/modules/` 里的 Python 模块。那些文件只是后端占位。

---

## 5. 页面怎么做

一个演示页，三个分区同时能看见，外加一键仿真。详情要是单独路由，API 不负责跳转：用返回的 `case_id` 自己打开该票。

| 分区 | 谁在用 | 页面做什么 |
| --- | --- | --- |
| 单单相符 | 电脑端关务 / 单证 | 上传报关单、增值税发票、装箱单、出口合同，再手动触发校验 |
| 单证相符 | 同上 | 展示规则引擎写出的 **R-HS-CN**、**R-HS-DEST** 两条结论，带法规名称、发布日期、原文摘录、来源链接 |
| 单货相符 | 手机浏览器 | 拍照或选图（唛头 / 现场箱单）。只提示唛头、批号、件数。不画力导向图 |

文案只写「申报前自查」。不要出现「监管」「团伙」「企业画像」「立案」「企业黑名单」。

页脚使用服务端同一句免责声明：

> 本系统为竞赛演示工具，输出不构成法律意见或正式归类裁定。

锂电池演示票上要写明：**不做出口管制筛查，不给出运 / 危化鉴定**，只做 HS 归类依据、单证勾稽和唛头核对。

不要做独立问答框，不要做登录、支付，不要对接单一窗口申报。

---

## 6. 对接接口

所有路径相对 `/api`。JSON 用 `application/json`，上传用 `multipart/form-data`。没有 401/403。

成功：HTTP 200，`code = 0`。失败：HTTP 400 / 404 / 500，`code` 与状态码相同，`data` 为 `null` 或 `{ "detail": "..." }`。票次、单据、照片、`run`、`load-demo`、报告、风险项和超图都已返回 200。未知 `demo_type` 返回 400。

列表字段名是 **`list`**，另有 `total`、`page`、`page_size`。查询默认 `page=1`、`page_size=20`，最大 100。

[api.md](api.md) 示例里的 `c_001`、`e_qty` 是示意。SQLite 主键是整数，Pydantic 出参里的 `id` / `case_id` / `node_id` / `edge_id` 按**数字**接。不要在前端把它们改成 `c_` 前缀再回传。

`verdict` 只有 `pass` / `warning` / `fail`，只能展示，不能提供修改入口。`insufficient_evidence` 是风险项的 `rule_outcome`，不是票次状态。票次状态只有 `pending` / `running` / `completed` / `failed`。`completed` 只表示流水线跑完，不表示单证全部相符。

### 6.1 演示路径（一键）

`POST /cases/load-demo`

```json
{ "demo_type": "battery-vietnam" }
```

`demo_type` 可省略、`null` 或 `""`，后端约定都当成 `battery-vietnam`。其它字符串是 400。请求体不要带真实报关单字段。

成功时响应里有 `case_id`、`case`、`report`。前端自己进入该票。这个接口**不会**走 `POST /cases`。

### 6.2 业务路径（手工）

1. `POST /cases` 建空票。必填 `case_no`。成功后应是 `status=pending`、`is_demo=false`，此时没有报告。
2. `POST /cases/{case_id}/documents` 上传单据。表单字段：`doc_type`（`declaration` / `invoice` / `packing` / `contract`）、`file`（pdf / png / jpg）。
3. `POST /cases/{case_id}/photos` 上传现场照片。表单字段：`kind`（`mark` / `packing`）、`file`（png / jpg）。
4. 上传**不会**自动校验。用户再点一次，才 `POST /cases/{id}/run`。请求体可空，或 `{ "force": true }` 用来重跑已完成的票。
5. 看结果：`GET /cases/{case_id}/report`、`GET /cases/{case_id}/risk-items`。超图只读：`GET /cases/{id}/hypergraph`。未跑过流水线时，票还在的话超图应是空数组，不是 404。

### 6.3 其余只读接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/cases` | 分页列表，可筛 `is_demo`、`status` |
| GET | `/cases/{id}` | 只有票次一行，不含单据和报告 |
| GET | `/cases/{case_id}/documents` | 单据列表，可筛 `doc_type` |
| GET | `/documents/{id}` | 单据详情，含 `ocr_fields`，不回文件二进制 |
| GET | `/cases/{case_id}/photos` | 照片列表，可筛 `kind` |
| GET | `/photos/{id}` | 照片详情 |
| GET | `/cases/{case_id}/risk-items` | 风险明细，可筛 `rule_id`、`verdict` |

没有这些接口，前端不要自己发明：超图的增删改、`PATCH` 判定、`/chat`、登录注册、支付、出口管制、危化鉴定。

报告里的法规链接、名称、日期、摘录来自接口字段。接口没给 `source_url` 时留空，不要填示例域名或编一条法规。

---

## 7. 展示时不要弄错的几件事

- 风险档映射只用于理解后端结果：`matched` → `pass`，`conflict` → `fail`，`hard` 和 `insufficient_evidence` → `warning`。前端不要再算一遍当结论。
- HS 必须分成中国（R-HS-CN）和目的国（R-HS-DEST）两条，不要合成一句总判定。
- 目的国为空时，R-HS-DEST 可以是 `insufficient_evidence`，票次仍可以是 `completed`。
- 超图快照没有 `verdict`。对错只在 `risk_items`。数量勾稽是同一条超边上的字段，不是企业连线。
- `ocr_source` 为 `fixture` 时要显示抽取来源，不要假装已经跑了 PaddleOCR。
- 辩论默认关闭。没有 `debate_triggered=true` 时不要画辩论面板。即便以后打开，辩论意见也不是最终判定。

---

## 8. 明确不用你做

- 不改 `backend/` 的业务实现，不接 PaddleOCR，不写规则引擎。
- 不新建用户、订单、聊天、支付模块。
- 不引入真实企业报关单、海关内部材料。
- 不做生产部署、Docker、K8s。Nginx 只在竞赛演示时才需要，开发阶段不要配。
