from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeEntry:
    title: str
    definition: str
    tables: list[str] = field(default_factory=list)
    example_sql: str = ""
    tags: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = ""
    status: str = "approved"  # pending / approved / rejected


KNOWLEDGE_HEADER_TEMPLATE = """# {title}

## 定义
{definition}

## 涉及表
{tables_section}

## 示例SQL
```sql
{example_sql}
```

## 标签
[{tags_str}]

## 元数据
- 创建时间：{created_at}
- 创建者：{created_by}
- 审核状态：{status}
"""
