from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings


ALLOWED_EXTENSIONS = {".pdf", ".txt"}


# 确保本地数据目录存在（上传目录、向量库持久化目录等）
def ensure_storage_dirs(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.index_status_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    settings.report_status_dir.mkdir(parents=True, exist_ok=True)
    settings.book_meta_dir.mkdir(parents=True, exist_ok=True)
    settings.external_meta_dir.mkdir(parents=True, exist_ok=True)


# 保存上传文件到本地 uploads 目录，并返回 book_id 与文件落盘路径
def save_upload_file(settings: Settings, upload: UploadFile) -> tuple[str, str, Path]:
    if not upload.filename:
        raise ValueError("filename is required")

    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext}")

    book_id = str(uuid4())
    stored_filename = f"{book_id}{ext}"
    stored_path = (settings.upload_dir / stored_filename).resolve()

    ensure_storage_dirs(settings)

    with stored_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)

    return book_id, stored_filename, stored_path


# 根据 book_id 在 uploads 目录中查找对应的已上传文件
def find_uploaded_file(settings: Settings, book_id: str) -> Path | None:
    ensure_storage_dirs(settings)
    candidates = sorted(settings.upload_dir.glob(f"{book_id}.*"))
    if not candidates:
        return None
    return candidates[0]
