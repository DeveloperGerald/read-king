from __future__ import annotations

import logging

from app.core.config import Settings


logger = logging.getLogger(__name__)


# 获取 Chat Model 实例（优先 Ollama，本项目默认使用本地推理）
def get_chat_model(settings: Settings):
    if settings.llm_provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Missing LLM dependencies. Install with: uv sync --group ai") from e

        logger.info(f"Using Ollama chat model: {settings.ollama_model}")
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    if settings.llm_provider in {"deepseek", "siliconflow"}:
        raise RuntimeError("Cloud LLM providers are not wired yet. Switch LLM_PROVIDER=ollama for now.")

    raise ValueError(f"unsupported llm_provider: {settings.llm_provider}")

