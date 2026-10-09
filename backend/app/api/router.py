"""汇总 /api 路由。没有聊天、登录、支付，也没有超图写入。"""

from fastapi import APIRouter

from app.api import cases, documents, photos, reports

api_router = APIRouter()
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(photos.router)
api_router.include_router(reports.router)
