# Shopkeeper Agent — 智能问数与知识库平台

> 面向电商运营和内部知识检索场景，用自然语言直接查询业务数据、检索文档，并自动生成可视化分析报表。

## 为什么做这个

电商运营每天需要查 GMV、销量、区域分布等数据，传统流程是提 BI 工单——单次查询从数小时到数天不等。企业内部知识库（制度、规范、手册）散落各处，查找效率低。

这个系统把两条线串到一起：**NL2SQL 查数据 + RAG 查文档**，让响应时间从天级降到秒级。

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│  Frontend  (Vite + React + Tailwind + ECharts)          │
│        │ SSE 流式推送                                     │
├────────┴─────────────────────────────────────────────────┤
│  API Layer  (FastAPI)                                    │
│  JWT 认证 / Rate Limit / CORS / 13 个 Router             │
├────────┬────────────────┬───────────────────────────────┤
│  NL2SQL Agent            │   RAG Agent   │  Report Agent│
│  (LangGraph 11 节点)      │  (4 节点)     │  (LLM 驱动)   │
│                          │               │              │
│  关键词抽取 ──→ 三路召回  │  关键词抽取   │  Schema →     │
│  合并 → 过滤 → 生成 SQL   │  → 多路召回    │  规划 SQL →   │
│  → 校验 → 修正 → 执行     │  → 组装上下文  │  处理 → 图表  │
│  → 自动图表构建           │  → 生成回答    │  → 报表文本   │
├────────┴────────────────┴───────────────────────────────┤
│  Memory System   │  Knowledge Base  │  Semantic Cache   │
│  持久/长期/短期    │  MD 文件管理     │  Qdrant 向量缓存  │
│  三级检索         │  LLM 自动提取    │  + 精确缓存       │
├─────────────────────────────────────────────────────────┤
│  Security & Engineering                                  │
│  PBKDF2 密码哈希   │  AST 沙箱隔离  │  SQL 注入防护     │
│  参数化查询        │  标识符白名单  │  CORS 安全配置    │
│  输入校验          │  异常日志覆盖  │  异步非阻塞 I/O   │
├─────────────────────────────────────────────────────────┤
│  Infrastructure                                         │
│  MySQL × 2 (meta + dw)  │  Qdrant (向量)  │  ES (全文)  │
│  BGE Embedding          │  DeepSeek LLM   │  Docker     │
└─────────────────────────────────────────────────────────┘
```

## 三个核心能力

### 1. 自然语言查数据 (NL2SQL)

用户输入"统计华北地区销售额"，系统走完一个 11 节点的 LangGraph 流程：

**关键词抽取 → 三路并行召回**（column 向量 / metric 向量 / value 全文索引）→ **合并去重 → 过滤候选表和指标 → 补充日期和数据库信息 → 生成 SQL → EXPLAIN 校验（最多 2 次自动修正）→ 执行 → 自动图表构建**

- **意图路由**：LLM 上下文感知分类器自动分发 SQL / RAG / Report 管线
- **安全执行**：sqlglot AST 全量遍历审查，只放行纯 SELECT，阻断 DDL/DML/写文件
- **错误容错**：每个节点独立容错，SQL 生成失败最多 3 次自动重试

### 2. 企业知识库问答 (RAG)

上传文档后自动切分、向量化、入库。用户提问时，系统从 Qdrant（向量）和 ES（BM25 全文）两条路并行召回，合并去重后交给 LLM 生成带来源引用的回答。

### 3. 深度分析报表 (Report)

LLM 根据数据表 Schema 自动规划 SQL 列表 + Python 预处理 + 图表配置，执行后生成完整的 Markdown 分析报告，支持多图表组合展示。

## 安全特性

| 项目 | 说明 |
|------|------|
| 密码存储 | PBKDF2-HMAC-SHA256，600K 次迭代，随机 16 字节盐值 |
| SQL 执行 | sqlglot AST 遍历 + 写操作黑名单，阻止 INSERT/UPDATE/DROP/文件写入 |
| SQL 注入 | 表名/列名正则白名单 `^[a-zA-Z0-9_一-鿿]+$` + 参数化查询 |
| 沙箱隔离 | exec() 执行前 AST 静态分析，移除危险内置函数（eval/exec/import/os） |
| 输入校验 | Pydantic Field min_length/max_length/pattern 约束 |
| CORS | 正则匹配 localhost 开发环境，生产环境需配置白名单 |

## 关键技术选型

| 层 | 选型 | 为什么 |
|---|---|---|
| Agent 框架 | LangGraph | StateGraph 让多节点流程可观测、可条件路由、可重试 |
| 向量库 | Qdrant | 本地部署，毫秒级检索 |
| 全文检索 | Elasticsearch | BM25 关键词检索，与向量检索互补 |
| Embedding | BGE-large-zh-v1.5 | 中文场景效果稳定 |
| LLM | DeepSeek | API 成本低，推理速度快 |
| 前端 | React + ECharts | SSE 流式解析 + 交互式图表展示 |

## 快速开始

### 依赖服务

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### 配置

```bash
cp .env.example .env
# 填入 LLM_API_KEY 等配置（生产环境请更换 JWT_SECRET）
```

### 启动后端

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
python -m app.scripts.build_meta_knowledge
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
│   ├── agent/            # NL2SQL Agent (LangGraph 11 节点)
│   ├── rag/              # RAG 文档问答 Agent
│   ├── report_agent/     # 深度分析报表 Agent
│   ├── reports/          # 预定义模板化报表
│   ├── memory/           # 三级记忆系统
│   ├── knowledge/        # 知识库管理 + LLM 自动提取
│   ├── auth/             # JWT 认证 (PBKDF2 密码哈希)
│   ├── cache/            # 语义缓存 + 精确缓存 + 频率限制
│   ├── core/             # 公共工具模块（关键词/MD解析/Token计数/图表构建）
│   └── schema_analyzer/  # Schema 自动读取与分析
├── conf/                 # 应用配置 (YAML + 环境变量)
├── data/                 # 数据目录（session / charts / docs）
├── prompts/              # LLM 提示词模板
├── frontend/             # React 前端
└── docker/               # Docker Compose 服务编排
```

## 工程治理

- **代码质量**：TypeScript 零错误编译，前端生产构建 311KB gzip
- **异常处理**：17 处静默吞异常改为带日志警告，关键路径重新抛出
- **异步 I/O**：所有文件读写和外部调用使用 asyncio.to_thread 避免阻塞事件循环
- **配置管理**：Qdrant 集合名、频率限制等硬编码值全部外移到统一配置
- **前端优化**：React.memo 缓存高频组件、SSE 解析器去重、模块级可变状态改为 useRef
- **用户体验**：删除操作确认对话框、生产环境零 console.warn

## 许可证

[MIT](LICENSE)
