from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings
from app.rag.vector_store import get_vector_store, clear_vector_store
from app.rag.chunking import chunk_text
from app.rag.structure import extract_toc
from app.services.file_service import ensure_storage_dirs
from app.services.file_service import find_uploaded_file
from app.services.text_extraction import extract_text


@dataclass(frozen=True)
class IndexStatus:
    book_id: str
    status: str
    updated_at: str
    total_chars: int | None = None
    total_chunks: int | None = None
    error: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_path(settings: Settings, book_id: str) -> Path:
    return settings.index_status_dir / f"{book_id}.json"


# 读取索引构建状态（不存在则返回 uploaded）
def get_index_status(settings: Settings, book_id: str) -> IndexStatus:
    ensure_storage_dirs(settings)
    p = _status_path(settings, book_id)
    if not p.exists():
        return IndexStatus(book_id=book_id, status="uploaded", updated_at=now_iso())

    data = json.loads(p.read_text("utf-8"))
    return IndexStatus(
        book_id=data.get("book_id", book_id),
        status=data.get("status", "unknown"),
        updated_at=data.get("updated_at", now_iso()),
        total_chars=data.get("total_chars"),
        total_chunks=data.get("total_chunks"),
        error=data.get("error"),
    )


# 更新索引状态并持久化
def update_index_status(settings: Settings, status: IndexStatus) -> None:
    ensure_storage_dirs(settings)
    p = _status_path(settings, status.book_id)
    payload = {
        "book_id": status.book_id,
        "status": status.status,
        "updated_at": status.updated_at,
        "total_chars": status.total_chars,
        "total_chunks": status.total_chunks,
        "error": status.error,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# 构建指定 book_id 的向量索引：抽取→分块→写入 Chroma
def build_book_index(
    settings: Settings,
    *,
    book_id: str,
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> IndexStatus:
    ensure_storage_dirs(settings)
    source_path = find_uploaded_file(settings, book_id)
    if source_path is None:
        status = IndexStatus(book_id=book_id, status="not_found", updated_at=now_iso())
        update_index_status(settings, status)
        return status

    running = IndexStatus(book_id=book_id, status="indexing", updated_at=now_iso())
    update_index_status(settings, running)

    try:
        # 强制重试时先清理旧索引，防止数据残留
        clear_vector_store(settings, book_id=book_id)

        extracted = extract_text(source_path)
        toc = extract_toc(extracted.text)
        chunks = chunk_text(extracted.text, max_chars=max_chars, overlap_chars=overlap_chars)
        vs = get_vector_store(settings, book_id=book_id)

        if toc:
            vs.add_texts(
                texts=[toc],
                metadatas=[{"book_id": book_id, "doc_type": "toc", "source": str(source_path), "file_type": extracted.file_type}],
                ids=[f"{book_id}:toc"],
            )

        texts = [c.text for c in chunks]
        ids = [f"{book_id}:{c.index}" for c in chunks]
        metadatas = [
            {
                "book_id": book_id,
                "chunk_index": c.index,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "section_title": c.section_title,
                "doc_type": "chunk",
                "source": str(source_path),
                "file_type": extracted.file_type,
            }
            for c in chunks
        ]

        if texts:
            vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        done = IndexStatus(
            book_id=book_id,
            status="completed",
            updated_at=now_iso(),
            total_chars=extracted.char_count,
            total_chunks=len(chunks),
        )
        update_index_status(settings, done)
        return done
    except Exception as e:  # noqa: BLE001
        failed = IndexStatus(
            book_id=book_id,
            status="failed",
            updated_at=now_iso(),
            error=str(e),
        )
        update_index_status(settings, failed)
        return failed
