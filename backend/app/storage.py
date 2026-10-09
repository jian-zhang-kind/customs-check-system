"""把上传文件写到 data/uploads。不识别内容，不调用 OCR。"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.api.errors import require_suffix
from app.config import MAX_UPLOAD_BYTES, REPO_ROOT


async def save_upload(
    upload: UploadFile,
    directory: Path,
    allowed_suffixes: frozenset[str],
) -> tuple[str, str]:
    """返回原始文件名，以及相对仓库根目录的存储路径。"""
    original = Path(upload.filename or "").name
    require_suffix(original, allowed_suffixes)
    suffix = original[original.rfind(".") :].lower()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=400, detail="文件超过 8MB")
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="缺文件")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    relative = destination.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    return original, relative


def remove_stored(relative_path: str) -> None:
    path = (REPO_ROOT / relative_path).resolve()
    if path.is_file() and REPO_ROOT.resolve() in path.parents:
        path.unlink()
