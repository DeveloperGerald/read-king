# ReadKing（读书报告生成系统）

上传中文电子书（PDF/TXT），可选结合个人读后感与自定义要求，通过 RAG + LangGraph 工作流生成读书报告。默认使用本地 Ollama；也支持切换到云端 Provider。

## 功能（MVP）

- 上传电子书并落盘
- 文本抽取与分块预览
- 构建向量索引（Chroma）并进行检索增强
- 生成读书报告（支持自定义要求与读后感）
- 查看生成状态并读取报告文件

## 快速开始（本地）

### 1) 后端（FastAPI）

1. 安装依赖管理工具（推荐）

```bash
brew install uv
```

2. 安装 Python 依赖

```bash
uv python pin 3.11
uv sync
```

如需启用 RAG / 工作流 / 解析等能力，安装对应依赖组：

```bash
uv sync --group ai --group ingest
```

如需使用 Chroma（HTTP Client 连接 Server）：

```bash
uv sync --group vectorstore
```

如需启用向量化（默认 Ollama Embeddings）：

```bash
uv sync --group embeddings
ollama pull nomic-embed-text
```

3. 配置环境变量

```bash
cp .env.example .env
```

4. 启动服务（文档默认端口 `8001`，与前端代理默认值一致）

```bash
uv run uvicorn app.main:app --reload --port 8001
```

5. 健康检查

```bash
curl http://127.0.0.1:8001/health
```

### 2) 向量库（可选：Chroma Server）

默认后端通过 HTTP 连接 `CHROMA_SERVER_HOST:CHROMA_SERVER_PORT`（默认 `127.0.0.1:8002`）。推荐用 Docker 运行 Chroma Server：

```bash
docker run -d --rm --name chromadb \
  -p 8002:8000 \
  -v "$(pwd)/data/chroma_db:/data" \
  chromadb/chroma
```

### 3) 前端（React + Vite）

前端开发服务器会把 `/api/*` 代理到后端，默认目标为 `http://127.0.0.1:8001`。

```bash
cd frontend
npm install
npm run dev
```

如需修改代理目标，创建 `frontend/.env` 并设置：

```bash
VITE_API_TARGET=http://127.0.0.1:8001
```

## 配置说明（后端 .env）

复制 `.env.example` 后按需修改：

- `LLM_PROVIDER`：`ollama` | `deepseek` | `siliconflow`
- `OLLAMA_BASE_URL` / `OLLAMA_MODEL`：本地 Ollama 地址与模型
- `EMBEDDING_PROVIDER`：`ollama` | `huggingface`
- `EMBEDDING_MODEL`：Embedding 模型名（默认 `nomic-embed-text`）
- `CHROMA_SERVER_HOST` / `CHROMA_SERVER_PORT`：Chroma Server 地址（默认 `127.0.0.1:8002`）
- `TAVILY_API_KEY`：可选，用于补充书籍外部信息（需额外依赖组，见下）

启用 Tavily 外部搜索（可选）：

```bash
uv sync --group external-search
```

## API 速览

后端 API 统一前缀为 `/api`：

- `POST /api/upload`：上传书籍
- `GET /api/books/{book_id}/text`：抽取文本（含预览）
- `GET /api/books/{book_id}/chunks`：预览分块
- `POST /api/books/{book_id}/index`：后台构建索引
- `GET /api/books/{book_id}/index/status`：查询索引状态
- `POST /api/books/{book_id}/report`：后台生成报告
- `GET /api/books/{book_id}/report/status`：查询报告状态
- `GET /api/books/{book_id}/report/file`：读取报告 Markdown
- `POST /api/books/{book_id}/workflow/context`：预览工作流上下文（不调用 LLM）
- `POST /api/books/{book_id}/workflow/prompt`：预览最终 prompt（不调用 LLM）
- `POST /api/books/{book_id}/workflow/outline`：只生成大纲（调用 LLM）

## 目录结构（简版）

- `app/`：FastAPI 后端
- `frontend/`：React + Vite 前端
- `data/`：本地数据（上传文件、索引状态、向量库持久化、报告输出）
- `scripts/`：脚本
- `tests/`：测试用例

## 兼容安装方式（requirements.txt）

如不使用 `uv`：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```
