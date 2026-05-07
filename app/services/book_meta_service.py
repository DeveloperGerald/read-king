from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings
from app.services.file_service import ensure_storage_dirs


@dataclass(frozen=True)
class BookMeta:
    book_id: str
    title: str | None = None
    author: str | None = None
    created_at: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta_path(settings: Settings, book_id: str) -> Path:
    return settings.book_meta_dir / f"{book_id}.json"


# 保存上传时的书籍基础信息（title/author），供后续外部检索与报告生成使用
def save_book_meta(settings: Settings, *, book_id: str, title: str | None, author: str | None) -> BookMeta:
    ensure_storage_dirs(settings)
    meta = {
        "book_id": book_id,
        "title": title.strip() if isinstance(title, str) and title.strip() else None,
        "author": author.strip() if isinstance(author, str) and author.strip() else None,
        "created_at": _now_iso(),
    }
    p = _meta_path(settings, book_id)
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return BookMeta(**meta)


# 读取书籍基础信息（如不存在则返回空）
def get_book_meta(settings: Settings, book_id: str) -> BookMeta:
    ensure_storage_dirs(settings)
    p = _meta_path(settings, book_id)
    if not p.exists():
        return BookMeta(book_id=book_id)
    data = json.loads(p.read_text("utf-8"))
    return BookMeta(
        book_id=data.get("book_id", book_id),
        title=data.get("title"),
        author=data.get("author"),
        created_at=data.get("created_at"),
    )

