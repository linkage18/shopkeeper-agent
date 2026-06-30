# Shopkeeper Agent — 项目启动指南

---

## 第 1 步：启动依赖服务（Docker）

```bash
cd D:\PythonProject\LLM\shopkeeper-agent-main
docker compose -f docker/docker-compose.yaml up -d
```

这会启动 4 个基础服务：

| 服务 | 端口 | 用途 |
|------|------|------|
| MySQL 8.0 | `3307` | 元数据库 + 数据仓库 |
| Elasticsearch | `9200` | BM25 全文检索（值匹配召回） |
| Qdrant v1.16 | `18933` (HTTP) / `18934` (gRPC) | 向量检索（字段/指标语义召回） |
| BGE Embedding | `8081` | 中文文本向量化（bge-large-zh-v1.5） |

验证容器全部启动：

```bash
docker ps
```

预期看到 5 个容器：`mysql`、`elasticsearch`、`kibana`、`qdrant`、`embedding`，状态均为 `Up`。

---

## 第 2 步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填入 LLM API Key：

```
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx   # DeepSeek 或其他兼容 OpenAI 的 API Key
JWT_SECRET=shopkeeper-dev-secret  # 开发环境可保持不变
```

---

## 第 3 步：安装 Python 依赖

```powershell
# 创建虚拟环境（Python 3.12+）
uv venv

# 激活虚拟环境
.\.venv\Scripts\activate

# 安装项目依赖
uv sync
```

---

## 第 4 步：构建元数据知识库

```bash
python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

这一步读取 `conf/meta_config.yaml` 中定义的表结构、字段、指标，将元数据写入三处：

- **MySQL meta 库**：存储表结构、字段类型、主外键关系
- **Qdrant 向量库**：为每个字段名/描述/别名生成向量点，供语义召回
- **ES 全文索引**：存储字段取值样例，供精确值匹配

输出示例：

```
INFO - 表信息和字段信息写入 Meta MySQL
INFO - 为字段信息生成向量索引
INFO - 为字段取值建立全文索引
INFO - 指标信息写入数据库成功
INFO - 为指标信息生成向量索引成功
```

> ⚠️ 如报错 `Duplicate entry ... for key 'PRIMARY'`，说明之前已构建过，需先清空元数据表再重建：

```bash
docker exec mysql mysql -u didilili -pdili123 meta -e "TRUNCATE TABLE column_info; TRUNCATE TABLE column_metric; TRUNCATE TABLE table_info; TRUNCATE TABLE metric_info;"
```

---

## 第 5 步：启动后端

```bash
uvicorn main:app --reload --port 8000
```

启动后访问：

- **Swagger API 文档**：`http://localhost:8000/docs`
- **健康检查**：`http://localhost:8000/health`

预期健康检查返回：

```json
{"status":"ok","services":{"mysql_meta":"ok","mysql_dw":"ok","qdrant":"ok","es":"ok"}}
```

---

## （可选）启动前端

```bash
cd frontend
pnpm install
pnpm run dev
```

前端开发服务器运行在 `http://localhost:5173`，会自动代理 `/api` 请求到后端 `localhost:8000`。

---

## 快速验证

### 健康检查

```bash
curl http://localhost:8000/health
```

### 登录获取 token

```bash
curl -X POST http://localhost:8000/api/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

### 执行一条 NL2SQL 查询

```bash
curl -X POST http://localhost:8000/api/query ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <your-token>" ^
  -d "{\"query\":\"按字母升序排列的所有专辑的标题是什么？\"}"
```

### 跑冒烟测试

```bash
python tests/smoke_test.py
```

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `build_meta_knowledge` 连接失败 | Docker 容器未就绪 | `docker ps` 检查容器状态，等待服务启动 |
| `Duplicate entry` 主键冲突 | 元数据表已有数据 | 先 TRUNCATE 表再重建（见第 4 步） |
| 登录返回 401 | 默认账号不存在 | 检查 MySQL `meta.users` 表是否有初始数据 |
| 查询返回空 SQL | LLM API Key 无效或 Embedding 服务未启动 | 检查 `.env` 中的 `LLM_API_KEY` |

---

> 基于 Shopkeeper Agent 项目源码，2025-06
