from __future__ import annotations

import json
import re
from typing import Any
from typing import Literal
from typing import TypedDict

from app.core.config import Settings
from app.services.file_service import find_uploaded_file
from app.services.text_extraction import extract_text
from app.rag.chunking import chunk_text
from app.rag.structure import extract_toc
from app.services.book_meta_service import get_book_meta
from app.services.external_info_service import get_external_book_info


# 系统提示词：定义角色、输出格式与约束
SYSTEM_PROMPT = "\n".join(
    [
        "你是一位擅长中文写作与结构化表达的读书笔记作者。",
        "你的任务是根据书籍内容与用户输入生成一份高质量读书报告。",
        "输出格式：Markdown。",
        "约束：",
        "- 不要杜撰书中未出现的事实；必要时使用‘书中提到/作者指出’等措辞。",
        "- 尽量贴近原文关键片段（允许适度改写以保证连贯）。",
        "- 语言为中文，结构清晰，条理分明。",
    ]
)


# 从 Tavily 搜索结果中挑选更像“书评/读后感/长评”的条目，并返回简短摘录
def _pick_review_snippets(results: list[dict], *, max_items: int = 3) -> list[dict]:
    def score_item(item: dict) -> int:
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        content = str(item.get("content") or "")

        hay = " ".join([title, url, content]).lower()
        score = 0
        for kw in ["书评", "读后感", "长评", "review", "book review", "书摘"]:
            if kw in hay:
                score += 3
        for kw in ["豆瓣", "douban", "goodreads", "medium", "notion", "知乎", "zhihu"]:
            if kw in hay:
                score += 2
        if "pdf" in hay:
            score -= 2
        if len(content.strip()) >= 120:
            score += 1
        return score

    ranked = sorted(results or [], key=score_item, reverse=True)
    picked: list[dict] = []
    seen_urls: set[str] = set()
    for item in ranked:
        url = str(item.get("url") or "").strip()
        if url and url in seen_urls:
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if not content and not title:
            continue
        snippet = content[:320]
        picked.append({"title": title, "url": url, "snippet": snippet})
        if url:
            seen_urls.add(url)
        if len(picked) >= max_items:
            break
    return picked


# 从检索结果中做“章节覆盖率控制”：同一章节最多保留 N 条，避免片段集中在同一章
def _select_snippets_with_coverage(
    items: list[tuple[str, dict[str, Any]]],
    *,
    max_total: int,
    per_section_max: int,
) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    per_section: dict[str, int] = {}
    used_texts: set[str] = set()

    for text, md in items:
        t = (text or "").strip()
        if not t or t in used_texts:
            continue

        section = str(md.get("section_title") or "").strip()
        key = section if section else "__no_section__"
        if per_section.get(key, 0) >= per_section_max:
            continue

        used_texts.add(t)
        per_section[key] = per_section.get(key, 0) + 1
        selected.append((t, md))
        if len(selected) >= max_total:
            break

    return selected


# 基于用户输入与通用任务模板生成检索 query 列表（尽量覆盖“结构/观点/方法/案例/误区”）
def _build_retrieval_queries(*, requirements: str, feelings: str, toc: str | None) -> list[str]:
    queries: list[str] = []
    if requirements:
        queries.append(requirements)
    if feelings:
        queries.append(feelings)

    queries += [
        "这本书的核心观点/主旨/要点是什么？",
        "作者的论证结构与关键论据有哪些？",
        "书中给出的关键方法/框架/步骤是什么？",
        "书中提到的典型例子/案例是什么？",
        "本书的章节结构与主线脉络是什么？",
        "作者指出的常见误区/反例/注意事项是什么？",
    ]

    if toc:
        toc_lines = [ln.strip() for ln in toc.split("\n") if ln.strip()]
        heading_like = []
        for ln in toc_lines:
            if ln.startswith("第") and ("章" in ln or "篇" in ln):
                heading_like.append(ln)
            if len(heading_like) >= 10:
                break

        # 这里取 10 是为了控制 prompt 体积：章节级 query 的边际收益在 8~12 左右趋于饱和
        # 如果后续想更稳，可以把这个数做成配置项，并按可用 token 动态调整
        for h in heading_like[:10]:
            queries.append(f"{h} 讲了什么？")
            queries.append(f"与 {h} 相关的关键观点/结论/方法是什么？")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        qn = q.strip()
        if not qn or qn in seen:
            continue
        seen.add(qn)
        out.append(qn)
    return out


class ReportState(TypedDict, total=False):
    book_id: str
    status: str
    error: str
    extracted_text: str
    context: str
    external_info: str
    user_requirements: str
    user_feelings: str
    prompt: str
    outline_markdown: str
    outline_json: dict[str, Any]
    workflow_mode: str


def _extract_json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    s = (text or "").strip()
    if not s:
        return None, "empty"

    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    if m:
        s = m.group(1).strip()

    try:
        obj = json.loads(s)
    except Exception as e:  # noqa: BLE001
        return None, f"json parse error: {e}"

    if not isinstance(obj, dict):
        return None, "json root is not object"
    return obj, None


def _validate_outline_json(obj: dict[str, Any]) -> str | None:
    if not isinstance(obj.get("title"), str) or not obj["title"].strip():
        return "missing title"
    sections = obj.get("sections")
    if not isinstance(sections, list) or not sections:
        return "missing sections"

    for si, sec in enumerate(sections):
        if not isinstance(sec, dict):
            return f"sections[{si}] not object"
        heading = sec.get("heading")
        if not isinstance(heading, str) or not heading.strip():
            return f"sections[{si}].heading missing"
        bullets = sec.get("bullets")
        if not isinstance(bullets, list) or not bullets:
            return f"sections[{si}].bullets missing"
        if len(bullets) > 12:
            return f"sections[{si}].bullets too many"
        for bi, b in enumerate(bullets):
            if isinstance(b, str):
                t = b.strip()
                if not t:
                    return f"sections[{si}].bullets[{bi}] empty"
                if len(t) > 60:
                    return f"sections[{si}].bullets[{bi}] too long"
                continue

            if isinstance(b, dict):
                text = b.get("text")
                if not isinstance(text, str) or not text.strip():
                    return f"sections[{si}].bullets[{bi}].text missing"
                if len(text.strip()) > 60:
                    return f"sections[{si}].bullets[{bi}].text too long"
                continue

            return f"sections[{si}].bullets[{bi}] invalid"
    return None


def _outline_json_to_markdown(obj: dict[str, Any]) -> str:
    title = str(obj.get("title") or "").strip() or "读书报告大纲"
    sections = obj.get("sections") or []
    lines: list[str] = [f"## {title}"]
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading") or "").strip()
        if heading:
            lines.append("")
            lines.append(f"### {heading}")
        bullets = sec.get("bullets") or []
        for b in bullets:
            if isinstance(b, str):
                t = b.strip()
                if t:
                    lines.append(f"- {t}")
                continue

            if isinstance(b, dict):
                text = str(b.get("text") or "").strip()
                if text:
                    lines.append(f"- {text}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def expand_report_from_prompt(
    *,
    settings: Settings,
    prompt: str,
    outline_markdown: str,
    outline_json: dict[str, Any] | None = None,
    max_attempts: int = 3,
) -> str:
    if not (prompt or "").strip():
        raise ValueError("missing prompt")
    if not (outline_markdown or "").strip():
        raise ValueError("missing outline_markdown")

    try:
        from langchain_core.messages import HumanMessage
        from langchain_core.messages import SystemMessage
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing LangChain dependency. Install with: uv sync --group ai") from e

    from app.llm.chat_model import get_chat_model

    model = get_chat_model(settings)
    outline_payload = outline_markdown
    if isinstance(outline_json, dict) and outline_json:
        outline_payload = json.dumps(outline_json, ensure_ascii=False)

    base = "\n\n".join(
        [
            prompt,
            "生成要求：按大纲扩写为完整读书报告（Markdown）。",
            "- 按下面大纲逐节扩写，保证结构清晰。",
            "- 不要引入未在片段/外部信息中出现的新事实。",
            "大纲：",
            outline_payload,
        ]
    )

    last_err: str | None = None
    for _ in range(max(1, int(max_attempts))):
        extra = ""
        if last_err:
            extra = "\n\n".join(["上一次输出为空或无效：", last_err, "请重新生成完整 Markdown 正文。"])
        msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=base + ("\n\n" + extra if extra else ""))]
        out = model.invoke(msgs)
        content = getattr(out, "content", None)
        if not isinstance(content, str) or not content.strip():
            last_err = "empty model output"
            continue
        return content

    raise RuntimeError(last_err or "empty model output")


# 组装生成用 prompt（复用在工作流与调试接口中）
def build_prompt_preview(
    *,
    settings: Settings,
    book_id: str,
    user_requirements: str | None = None,
    user_feelings: str | None = None,
) -> dict[str, str]:
    path = find_uploaded_file(settings, book_id)
    if path is None:
        raise RuntimeError("book not found")

    extracted = extract_text(path)
    context = build_context(
        settings=settings,
        book_id=book_id,
        extracted_text=extracted.text,
        user_requirements=user_requirements,
        user_feelings=user_feelings,
    )

    meta = get_book_meta(settings, book_id)
    info = get_external_book_info(settings, book_id=book_id, title=meta.title, author=meta.author)
    parts: list[str] = []
    if info.title:
        parts.append(f"书名：{info.title}")
    if info.author:
        parts.append(f"作者：{info.author}")
    if info.description:
        parts.append("简介（Tavily）：")
        parts.append(info.description)
    if info.tavily_answer:
        parts.append("补充（Tavily Answer）：")
        parts.append(info.tavily_answer)
    if info.tavily_results:
        reviews = _pick_review_snippets(info.tavily_results, max_items=3)
        if reviews:
            parts.append("优质书评（Tavily 结果节选）：")
            for r in reviews:
                title = r.get("title") or ""
                url = r.get("url") or ""
                snippet = (r.get("snippet") or "").strip()
                line = f"- {title}"
                if url:
                    line += f" ({url})"
                parts.append(line)
                if snippet:
                    parts.append(f"  摘要：{snippet}")
    if info.sources:
        parts.append("来源：" + ", ".join(info.sources))
    external_info = "\n".join(parts).strip()

    requirements = (user_requirements or "").strip()
    feelings = (user_feelings or "").strip()
    prompt = "\n\n".join(
        [
            "请生成一份读书报告，建议包含：",
            "1) 一句话结论（可选）\n2) 书籍简介\n3) 结构梳理（按篇章/章节）\n4) 核心观点与论证\n5) 亮点与不足\n6) 个人理解与反思（融合用户读后感）\n7) 可实践建议/行动清单",
            f"用户要求：{requirements if requirements else '（无）'}",
            f"用户读后感/理解：{feelings if feelings else '（无）'}",
            "外部信息（用于补充背景与简介，若与正文冲突以正文为准）：",
            external_info if external_info else "（无）",
            "以下是从全书抽取的关键片段（用于支撑生成与避免断章取义）：",
            context,
        ]
    )
    return {"context": context, "external_info": external_info, "prompt": prompt}


# 从整本书中抽取关键片段并拼装成 context：优先向量检索，否则退化为分块采样/原文切片
def build_context(
    *,
    settings: Settings,
    book_id: str,
    extracted_text: str,
    user_requirements: str | None = None,
    user_feelings: str | None = None,
    max_context_chars: int = 12000,
) -> str:
    text = (extracted_text or "").strip()
    if not text:
        raise ValueError("missing extracted_text")

    requirements = (user_requirements or "").strip()
    feelings = (user_feelings or "").strip()
    toc = extract_toc(text)
    queries = _build_retrieval_queries(requirements=requirements, feelings=feelings, toc=toc)

    snippets: list[tuple[str, dict[str, Any]]] = []
    candidates: list[tuple[str, dict[str, Any]]] = []

    try:
        from app.rag.vector_store import get_vector_store

        vs = get_vector_store(settings, book_id=book_id)
        for q in queries[: int(settings.retrieval_queries_limit)]:
            try:
                docs = vs.max_marginal_relevance_search(q, k=6, fetch_k=24)
            except Exception:
                docs = vs.similarity_search(q, k=6)

            for d in docs:
                t = (d.page_content or "").strip()
                if not t:
                    continue
                candidates.append((t, dict(d.metadata or {})))
            if len(candidates) >= int(settings.retrieval_max_snippets) * 6:
                break
    except Exception:
        pass

    if candidates:
        snippets = _select_snippets_with_coverage(
            candidates,
            max_total=int(settings.retrieval_max_snippets),
            per_section_max=int(settings.retrieval_per_section_max),
        )

    if not snippets:
        try:
            chunks = chunk_text(text, max_chars=1200, overlap_chars=120)
        except Exception:
            chunks = []

        if chunks:
            take = min(12, len(chunks))
            idxs = [int(i * (len(chunks) - 1) / max(1, take - 1)) for i in range(take)]
            for i in idxs:
                c = chunks[i]
                snippets.append(
                    (
                        c.text,
                        {
                            "book_id": book_id,
                            "chunk_index": c.index,
                            "section_title": c.section_title,
                            "doc_type": "chunk",
                            "source": "local_sampling",
                        },
                    )
                )
        else:
            n = len(text)
            windows = [
                (0, min(n, 1200)),
                (max(0, n // 2 - 600), min(n, n // 2 + 600)),
                (max(0, n - 1200), n),
            ]
            for idx, (a, b) in enumerate(windows):
                piece = text[a:b].strip()
                if piece:
                    snippets.append((piece, {"book_id": book_id, "chunk_index": idx, "doc_type": "raw", "source": "raw_slicing"}))

    context_parts: list[str] = []
    if toc:
        context_parts.append("[目录]")
        context_parts.append(toc)

    for i, (t, md) in enumerate(snippets, start=1):
        context_parts.append(t)

    context = "\n".join(context_parts)
    return context[:max_context_chars] if len(context) > max_context_chars else context


# 构建读书报告生成的 LangGraph 工作流（后续可逐步扩展为多 Agent 结构）
def build_report_graph(*, settings: Settings):
    try:
        from langgraph.graph import END
        from langgraph.graph import StateGraph
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing LangGraph dependency. Install with: uv sync --group ai") from e

    # 抽取书籍文本：从 uploads 中定位文件并进行抽取清洗
    def node_extract(state: ReportState) -> ReportState:
        book_id = state.get("book_id")
        if not book_id:
            return {"status": "failed", "error": "missing book_id"}

        path = find_uploaded_file(settings, book_id)
        if path is None:
            return {"status": "failed", "error": "book not found"}

        extracted = extract_text(path)
        return {
            "status": "extracted",
            "extracted_text": extracted.text,
        }

    # 从整本书中抽取关键片段：优先走向量检索，否则退化为本地分块采样
    def node_retrieve_key_snippets(state: ReportState) -> ReportState:
        text = (state.get("extracted_text") or "").strip()
        if not text:
            return {"status": "failed", "error": "missing extracted_text"}

        book_id = state.get("book_id")
        if not book_id:
            return {"status": "failed", "error": "missing book_id"}
        requirements = (state.get("user_requirements") or "").strip()
        feelings = (state.get("user_feelings") or "").strip()

        try:
            context = build_context(
                settings=settings,
                book_id=book_id,
                extracted_text=text,
                user_requirements=requirements,
                user_feelings=feelings,
            )
        except Exception as e:  # noqa: BLE001
            return {"status": "failed", "error": str(e)}

        return {"status": "context_ready", "context": context}

    # 补充外部书籍信息：通过免费接口获取简介/出版年份/主题等，增强报告背景信息
    def node_external_enrich(state: ReportState) -> ReportState:
        book_id = state.get("book_id")
        if not book_id:
            return {"status": "failed", "error": "missing book_id"}

        meta = get_book_meta(settings, book_id)
        info = get_external_book_info(settings, book_id=book_id, title=meta.title, author=meta.author)

        parts: list[str] = []
        if info.title:
            parts.append(f"书名：{info.title}")
        if info.author:
            parts.append(f"作者：{info.author}")
        if info.description:
            parts.append("简介（Tavily）：")
            parts.append(info.description)
        if info.tavily_answer:
            parts.append("补充（Tavily Answer）：")
            parts.append(info.tavily_answer)
        if info.tavily_results:
            reviews = _pick_review_snippets(info.tavily_results, max_items=3)
            if reviews:
                parts.append("优质书评（Tavily 结果节选）：")
                for r in reviews:
                    title = r.get("title") or ""
                    url = r.get("url") or ""
                    snippet = (r.get("snippet") or "").strip()
                    line = f"- {title}"
                    if url:
                        line += f" ({url})"
                    parts.append(line)
                    if snippet:
                        parts.append(f"  摘要：{snippet}")
        if info.sources:
            parts.append("来源：" + ", ".join(info.sources))

        external_text = "\n".join(parts).strip()
        return {"status": "external_ready", "external_info": external_text}

    # 构造生成用提示词：把用户要求/读后感与书籍内容拼装成可控输入
    def node_prepare_prompt(state: ReportState) -> ReportState:
        requirements = (state.get("user_requirements") or "").strip()
        feelings = (state.get("user_feelings") or "").strip()
        context = (state.get("context") or "").strip()
        if not context:
            return {"status": "failed", "error": "missing context"}

        external_info = (state.get("external_info") or "").strip()

        prompt = "\n\n".join(
            [
                "请生成一份读书报告，建议包含：",
                "1) 一句话结论（可选）\n2) 书籍简介\n3) 结构梳理（按篇章/章节）\n4) 核心观点与论证\n5) 亮点与不足\n6) 个人理解与反思（融合用户读后感）\n7) 可实践建议/行动清单",
                f"用户要求：{requirements if requirements else '（无）'}",
                f"用户读后感/理解：{feelings if feelings else '（无）'}",
                "外部信息（用于补充背景与简介，若与正文冲突以正文为准）：",
                external_info if external_info else "（无）",
                "以下是从全书抽取的关键片段（用于支撑生成与避免断章取义）：",
                context,
            ]
        )

        return {"status": "prompt_ready", "user_requirements": requirements, "user_feelings": feelings, "prompt": prompt}

    # 调用 LLM 生成报告：默认走本地 Ollama（LangChain ChatOllama）
    def node_generate_outline(state: ReportState) -> ReportState:
        prompt = state.get("prompt")
        if not prompt:
            return {"status": "failed", "error": "missing prompt"}

        try:
            from langchain_core.messages import HumanMessage
            from langchain_core.messages import SystemMessage
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Missing LangChain dependency. Install with: uv sync --group ai") from e

        from app.llm.chat_model import get_chat_model

        model = get_chat_model(settings)
        base = "\n\n".join(
            [
                prompt,
                "生成要求（阶段1：只输出 JSON 大纲，不要输出 Markdown/正文）：",
                "- 只输出一个 JSON object，禁止输出任何额外文字/解释/代码块标记。",
                "- bullets 使用字符串数组，每条尽量短（<=60字），不要写成段落。",
                "JSON schema：",
                '{"title":"...","sections":[{"heading":"...","bullets":["...","..."]}]}',
            ]
        )

        last_err: str | None = None
        for attempt in range(3):
            extra = ""
            if last_err:
                extra = "\n\n".join(
                    [
                        "上一次输出无法解析或不符合 schema：",
                        last_err,
                        "请严格只输出 JSON object。",
                    ]
                )
            msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=base + ("\n\n" + extra if extra else ""))]
            out = model.invoke(msgs)
            content = getattr(out, "content", None)
            if not isinstance(content, str) or not content.strip():
                last_err = "empty model output"
                continue
            obj, err = _extract_json_object(content)
            if err or obj is None:
                last_err = err or "unknown"
                continue
            v = _validate_outline_json(obj)
            if v:
                last_err = v
                continue
            md = _outline_json_to_markdown(obj)
            return {"status": "outlined", "outline_markdown": md, "outline_json": obj}

        return {"status": "failed", "error": last_err or "outline json invalid"}

    def node_expand_report(state: ReportState) -> ReportState:
        prompt = state.get("prompt")
        outline = state.get("outline_markdown")
        outline_json = state.get("outline_json")
        if not prompt:
            return {"status": "failed", "error": "missing prompt"}
        if not outline:
            return {"status": "failed", "error": "missing outline_markdown"}

        try:
            from langchain_core.messages import HumanMessage
            from langchain_core.messages import SystemMessage
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Missing LangChain dependency. Install with: uv sync --group ai") from e

        from app.llm.chat_model import get_chat_model

        model = get_chat_model(settings)
        outline_payload = outline
        if isinstance(outline_json, dict) and outline_json:
            outline_payload = json.dumps(outline_json, ensure_ascii=False)

        base = "\n\n".join(
            [
                prompt,
                "生成要求（阶段2：按大纲扩写正文）：",
                "- 按下面大纲逐节扩写为完整读书报告（Markdown）。",
                "- 不要引入未在片段/外部信息中出现的新事实。",
                "大纲（优先按结构执行）：",
                outline_payload,
            ]
        )

        last_err: str | None = None
        for attempt in range(2):
            extra = ""
            if last_err:
                extra = "\n\n".join(["上一次输出为空或无效：", last_err, "请重新生成完整 Markdown 正文。"])
            msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=base + ("\n\n" + extra if extra else ""))]
            out = model.invoke(msgs)
            content = getattr(out, "content", None)
            if not isinstance(content, str) or not content.strip():
                last_err = "empty model output"
                continue
            return {"status": "completed", "report_markdown": content}
        return {"status": "failed", "error": last_err or "empty model output"}

    # 统一错误收敛：把异常信息写到 state 里，便于 API 层返回
    def node_catch_error(state: ReportState) -> ReportState:
        err = state.get("error") or "unknown error"
        return {"status": "failed", "error": err}

    graph = StateGraph(ReportState)
    graph.add_node("extract", node_extract)
    graph.add_node("retrieve", node_retrieve_key_snippets)
    graph.add_node("external", node_external_enrich)
    graph.add_node("prepare_prompt", node_prepare_prompt)
    graph.add_node("outline", node_generate_outline)
    graph.add_node("expand", node_expand_report)
    graph.add_node("catch_error", node_catch_error)

    graph.set_entry_point("extract")

    # 根据节点产出的状态字段决定下一跳，失败统一进入 catch_error
    def route_after_extract(state: ReportState) -> str:
        return "catch_error" if state.get("status") == "failed" else "retrieve"

    def route_after_retrieve(state: ReportState) -> str:
        return "catch_error" if state.get("status") == "failed" else "external"

    def route_after_external(state: ReportState) -> str:
        return "catch_error" if state.get("status") == "failed" else "prepare_prompt"

    def route_after_prepare(state: ReportState) -> str:
        return "catch_error" if state.get("status") == "failed" else "outline"

    def route_after_outline(state: ReportState) -> str:
        if state.get("status") == "failed":
            return "catch_error"
        if state.get("workflow_mode") == "outline":
            return END
        return "expand"

    def route_after_expand(state: ReportState) -> str:
        return "catch_error" if state.get("status") == "failed" else END

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "retrieve": "retrieve",
            "catch_error": "catch_error",
        },
    )
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "external": "external",
            "catch_error": "catch_error",
        },
    )
    graph.add_conditional_edges(
        "external",
        route_after_external,
        {
            "prepare_prompt": "prepare_prompt",
            "catch_error": "catch_error",
        },
    )
    graph.add_conditional_edges(
        "prepare_prompt",
        route_after_prepare,
        {
            "outline": "outline",
            "catch_error": "catch_error",
        },
    )
    graph.add_conditional_edges(
        "outline",
        route_after_outline,
        {
            "expand": "expand",
            END: END,
            "catch_error": "catch_error",
        },
    )
    graph.add_conditional_edges(
        "expand",
        route_after_expand,
        {
            END: END,
            "catch_error": "catch_error",
        },
    )
    graph.add_edge("catch_error", END)

    return graph.compile()


# 运行一次报告生成工作流，返回最终 state（用于后续 API 层封装）
def run_report_workflow(
    *,
    settings: Settings,
    book_id: str,
    user_requirements: str | None = None,
    user_feelings: str | None = None,
    mode: Literal["report", "context", "outline"] = "report",
) -> dict[str, Any]:
    if mode == "context":
        path = find_uploaded_file(settings, book_id)
        if path is None:
            return {"book_id": book_id, "status": "failed", "error": "book not found"}
        extracted = extract_text(path)
        try:
            ctx = build_context(
                settings=settings,
                book_id=book_id,
                extracted_text=extracted.text,
                user_requirements=user_requirements,
                user_feelings=user_feelings,
            )
        except Exception as e:  # noqa: BLE001
            return {"book_id": book_id, "status": "failed", "error": str(e)}
        return {"book_id": book_id, "status": "context_ready", "context": ctx}

    app = build_report_graph(settings=settings)
    state: ReportState = {
        "book_id": book_id,
        "status": "init",
        "user_requirements": user_requirements or "",
        "user_feelings": user_feelings or "",
        "workflow_mode": mode,
    }
    return app.invoke(state)
