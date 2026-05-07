from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.rag.document_loading import load_documents


_RE_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_RE_TRAILING_SPACES = re.compile(r"[ \t\u3000]+$")
_RE_INLINE_WHITESPACE = re.compile(r"[ \t\u3000]{2,}")


@dataclass(frozen=True)
class ExtractedText:
    file_type: str
    text: str
    char_count: int
    line_count: int


# 统一清洗抽取出的文本：规整换行、去除行尾空白、压缩过多空行
def _clean_text(raw: str) -> str:
    s = raw.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\x00", "")
    s = s.replace("\u00a0", " ")
    lines = []
    for line in s.split("\n"):
        line = _RE_TRAILING_SPACES.sub("", line)
        line = _RE_INLINE_WHITESPACE.sub(" ", line)
        lines.append(line)
    s = "\n".join(lines).strip()
    s = _RE_MULTIPLE_NEWLINES.sub("\n\n", s)
    return s


# 抽取 TXT/PDF 文本并做清洗，返回可用于后续分块与 RAG 的标准化文本
def extract_text(path: Path) -> ExtractedText:
    ext = path.suffix.lower().lstrip(".")
    try:
        docs = load_documents(path)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(str(e)) from e

    raw = "\n\n".join((d.page_content or "") for d in docs)
    cleaned = _clean_text(raw)

    return ExtractedText(
        file_type=ext,
        text=cleaned,
        char_count=len(cleaned),
        line_count=cleaned.count("\n") + 1 if cleaned else 0,
    )
