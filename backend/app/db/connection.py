"""sqlite3 连接。每次取出的连接都打开外键。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from app.config import DB_PATH


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 上传接口是异步的，同步依赖创建的连接会在另一个线程里使用。
    # 每个请求独占一条连接，请求内不会并发访问它。
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """请求级连接。正常结束时提交，异常时回滚。"""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
