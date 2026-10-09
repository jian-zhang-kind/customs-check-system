"""运行配置。只放路径、端口和开发态 CORS，不放业务开关实现。"""

from __future__ import annotations

import os
from pathlib import Path

# backend/app/config.py -> 仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

API_PREFIX = "/api"
HOST = "127.0.0.1"
PORT = 8000

# tech-stack：业务库放仓库 data/app.db，不用 SQLAlchemy。
DB_PATH = REPO_ROOT / "data" / "app.db"
SCHEMA_PATH = REPO_ROOT / "docs" / "sql" / "schema.sql"
OCR_FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "ocr_simulation.json"
TEMPLATE_PATH = REPO_ROOT / "data" / "hypergraph" / "constraint_templates.json"
CHUNK_PATH = REPO_ROOT / "data" / "knowledge" / "hs_tariff_chunks.json"

# 上传文件。库里只存相对仓库根目录的路径。
DOCUMENT_UPLOAD_DIR = REPO_ROOT / "data" / "uploads" / "documents"
PHOTO_UPLOAD_DIR = REPO_ROOT / "data" / "uploads" / "photos"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# 仅开发调试白名单。禁止 allow_origins=["*"] 且 allow_credentials=True。
CORS_ORIGINS = (
    "http://127.0.0.1:3000",
    "http://localhost:3000",
)

# development：Nuxt :3000 + CORS。demo / fallback 同源，不挂 CORS。
APP_ENV = os.getenv("APP_ENV", "development")

# 辩论默认关闭。骨架不读取该值去调用模型。
DEBATE_ENABLED = False


def cors_enabled() -> bool:
    return APP_ENV == "development"
