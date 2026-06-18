# 记忆系统设计方案 — Memory System Spec

## 一、概述

当前知识记忆系统（`app/knowledge/`）仅有单层 MD 文件存储。升级为 **分层记忆架构**，按时效性和作用域分为三层：

```
短期记忆（Short-Term Memory）  ← 当前会话上下文
  │  自动管理，无需持久化
  ▼
长期记忆（Long-Term Memory）   ← 跨会话复用的结构化知识
  │  LLM 自动提取 + 管理员审核
  ▼
持久记忆（Persistent Memory）  ← 系统级规则与口径
  │  人工定义，不可被 LLM 覆盖
```

## 二、分层架构

### 2.1 短期记忆（Session Memory）

| 属性 | 说明 |
|------|------|
| 存储 | `data/sessions/{session_id}.jsonl`（现有） |
| 内容 | 当前对话轮次、用户问题、Agent 回答、中间检索结果 |
| 生命周期 | 会话结束或 24h 后自动清理 |
| 检索方式 | 直接按 session_id 读取完整 JSONL |
| 容量 | 默认保留最近 6 轮对话 |

**优化点**：
- 增加 `summary` 字段（已有）：每轮对话后 LLM 生成摘要，会话恢复时优先使用摘要
- 增加 `intent` 标签：标记本轮是 "sql"/"rag"/"analysis"，便于分类检索

### 2.2 长期记忆（Long-Term Memory）

| 属性 | 说明 |
|------|------|
| 存储 | `data/knowledge/shared/` + `data/knowledge/private/{user_id}/` |
| 内容 | 业务口径定义、字段别名映射、指标计算规则 |
| 生命周期 | 永久保存，除非管理员删除 |
| 检索方式 | 全文搜索 + Qdrant 向量语义搜索 |
| 审核机制 | 新条目状态为 `pending`，管理员审核后改为 `approved` |

**分层子类型**：

```
knowledge/
├── shared/                    # 共享记忆（所有人可见，管理员可改）
│   ├── definitions/           # 业务口径定义（如：留存率=...）
│   ├── metrics/               # 指标说明（如：GMV = SUM(order_amount)）
│   └── mappings/              # 同义词映射（如：销售额↔GMV↔order_amount）
└── private/{user_id}/         # 私有记忆（仅用户自己可见）
    ├── favorites/             # 用户收藏的查询
    └── aliases/               # 用户自定义别名
```

**新增子目录结构**：
```
data/knowledge/
├── shared/
│   ├── definitions/
│   │   ├── 留存率定义.md
│   │   └── 转化率定义.md
│   ├── metrics/
│   │   ├── GMV.md
│   │   └── AOV.md
│   └── mappings/
│       ├── 销售额.md
│       └── 地区名称.md
└── private/
    └── {user_id}/
        ├── favorites/
        │   └── 常用查询.md
        └── aliases/
            └── 我的别名.md
```

### 2.3 持久记忆（Persistent Memory）

| 属性 | 说明 |
|------|------|
| 存储 | MySQL meta 库（`memory_persistent` 表） |
| 内容 | 系统级规则、数据权限、安全策略 |
| 生命周期 | 永久，仅管理员可通过后台修改 |
| 检索方式 | 直接 SQL 查询 |
| 优先级 | 高于长期记忆，不可被 LLM 自动覆盖 |

**存储结构**：

```sql
CREATE TABLE memory_persistent (
    id         VARCHAR(64) PRIMARY KEY,
    category   VARCHAR(32) NOT NULL,   -- rule / security / permission
    name       VARCHAR(128) NOT NULL,
    content    TEXT NOT NULL,
    priority   INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 三、写入流程

### 3.1 短期记忆写入

```
用户输入 → Agent 执行 → 生成回答
  → hooks.py → append to data/sessions/{session_id}.jsonl
  → 更新 session_summary（LLM 压缩历史）
```

现有逻辑在 `app/rag/hooks.py`，无需改动。

### 3.2 长期记忆写入（LLM 自动提取）

```
每次 Agent 执行完毕后：
  → extractor.py 判断本轮是否有"有价值的知识"
  → 规则：用户明确给出定义/口径/规则，或 Agent 修正了自己的错误
  → 如果有：
      → LLM 提取结构化信息（标题 + 定义 + 涉及表 + 示例SQL + 标签）
      → 写入 data/knowledge/shared/definitions/{title}.md
      → 状态标记为 pending
      → 通知管理员审核
```

**提取 prompt 示例**：

```
判断以下对话中是否包含有价值的业务知识定义。

用户问题：{query}
Agent 生成的 SQL：{sql}
查询结果：{result}

如果有业务口径、指标定义、规则说明等，以JSON格式输出：
{"has_knowledge": true, "title": "...", "definition": "...", 
 "tables": [...], "example_sql": "...", "tags": [...]}

如果没有，返回 {"has_knowledge": false}
```

### 3.3 持久记忆写入（仅管理员）

```
管理员 → 登录（role=admin）
  → POST /api/memory/persistent
  → MySQL memory_persistent 表写入
  → 下次查询自动注入 system prompt
```

## 四、检索流程

### 4.1 多级级联检索

```
用户输入 query
  │
  ├─ 1. 持久记忆检索（MySQL）
  │   → 命中规则/权限 → 注入 system prompt（最高优先级）
  │
  ├─ 2. 长期记忆检索（文件系统 + Qdrant 向量）
  │   → 全文搜索 definitions + metrics + mappings
  │   → Qdrant 语义搜索（标题和标签）
  │   → 合并结果，按得分排序
  │
  ├─ 3. 短期记忆检索（JSONL）
  │   → 当前会话的最近 6 轮上下文
  │   → session_summary
  │
  └─ 4. 综合注入
      → 持久记忆 + 长期记忆 Top-5 + 短期记忆摘要
      → 拼入 system prompt 的 [知识参考] 部分
```

### 4.2 检索优先级

```
持久记忆 > 长期记忆中 status=approved > 长期记忆中 status=pending > 短期记忆
```

优先级由 `priority` 字段控制，持久记忆的 `priority=100`，长期记忆 `priority=50`，短期记忆 `priority=10`。

## 五、接口设计

### 5.1 长期记忆 API（已有 + 扩展）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/knowledge/list` | 列出所有知识 | user |
| GET | `/api/knowledge/get/{title}` | 获取单条知识 | user |
| GET | `/api/knowledge/search?q=` | 搜索知识 | user |
| POST | `/api/knowledge/save` | 新增/编辑知识 | admin（shared）/ user（private） |
| DELETE | `/api/knowledge/delete/{title}` | 删除知识 | admin（shared）/ user（private） |
| POST | `/api/knowledge/approve` | 审核通过（pending→approved） | admin |
| GET | `/api/knowledge/pending` | 列出待审核条目 | admin |

### 5.2 持久记忆 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/memory/persistent` | 列出持久记忆 | admin |
| POST | `/api/memory/persistent` | 新增/编辑持久记忆 | admin |
| DELETE | `/api/memory/persistent/{id}` | 删除持久记忆 | admin |

## 六、数据流图

```
用户查询
  │
  ▼
┌─────────────────────────────────────────────┐
│              Memory Retriever               │
│                                             │
│  1. MySQL → Persistent Memory              │
│     (规则/权限/安全策略)                    │
│                                             │
│  2. FileSystem + Qdrant → Long-Term Memory │
│     (definitions/metrics/mappings)          │
│     → 过滤 status=approved                  │
│     → 按 priority 排序                     │
│                                             │
│  3. JSONL → Short-Term Memory              │
│     (当前会话上下文 + summary)             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
            System Prompt 组装
  [知识参考]
  持久记忆内容
  长期记忆 Top-5
  短期记忆摘要
  
  [用户问题]
  {query}
                      │
                      ▼
               Agent 执行
                      │
                      ▼
            Extractor（后处理）
  判断是否有关键知识 → 写入长期记忆（pending）
```

## 七、目录结构变更

```
app/
├── memory/                     # 新增：记忆系统总模块
│   ├── __init__.py
│   ├── short_term.py          # 短期记忆（封装现有 session hooks）
│   ├── long_term.py           # 长期记忆（封装现有 knowledge manager）
│   ├── persistent.py          # 持久记忆（MySQL）
│   ├── retriever.py           # 多级级联检索
│   └── router.py              # 持久记忆 API
├── knowledge/                  # 长期记忆（已有，增强子目录分层）
└── ...
```

## 八、存储对比

| 维度 | 短期记忆 | 长期记忆 | 持久记忆 |
|------|---------|---------|---------|
| 存储介质 | JSONL 文件 | MD 文件 + Qdrant | MySQL |
| 数据量 | 几百 KB/会话 | MB 级 | KB 级 |
| 写入频率 | 每轮对话 | 每次有价值对话后 | 极少（管理员操作） |
| 读取频率 | 每轮对话 | 每次查询 | 每次查询 |
| 一致性要求 | 低 | 中 | 高 |
| 备份策略 | 无需备份 | Git 版本管理 | MySQL 定期备份 |
| 并发写入 | 低（单用户） | 低 | 极低 |
