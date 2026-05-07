# ReadKing - 目录结构 (后端核心导向)

```
read-king/
├── app/                        # FastAPI 应用
│   ├── main.py                 # 程序入口
│   ├── api/                    # 极简 API 路由
│   │   └── endpoints.py        # upload, generate, status, optimize
│   ├── core/                   # 核心配置
│   │   └── config.py           # 环境变量与 LLM 配置
│   ├── models/                 # 数据库模型 (SQLAlchemy)
│   ├── schemas/                # Pydantic 验证模型
│   ├── services/               # 业务逻辑
│   │   ├── book_service.py     # 文件上传与解析
│   │   └── report_service.py   # 报告任务管理
│   ├── agents/                 # LangGraph Agent 系统 (重点)
│   │   ├── workflow.py         # LangGraph 图定义
│   │   ├── reader_agent.py     # 负责 RAG 检索
│   │   ├── reflector_agent.py  # 负责融合个人感悟
│   │   ├── writer_agent.py     # 负责文本生成
│   │   └── reviewer_agent.py   # 负责质量把控
│   ├── rag/                    # RAG 组件
│   │   ├── vector_store.py     # ChromaDB 封装
│   │   └── processor.py        # 中文分块与 Embedding
│   └── mcp/                    # MCP 集成
│       └── tools.py            # Wiki/OpenLibrary 工具定义
├── web/                        # 极简前端 (奶油色调)
│   ├── index.html
│   ├── style.css               # 浅棕色/奶油色主题
│   └── app.js
├── data/                       # 本地存储
│   ├── uploads/                # 原始电子书
│   └── chroma_db/              # 向量数据库
├── tests/                      # 核心逻辑测试
├── .env                        # API Keys
├── requirements.txt            # 依赖
└── README.md
```

## 目录说明

1.  **app/agents/**: 这是项目的核心，展示了你对 LangGraph 和多 Agent 协作的理解。
2.  **app/rag/**: 展示你对长文本处理、中文分块策略以及向量检索优化的能力。
3.  **web/**: 极简实现，主要用于展示后端生成的成果，配色遵循浅棕与奶油色。
4.  **mcp/**: 展示你紧跟大模型前沿技术（Model Context Protocol）的集成能力。
