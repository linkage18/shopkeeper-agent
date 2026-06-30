# Shopkeeper Agent — 工程改进计划

> 基于代码审查生成的改进路线图，按优先级排列，涵盖架构、安全、可测试性、可靠性和代码质量。

---

## P0 — 必须修复

### 1. 消除全局可变单例，引入依赖注入

**现状**：`app_config`、`llm`、`graph`、所有 `*_client_manager` 均在模块级初始化为全局单例。任何测试只要 `import` 这些模块就会触发真实的外部连接和数据库链接。

**改法**：

- 将所有 `*_client_manager` 的初始化移到 FastAPI `lifespan` 中，实例挂到 `app.state`
- `QueryService` 改为由 FastAPI `Depends` 按请求组装，使用 `app.state` 中的客户端实例
- `graph`（LangGraph 编译对象）放入 `app.state`，每个请求通过 factory 创建新的 `context` 和 `state`
- `llm` 改为可配置注入，测试时可通过 `dependency-override` 替换为 mock
- 删除 `app/agent/llm.py` 和 `app/rag/nodes.py` 中的模块级 `_llm = shared_llm`，改为从 context 读取

**影响文件**：`main.py`, `app/api/lifespan.py`, `app/api/dependencies.py`, `app/conf/app_config.py`, `app/agent/graph.py`, `app/agent/llm.py`, `app/rag/nodes.py`, `app/services/query_service.py`

---

### 2. 文件存储替换为数据库（并发安全）

**现状**：记忆和知识系统直接读写 MD 文件和 JSONL 文件，无事务、无锁、无原子性，多请求并发时存在数据损坏风险。

**改法**：

- **短期记忆**（会话记录）：将 `data/sessions/*.jsonl` 迁移到 MySQL `session_messages` 表，按 `session_id` 索引
- **长期记忆**（知识定义）：将 `data/knowledge/shared/` 下的 MD 文件迁移到 MySQL `knowledge_entries` 表，保留 `scope`、`status`、`tags` 等字段
- 迁移期间保留 MD 文件作为只读 fallback，加 `filelock` 防止并发写入冲突
- 统一用 SQLAlchemy `AsyncSession` 操作，不再阻塞 event loop

**影响文件**：`app/memory/short_term.py`, `app/memory/long_term.py`, `app/knowledge/manager.py`, `app/knowledge/extractor.py`

---

### 3. 修复 Reports 模板 SQL 注入

**现状**：`app/reports/executor.py:render_sql()` 用 `str.replace("{k}", str(v))` 做参数替换，参数值可包含任意 SQL 片段。

**改法**：

- 方案 A（推荐）：模板 SQL 改为带占位符的参数化查询，执行时传参数值
- 方案 B（快速修复）：对参数值做 SQL 转义（至少替换单引号为双引号），并对参数值做类型白名单校验（字符串必须符合预期 pattern，数字必须能 `float()` 转换）

**影响文件**：`app/reports/executor.py`, `app/reports/router.py`

---

## P1 — 应该修复

### 4. 消除 `except Exception: pass`

**现状**：`app/knowledge/extractor.py`, `app/reports/miner.py`, `app/rag/nodes.py` 等多处存在无日志的异常沉默。

**改法**：

- 所有 `except Exception: pass` 至少改为 `logger.warning(...)` + 标记降级状态
- 关键路径（如 RAG 多路召回）改为结构化错误报告：返回 `recall_status = {"qdrant": "success|degraded|failed", "es": ...}`
- `app/services/query_service.py` 中记忆检索失败不影响主流程，需在 SSE 消息中标注 `memory_status: "degraded"`

**影响文件**：`app/knowledge/extractor.py`, `app/reports/miner.py`, `app/rag/nodes.py`, `app/services/query_service.py`

---

### 5. 修复同步/异步混用

**现状**：`app/memory/long_term.py` 使用 `Path.read_text()` 同步文件 IO，被 `async def retrieve_all()` 调用链调用，阻塞 event loop。

**改法**：

- 使用 `aiofiles` 替代 `Path.read_text()` / `Path.write_text()`
- 或（配合改进 #2）直接走异步数据库操作

**影响文件**：`app/memory/long_term.py`, `app/knowledge/manager.py`

---

### 6. 加强 SQL 安全审计

**现状**：`run_sql.py` 的 `_assert_readonly_sql()` 只检查顶层 AST 节点类型，可能遗漏嵌套写操作。CTE 的 `WITH ... SELECT` 是安全的，但 future 扩展如果引入写 CTE 会绕过。

**改法**：

- 用 `sqlglot` 做全 AST 遍历，拒绝任何非 Select 节点
- 或改用数据库侧的 `SET TRANSACTION READ ONLY` 或创建只读数据库用户
- 增加单元测试覆盖各类绕过场景

**影响文件**：`app/agent/nodes/run_sql.py`, `tests/test_sql_security.py`

---

### 7. 解耦 Agent 节点职责

**现状**：

- `app/rag/nodes.py:generate_answer` 同时做 LLM 调用、提取 sources、生成 metrics、写 streaming、执行 post hooks
- `app/agent/nodes/run_sql.py:run_sql` 同时做 SQL 校验、图表推断、缓存写入、知识提取

**改法**：

- 将 post-processing（cache write、knowledge extraction、metrics 记录）抽离为 LangGraph 图的后置节点或 background task
- 每个节点只做一件事：`generate_answer` 只调用 LLM 并返回回答文本，hooks 在后置节点中执行

**影响文件**：`app/rag/nodes.py`, `app/rag/graph.py`, `app/agent/nodes/run_sql.py`, `app/agent/graph.py`

---

## P2 — 值得修复

### 8. 补全类型安全

**现状**：

- `TypedDict` 字段大量用裸 `list` 而非 `list[SomeType]`
- `RagAgentContext.meta_mysql_repository: object | None = None`
- `app/reports/` 模块全方位使用 `dict[str, Any]` 和 `list[dict]`

**改法**：

- 所有 LangGraph State 和 Context 的 TypedDict 补全具体类型
- `reports/` 模块引入 Pydantic models（已有 `app/models/` 但未被使用）
- 消除 `list[dict]` 和 `dict[str, Any]`

**影响文件**：`app/rag/state.py`, `app/rag/context.py`, `app/agent/state.py`, `app/agent/context.py`, `app/reports/*.py`

---

### 9. 明确配置命名空间

**现状**：`app_config.yaml` 中 `es.index_name` 和 `rag.es.index_name` 均名为 `index_name`，未区分用途。

**改法**：

- `rag.es.index_name` → `rag.es.doc_index_name`
- `rag.qdrant.parent_collection` / `rag.qdrant.sub_collection` 添加注释
- 配置 key 添加 `# 用途：...` 注释

**影响文件**：`conf/app_config.yaml`, `app/conf/app_config.py`

---

### 10. 统一记忆注入路径

**现状**：`QueryService.query()` 手动调用 `retrieve_all()` 把记忆拼进 query 字符串，之后 `add_extra_context` 节点又从 state 读取。同类信息走了两条不同路径进入 prompt。

**改法**：

- 统一由 Graph 节点 `add_extra_context` 完成所有记忆注入
- 删除 `QueryService` 中的 `retrieve_all` 调用
- 如果是为了缓存加速，改为在 service 层只做精确缓存命中检查，不做记忆拼装

**影响文件**：`app/services/query_service.py`, `app/agent/nodes/add_extra_context.py`

---

### 11. 配置中的中文关键词改为 LLM 判断

**现状**：`run_sql.py` 和 `generate_sql.py` 用硬编码中文列表判断用户是否需要图表。

**改法**：

- 在 `generate_sql` 的 prompt 指令中加入"判断用户是否期望图表输出"，让 LLM 决定
- 或做成可配置的 `CHART_KEYWORDS` 列表，支持多语言

**影响文件**：`app/agent/nodes/generate_sql.py`, `app/agent/nodes/run_sql.py`

---

## P3 — 顺手修复

### 12. 清理 Graph 文件底部的 `__main__` 测试代码

**现状**：`app/agent/graph.py`、`app/rag/graph.py`、`app/clients/mysql_client_manager.py`、`app/conf/app_config.py` 等文件底部包含大段 `if __name__ == "__main__"` 测试代码。

**改法**：删除这些代码块，真实的集成测试移至 `tests/` 目录下。

---

### 13. 添加健康检查端点

```python
@app.get("/health")
async def health():
    return {"status": "ok", "services": {"mysql": ..., "qdrant": ..., "es": ...}}
```

---

### 14. 删除未使用的模块

**现状**：

- `app/repositories/__init__.py` 内容为空
- `app/cache/__init__.py` 内容为空
- `app/reports/miner.py` 与 `app/reports/executor.py` 中的 `extract_knowledge_from_report` 是重复定义（同名函数在两处出现）

**改法**：清理未使用的占位文件，删除重复代码。

---

## 实施建议

### 阶段 1（优先做）

1. P0 #3 — 修复 SQL 注入（改动最小，安全风险最高）
2. P0 #1 — 依赖注入重构（改动最大，是整个项目可测性的基础）
3. P1 #4 — 消除沉默异常（配合 #1 一次性改完）

### 阶段 2

4. P0 #2 — 文件存储迁移到数据库
5. P1 #5 — 修复 sync/async 混用
6. P1 #6 — SQL 安全审计增强

### 阶段 3

7. P1 #7 — 解耦节点职责
8. P2 以下所有问题

---

_生成日期：2026-06-22_
