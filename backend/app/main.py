"""FastAPI 入口。

开发启动（在 backend/ 目录）::

    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.config import API_PREFIX, CORS_ORIGINS, cors_enabled
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="关务慧眼",
    summary="出口货物海关申报自查系统 API",
    description=(
        "纯 API 骨架：路由占位，启动时按 docs/sql/schema.sql 建库。"
        "不执行 OCR、对齐、超图、RAG、规则引擎或辩论，不写入 verdict。"
        "成功响应为 code=0；失败时 code 与 HTTP 状态码相同。"
        "占位路由返回 HTTP 501，该状态只表示尚未实现，不是业务错误码。"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

if cors_enabled():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(CORS_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=API_PREFIX)
