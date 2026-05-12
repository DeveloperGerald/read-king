from __future__ import annotations

import logging
from typing import Any, List, Optional

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.core.config import Settings
from app.services.file_service import find_uploaded_file
from app.services.text_extraction import extract_text
from app.rag.structure import extract_toc
from app.services.book_meta_service import get_book_meta
from app.services.external_info_service import get_external_book_info
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

@tool
def get_book_structure(book_id: str, config: RunnableConfig) -> str:
    """获取书籍的目录结构(TOC)和基本信息。当你需要了解书籍的全局框架或章节分布时使用。"""
    settings: Settings = config.get("configurable", {}).get("settings")
    if not settings:
        return "Error: settings not found in config"
    
    path = find_uploaded_file(settings, book_id)
    if path is None:
        return f"Error: book {book_id} not found"

    extracted = extract_text(path)
    toc = extract_toc(extracted.text)
    meta = get_book_meta(settings, book_id)
    
    res = [f"书名：{meta.title}", f"作者：{meta.author}"]
    if toc:
        res.append("\n[目录结构]")
        res.append(toc)
    else:
        res.append("\n无法提取目录结构。")
        
    return "\n".join(res)

@tool
def search_book_content(query: str, book_id: str, config: RunnableConfig) -> str:
    """搜索书籍内部的具体内容、观点或案例。支持语义检索。当你需要寻找支撑材料或具体细节时使用。"""
    settings: Settings = config.get("configurable", {}).get("settings")
    if not settings:
        return "Error: settings not found in config"

    try:
        vs = get_vector_store(settings, book_id=book_id)
        # 这里的 k 和 fetch_k 可以根据需求微调，或者通过 settings 配置
        try:
            docs = vs.max_marginal_relevance_search(query, k=6, fetch_k=24)
        except Exception:
            docs = vs.similarity_search(query, k=6)
            
        if not docs:
            return "未在书中找到相关内容。"
            
        parts = []
        for i, d in enumerate(docs, 1):
            content = d.page_content.strip()
            section = d.metadata.get("section_title", "未知章节")
            parts.append(f"--- 匹配片段 {i} (章节: {section}) ---\n{content}")
            
        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"Error searching book content: {e}")
        return f"搜索书内内容时出错: {e}"

@tool
def search_web_info(query: str, book_id: str, config: RunnableConfig) -> str:
    """在互联网上搜索书籍的背景、书评、作者相关信息或社会评价。当你需要补充书外上下文时使用。"""
    settings: Settings = config.get("configurable", {}).get("settings")
    if not settings:
        return "Error: settings not found in config"
    
    if not settings.tavily_api_key:
        return "未配置 Tavily API Key，无法进行联网搜索。"

    meta = get_book_meta(settings, book_id)
    # 结合书名和作者增强搜索准确性
    full_query = f"书籍《{meta.title}》{meta.author} {query}"
    
    try:
        info = get_external_book_info(settings, book_id=book_id, title=meta.title, author=meta.author)
        # 注意：get_external_book_info 内部其实已经做了 Tavily 搜索并缓存了
        # 这里我们可以直接返回格式化后的结果，或者根据 query 重新触发
        
        parts = []
        if info.description:
            parts.append(f"简介: {info.description}")
        if info.tavily_answer:
            parts.append(f"补充背景: {info.tavily_answer}")
            
        if info.tavily_results:
            from app.agents.workflow import _pick_review_snippets
            reviews = _pick_review_snippets(info.tavily_results, max_items=3)
            if reviews:
                parts.append("\n[相关书评/资料]")
                for r in reviews:
                    parts.append(f"- {r['title']} ({r['url']})\n  摘要: {r['snippet']}")
        
        return "\n".join(parts) if parts else "未找到相关的外部信息。"
    except Exception as e:
        logger.error(f"Error searching web info: {e}")
        return f"联网搜索时出错: {e}"
