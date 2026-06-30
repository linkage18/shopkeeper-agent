# Shopkeeper Agent — 面试100问（全覆盖）

> 项目：Shopkeeper Agent（电商智能问数与知识库助手）  
> 分类：计算机基础 / 八股 / 场景 / 项目设计与工程化 / HR  
> 每题均从本项目的实际代码、架构和设计决策出发

---

## 一、计算机基础（20问）

### 1. 协程 vs 普通函数的本质区别是什么？项目里哪里用到了协程？
**考察点**: async/await 理解  
**参考**: 项目中所有 Agent 节点都是 `async def`，LangGraph `graph.astream()` 是异步的；FastAPI 路由均为 async；`asyncio.gather` 并发召回三路数据。

### 2. 事件循环（Event Loop）在 FastAPI 中是如何工作的？为什么一个线程能同时处理多个请求？
**考察点**: 事件循环机制  
**参考**: Uvicorn 主线程运行 asyncio event loop，每个请求对应一个协程，遇到 `await`（如数据库查询）就挂起，事件循环切换到其他协程。

### 3. ContextVar 和全局变量有什么区别？项目里 request_id 为什么用 ContextVar 而不是函数参数传递？
**考察点**: ContextVar 原理  
**参考**: `app/core/context.py` 中 `request_id_ctx_var`，每个协程有独立"背包"，并发不串值。

### 4. HTTP SSE（Server-Sent Events）和 WebSocket 的区别？本项目为什么选 SSE？
**考察点**: 网络协议选型  
**参考**: 项目需要单向推送（服务端→前端进度/结果），不需要双向通信。SSE 基于 HTTP，实现更简单，复用现有中间件。

### 5. SQL 注入的原理是什么？项目里用了哪几层防护？
**考察点**: 安全基础  
**参考**: 三层防护——① 路由层正则拦截 DML/DDL 关键词；② sqlglot AST 白名单只放行 SELECT；③ MySQL 只读账号。见 `run_sql.py` `_assert_readonly_sql`。

### 6. 什么是向量检索？Qdrant 中余弦相似度（Cosine Similarity）如何计算？
**考察点**: 向量检索基础  
**参考**: cosine(A,B) = A·B / (|A|×|B|)，范围 [-1,1]，项目用于 column/metric 语义召回，threshold 通常 >0.7。

### 7. BM25 是什么？它和向量检索各有什么优劣？
**考察点**: 全文检索 vs 语义检索  
**参考**: BM25 是 TF-IDF 的升级版，擅长精确关键词匹配（如专有名词、ID），向量检索擅长语义匹配（如"销售额"→"order_amount"）。项目用 ES 做 BM25，Qdrant 做向量，互补。

### 8. 数据库索引的 B+Tree 结构为什么适合范围查询？MySQL InnoDB 的主键索引和数据是怎么存的？
**考察点**: 数据库存储引擎  
**参考**: B+Tree 叶子节点形成有序链表，范围扫描高效。InnoDB 聚簇索引：主键索引的叶子节点直接存整行数据。

### 9. JWT 的认证流程是怎样的？项目里 access_token 存在哪？过期了怎么办？
**考察点**: 认证机制  
**参考**: `app/auth/jwt.py` 签发 JWT，`main.py` 中间件解析 Bearer token 写入 `request.state.user`。当前无 refresh token 机制（原型级）。

### 10. RESTful API 设计原则有哪些？`/api/query` 和 `/api/rag/query` 为什么都用 POST 而不是 GET？
**考察点**: API 设计  
**参考**: 查询可能涉及复杂 body（长文本、history），超过 URL 长度限制。POST 也更安全，不会在 URL 中暴露查询内容。

### 11. 进程和线程的区别？Python 的 GIL 对异步编程有影响吗？
**考察点**: OS 基础 + Python 特性  
**参考**: GIL 限制同一时刻只有一个线程执行 Python 字节码，但 async/await 是单线程协程切换，不受 GIL 影响。IO 密集型用 async，CPU 密集型用多进程。

### 12. Docker 容器和虚拟机的区别？`docker-compose.yaml` 中多个服务之间如何通信？
**考察点**: 容器化基础  
**参考**: 容器共享宿主机内核，轻量；VM 独立 OS。docker-compose 通过 service name 做 DNS 解析，如 MySQL 用 `mysql_meta:3307`。

### 13. 什么是幂等性？`build_meta_knowledge.py` 中的元数据构建是幂等的吗？
**考察点**: 幂等性理解  
**参考**: 当前不是幂等的——主键重复会报错。应改为 upsert 或先清库再写入。

### 14. TCP 三次握手和四次挥手的过程？为什么三次不是两次？
**考察点**: 网络基础  
**参考**: 三次握手确保双方收发能力正常（防止历史连接）。项目中的 MySQL/Qdrant/ES 连接池底层都是 TCP。

### 15. 哈希表（Hash Table）的时间复杂度是多少？Python dict 的底层实现是什么？
**考察点**: 数据结构  
**参考**: 平均 O(1)。Python dict 使用开放寻址法 + 随机探测。项目中 `exact_cache` 用 dict 做内存缓存。

### 16. 正则表达式 (a|b)* 能匹配什么？项目中用正则做了哪些事？
**考察点**: 正则基础  
**参考**: 匹配 a 和 b 的任意组合（包括空串）。项目用正则做 SQL 破坏性操作拦截和 Prompt 注入检测。

### 17. JSON 序列化时遇到 Decimal/Set 类型怎么办？项目里如何解决？
**考察点**: 数据序列化  
**参考**: `report_agent/router.py` 中 `_default_json` 函数处理 Decimal→float, set→list。

### 18. N+1 查询问题是什么？SQLAlchemy 中如何避免？
**考察点**: ORM 性能  
**参考**: 关联查询时每条记录触发一次额外查询。用 `selectinload`/`joinedload` 预加载。项目中 Repository 层用 raw SQL 而非 ORM 关系，避免了 N+1。

### 19. 什么是死锁？数据库事务隔离级别有哪些？
**考察点**: 数据库并发  
**参考**: 项目使用 MySQL InnoDB 默认 REPEATABLE READ。`async with session.begin()` 确保事务边界清晰，降低死锁风险。

### 20. CPU 缓存（L1/L2/L3）和主存的访问速度差多少数量级？这对程序优化有什么启示？
**考察点**: 计算机体系结构  
**参考**: L1 ~1ns，主存 ~100ns，差两个数量级。启示：减少 cache miss，数据局部性。向量检索中连续内存访问比随机访问快得多。

---

## 二、八股题（25问）

### 21. 详细解释 async/await 的工作原理，包括事件循环、协程挂起和恢复的完整过程。
**考察点**: Python 异步深度  
**参考**: `app/agent/nodes/*.py` 中每个节点都是 `async def`。`await` 将控制权交还 event loop，loop 轮询 IO 就绪的协程恢复执行。

### 22. LangGraph 的 StateGraph 和普通 Chain 有什么区别？什么场景用哪个？
**考察点**: Agent 框架理解  
**参考**: Chain 是线性的；StateGraph 支持条件分支（条件边）、并行（fan-out/fan-in）、循环。项目 NL2SQL 需要并行召回 + SQL 校验失败回环，必须用 StateGraph。

### 23. FastAPI 的依赖注入（Depends）是如何实现的？和 Spring 的 DI 有什么区别？
**考察点**: 框架原理  
**参考**: FastAPI 通过参数签名递归解析依赖树，函数式注入。Spring 是类/注解式。项目 `dependencies.py` 中 Session→Repository→Service 逐级组装。

### 24. 向量数据库 Qdrant 和传统数据库 MySQL 的核心区别？什么数据适合放向量库？
**考察点**: 数据库选型  
**参考**: Qdrant 存高维向量做 ANN 近似最近邻搜索，适合语义相似度匹配；MySQL 存结构化数据做精确查询和 JOIN。项目：column/metric 语义信息 → Qdrant，表字段结构化信息 → MySQL。

### 25. Elasticsearch 的倒排索引原理？为什么 ES 检索比 MySQL LIKE 快？
**考察点**: 搜索引擎原理  
**参考**: 倒排索引：词→文档列表的映射，O(1) 定位。MySQL LIKE 是逐行扫描。项目 ES 存 value 真实取值做全文索引。

### 26. BGE Embedding 模型的输出是什么？为什么 "销售额" 和 "order_amount" 的向量很接近？
**考察点**: Embedding 原理  
**参考**: BGE-large-zh-v1.5 输出 1024 维浮点向量。训练时通过对比学习让语义相近文本的向量距离更近。

### 27. LangGraph 中 State 和 Context 分别放什么？为什么 Context 里的 Repository 不可序列化？
**考察点**: 状态管理设计  
**参考**: State=可序列化的业务数据（query, keywords, sql, result），会推前端；Context=不可序列化的运行时依赖（Repository, Embedding client），只在图内传递。

### 28. Runtime 在 LangGraph 中是什么角色？stream_writer 和 Runtime 的关系？
**考察点**: LangGraph 内部机制  
**参考**: Runtime 是 LangGraph 自动生成的执行期上下文对象，每个 `astream()` 调用创建独立实例。`stream_writer` 是 Runtime 的属性，是节点→调用方推送 SSE 的通道。

### 29. jieba 分词的 TF-IDF 算法原理？为什么用 `allowPOS` 过滤词性？
**考察点**: NLP 基础  
**参考**: TF-IDF = 词频 × 逆文档频率，提取关键实词。`allowPOS` 过滤掉"的""了"等虚词，保留名词、动词、形容词，提高关键词质量。

### 30. sqlglot 如何解析 SQL？为什么要全 AST 遍历而不是正则判断？
**考察点**: SQL 解析  
**参考**: sqlglot 将 SQL 文本解析为 AST 语法树。正则可能被绕过（如注释中嵌入、字符串拼接），AST 保证无死角遍历每个节点类型。

### 31. 什么是幻读、不可重复读、脏读？MySQL 默认隔离级别防止了哪些？
**考察点**: 事务隔离  
**参考**: 脏读=读到未提交；不可重复读=同事务两次读结果不同；幻读=范围查询新增/删除行。REPEATABLE READ 防脏读和不可重复读，通过间隙锁部分防幻读。

### 32. asyncio.gather 和 asyncio.wait 的区别？项目里为什么用 gather 做并行召回？
**考察点**: 异步并发  
**参考**: gather 按参数顺序返回结果列表，更简洁，支持 `return_exceptions=True` 让单个失败不抛异常。项目中 Qdrant 和 ES 两路并发用 `gather`，各自容错。

### 33. Python 的 `async with` 和普通 `with` 有什么区别？项目里怎么用的？
**考察点**: 异步上下文管理器  
**参考**: `async with` 的 `__aenter__`/`__aexit__` 是协程，数据库 `session.begin()` 需要异步提交/回滚。项目 `dependencies.py` 大量使用。

### 34. Pydantic 模型的作用是什么？和 dataclass 有什么区别？
**考察点**: 数据校验  
**参考**: Pydantic 支持自动类型校验、JSON Schema 生成、序列化。项目 `QuerySchema` 用 Pydantic 做请求体验证，实体数据用 dataclass（轻量，不依赖框架）。

### 35. 什么是连接池？SQLAlchemy 的连接池默认大小是多少？项目如何管理？
**考察点**: 数据库连接管理  
**参考**: 连接池复用数据库连接，避免频繁创建/销毁。默认 pool_size=5。项目在 `lifespan` 中初始化 engine，请求级创建 Session，请求结束归还连接。

### 36. YAML 和 JSON 配置文件的优劣？项目为什么用 YAML 做配置？
**考察点**: 配置文件格式  
**参考**: YAML 支持注释、引用、多行字符串，人可读性好。项目 `meta_config.yaml` 有大量字段注释和别名，YAML 更合适。

### 37. Python 的 `__init__.py` 文件作用？项目里你怎么组织的？
**考察点**: Python 包管理  
**参考**: 标识目录为 Python 包，可定义 `__all__` 控制导出。项目每个模块都有 `__init__.py`，agent 层的 state/context 在 `__init__.py` 中统一导出。

### 38. 什么是熔断器（Circuit Breaker）模式？项目里怎么实现的？
**考察点**: 容错模式  
**参考**: 连续失败超过阈值自动"熔断"，快速失败而不继续调用。项目 `rag/metrics.py` 中 Qdrant/ES 各自独立计数，两路都熔断则跳过检索返回空。

### 39. SSE 的 `text/event-stream` MIME 类型是什么含义？前端 fetch 如何解析？
**考察点**: SSE 协议  
**参考**: 声明这是一个事件流。前端 `ReadableStream.getReader()` 逐块读取，按 `data:` 行分割，JSON.parse 后更新 React 状态。

### 40. Git 的 `.gitignore` 忽略规则？`.env` 文件为什么不能提交？
**考察点**: 版本控制实践  
**参考**: `.env` 含 LLM_API_KEY 等敏感信息。项目 `.gitignore` 中包含 `.env`、`__pycache__`、`node_modules`、venv 等。

### 41. 延迟和吞吐量有什么区别？优化系统时你优先哪一个？
**考察点**: 性能指标  
**参考**: 延迟=单次响应时间，吞吐量=单位时间处理请求数。NL2SQL 场景优先延迟（用户等待），批处理优先吞吐。

### 42. Python 的 `typing` 模块里 `TypedDict` 和普通 dict 有什么区别？
**考察点**: 类型注解  
**参考**: TypedDict 定义 dict 的键和值类型，IDE 自动补全，mypy 做静态检查。项目 State 和 Context 都用 TypedDict。

### 43. SQLAlchemy 的 `AsyncSession` 和 `Session` 的区别？异步的好处？
**考察点**: 异步 ORM  
**参考**: AsyncSession 不阻塞事件循环，await 数据库操作时可以让出线程处理其他请求。FastAPI async 路由必须用 AsyncSession。

### 44. 什么是过拟合？机器学习中如何防止？
**考察点**: ML 基础  
**参考**: 训练集效果好但测试集差。防止方法：正则化、Dropout、早停、数据增强。项目 BGE 模型本身是预训练好的，不在本项目微调。

### 45. Round-Robin 和最少连接数（Least Connection）负载均衡各有何优劣？
**考察点**: 分布式基础  
**参考**: RR 简单但不考虑服务器负载差异；LC 更合理但需要维护连接计数。项目当前单实例，未涉及。

---

## 三、场景题（20问）

### 46. 用户输入"上个月华东区各品牌的销售额，按从高到低排序"——请描述从 HTTP 请求到返回结果的完整调用链路。
**考察点**: 全链路理解  
**参考**: POST `/api/intent/classify` → 识别为 sql → POST `/api/query` → QueryService 组装 State+Context → LangGraph 11节点 → SSE 推前端。

### 47. LLM 生成的 SQL 中，字段名 `order_amount` 写成了 `sales_amount`，系统会怎么处理？
**考察点**: SQL 校验修正闭环  
**参考**: validate_sql 执行 EXPLAIN 报错 "Unknown column 'sales_amount'" → 错误信息写入 State → 条件路由判断 retry_count<2 → correct_sql 节点将错误+上下文传给 LLM 修正 → 回到 validate_sql 重新校验。

### 48. 如果 Qdrant 服务宕机了，用户的 NL2SQL 查询还能正常执行吗？
**考察点**: 容错设计  
**参考**: 不能。column/metric 召回强依赖 Qdrant 向量检索。但 RAG 链路有熔断机制——Qdrant 失败不影响 ES 那路，两路皆失败则返回空。NL2SQL 当前缺少类似容错。

### 49. 用户说"帮我查一下苹果的销量"，但"苹果"在数据库里是品牌还是商品名？系统怎么分辨？
**考察点**: 语义消歧  
**参考**: 关键词抽取 → 三路并行召回中，value 召回走 ES 全文检索，会匹配到品牌维表的真实取值 "苹果"，column 召回匹配 "product_name" 等字段。如果两者都匹配，merge 节点会按置信度排序，LLM 过滤节点做最终裁决。

### 50. 知识库里有 1000 个 MD 文档，用户问"公司的请假制度是什么"，RAG 怎么找到正确的那份文档？
**考察点**: RAG 检索链路  
**参考**: jieba 提取关键词 ("请假", "制度") → Qdrant 向量检索语义匹配 + ES BM25 精确匹配 "请假" → 子块命中 → 回溯父块 → 按分数排序，top-K 截断 → 组装上下文 → LLM 生成回答。

### 51. 前端展示 SSE 进度时，如果网络断开 3 秒后重连，进度会丢失吗？
**考察点**: 网络异常处理  
**参考**: 当前实现会丢失。SSE 是单向推送，没有断点续传。改进方案：服务端保存 session 状态，前端 reconnect 时传 last_event_id，服务端从断点继续推。

### 52. 用户连续 5 次问"统计各大区 GMV"，每次都走完整 11 节点链路吗？有什么优化方案？
**考察点**: 缓存策略  
**参考**: 当前每次都走完整链路。可用语义缓存：`semantic_cache_search` 在 Qdrant 中查相似 query，余弦相似度 >0.95 直接返回缓存结果，跳过 LangGraph。

### 53. 数据库表结构新增了一列 `discount_amount`，需要修改哪些配置和代码？
**考察点**: 元数据维护  
**参考**: 修改 `conf/meta_config.yaml` 添加字段定义 → 运行 `build_meta_knowledge.py` 同步到 MySQL meta 库 + Qdrant。代码无需修改（配置驱动）。

### 54. 用户问"最近一周的销售趋势"，但 `dim_date` 表最新只到 2025-03-31，系统应该怎么响应？
**考察点**: 边界条件处理  
**参考**: `add_extra_context` 节点补充当前日期信息 → LLM 生成 SQL 时自动定位可用时间范围 → 如果超出范围，结果为空，SQL 执行节点返回空数组。报告链路会主动 ask_user 而非强行总结。

### 55. 前端用户上传了一个 10MB 的 PDF 文档到知识库，系统如何处理？
**考察点**: RAG 入库流程  
**参考**: POST `/api/rag/upload` → 按标题/空行切分父块 → 父块写入 Qdrant placeholder → 父块切成 256 token 子块 → BGE Embedding（batch=10）→ 子块向量写入 Qdrant + 全文写入 ES → 返回块数量。

### 56. 两个用户同时问问题，其中一个的 ContextVar 里的 request_id 会串到另一个吗？
**考察点**: 并发安全  
**参考**: 不会。每个请求绑定到不同的协程，ContextVar 按协程隔离存储，互不影响。

### 57. 用户输入"帮我生成一份 Q1 销售分析报告"，系统内部会经历哪些步骤？
**考察点**: Report Agent 流程  
**参考**: 读取 Schema → 记忆检索 → LLM 规划（SQL列表+Python预处理+图表配置）→ 执行 SQL → 检查结果是否为空 → Python 沙箱处理 → 构建图表 → 生成 Markdown 报告 → SSE 推送。

### 58. 如果 Python 沙箱中的代码包含 `import os; os.system("rm -rf /")`，系统能否拦截？
**考察点**: 安全沙箱  
**参考**: `sandbox.py` 中 `_check_safety` 会检测关键字 "os"、"subprocess" 等，抛 SandboxError。且 `exec` 的 builtins 被白名单限制，`__import__` 不可用。

### 59. 用户意图分类出错——把"什么是 GMV"分类为 sql 而不是 rag，会怎样？
**考察点**: 意图分类容错  
**参考**: intent router 分类错误会导致 NL2SQL Agent 尝试找表和字段，但"什么是"没有数据字段匹配，最终可能返回空或低质量 SQL。需要完善 intent 训练数据。

### 60. 系统运行一个月后查询越来越慢，可能是什么原因？怎么排查？
**考察点**: 性能诊断  
**参考**: 可能原因：Qdrant 集合膨胀、ES 索引碎片化、MySQL 表数据增长无索引、内存缓存未清理。排查：看 `/health` 端点各服务状态、分析 `rag_metrics` 各阶段耗时、检查慢查询日志。

### 61. 如果公司要部署到生产环境，还需要补充哪些？
**考察点**: 生产化意识  
**参考**: Nginx 反向代理、HTTPS、进程守护（supervisor/systemd）、环境变量管理、日志采集（ELK）、监控告警（Prometheus）、数据库备份、限流、容器健康检查。

### 62. 用户说"帮我查上个月卖了多少"，但系统中记录的是"销售额"，不是"卖了多少"，怎么处理？
**考察点**: 语义映射  
**参考**: jieba 关键词抽取 → LLM 扩展同义词（"卖了多少"→"销售额""GMV""order_amount"）→ Qdrant 向量检索匹配 `order_amount` 字段 → 和 `metric_info` 中的 GMV 定义匹配。

### 63. 一个恶意用户每秒发 1000 次请求，系统有哪些防护？
**考察点**: 限流和安全  
**参考**: `cache/services.py` 中 `check_rate_limit` 是内存字典，30次/60秒/单进程。原型级防护。生产需要 Redis 分布式限流 + Nginx limit_req + WAF。

### 64. SQL 安全校验只放行 SELECT，但 business 用户需要跑 INSERT 怎么办？
**考察点**: 权限设计  
**参考**: NL2SQL 是只读查询系统。写操作应走独立的数据录入/管理模块，使用不同的数据库账号和权限，不在问数 Agent 中支持。

### 65. 给新人介绍这个项目，你会怎么用一个数字或概念让他们秒懂这个项目解决了什么问题？
**考察点**: 沟通表达  
**参考**: "把查数据从提工单等半天，变成像聊天一样 5 秒出结果。"

---

## 四、项目设计与工程化（25问）

### 66. 为什么用 LangGraph 而不是直接 11 个函数顺序调用？
**考察点**: 框架选型  
**参考**: 普通函数串联做不到条件回环（SQL 校验失败→修正→重新校验），也做不到三路并行召回 + 合并。LangGraph 的条件边和 fan-out/fan-in 天然支持。

### 67. State 和 Context 为什么要分离？如果全放 State 里有什么问题？
**考察点**: 架构设计  
**参考**: State 序列化为 JSON 推前端，Context 中的 Repository 含数据库连接不可序列化。分离后测试可 mock Context，节点不感知全局依赖。

### 68. 三路召回（column / metric / value）为什么要并行而不是串行？
**考察点**: 性能优化  
**参考**: 三条路完全独立，串行会增加总延迟（三次网络往返叠加）。并行用 `asyncio.gather` 同时发送，总耗时≈最慢的那路。

### 69. 为什么不直接把 `meta_config.yaml` 喂给 LLM，而是构建元数据知识库？
**考察点**: 系统设计  
**参考**: YAML 是同步清单，不含运行时信息（字段类型、真实取值）。知识库能向量检索语义匹配字段，ES 做值域匹配。如果每次读 YAML，无法做语义搜索。

### 70. 项目中 Entity、ORM Model、Mapper、Repository、Service 各层分别承担什么职责？为什么分这么多层？
**考察点**: 分层架构  
**参考**: Entity=业务通用对象；ORM Model=MySQL 表映射；Mapper=Entity↔ORM 转换；Repository=封装存储访问；Service=编排完整流程。分层后换存储只需改 Repository。

### 71. `lifespan` 中初始化客户端连接 vs 每个请求创建连接，各有什么优劣？项目怎么选的？
**考察点**: 连接管理  
**参考**: 项目在 `lifespan` 启动时初始化 Qdrant/ES/MySQL engine（复用连接池），请求级创建 Session（事务边界清晰）。启动创建减少频繁连接开销。

### 72. 语义缓存（Semantic Cache）和精确缓存（Exact Cache）的区别？项目两套都实现了吗？
**考察点**: 缓存设计  
**参考**: 精确缓存：相同 query 哈希匹配，命中快但变体不命中。语义缓存：Embedding 相似度匹配，"查GMV"能命中"统计GMV"。项目两套都实现了（`cache/services.py`）。

### 73. schema_analyzer 为什么用 600 秒的内存缓存而不是每次都查 MySQL？
**考察点**: 缓存策略  
**参考**: 表结构变更频率低，每次都查是浪费。600 秒 TTL + 手动 `clear_schema_cache()` 做失效，平衡实时性和性能。

### 74. document chunk 的父子块切分策略是什么？为什么检索用子块，回答用父块？
**考察点**: RAG 切分策略  
**参考**: 子块 256 token 粒度小命中准，但上下文不完整；父块是一段完整内容，信息充足。检索命中子块后回溯父块，兼顾精度和完整性。

### 75. Qdrant 和 ES 的召回分数如何归一化合并？
**考察点**: 分数融合  
**参考**: Qdrant 余弦相似度 [0,1] 直接用；ES BM25 分数 [0,20+]，用 sigmoid(score/5) 映射到 [0,1]，然后加权排序取 top-K。

### 76. `run_sql` 节点里的 `_build_chart_data` 函数怎么自动判断图表类型（柱状图/折线图/饼图）？
**考察点**: 自动可视化  
**参考**: 维度字段含 date/time → 折线图；数据 ≤8 行 + 用户含"占比/比例"关键词 → 饼图；多指标 → 多系列柱状图；默认 → 柱状图。

### 77. 记忆系统分三层（短期/长期/持久），各层的数据结构、存储和生命周期是什么？
**考察点**: 记忆系统设计  
**参考**: 短期=对话列表（内存，会话级）；长期=MD 文件的知识定义（文件系统，永久）；持久=会话摘要和关键事实（MySQL/JSONL，永久）。每层解决不同问题。

### 78. Python 沙箱的安全限制做了哪些？还有哪些安全风险？
**考察点**: 沙箱安全  
**参考**: 关键字黑名单（os/subprocess/sys等）、`__builtins__` 白名单、禁止外部 import。风险：exec 本身仍有逃逸可能，生产应用容器隔离（如 gVisor）。

### 79. 报告生成的规划器（Planner）做了什么？为什么需要 LLM 规划而不是固定模板？
**考察点**: 智能规划  
**参考**: Planner 根据用户 query + Schema 决定：① 需要执行哪些 SQL；② 是否需要 Python 预处理；③ 用什么图表。每个分析场景不同，固定模板不够灵活。

### 80. 前端如何解析 SSE 事件流？`ReadableStream.getReader()` 读取后怎么区分 progress 和 result 事件？
**考察点**: 前后端联调  
**参考**: `frontend/src/lib/agentApi.ts` 中 fetch 获取 response.body → `getReader()` 循环读取 chunk → 按 `\n\n` 分割 → 解析 `data:` 行 JSON → 按 `type` 字段分发（progress→StepRail 更新，result→MessageBubble 显示）。

### 81. 项目的 `.editorconfig` 和 `.pre-commit-config.yaml` 的作用是什么？
**考察点**: 工程规范  
**参考**: `.editorconfig` 统一编辑器设置（缩进、编码等）；`.pre-commit` 在 git commit 前自动运行 ruff 格式化/检查，保证代码质量。

### 82. 如果要把项目从单机扩展到多实例部署，哪些组件需要改？
**考察点**: 扩展性  
**参考**: 内存缓存和 rate limiter 需从 dict 迁到 Redis；SSE session 状态需共享存储；数据库连接池需调大；前端需要负载均衡。

### 83. 为什么 Reports 模块用 YAML 模板定义报告结构（`reports/templates/`）？
**考察点**: 模板化设计  
**参考**: 常见分析模式（趋势/对比/TopN/分布/明细）可模板化。YAML 定义 SQL 模板+图表配置+文本说明，减少 LLM 调用，提高稳定性。

### 84. `eval_test.py` 和 `tests/` 里的测试用例目前覆盖了哪些场景？还缺什么？
**考察点**: 测试覆盖  
**参考**: 覆盖：SQL 安全拦截、基本 API 调用、RAG 召回。缺失：单元测试（每个节点独立测试）、mock 测试、集成测试、准确率评测集。

### 85. 前端 Vite 的开发代理（proxy）解决了什么跨域问题？
**考察点**: 前端工程化  
**参考**: `vite.config.ts` 配置 proxy 将 `/api` 请求转发到后端 `localhost:8000`，开发时前后端同源避免 CORS，生产用 Nginx 反向代理。

### 86. DeepSeek LLM 通过 OpenAI 兼容接口接入，如果要换成 Qwen2.5 需要改哪些代码？
**考察点**: 模型替换  
**参考**: 改 `conf/app_config.yaml` 中 `llm.base_url` 和 `llm.model_name`，以及 `.env` 中 `LLM_API_KEY`。代码层 `app/agent/llm.py` 通过 `init_chat_model` 用 `model_provider="openai"` 无需改代码。

### 87. 为什么 prompt 模板放在 `prompts/` 目录用文件管理，而不是硬编码在代码里？
**考察点**: Prompt 工程管理  
**参考**: 分离代码和 prompt，方便非开发人员调优 prompt、版本对比、A/B 测试。`app/prompt/prompt_loader.py` 做统一加载。

### 88. `RagMetrics` 类记录了什么？为什么 NL2SQL 链路没有对应的 Metrics？
**考察点**: 可观测性  
**参考**: RAG 记录了查询次数、成功率、延迟、召回数量、上下文大小等。NL2SQL 链路缺失 metrics——这是当前不足，需要补充 SQL 成功率、字段召回率、各节点耗时等。

### 89. 项目中日志使用了什么方案？`request_id` 在日志中起什么作用？
**考察点**: 日志设计  
**参考**: `app/core/log.py` 使用 loguru。`request_id` 通过 ContextVar 注入每个请求，日志中标记，方便排查单个请求的完整调用链。

### 90. 整个项目的环境变量管理方案是什么？如果要在 CI/CD 中注入环境变量怎么做？
**考察点**: 配置管理  
**参考**: `.env` 文件 + `conf/app_config.yaml`（OmegaConf 解析）。CI/CD 可通过 GitHub Secrets / K8s ConfigMap / 启动命令 `-e` 注入。

---

## 五、HR题（10问）

### 91. 请用一句话概括这个项目解决了什么问题？
**参考回答**: "让电商运营用自然语言像聊天一样查数据和找文档，把传统 BI 工单从天级降到秒级。"

### 92. 你在这个项目中最大的技术成长是什么？
**参考回答**: "学会了把复杂 AI 流程拆成可观测、可容错、可重试的节点——从函数串联思维升级到了 Agent 编排思维。以及理解了元数据知识库对于 NL2SQL 的关键作用。"

### 93. 你在项目中有没有和他人协作的经历？遇到分歧怎么处理？
**参考回答**: 个人项目就如实说。如果有协作，强调：先对齐标准（代码规范/接口契约），用数据说话（性能对比/测试结果），必要时升级决策。

### 94. 这个项目你如果重新做一遍，会怎么改进？
**参考回答**: "先写测试再写代码。先把记忆系统从文件迁到数据库。先做评测集再优化流程。另外会更早引入 Metrics，让每个环节的效果可量化。"

### 95. 你怎么看待自己目前的技术水平？和同龄人比的优势和差距在哪？
**参考回答**: "优势是工程化思维——不仅会写代码，还理解分层架构、容错设计、前后端联调。差距在分布式系统经验——当前是单机原型，没接触过真正的生产环境运维。"

### 96. 你为什么选择做 AI Agent 方向？你是怎么学习这个方向的？
**参考回答**: "因为 Agent 是 LLM 落地最务实的路径——不是取代人，而是加速人。我通过跑 LangGraph 官方教程理解框架，然后自己设计这个项目从配置→检索→生成→校验的完整链路来实践。"

### 97. 描述一个你解决过的最棘手的技术 bug，你怎么排查的？
**参考回答**: "State 和 Context 混淆导致 Repository 序列化报错——一开始不理解为什么 Context 要分离。通过读 LangGraph 源码理解了序列化路径，最终正确分离了两类数据。"

### 98. 你对第一份工作的期望是什么？更看重什么？
**参考回答**: "更看重技术成长空间和 mentor 质量。希望参与真实生产系统，学习分布式、评测体系、CI/CD 这些原型项目欠缺的环节。薪资和 title 是次要的。"

### 99. 你怎么保持技术学习？最近在关注什么新技术？
**参考回答**: "读官方文档和源码为主（LangGraph/FastAPI），看论文理解原理（RAG/Agent），动手做项目验证。最近关注 MCP（Model Context Protocol）和 Agent-to-Agent 协作。"

### 100. 你有什么想问我们的？
**参考问题清单**:
- "你们在线上的 NL2SQL 或 RAG 系统是怎么做的？遇到过什么坑？"
- "团队目前最看重候选人的什么能力？"
- "如果我能加入，前三个月你会期望我在哪个方向产出？"
- "代码规范和测试覆盖率你们有标准吗？"

---

> ## 使用建议
>
> 1. **分类练习**: 每天练一类（基础→八股→场景→设计→HR），每类练完再练下一类
> 2. **结合代码**: 每题都找到对应源码文件，边看代码边回答，加深记忆
> 3. **录音自检**: 每题录音回答，回听检查流畅度和准确度
> 4. **模拟面试**: 找人随机抽题，2 分钟回答 + 追问，模拟真实压力
> 5. **重点记忆 8 个高频题**: Q3(为什么用LangGraph)、Q4(SQL校验闭环)、Q5(三路召回)、Q9(元数据知识库)、Q23(Depends组装)、Q28(Runtime与stream_writer)、Q30(sqlglot安全)、Q49(语义消歧)

---

> 文件：`docs/interview-100-questions.md`  
> 基于项目源码生成，覆盖 5 大类别共 100 题
