# 简历每一点的「为什么这样做」——面试准备

---

## 1. 为什么分成三类 Agent + 意图路由，而不是一个 Agent 包办？

**直觉回答**：「问数据」「问知识」「出报告」是三种完全不同的任务，输入输出、检索策略、校验逻辑都不同，硬塞在一起会导致状态爆炸、难测试、难迭代。

**展开说**：

| 维度 | NL2SQL Agent | RAG Agent | Report Agent |
|------|-------------|-----------|-------------|
| 输入 | 自然语言问题 | 自然语言问题 | 分析需求 |
| 检索源 | MySQL 字段 + Qdrant 向量 + ES 值 | Qdrant 文档块 + ES 全文 | MySQL Schema + 记忆 |
| 输出 | SQL + 行数据 + 图表 | Markdown 文本 + 引用 | ECharts + Markdown 报告 |
| 校验 | EXPLAIN + sqlglot AST 安全检查 | 无（文本生成不需校验） | SQL 执行 + Python 沙箱 |
| 节点数 | 11 个 | 4 个 | 3 阶段管道 |

**关键代码**：`app/intent/router.py` 用一次 LLM 调用把用户问题分为 `sql` / `rag` / `report` 三个 token，前端根据路由结果调用不同的 API 端点。每个 Agent 有自己的 `State` 和 `Context` 类型，互不干扰。

**反问准备**：「如果用户问的是既需要查数据又需要查文档的复合问题怎么办？」→ 当前设计不支持，这是一个已知的边界场景。生产环境可以加一个 fallback：如果单一 Agent 返回空或低置信度，自动尝试另一条链路。

---

## 2. 为什么用 YAML 维护 Schema + MySQL+Qdrant+ES 三层元数据，而不是直接把 DDL 喂给 LLM？

**直觉回答**：全量 DDL 太大了（几十张表几百个字段），LLM 塞不下，也找不到正确的字段。我们需要一个「检索 → 生成」的管道——先召回问题相关的字段，再只把这几张表喂给 LLM。

**三个具体问题**：

| 问题 | 方案 | 存储 |
|------|------|------|
| 用户说"销售额"但字段叫 `order_amount` | 语义向量检索找同义词 | Qdrant（BGE Embedding）|
| 用户说"华东区"但需要知道这个值存不存在 | 精确/模糊值匹配 | ES（BM25 全文检索）|
| 需要查字段类型、主外键、指标口径 | 结构化查询 | MySQL meta 库 |

**配置驱动设计**：改表结构只需改 `conf/meta_config.yaml`，跑一次 `build_meta_knowledge.py` 即可，不需要改代码。`sync: true/false` 控制哪些字段进入 ES 索引（主键、内部 ID 等无用字段设为 false）。

**关键代码**：`app/services/meta_knowledge_service.py` 第 109-134 行，每个字段会拆成多个向量点（字段名、描述、每个别名），提高同义词命中率。

---

## 3. 为什么 State 和 Context 要分开？

**直觉回答**：State 要序列化成 JSON 推给前端，只能放可序列化的业务数据。Context 放数据库连接、API 客户端这些不可序列化的运行时依赖，只在图内部传递。

**如果不分开会怎样**？把 Repository（数据库 Session）塞进 State → 尝试序列化时抛出 `TypeError: Object of type AsyncSession is not JSON serializable`。这是实际踩过的坑。

**三个好处**：

| 好处 | 说明 |
|------|------|
| 可测试性 | 测试时可以 mock Context 里的 Repository，不需要真实数据库 |
| 多租户 | 不同请求可以使用不同的 Context（如不同数据库连接） |
| 解耦 | 节点通过 `runtime.context[name]` 读取依赖，不感知全局单例 |

**关键代码**：`app/agent/state.py` vs `app/agent/context.py` — State 全是 `str`、`list`、`int` 等简单类型，Context 全是 `Repository`、`Client` 等复杂对象。

---

## 4. 为什么用 SSE 而不是 WebSocket 或轮询？

**直觉回答**：这是纯服务端→客户端的单向进度推送，SSE 是最轻量的方案。WebSocket 是双向的，对当前场景过重；轮询浪费带宽且增加延迟。

**三种方案对比**：

| 方案 | 缺点 |
|------|------|
| 轮询 | 客户端每 N 秒问"好了没"，浪费带宽。11 个节点需要轮询 11 次或设一个 job ID 系统 |
| WebSocket | 双向持久连接 → 需要心跳、重连逻辑、服务端维护状态。对本场景来说过重 |
| **SSE** | 单向、文本、HTTP 原生。前端用 `fetch()` + `ReadableStream.getReader()` 逐块读取即可，天然支持 `AbortController` 取消 |

**实现方式**：每个 LangGraph 节点调用 `writer({"type": "progress", "step": "生成SQL", "status": "running"})` → FastAPI 包装成 `data: {...}\n\n` → `StreamingResponse(media_type="text/event-stream")` → 前端 `response.body.getReader()` 逐块读取，按 `\n\n` 分割，解析 `data:` 行，按 `type` 字段分发。

**关键代码**：
- 后端：`app/api/routers/query_router.py` 第 58-60 行（StreamingResponse）
- 前端：`frontend/src/lib/agentApi.ts` 第 15-59 行（ReadableStream）

---

## 面试话术速记

> 面试官：为什么分成三个 Agent？
> **你**：因为问数据、问文档、出报告这三个任务的检索源和校验逻辑完全不同。NL2SQL 需要 Schema 召回 + SQL 校验回环，RAG 需要文档块召回 + 引用溯源，Report 需要规划执行 + 图表渲染。放在一个图里，State 会膨胀到不可维护。

> 面试官：为什么不用直接把 DDL 喂给 LLM？
> **你**：全量 DDL 太多了，LLM 上下文窗口装不下。更重要的是——用户说"销售额"，DDL 里只有 `order_amount`，LLM 猜不出来。所以我们建了一个元数据知识库，用向量检索做同义词匹配，ES 做值匹配，只有命中的字段才喂给 LLM。

> 面试官：State 和 Context 分开有什么好处？
> **你**：最直接的好处是可测试——mock Context 里的 Repository 就能跑单测，不需要起数据库。另外 State 序列化成 JSON 推前端，如果把带连接池的 Repository 放进去，序列化会直接报错。

> 面试官：为什么选 SSE？
> **你**：因为只是后端往前端推进度，不需要前端往后端发消息。SSE 比 WebSocket 轻量得多——HTTP 原生、不需要心跳、不需要重连逻辑、`AbortController` 天然支持取消。前端用 `fetch` + `ReadableStream` 就能消费。
