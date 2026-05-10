from __future__ import annotations

import logging

from app.core.config import Settings
from app.rag.embeddings import get_embeddings


logger = logging.getLogger(__name__)


# 校验 Chroma client 与 LangChain 依赖是否安装
def _require_vectorstore() -> None:
    try:
        import chromadb  # noqa: F401
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing Chroma client dependency. Install with: uv sync --group vectorstore") from e
    try:
        import langchain_community  # noqa: F401
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing LangChain dependency. Install with: uv sync --group ai") from e


# 获取 Chroma 的 HTTP Client（连接到 Docker/远端 Chroma Server）
def get_chroma_http_client(settings: Settings):
    _require_vectorstore()
    import chromadb

    return chromadb.HttpClient(host=settings.chroma_server_host, port=settings.chroma_server_port)


# 生成每本书对应的 collection 名（按前缀隔离不同 book_id 数据）
def get_collection_name(settings: Settings, *, book_id: str) -> str:
    prefix = settings.chroma_collection_prefix.strip()
    if not prefix:
        prefix = "readking"
    return f"{prefix}_{book_id}"


# 清理指定 book_id 的向量集合
def clear_vector_store(settings: Settings, *, book_id: str) -> None:
    _require_vectorstore()
    client = get_chroma_http_client(settings)
    collection_name = get_collection_name(settings, book_id=book_id)
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted Chroma collection: {collection_name}")
    except Exception:
        # 如果集合不存在，忽略错误
        logger.warning(f"Collection {collection_name} not found, skip deletion.")


# 获取 LangChain VectorStore（Chroma），用于 add_texts / similarity_search
def get_vector_store(settings: Settings, *, book_id: str):
    _require_vectorstore()

    from langchain_community.vectorstores import Chroma

    client = get_chroma_http_client(settings)
    embeddings = get_embeddings(settings)
    collection_name = get_collection_name(settings, book_id=book_id)
    logger.info(f"Using Chroma collection: {collection_name}")

    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
