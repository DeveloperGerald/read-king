from __future__ import annotations

import logging

from app.core.config import Settings


logger = logging.getLogger(__name__)


# 获取 Chat Model 实例（支持 Ollama, DeepSeek, SiliconFlow）
def get_chat_model(settings: Settings):
    """
    根据配置获取对应的聊天模型实例。
    优先支持本地 Ollama，同时支持 DeepSeek 和 SiliconFlow 等云端提供商。
    """
    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOllama
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("Missing LLM dependencies. Install with: uv sync --group ai") from e

        logger.info(f"Using Ollama chat model: {settings.ollama_model}")
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    if settings.llm_provider == "deepseek":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOpenAI
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("Missing OpenAI dependencies. Install with: pip install langchain-openai") from e

        logger.info(f"Using DeepSeek chat model: {settings.deepseek_model}")
        
        # 针对 DeepSeek 官方 API 优化
        # 1. 强制使用默认的 json_schema 模式，避免 API 不支持的 response_format
        # 2. 如果是 deepseek-chat，它对 JSON Mode 的支持通常需要显式开启或通过 Prompt 引导
        return ChatOpenAI(
            model=settings.deepseek_model,
            openai_api_key=settings.deepseek_api_key,
            openai_api_base=settings.deepseek_api_base,
            # 某些版本的 DeepSeek API 可能不支持 tool_choice 或特定的 response_format
            # 这里可以通过 default_options 或其他方式微调，但通常 with_structured_output 的 method="json_schema" 更通用
        )

    if settings.llm_provider == "siliconflow":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOpenAI
            except Exception as e:  # noqa: BLE001
                raise RuntimeError("Missing OpenAI dependencies. Install with: pip install langchain-openai") from e

        logger.info(f"Using SiliconFlow chat model: {settings.siliconflow_model}")
        return ChatOpenAI(
            model=settings.siliconflow_model,
            openai_api_key=settings.siliconflow_api_key,
            openai_api_base=settings.siliconflow_api_base,
        )

    raise ValueError(f"unsupported llm_provider: {settings.llm_provider}")

