"""接口时间戳。统一用 UTC，秒级，形如 2026-01-01T00:00:00Z。"""

from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
