from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"

    deepseek_api_base: str | None = "https://api.deepseek.com"
    deepseek_api_key: str | None = Field(default=None, repr=False)
    deepseek_model: str = "deepseek-chat"

    siliconflow_api_base: str | None = "https://api.siliconflow.cn/v1"
    siliconflow_api_key: str | None = Field(default=None, repr=False)
    siliconflow_model: str = "deepseek-ai/DeepSeek-V3"

    tavily_api_key: str | None = Field(default=None, repr=False)
    tavily_max_results: int = 5
    tavily_topic: str = "general"

    retrieval_max_snippets: int = 18
    retrieval_per_section_max: int = 2
    retrieval_queries_limit: int = 12

    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./data/uploads")
    chroma_persist_dir: Path = Path("./data/chroma_db")
    index_status_dir: Path = Path("./data/index_status")
    report_dir: Path = Path("./data/reports")
    report_status_dir: Path = Path("./data/report_status")
    book_meta_dir: Path = Path("./data/book_meta")
    external_meta_dir: Path = Path("./data/external_meta")

    chroma_server_host: str = "127.0.0.1"
    chroma_server_port: int = 8002
    chroma_collection_prefix: str = "readking"

    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = Field(default=None, repr=False)
    langchain_project: str = "read-king"

    log_level: str = "info"

    # 校验配置在不同 Provider 下的必填项，避免运行到一半才报错
    @model_validator(mode="after")
    def validate_provider(self) -> "Settings":
        if self.llm_provider == "ollama":
            if not self.ollama_base_url:
                raise ValueError("OLLAMA_BASE_URL is required when LLM_PROVIDER=ollama")
            if not self.ollama_model:
                raise ValueError("OLLAMA_MODEL is required when LLM_PROVIDER=ollama")

        if self.llm_provider == "deepseek":
            if not self.deepseek_api_base:
                raise ValueError("DEEPSEEK_API_BASE is required when LLM_PROVIDER=deepseek")
            if not self.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek")

        if self.llm_provider == "siliconflow":
            if not self.siliconflow_api_base:
                raise ValueError("SILICONFLOW_API_BASE is required when LLM_PROVIDER=siliconflow")
            if not self.siliconflow_api_key:
                raise ValueError("SILICONFLOW_API_KEY is required when LLM_PROVIDER=siliconflow")

        self.data_dir = self._resolve_path(self.data_dir)
        self.upload_dir = self._resolve_path(self.upload_dir)
        self.chroma_persist_dir = self._resolve_path(self.chroma_persist_dir)
        self.index_status_dir = self._resolve_path(self.index_status_dir)
        self.report_dir = self._resolve_path(self.report_dir)
        self.report_status_dir = self._resolve_path(self.report_status_dir)
        self.book_meta_dir = self._resolve_path(self.book_meta_dir)
        self.external_meta_dir = self._resolve_path(self.external_meta_dir)

        return self

    @staticmethod
    def _resolve_path(p: Path) -> Path:
        if p.is_absolute():
            return p
        return (PROJECT_ROOT / p).resolve()


# 以更宽容的方式加载 .env：支持带 "export" 或行首 "-" 的误格式行，避免 python-dotenv 报告告警
def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw in path.read_text("utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith("\"") and value.endswith("\"")) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        os.environ.setdefault(key, value)


# 统一获取配置（带缓存），用于 FastAPI 启动与依赖注入
@lru_cache
def get_settings() -> Settings:
    load_env_file(PROJECT_ROOT / ".env")
    return Settings()
