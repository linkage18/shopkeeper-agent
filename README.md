# Shopkeeper Agent — 电商智能问数助手

基于 **FastAPI + LangGraph + RAG + NL2SQL** 的智能数据查询助手，支持用自然语言查询电商数据库，以及基于内部文档的知识库问答。

## 功能

- **NL2SQL 查询**：输入自然语言 → 自动生成 SQL → 执行并返回结果表格
- **RAG 知识库问答**：上传企业内部文档（.md/.txt/.pdf/.docx），基于向量 + BM25 混合检索问答
- **流式交互**：SSE 实时展示 Agent 思考过程（关键词提取 → 字段召回 → SQL 生成 → 执行结果）
- **多轮对话**：支持上下文保持和追问
- **安全防护**：Prompt 注入检测（正则 + Embedding 相似度双层防护）+ SQL 破坏性操作拦截

## 架构概览

```
用户输入 → FastAPI → LangGraph Agent (13 nodes) → 结果返回
                         ├─ 关键词提取
                         ├─ 向量/ES 混合召回
                         ├─ SQL 生成 & 验证
                         └─ 执行 & 格式化输出
```

**技术栈**：Python 3.12+, FastAPI, LangGraph, LangChain, SQLAlchemy (async), Qdrant, Elasticsearch, Transformers (BGE), Docker

## 前置准备

- Python ≥ 3.12, < 3.14
- 包管理器：`uv`（推荐）或 `pip`
- Docker & Docker Compose（运行 MySQL / Qdrant / ES / Embedding 服务）
- LLM API Key（DeepSeek）

## 快速开始

### 1. 启动依赖服务

```bash
docker compose -f docker/docker-compose.yaml up -d
```

启动的服务：MySQL 8.0, Elasticsearch 8.x + Kibana, Qdrant v1.16, Text Embeddings Inference (BGE)

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 LLM API Key：

```env
LLM_API_KEY=sk-your-key-here
```

数据库配置可在 `conf/app_config.yaml` 中修改。

### 3. 安装依赖

```bash
uv sync
# 或 pip install -r requirements.txt（如使用 pip）
```

### 4. 初始化元数据

确保 MySQL 中已创建 `meta` 和 `dw` 两个数据库，并导入对应的表结构与测试数据。

### 5. 启动后端

```bash
uv run python main.py
# 或 python main.py
```

服务默认运行在 `http://localhost:8000`。

### 6. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端默认运行在 `http://localhost:5173`。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/query` | NL2SQL 查询（SSE 流式） |
| POST | `/api/rag/query` | 知识库问答（SSE 流式） |
| POST | `/api/rag/upload` | 上传文档到知识库 |
| GET | `/api/rag/metrics` | 运行时指标 |
| GET | `/api/rag/sessions` | 会话列表 |
| DELETE | `/api/rag/sessions/{id}` | 删除会话 |

## 项目结构

```
shopkeeper-agent-main/
├── main.py                 # FastAPI 入口
├── conf/                   # 配置文件
├── prompts/                # LLM Prompt 模板
├── app/
│   ├── api/                # 路由 & 依赖注入
│   ├── agent/              # LangGraph 工作流（13 个节点）
│   ├── rag/                # RAG 知识库链路
│   ├── services/           # 业务服务层
│   ├── clients/            # 外部客户端（MySQL / ES / Qdrant / Embedding）
│   ├── repositories/       # 数据仓储层
│   ├── entities/           # 领域实体
│   └── models/             # 数据模型
├── frontend/               # Vite + React + Tailwind 前端
├── docker/                 # Docker Compose 编排
├── data/                   # 运行时数据（文档 / 会话）
├── tests/                  # 测试
└── docs/                   # 文档
```

## 配置说明

- `conf/app_config.yaml`：数据库、Qdrant、ES、LLM、RAG 等核心配置
- `conf/meta_config.yaml`：数据库表结构与指标的同义词映射

## 测试

```bash
# 启动服务后运行冒烟测试
uv run python tests/smoke_test.py
```

## License

[MIT](LICENSE)
