from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import Settings
from app.services.file_service import ensure_storage_dirs


@dataclass(frozen=True)
class ExternalBookInfo:
    title: str | None
    author: str | None
    description: str | None
    tavily_answer: str | None
    tavily_results: list[dict]
    sources: list[str]
    fetched_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_path(settings: Settings, book_id: str) -> Path:
    return settings.external_meta_dir / f"{book_id}.json"


def _is_cache_fresh(data: dict, *, ttl_hours: int) -> bool:
    try:
        fetched_at = datetime.fromisoformat(data.get("fetched_at"))
    except Exception:
        return False
    return fetched_at >= datetime.now(timezone.utc) - timedelta(hours=ttl_hours)


def _safe_str(v) -> str | None:
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _tavily_search(*, api_key: str, query: str, max_results: int, topic: str) -> dict | None:
    try:
        from langchain_tavily import TavilySearch
    except Exception:
        return None

    os.environ["TAVILY_API_KEY"] = api_key
    tool = TavilySearch(max_results=max_results, topic=topic, include_answer=True)
    try:
        return tool.invoke({"query": query})
    except Exception:
        return None


# 获取外部书籍信息（默认使用免费接口 Open Library + Wikipedia，并带本地缓存）
def get_external_book_info(
    settings: Settings,
    *,
    book_id: str,
    title: str | None,
    author: str | None,
    ttl_hours: int = 72,
) -> ExternalBookInfo:
    ensure_storage_dirs(settings)

    p = _cache_path(settings, book_id)
    if p.exists():
        data = json.loads(p.read_text("utf-8"))
        if _is_cache_fresh(data, ttl_hours=ttl_hours):
            return ExternalBookInfo(
                title=data.get("title"),
                author=data.get("author"),
                description=data.get("description"),
                tavily_answer=data.get("tavily_answer"),
                tavily_results=list(data.get("tavily_results") or []),
                sources=list(data.get("sources") or []),
                fetched_at=data.get("fetched_at") or _now_iso(),
            )

    t = _safe_str(title)
    a = _safe_str(author)
    sources: list[str] = []
    description: str | None = None
    tavily_answer: str | None = None
    tavily_results: list[dict] = []

    if t:
        if settings.tavily_api_key:
            q = " ".join(x for x in [t, a, "简介", "作者", "书评", "背景"] if x)
            raw = _tavily_search(
                api_key=settings.tavily_api_key,
                query=q,
                max_results=int(settings.tavily_max_results),
                topic=str(settings.tavily_topic),
            )
            if isinstance(raw, dict):
                tavily_answer = _safe_str(raw.get("answer"))
                tavily_results = list(raw.get("results") or [])[: int(settings.tavily_max_results)]
                if tavily_answer or tavily_results:
                    sources.append("tavily")
                if not description and tavily_answer:
                    description = tavily_answer

    info = ExternalBookInfo(
        title=t,
        author=a,
        description=description,
        tavily_answer=tavily_answer,
        tavily_results=tavily_results,
        sources=sources,
        fetched_at=_now_iso(),
    )

    payload = {
        "title": info.title,
        "author": info.author,
        "description": info.description,
        "tavily_answer": info.tavily_answer,
        "tavily_results": info.tavily_results,
        "sources": info.sources,
        "fetched_at": info.fetched_at,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return info
