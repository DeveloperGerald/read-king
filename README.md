# ReadKing (读书报告生成系统)

ReadKing 是一个基于大模型技术的智能文档处理平台，专注于为用户提供高质量、个性化的读书报告生成服务。本项目通过 **LangGraph** 构建多 Agent 协作工作流，结合 **RAG (检索增强生成)** 技术，实现对长文本书籍的深度理解与分析。

---

## 1. 项目功能描述

- **智能书籍处理**：支持上传 PDF/TXT 电子书，自动进行文本提取、分块及索引构建。
- **RAG 增强分析**：基于本地向量库，针对长篇书籍进行精准的内容检索，确保生成报告的准确性。
- **多 Agent 协作工作流**：
    - **深度研究**：通过“书籍专家”与“背景研究员”并行工作，覆盖书内细节与外部背景。
    - **个性化融合**：支持用户输入个人读后感与特殊要求，Agent 将其与书籍核心思想深度融合。
    - **循环审核与润色**：内置“资深编辑”审核机制，确保报告逻辑严密、风格贴合需求。
- **低成本/本地优先**：默认使用本地 **Ollama** 运行模型，推理成本为零，且支持一键切换至云端 Provider（如 DeepSeek、SiliconFlow）。
- **外部信息补充**：集成 Tavily 搜索，自动获取作者背景、社会评价及同类作品对比。
- **美观的前端展示**：基于 React + Tailwind 设计，提供极简且具有“温暖阅读感”的用户界面。

---

## 2. 如何快速启动

### 2.1 后端启动 (FastAPI)

1. **环境准备**：推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。
   ```bash
   # 安装 uv (如果尚未安装)
   brew install uv
   
   # 同步环境及依赖
   uv sync --group ai --group ingest --group vectorstore --group embeddings
   ```

2. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 根据需要编辑 .env 文件
   ```

3. **启动服务**：
   ```bash
   # 默认运行在 8001 端口
   uv run uvicorn app.main:app --reload --port 8001
   ```

### 2.2 向量库启动 (ChromaDB)

本项目后端通过 HTTP 连接 Chroma Server。推荐使用 Docker 快速运行：
```bash
docker run -d --rm --name chromadb \
  -p 8002:8000 \
  -v "$(pwd)/data/chroma_db:/data" \
  chromadb/chroma
```

### 2.3 前端启动 (React)

1. **安装依赖**：
   ```bash
   cd frontend
   npm install
   ```

2. **启动开发服务器**：
   ```bash
   npm run dev
   ```
   前端默认通过代理访问 `http://127.0.0.1:8001`。

---

## 3. 如何使用配置

项目通过根目录下的 `.env` 文件进行配置，主要配置项包括：

- **LLM Provider**：
  - `LLM_PROVIDER`: 可选 `ollama` (默认), `deepseek`, `siliconflow`。
  - `OLLAMA_BASE_URL`: 本地 Ollama 服务地址。
  - `OLLAMA_MODEL`: 指定模型名称（如 `qwen2.5:7b`）。
- **Embedding**：
  - `EMBEDDING_PROVIDER`: 可选 `ollama` 或 `huggingface`。
  - `EMBEDDING_MODEL`: 向量化模型名称（默认 `nomic-embed-text`）。
- **向量库**：
  - `CHROMA_SERVER_HOST` & `CHROMA_SERVER_PORT`: Chroma 服务地址（默认 `127.0.0.1:8002`）。
- **外部搜索 (可选)**：
  - `TAVILY_API_KEY`: 若需开启外部背景研究，请配置 Tavily API Key。

---

## 4. 目录结构

```text
read-king/
├── app/                # 后端核心逻辑 (Python/FastAPI)
│   ├── agents/         # LangGraph 工作流与 Agent 定义
│   ├── api/            # API 路由与接口实现
│   ├── core/           # 全局配置与核心组件
│   ├── llm/            # LLM 适配器 (Ollama/OpenAI)
│   ├── rag/            # RAG 模块 (加载、分块、向量库)
│   ├── services/       # 业务逻辑服务层
│   └── main.py         # FastAPI 入口
├── frontend/           # 前端应用 (React/TypeScript/Vite)
│   ├── src/            # 前端源码
│   └── tailwind.config.js
├── data/               # 本地存储 (书籍上传、索引、报告、数据库)
├── scripts/            # 工具脚本 (测试、验证)
├── tests/              # 后端测试用例
├── .env.example        # 环境变量模板
└── pyproject.toml      # 项目依赖配置
```

---

## 5. 项目架构

本项目采用典型的 **前后端分离** 架构，并深度集成大模型工作流：

- **前端层**：React 18 + TypeScript 构建，利用 Tailwind CSS 提供现代化的 UI 交互。
- **API 层**：FastAPI 提供异步高性能接口，负责书籍上传、状态查询及生成任务分发。
- **Agent 编排层**：**LangGraph** 核心引擎，负责管理复杂的 Agent 状态转移、并行执行与循环反馈。
- **RAG 引擎**：**ChromaDB** 向量数据库 + **LangChain** 组件，实现基于语义的文档检索。
- **模型推理层**：支持本地（Ollama）与云端（API Provider）灵活切换。
- **存储层**：本地文件系统存储原始书籍与生成的 Markdown 报告。

---

## 6. Agent 工作流

ReadKing 的核心在于其基于 LangGraph 构建的 **Agentic Workflow**，具体流程如下：

1. **研究入口 (Research Entry)**：
   - 系统接收书籍 ID、用户要求及感悟。
   - 启动并行研究任务。

2. **并行研究 (Parallel Research)**：
   - **书籍专家 (Book Expert)**：调用 RAG 工具深入研读全书，提取核心论点、金句与结构。
   - **背景研究员 (Context Researcher)**：调用外部搜索工具，搜集作者背景、社会影响及同类对比。

3. **研究反思 (Research Reflection)**：
   - **研究主管 (Reflector)**：审视两位研究员搜集的素材是否充足。
   - 若素材不足，根据缺失类型（书内或书外）指引 Agent 重新进行针对性研究（最多重试 2 次）。

4. **规划与大纲 (Planner)**：
   - 基于研究成果，生成结构化的报告大纲（包含标题、核心章节及要点）。

5. **正文撰写 (Writer)**：
   - **读书博主 (Writer)**：根据大纲和研究背景，撰写完整的 Markdown 报告。

6. **质量审核 (Reviewer)**：
   - **资深编辑 (Reviewer)**：检查报告是否覆盖要点、语言是否生动、是否存在杜撰。
   - 若审核未通过，提供反馈并要求 Writer 进行局部修改（最多循环 3 次）。

7. **最终润色 (Polisher)**：
   - **排版专家 (Polisher)**：根据设定的风格（如“读书博主风”），优化排版、语气并加粗关键信息。

8. **输出 (END)**：
   - 生成最终的 Markdown 报告并保存至本地。
