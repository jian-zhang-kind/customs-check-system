"""占位错误与上传后缀校验。正式业务错误码仍只有 400 / 404 / 500。"""

from __future__ import annotations

import logging
from typing import NoReturn

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")

DOC_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg"})
PHOTO_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})


def not_implemented(action: str) -> NoReturn:
    """骨架占位。501 不是业务错误码，对应路由实现后应删除。"""
    raise HTTPException(status_code=501, detail=f"{action} 尚未实现")


def require_suffix(filename: str | None, allowed: frozenset[str]) -> None:
    if not filename:
        raise HTTPException(status_code=400, detail="缺文件或类型不支持")
    dot = filename.rfind(".")
    if dot < 0:
        raise HTTPException(status_code=400, detail="类型不支持")
    suffix = filename[dot:].lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="类型不支持")


def error_body(code: int, message: str) -> dict[str, object]:
    return {"code": code, "message": message, "data": {"detail": message}}


def register_exception_handlers(app: FastAPI) -> None:
    # 注册在 Starlette 基类上，404/405 和业务里抛出的 HTTPException 才会走同一套响应。
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


async def _http_exception_handler(_request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=500, content=error_body(500, "服务错误"))
    detail = exc.detail
    message = detail if isinstance(detail, str) else "请求错误"
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.status_code, message))


async def _validation_exception_handler(_request, exc: Exception) -> JSONResponse:
    message = "参数错误"
    if isinstance(exc, RequestValidationError):
        parts: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(item) for item in err.get("loc", []) if item != "body")
            text = err.get("msg", "参数错误")
            parts.append(f"{loc}: {text}" if loc else str(text))
        if parts:
            message = "; ".join(parts)
    return JSONResponse(status_code=400, content=error_body(400, message))


async def _unhandled_exception_handler(_request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常", exc_info=exc)
    return JSONResponse(status_code=500, content=error_body(500, "服务错误"))
