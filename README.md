<div align='center'>
  <h1 style="margin-top: 15px;">Shopkeeper Agent · 电商智能问数助手</h1>
  <h4><b>shopkeeper-agent</b></h4>
  <p><em>基于 FastAPI + LangGraph + RAG + NL2SQL 的电商智能数据查询助手，支持自然语言查数与内部文档知识库问答</em></p>
</div>

<div align='center'>

![AI](https://img.shields.io/badge/AI-Agent-00c853?style=flat)
![LangGraph](https://img.shields.io/badge/LangGraph-1.1.6-1C3C3C.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-SSE-009688.svg?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

> **本项目基于 [didilili/shopkeeper-agent](https://github.com/didilili/shopkeeper-agent) 进行二次创作，在其 NL2SQL + RAG 架构基础上进行了增强与完善。**

## 项目介绍

电商运营团队每天需要频繁查询销售数据（GMV、AOV、销量、区域分布等），传统流程需向 BI 提工单，单次查询耗时数小时到数天。同时企业内部知识库（制度、规范、手册）分散在多处，查找效率低。

本系统将大语言模型的 NL2SQL 与 RAG 技术结合，把数据查询入口从「找 BI 写 SQL」变为「用自然语言直接提问」，将响应时间从天级降为秒级。

```text
用户输入自然语言问题
  -> LangGraph 13 节点工作流逐级执行
    -> 关键词提取 + 3 路并行召回（Qdrant 向量 + ES BM25 + 精确匹配）
    -> LLM 生成 SQL -> sqlglot 语法校验 -> 失败自动修正
    -> 数仓执行查询
  -> SSE 流式返回中间过程与最终结果
  -> 前端实时展示思考链路与数据表格
```

## 与原版的差异

本项目在原始 shopkeeper-agent 基础上做了以下增强：

| 维度 | 原版 | 本版 |
|------|------|------|
| **架构文档** | 简略 | 完整四层架构图 + NL2SQL/RAG 双流程 + 混合检索策略 |
| **PRD** | 无 | 完整 PRD 文档（背景、指标、用户故事、验收标准） |
| **README** | 基础 | 系统化 README，含架构、部署、API、安全边界等完整章节 |
| **Git 托管** | 仅 Gitee | GitHub 公开仓库，持续更新 |
| **质量文档** | 无 | 项目分析报告、职责描述、能力边界说明 |

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│        React + Tailwind (Vite) · SSE 流式展示            │
├──────────────────────────────────────────────────────────┤
│                     API Layer (FastAPI)                   │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│   │  POST /query  │  │ POST /rag/*  │  │  Middleware   │  │
│   │  NL2SQL 查询   │  │ RAG 问答/上传 │  │ request_id    │  │
│   └──────┬───────┘  └──────┬───────┘  │ 安全拦截        │  │
├──────────┼──────────────────┼──────────────────────────────┤
│          ▼                  ▼           Agent Layer        │
│  ┌─────────────────────────────────────────────────┐      │
│  │         LangGraph 工作流 (13 节点 DAG)           │      │
│  │                                                   │      │
│  │  extract_keywords  →  3路并行召回                  │      │
│  │    (LLM提取关键词)      ├─ Qdrant 向量 → 字段/指标   │      │
│  │                         ├─ ES BM25   → 维度值        │      │
│  │                         └─ LLM 扩展  → 同义词/别名    │      │
│  │                                                   │      │
│  │  merge_retrieved → filter_table → filter_metric   │      │
│  │                                                   │      │
│  │  generate_sql → validate_sql ─┬─ pass → run_sql   │      │
│  │                 (sqlglot校验)  └─ fail → correct_sql│      │
│  │                                                   │      │
│  │  add_extra_context → SSE 流式返回                  │      │
│  └─────────────────────────────────────────────────┘      │
├──────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │  MySQL   │ │  Qdrant  │ │    ES    │ │  Embedding  │  │
│  │ (meta+dw)│ │ (vector) │ │ (BM25)   │ │  (BGE)      │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌──────────┐ ┌────────────────────────────┐             │
│  │ LLM API  │ │  Reranker (可选)            │             │
│  │(DeepSeek)│ │  (BGE Reranker v2-m3)      │             │
│  └──────────┘ └────────────────────────────┘             │
└──────────────────────────────────────────────────────────┘
```

### NL2SQL 查询流程

| 阶段 | 节点 | 动作 |
|------|------|------|
| 语义理解 | `extract_keywords` | jieba 分词 + LLM 提取核心业务实体 |
| 并行召回 | `recall_column` | Qdrant 向量检索相关表字段 |
| | `recall_metric` | Qdrant 向量检索相关业务指标 |
| | `recall_value` | ES 全文检索具体维度值 |
| 查询扩展 | `extend_keywords` | LLM 将别名/同义词映射到标准字段名 |
| 融合精筛 | `merge_retrieved` → `filter_table` → `filter_metric` | 合并召回结果，裁掉无关表和指标 |
| SQL 生成 | `generate_sql` | LLM 根据表结构 + 指标 + 条件生成 SQL |
| 验证闭环 | `validate_sql` → `correct_sql`（失败时） | sqlglot 语法 + 语义校验，自动修正 |
| 查询执行 | `run_sql` | asyncmy 在数仓执行只读查询 |
| 结果输出 | `add_extra_context` | 生成最终回答 → SSE 流式推送到前端 |

### RAG 知识库问答

```
文档上传 → 分段(chunk) → BGE Embedding 向量化 → 存入 Qdrant + ES
                    ↑
用户提问 → 注入检测(正则 + Embedding 双层) 
         → 混合检索(向量 0.4 + BM25 0.4 + 精确 0.2) 
         → [可选] BGE Reranker 重排序 
         → LLM 生成回答(附来源引用) → SSE 流式返回
```

## 项目技术栈

| 模块 | 技术 | 作用 |
|------|------|------|
| 后端框架 | `FastAPI` | API 路由、SSE 流式、依赖注入 |
| Agent 编排 | `LangGraph` | 13 节点有向图工作流 |
| LLM 接入 | `LangChain` / `langchain-deepseek` | DeepSeek Chat API 封装 |
| 向量检索 | `Qdrant` | 字段/指标/知识库语义检索 |
| 全文检索 | `Elasticsearch` | 维度值 BM25 召回 + 知识库全文搜索 |
| 向量模型 | `BGE` (BAAI/bge-large-zh-v1.5) | 文本 Embedding |
| 重排序 | `BGE Reranker v2-m3`（可选） | 检索结果二次精排 |
| 数据库 | `MySQL` 8.0 + `SQLAlchemy` (async) | 元数据存储 + 数仓查询 |
| 前端 | `React 19` + `Vite` + `Tailwind` | 对话式交互界面 |
| SQL 校验 | `sqlglot` | 语法树解析 + 字段存在性校验 |
| 日志 | `loguru` | 结构化日志 + request_id 链路 |
| 容器化 | `Docker` / `Docker Compose` | 6 容器一键编排 |

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
# 编辑 .env，填入 LLM_API_KEY

# 3. 启动依赖服务（MySQL + ES + Qdrant + Embedding）
docker compose -f docker/docker-compose.yaml up -d

# 4. 初始化数据库元数据
# 确保 MySQL 中已创建 meta 和 dw 数据库，导入 docker/mysql/ 下的 SQL 脚本

# 5. 启动后端
uv run python main.py

# 6. 启动前端
cd frontend
pnpm install
pnpm dev
```

## API 接口

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/query` | NL2SQL 查询（SSE 流式） |
| POST | `/api/rag/query` | 知识库问答（SSE 流式） |
| POST | `/api/rag/upload` | 上传文档到知识库 |
| GET | `/api/rag/metrics` | 运行时指标 |
| GET | `/api/rag/sessions` | 会话列表 |
| DELETE | `/api/rag/sessions/{id}` | 删除会话 |

## 项目结构

```
shopkeeper-agent/
├── main.py                 # FastAPI 入口
├── conf/                   # 配置文件（app/meta 双 YAML）
├── prompts/                # 7 个独立 .prompt 模板文件
├── app/
│   ├── api/                # 路由层 + 依赖注入
│   │   ├── routers/        # query_router, rag_query_router
│   │   ├── schemas/        # 请求/响应模型
│   │   ├── dependencies.py # 依赖组装
│   │   └── lifespan.py     # 生命周期管理
│   ├── agent/              # LangGraph 工作流
│   │   ├── graph.py        # 13 节点 DAG 编排
│   │   ├── state.py        # 状态定义
│   │   ├── llm.py          # LLM 调用封装
│   │   └── nodes/          # 每个节点独立文件
│   ├── rag/                # RAG 知识库（Qdrant + ES + BGE）
│   ├── services/           # 业务服务层
│   ├── clients/            # 外部客户端管理
│   ├── repositories/       # 数据仓储（MySQL / Qdrant / ES）
│   └── entities/           # 领域实体
├── frontend/               # React + Vite + Tailwind
├── docker/                 # Docker Compose + 各服务配置
├── tests/                  # 冒烟测试、RAG 测试、SQL 安全测试
├── docs/                   # PRD、架构图、分析报告
└── data/                   # 运行时数据（会话、文档）
```

## 安全控制

- **SQL 只写拦截**：正则匹配 DML/DDL 关键词（INSERT/UPDATE/DELETE/DROP/TRUNCATE），进入 LangGraph 前阻断
- **Prompt 注入防护**：双层检测——正则规则（0.1ms 拦截 80% 攻击）+ Embedding 余弦相似度（50ms 拦截绕过变体）
- **请求追踪**：每个请求分配唯一 `request_id`，注入全链路日志
- **文件上传限制**：仅允许 `.md / .txt / .pdf / .docx / .html` 格式

## 配置说明

- `conf/app_config.yaml`：数据库连接、Qdrant/ES 地址、LLM 参数、RAG 权重与阈值
- `conf/meta_config.yaml`：表结构定义、字段别名、指标口径（NL2SQL 同义词映射核心）
- `prompts/`：7 个独立 prompt 文件，覆盖 SQL 生成、修正、关键词扩展、筛选等环节

## 测试

```bash
# 冒烟测试（需先启动服务）
uv run python tests/smoke_test.py

# RAG 综合测试
uv run python tests/test_rag_comprehensive.py

# SQL 安全测试
uv run python tests/test_sql_security.py
```

## 能力边界

本项目聚焦电商数据查询场景，覆盖 NL2SQL 全链路、RAG 知识库问答、多轮对话、安全防护。以下能力不在当前范围：

- 用户认证、权限管理和多租户隔离
- 可视化图表（柱状图 / 折线图等，当前以表格展示）
- 数据导出（CSV / Excel）
- 定时报表和订阅推送
- 数据库写入和修改操作
- 移动端适配
- 第三方集成（钉钉 / 飞书 / 企微）

## License

[MIT](LICENSE)
