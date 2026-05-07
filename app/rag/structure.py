from __future__ import annotations

import re
from bisect import bisect_right


_RE_TOC_TITLE = {"目录", "內容", "contents", "content"}

_RE_HEADING = re.compile(r"^(\s*)(第[0-9一二三四五六七八九十百千]+[章节回幕篇节])\s*(.*)$")

_RE_NUMBERED = re.compile(r"^\s*(\d{1,2})\s*[\.、]\s*(.+)$")


# 判断一行文本是否像“标题/章节”
def is_heading_like(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if _RE_HEADING.match(t):
        return True
    if _RE_NUMBERED.match(t):
        return True
    if t.startswith("第") and ("章" in t or "篇" in t or "节" in t):
        return True
    return False


# 判断一行末尾是否像页码（用于目录片段识别）
def looks_like_page_suffix(line: str) -> bool:
    t = line.strip().rstrip(".·…")
    if not t:
        return False
    tail = t.split()[-1]
    return tail.isdigit() and 1 <= len(tail) <= 4


# 从全文中尽量提取“目录/章节结构”片段，用于给 LLM 与检索提供结构线索
def extract_toc(text: str, *, max_chars: int = 2000) -> str | None:
    s = (text or "").strip()
    if not s:
        return None

    lines = s.split("\n")

    explicit_start = None
    for i, line in enumerate(lines[:800]):
        t = line.strip()
        if t.lower() in _RE_TOC_TITLE:
            explicit_start = i
            break

    scan_upto = min(len(lines), 2000)

    def score_line(line: str) -> int:
        t = line.strip()
        if not t:
            return 0
        score = 0
        if is_heading_like(t):
            score += 2
        if looks_like_page_suffix(t):
            score += 1
        if len(t) > 60:
            score -= 1
        return score

    window = 120
    best = None
    best_score = -1
    start_candidates = [explicit_start] if explicit_start is not None else []
    if not start_candidates:
        start_candidates = list(range(0, max(0, scan_upto - window), 20))

    for start in start_candidates:
        if start is None:
            continue
        end = min(scan_upto, start + window)
        scores = [score_line(ln) for ln in lines[start:end]]
        total = sum(scores)
        heading_hits = sum(1 for sc in scores if sc >= 2)
        if heading_hits < 6:
            continue
        if total > best_score:
            best_score = total
            best = (start, end)

    if best is None:
        return None

    start, end = best
    buf: list[str] = []
    empty_run = 0
    for line in lines[start:end]:
        t = line.rstrip()
        if not t.strip():
            empty_run += 1
        else:
            empty_run = 0
        buf.append(t)
        if empty_run >= 6:
            break
        if sum(len(x) + 1 for x in buf) >= max_chars:
            break

    toc = "\n".join(buf).strip()
    return toc[:max_chars] if toc else None


# 扫描全文提取 (start_char, title)：不依赖“前 N 行”的假设，能覆盖尾部章节标题
def extract_headings(text: str) -> list[tuple[int, str]]:
    s = text or ""
    if not s:
        return []

    headings: list[tuple[int, str]] = []

    for m in re.finditer(r"(?m)^.*$", s):
        line = m.group(0)
        t = line.strip()
        if not t:
            continue

        mh = _RE_HEADING.match(t)
        if mh:
            title = (mh.group(2) + mh.group(3)).strip() if mh.group(3) else mh.group(2).strip()
            headings.append((m.start(), title))
            continue

        mn = _RE_NUMBERED.match(t)
        if mn:
            headings.append((m.start(), t))

    return headings


# 根据 chunk 起始位置查找最近的上一条标题
def find_section_title(headings: list[tuple[int, str]], *, start_char: int) -> str | None:
    if not headings:
        return None
    starts = [h[0] for h in headings]
    idx = bisect_right(starts, start_char) - 1
    if idx < 0:
        return None
    return headings[idx][1]
