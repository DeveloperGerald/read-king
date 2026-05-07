from __future__ import annotations

from pathlib import Path


# 校验 LangChain 相关依赖是否安装（按需依赖，避免无关功能启动失败）
def _require_langchain() -> None:
    try:
        import langchain_core  # noqa: F401
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing LangChain dependencies. Install with: uv sync --group ai") from e


# 按文件类型加载为 LangChain Document 列表（当前仅支持 TXT/PDF）
def load_documents(path: Path) -> list[Document]:
    _require_langchain()
    from langchain_core.documents import Document

    ext = path.suffix.lower()

    if ext == ".pdf":
        try:
            from langchain_community.document_loaders import PyPDFLoader
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Missing PDF loader dependencies. Install with: uv sync --group ai --group ingest") from e

        loader = PyPDFLoader(str(path))
        return loader.load()

    if ext == ".txt":
        try:
            from langchain_community.document_loaders import TextLoader
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Missing TXT loader dependencies. Install with: uv sync --group ai") from e

        raw = path.read_bytes()
        encoding: str | None = None
        for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
            try:
                raw.decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue

        loader = TextLoader(str(path), encoding=encoding)
        docs = loader.load()
        for d in docs:
            d.metadata.setdefault("file_type", "txt")
        return docs

    raise ValueError(f"unsupported file type: {ext}")
