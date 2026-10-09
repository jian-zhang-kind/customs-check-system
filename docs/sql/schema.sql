-- 关务慧眼 SQLite schema（sqlite3 原生语法）
-- 依据：docs/api.md、docs/tech-stack.md
-- 仅建表与索引，不含业务逻辑、不含 ORM。
-- 连接后必须：PRAGMA foreign_keys = ON;
--
-- 建表顺序：先 cases/documents/photos，再超图三表，再 check_reports/risk_items
-- （risk_items.edge_id 引用 hyperedges.id）
-- JSON 字段用 TEXT 存序列化字符串（ocr_fields、evidence）。

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. cases 票次
-- ---------------------------------------------------------------------------
CREATE TABLE cases (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    case_no              TEXT    NOT NULL,
    title                TEXT,
    remark               TEXT,
    status               TEXT    NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    is_demo              INTEGER NOT NULL DEFAULT 0
                             CHECK (is_demo IN (0, 1)),
    demo_type            TEXT,
    destination_country  TEXT,
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    UNIQUE (case_no)
);

-- GET /cases?status=&is_demo= 列表筛选
CREATE INDEX idx_cases_status ON cases (status);
CREATE INDEX idx_cases_is_demo ON cases (is_demo);

-- ---------------------------------------------------------------------------
-- 2. documents 单据（业务上传 / 演示种子）
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER NOT NULL,
    doc_type      TEXT    NOT NULL
                      CHECK (doc_type IN ('declaration', 'invoice', 'packing', 'contract')),
    filename      TEXT    NOT NULL,
    storage_path  TEXT    NOT NULL,
    ocr_source    TEXT    CHECK (ocr_source IS NULL OR ocr_source IN ('paddle', 'fixture')),
    ocr_fields    TEXT,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
);

-- GET /cases/{id}/documents
CREATE INDEX idx_documents_case_id ON documents (case_id);

-- ---------------------------------------------------------------------------
-- 3. photos 现场照片
-- ---------------------------------------------------------------------------
CREATE TABLE photos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER NOT NULL,
    kind          TEXT    NOT NULL
                      CHECK (kind IN ('mark', 'packing')),
    filename      TEXT    NOT NULL,
    storage_path  TEXT    NOT NULL,
    ocr_source    TEXT    CHECK (ocr_source IS NULL OR ocr_source IN ('paddle', 'fixture')),
    ocr_fields    TEXT,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
);

-- GET /cases/{id}/photos
CREATE INDEX idx_photos_case_id ON photos (case_id);

-- ---------------------------------------------------------------------------
-- 4-6. 超图实例（随 Pipeline 落库；禁止业务 CRUD；只读 GET /cases/{id}/hypergraph）
-- 须建在 risk_items 之前，因 edge_id 外键。
-- ---------------------------------------------------------------------------
CREATE TABLE field_nodes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER NOT NULL,
    document_id   INTEGER,
    field_name    TEXT    NOT NULL,
    field_value   TEXT,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE SET NULL
);

CREATE INDEX idx_field_nodes_case_id ON field_nodes (case_id);

CREATE TABLE hyperedges (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id           INTEGER NOT NULL,
    constraint_type   TEXT    NOT NULL,
    rule_id           TEXT    NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
);

CREATE INDEX idx_hyperedges_case_id ON hyperedges (case_id);

CREATE TABLE hyperedge_members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL,
    edge_id    INTEGER NOT NULL,
    node_id    INTEGER NOT NULL,
    slot_name  TEXT    NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
    FOREIGN KEY (edge_id) REFERENCES hyperedges (id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES field_nodes (id) ON DELETE CASCADE
);

CREATE INDEX idx_hyperedge_members_edge_id ON hyperedge_members (edge_id);
CREATE INDEX idx_hyperedge_members_case_id ON hyperedge_members (case_id);

-- ---------------------------------------------------------------------------
-- 7. check_reports 报告头（每次 run 覆盖：一票一行）
-- ---------------------------------------------------------------------------
CREATE TABLE check_reports (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id           INTEGER NOT NULL,
    status            TEXT    NOT NULL
                          CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    summary_verdict   TEXT    CHECK (summary_verdict IS NULL
                          OR summary_verdict IN ('pass', 'warning', 'fail')),
    debate_triggered  INTEGER NOT NULL DEFAULT 0
                          CHECK (debate_triggered IN (0, 1)),
    created_at        TEXT    NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
    UNIQUE (case_id)
);

-- UNIQUE(case_id) 已覆盖 GET /cases/{id}/report，不再单独建 case_id 索引。

-- ---------------------------------------------------------------------------
-- 8. risk_items 风险明细（仅规则引擎写入；无 PATCH）
-- ---------------------------------------------------------------------------
CREATE TABLE risk_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id           INTEGER NOT NULL,
    report_id         INTEGER NOT NULL,
    rule_id           TEXT    NOT NULL,
    verdict           TEXT    NOT NULL
                          CHECK (verdict IN ('pass', 'warning', 'fail')),
    rule_outcome      TEXT    NOT NULL
                          CHECK (rule_outcome IN (
                              'matched', 'conflict', 'hard', 'insufficient_evidence'
                          )),
    risk_level        TEXT,
    description       TEXT,
    evidence          TEXT,
    edge_id           INTEGER,
    chunk_id          TEXT,
    jurisdiction      TEXT    CHECK (jurisdiction IS NULL OR jurisdiction IN ('CN', 'VN')),
    regulation_name   TEXT,
    publish_date      TEXT,
    source_url        TEXT,
    excerpt           TEXT,
    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES check_reports (id) ON DELETE CASCADE,
    FOREIGN KEY (edge_id) REFERENCES hyperedges (id) ON DELETE SET NULL
);

CREATE INDEX idx_risk_items_case_id ON risk_items (case_id);
CREATE INDEX idx_risk_items_case_rule ON risk_items (case_id, rule_id);

-- ---------------------------------------------------------------------------
-- 索引建议（场景 / 为何不建更多）
-- ---------------------------------------------------------------------------
-- 已建：
--   idx_cases_status / idx_cases_is_demo
--     场景：GET /cases 按状态、是否演示票筛选。
--   idx_documents_case_id / idx_photos_case_id
--     场景：按票列单据、照片。SQLite 不为 FK 自动建索引。
--   check_reports UNIQUE(case_id)
--     场景：一票一份当前报告；兼作 GET report 查找。
--   idx_risk_items_case_id / idx_risk_items_case_rule
--     场景：报告明细、按 R-HS-CN 等 rule_id 过滤。
--   idx_field_nodes_case_id / idx_hyperedges_case_id
--   idx_hyperedge_members_case_id / idx_hyperedge_members_edge_id
--     场景：GET /cases/{id}/hypergraph；run 时按票删除重建。
-- 不建：
--   case_no 已有 UNIQUE，不必再索引。
--   title / remark / excerpt / source_url / ocr_fields 不走等值查询。
--   created_at：演示数据量小，按 id 倒序即可。
--   documents(doc_type)、photos(kind)：一票最多数行，前缀 case_id 足够。
--   risk_items(report_id)：一票一报告，case_id 已覆盖。
--   node_id 单列：成员查询以 edge_id 为主。
