from __future__ import annotations

import logging

from app.core.config import Settings


logger = logging.getLogger(__name__)


# 获取 Embeddings 实例（优先使用 Ollama，HuggingFace 作为可选后备）
def get_embeddings(settings: Settings):
    if settings.embedding_provider == "ollama":
        try:
            from langchain_community.embeddings import OllamaEmbeddings
        except ImportError as e:
            raise RuntimeError("Missing embeddings dependencies. Install with: uv sync --group embeddings") from e

        logger.info(f"Using Ollama embeddings model: {settings.embedding_model}")
        return OllamaEmbeddings(base_url=settings.ollama_base_url, model=settings.embedding_model)

    if settings.embedding_provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as e:
            raise RuntimeError("Missing HuggingFace embeddings dependencies. Install with: uv sync --group embeddings-hf") from e

        logger.info(f"Loading HuggingFace embedding model: {settings.embedding_model}")
        model_kwargs = {"device": "cpu"}
        encode_kwargs = {"normalize_embeddings": True}
        return HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )

    raise ValueError(f"unsupported embedding_provider: {settings.embedding_provider}")
