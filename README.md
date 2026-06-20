<div align='center'>
  <h1 style="margin-top: 15px;">Shopkeeper Agent · 电商智能问数助手</h1>
  <h4><b>shopkeeper-agent</b></h4>
  <p><em>基于 FastAPI + LangGraph + RAG + NL2SQL 的电商智能数据查询与深度分析系统</em></p>
</div>

<div align='center'>

![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1.6-1C3C3C.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688.svg?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

> **本项目基于 [didilili/shopkeeper-agent](https://github.com/didilili/shopkeeper-agent) 进行二次开发**，在其 NL2SQL + RAG 基础架构上进行了系统性增强，新增鉴权、知识记忆、深度分析报告、语义缓存等企业级功能，并重构了前端 UI 与测试体系。

---

## 与原始项目的差异

| 维度 | 原始项目 | 本版本 |
|------|----------|--------|
| **用户鉴权** | 无 | JWT 登录/注册，admin/user 角色，请求中间件鉴权，401 自动登出 |
| **知识记忆系统** | 无 | MD 文件存储，LLM 自动从对话中提取定义/口径，共享（管理员审核）和私有记忆 |
| **语义缓存** | 无 | Qdrant 向量语义缓存 + 内存精确缓存，相同 query 直接命中 |
| **频率限制** | 无 | 基于内存的 rate limiter，防止恶意刷请求 |
| **深度分析报告** | 无 | LLM 驱动的报告生成管线（计划 SQL → 执行 → Python 预处理 → 图表 → 报告文本），自动检测空数据并询问用户 |
| **动态可视化** | 无 | 从数据库 Schema 自动生成可选的维度和指标，根据选择自动过滤可用图表类型（柱状/折线/饼图），禁用无效选项并提示原因 |
| **多语言意图路由** | 无 | LLM 上下文感知意图分类（sql/rag/report），传递 20 轮对话历史，支持追问上下文保持 |
| **查询队列** | 无 | 流式查询中发送新问题自动排队，当前完成后再执行 |
| **会话持久化** | 无 | SQL/报告/RAG 全部保存到后端 session 文件，含完整数据和图表，刷新不丢失，按类型分区显示 |
| **Token 统计** | 无 | tiktoken 估算每次 LLM 调用的 token 消耗，侧边栏实时显示 |
| **智能图表生成** | 无 | SQL 执行后自动分析结果字段类型，自动判断图表类型（柱状/折线/饼图/多系列），支持 ECharts 交互式渲染 |
| **自动 SQL 修正** | 无 | 检测 `Unknown column` 错误，自动匹配合适字段名重试（amount→order_amount, quantity→order_quantity） |
| **前端 UI** | 暖黑漆器 | 瓷白色主题，登录页面，会话搜索/恢复，知识管理面板，动态可视化界面，可折叠样例 |
| **测试体系** | 无 | 模块单元测试 + 集成测试 + API 端点测试 |
| **托管** | Gitee | GitHub 公开仓库 |
| **项目文档** | 无 | 完整 PRD、架构文档、技术概念总结、记忆系统设计规格 |

---

## 项目介绍

电商运营团队每天需要频繁查询销售数据（GMV、AOV、销量、区域分布等），传统流程需向 BI 提工单，单次查询耗时数小时到数天。同时企业内部知识库（制度、规范、手册）分散在多处，查找效率低。

本系统将大语言模型的 NL2SQL 与 RAG 技术结合，把数据查询入口从「找 BI 写 SQL」变为「用自然语言直接提问」，将响应时间从天级降为秒级。

## 技术栈

| 层次 | 技术 | 用途 |
|------|------|------|
| **后端框架** | Python 3.12, FastAPI, Uvicorn | 异步 API 服务，SSE 流式推送 |
| **AI Agent** | LangGraph, LangChain, DeepSeek API | 13 节点 NL2SQL 工作流，工具调用链 |
| **报告管线** | LLM Planner + SQL Executor + pandas Sandbox | 智能报告生成，安全 Python 预处理 |
| **RAG 检索** | Qdrant (向量), Elasticsearch (BM25), BGE Embedding | 混合检索，父子块索引 |
| **数据库** | MySQL 8.0, SQLAlchemy (async), asyncmy | 数仓查询，元数据管理，会话持久化 |
| **SQL 引擎** | sqlglot (AST 校验), EXPLAIN 执行计划分析 | SQL 安全白名单，自动列名修正 |
| **鉴权** | JWT (HMAC-SHA256), ContextVar 中间件 | 用户登录/注册，admin/user 角色，401 自动登出 |
| **记忆系统** | 三级存储：持久 (MySQL) + 长期 (MD 文件) + 短期 (JSONL) | 业务口径知识，对话上下文注入 |
| **意图路由** | LLM 上下文感知分类 (sql/rag/report) | 自动分流到对应管线，支持 20 轮历史 |
| **缓存** | Qdrant 语义缓存 + 内存精确缓存 + 频率限制 | 重复查询秒回，防恶意刷请求 |
| **Token 统计** | tiktoken 估算 | 每次 LLM 调用的 token 消耗追踪 |
| **前端** | React 19, Vite, Tailwind CSS, TypeScript | 瓷白色 UI，ECharts 交互式图表 |
| **可视化** | ECharts 6, echarts-for-react | 柱状/折线/饼图/多系列，可交互缩放 |
| **容器化** | Docker, Docker Compose | 6 容器一键编排 (MySQL/ES/Qdrant/Embedding/Kibana) |
| **测试** | pytest, httpx, TypeScript (tsc) | 模块测试，API 集成测试，类型检查 |

### 功能特性

- **NL2SQL 查询**：输入自然语言 → 自动生成 SQL → 执行并返回结果表格
- **RAG 知识库问答**：上传文档（.md/.txt/.pdf/.docx），基于向量 + BM25 混合检索问答
- **深度分析报告**：5 个分析模板 → 自动生成多条 SQL → Python 聚合 → matplotlib 图表 → Markdown 报告
- **知识记忆系统**：对话中自动识别业务口径/定义，存入共享/私有记忆，下次检索自动注入上下文
- **多轮对话**：支持上下文保持和追问
- **流式交互**：SSE 实时展示 Agent 思考过程
- **安全防护**：Prompt 注入检测 + SQL AST 白名单 + JWT 鉴权 + 频率限制
- **语义缓存**：相同 query 自动缓存，命中直接返回

---

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                     Presentation Layer                    │
│        React 19 + Tailwind · 瓷白色主题 · SSE 流式      │
├──────────────────────────────────────────────────────────┤
│                     API Layer (FastAPI)                   │
│   22 条路由 · JWT 鉴权中间件 · ContextVar 链路追踪       │
│   频率限制 · 请求/响应日志                               │
├──────────────────────────────────────────────────────────┤
│                     Agent Layer (LangGraph)               │
│  ┌─────────────────────────────────────────────────┐     │
│  │  NL2SQL Agent (11 节点 DAG)                     │     │
│  │  extract_keywords → 3路召回 → 合并 → 双路过滤    │     │
│  │  → SQL生成 → 校验→修正闭环(最多2次) → 执行      │     │
│  └─────────────────────────────────────────────────┘     │
│  ┌─────────────────────────────────────────────────┐     │
│  │  RAG Agent (4 节点)                             │     │
│  │  keywords → Qdrant+ES召回 → 父子块回溯 → 生成   │     │
│  └─────────────────────────────────────────────────┘     │
├──────────────────────────────────────────────────────────┤
│                  Enhancement Layer (新增)                 │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐       │
│  │  Auth    │ │Knowledge │ │  Cache              │       │
│  │  JWT鉴权  │ │ MD记忆   │ │  语义/精确缓存+限流  │       │
│  └──────────┘ └──────────┘ └────────────────────┘       │
│  ┌─────────────────────────────────────────────────┐     │
│  │  Reports (深度分析)                               │     │
│  │  5 模板 → 多 SQL → Python聚合 → matplotlib → MD  │     │
│  └─────────────────────────────────────────────────┘     │
├──────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
│  │MySQL │ │Qdrant│ │  ES  │ │ BGE  │ │ LLM  │         │
│  │meta+ │ │vector│ │BM25  │ │embd  │ │DS API│         │
│  │dw    │ │      │ │      │ │      │ │      │         │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘         │
└──────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python ≥ 3.12, < 3.14
- `uv`（推荐）或 `pip`
- Docker & Docker Compose
- Node.js & `pnpm`
- DeepSeek API Key

### 启动

```bash
# 1. 克隆并安装后端依赖
git clone https://github.com/linkage18/shopkeeper-agent.git
cd shopkeeper-agent
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY，JWT_SECRET（可选，有默认值）

# 3. 启动依赖服务（MySQL + ES + Qdrant + Embedding）
docker compose -f docker/docker-compose.yaml up -d

# 4. 初始化数据库和用户表
Start-Sleep -Seconds 15
docker exec mysql mysql -uroot -pdili123 meta -e "
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(16) DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);"

# 5. 启动后端
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 6. 启动前端
cd frontend
pnpm install
pnpm dev
```

### 快速验证

```bash
# 注册管理员
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取 token 并测试
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 查询知识库
curl -s http://localhost:8000/api/knowledge/list \
  -H "Authorization: Bearer $TOKEN"

# 运行深度分析
curl -s -X POST http://localhost:8000/api/reports/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"template_id":"trend","params":{"metric":"order_amount","granularity":"month","start_date":20250101,"end_date":20250331}}'
```

---

## API 接口

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册 | 无 |
| POST | `/api/auth/login` | 登录 | 无 |
| GET | `/api/auth/me` | 当前用户信息 | 需 Token |
| GET | `/api/knowledge/list` | 知识列表 | 需 Token |
| GET | `/api/knowledge/search?q=` | 搜索知识 | 需 Token |
| POST | `/api/knowledge/save` | 新增/编辑知识 | 需 Token |
| DELETE | `/api/knowledge/delete/{title}` | 删除知识 | 需 Token |
| GET | `/api/reports/templates` | 分析模板列表 | 需 Token |
| POST | `/api/reports/analyze` | 执行深度分析 | 需 Token |
| POST | `/api/query` | NL2SQL 查询（SSE） | 需 Token |
| POST | `/api/rag/query` | 知识库问答（SSE） | 需 Token |
| POST | `/api/rag/upload` | 上传文档 | 需 Token |

---

## 项目结构

```
shopkeeper-agent/
├── main.py                   # FastAPI 入口
├── conf/                     # 配置文件
├── prompts/                  # 7 个 LLM Prompt 模板
├── app/
│   ├── auth/                 # JWT 鉴权（新增）
│   ├── knowledge/            # 知识记忆系统（新增）
│   ├── cache/                # 语义缓存 + 限流（新增）
│   ├── reports/              # 深度分析报告（新增）
│   │   └── templates/        # 5 个分析模板 YAML
│   ├── agent/                # NL2SQL LangGraph 工作流
│   ├── rag/                  # RAG 知识库
│   ├── services/             # 业务服务层
│   ├── clients/              # 外部客户端管理
│   ├── repositories/         # 数据仓储层
│   └── entities/             # 领域实体
├── frontend/                 # React + Vite + Tailwind
│   └── src/components/       # 新增：LoginPage, AnalysisPanel, KnowledgeManager, SessionSearch
├── docker/                   # Docker Compose 编排
├── tests/                    # 测试文件（新增）
│   ├── test_v2_modules.py    # 模块单元测试（15 项）
│   ├── live_test.py          # 集成测试（5 项）
│   └── fix_test.py           # 分析模板验证
├── data/
│   ├── knowledge/            # 知识记忆 MD 文件
│   └── sessions/             # 会话记录
└── docs/                     # 文档
    ├── PRD_shopkeeper_agent.md
    ├── core-concepts.md
    └── RESPONSIBILITIES.md
```

---

## 技术栈

| 模块 | 技术 | 来源 |
|------|------|------|
| Agent 编排 | LangGraph | 原始 |
| 后端框架 | FastAPI | 原始 |
| 向量检索 | Qdrant | 原始 |
| 全文检索 | Elasticsearch | 原始 |
| 向量模型 | BGE (bge-large-zh-v1.5) | 原始 |
| 数据库 | MySQL 8.0 + SQLAlchemy | 原始 |
| SQL 校验 | sqlglot | 原始 |
| LLM | DeepSeek API | 原始 |
| **鉴权** | **自实现 JWT (HMAC-SHA256)** | **新增** |
| **知识记忆** | **文件系统 MD 存储** | **新增** |
| **缓存** | **Qdrant 语义缓存 + 内存精确缓存** | **新增** |
| **图表** | **matplotlib** | **新增** |
| **前端主题** | **瓷白色 Tailwind** | **新增** |
| **分词** | jieba | 原始 |

---

## License

[MIT](LICENSE)
