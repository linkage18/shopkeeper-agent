# Shopkeeper Agent — 电商智能问数与知识库助手

> 面向电商运营和内部知识检索场景，用自然语言直接查询业务数据、检索文档，并自动生成可视化报表。

## 为什么做这个

电商运营每天需要查 GMV、销量、区域分布等数据，传统流程是提 BI 工单——单次查询从数小时到数天不等。企业内部知识库（制度、规范、手册）散落各处，查找效率低。

这个系统把两条线串到一起：**NL2SQL 查数据 + RAG 查文档**，让响应时间从天级降到秒级。

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│  Frontend  (Vite + React + Tailwind + ECharts)          │
│        │ SSE 流式推送                                    │
├────────┴─────────────────────────────────────────────────┤
│  API Layer  (FastAPI)                                    │
│  JWT 认证 / Rate Limit / 13 个 Router                    │
├────────┬────────────────┬───────────────────────────────┤
│  NL2SQL Agent            │   RAG Agent   │  Report Agent│
│  (LangGraph 11 节点)      │  (4 节点)     │  (LLM 驱动)  │
│                          │               │              │
│  关键词抽取 ──→ 三路召回  │  关键词抽取   │  Schema →     │
│  合并 → 过滤 → 生成 SQL   │  → 多路召回    │  规划 SQL →   │
│  → 校验 → 修正 → 执行     │  → 组装上下文  │  处理 → 图表  │
│                          │  → 生成回答    │  → 报表文本   │
├────────┴────────────────┴───────────────────────────────┤
│  Memory System   │  Knowledge Base  │  Semantic Cache   │
│  持久/长期/短期    │  MD 文件管理     │  Qdrant 向量缓存  │
│  三级检索         │  LLM 自动提取    │  + 精确缓存       │
├─────────────────────────────────────────────────────────┤
│  Infrastructure                                         │
│  MySQL × 2 (meta + dw)  │  Qdrant (向量)  │  ES (全文)  │
│  BGE Embedding          │  DeepSeek LLM   │  Docker     │
└─────────────────────────────────────────────────────────┘
```

## 三个核心能力

### 1. 自然语言查数据 (NL2SQL)

用户输入"统计华北地区销售额"，系统走完一个 11 节点的 LangGraph 流程：

**关键词抽取 → 三路并行召回**（column 向量 / metric 向量 / value 全文索引）→ **合并去重 → 过滤候选表和指标 → 补充日期和数据库信息 → 生成 SQL → EXPLAIN 校验（最多 2 次自动修正）→ 执行 → 返回图表**

### 2. 企业知识库问答 (RAG)

上传文档后自动切分、向量化、入库。用户提问时，系统从 Qdrant（向量）和 ES（BM25 全文）两条路并行召回，合并去重后交给 LLM 生成带来源引用的回答。

### 3. 深度分析报表 (Report)

LLM 根据数据表 Schema 自动规划 SQL 列表 + Python 预处理 + 图表配置，执行后生成完整的 Markdown 分析报告。

## 关键技术选型

| 层 | 选型 | 为什么 |
|---|---|---|
| Agent 框架 | LangGraph | StateGraph 让多节点流程可观测、可条件路由、可重试，比直接调 LLM 更可控 |
| 向量库 | Qdrant | 本地部署，不依赖云服务，性能满足毫秒级检索 |
| 全文检索 | Elasticsearch | 提供 BM25 关键词检索，与向量检索互补 |
| Embedding | BGE-large-zh-v1.5 | 中文场景效果稳定，支持本地部署 |
| LLM | DeepSeek | API 成本低，推理速度快 |
| 前端 | React + ECharts | SSE 流式解析 + 交互式图表展示 |

## 快速开始

### 依赖服务

```bash
# 启动 MySQL、Qdrant、ES、Embedding 和 Reranker 服务
docker compose -f docker/docker-compose.yaml up -d
```

### 配置

复制并编辑环境变量：

```bash
cp .env.example .env
# 填入 LLM_API_KEY 等配置
```

### 启动后端

```bash
# 创建虚拟环境
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
uv sync

# 构建元数据知识库
python -m app.scripts.build_meta_knowledge

# 启动服务
uvicorn main:app --reload --port 8000
```

### 启动前端

```bash
cd frontend
pnpm install
pnpm run dev
```

访问 `http://localhost:5173` 即可使用。

## 项目结构

```
├── app/
│   ├── agent/          # NL2SQL Agent (LangGraph)
│   ├── rag/            # RAG 文档问答 Agent
│   ├── report_agent/   # 深度分析报表 Agent
│   ├── reports/        # 预定义模板化报表
│   ├── memory/         # 三级记忆系统
│   ├── knowledge/      # 知识库管理 + LLM 自动提取
│   ├── auth/           # JWT 认证
│   ├── cache/          # 语义缓存
│   └── schema_analyzer/ # Schema 自动读取与分析
├── conf/               # 应用配置
├── data/               # 数据目录（session / charts / docs）
├── prompts/            # LLM 提示词模板
├── frontend/           # React 前端
└── docker/             # Docker Compose 服务编排
```

## 许可证

[MIT](LICENSE)
