from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    index: int
    start_char: int | None = None
    end_char: int | None = None
    section_title: str | None = None


# 将长文本按中文友好的分隔符切分为多个 chunk，并保留 overlap 便于检索召回
def chunk_text(
    text: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> list[TextChunk]:
    normalized = text.strip()
    if not normalized:
        return []

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing LangChain splitter dependency. Install with: uv sync --group ai") from e

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=overlap_chars,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    parts = splitter.split_text(normalized)

    from app.rag.structure import extract_headings
    from app.rag.structure import find_section_title

    headings = extract_headings(normalized)
    chunks: list[TextChunk] = []
    cursor = 0
    for i, p in enumerate(parts):
        t = p.strip()
        if not t:
            continue
        start = normalized.find(t, max(0, cursor - overlap_chars - 16))
        if start < 0:
            start = cursor
        end = start + len(t)
        cursor = end
        title = find_section_title(headings, start_char=start)
        chunks.append(
            TextChunk(
                chunk_id=str(uuid4()),
                text=t,
                index=i,
                start_char=start,
                end_char=end,
                section_title=title,
            )
        )

    return chunks
