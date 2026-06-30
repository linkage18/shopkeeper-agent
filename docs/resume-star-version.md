自然语言问数与数据分析 Agent 系统 — 2025-06 ～ 2025-10
技术栈：Python、FastAPI、LangGraph、LangChain、MySQL、Qdrant、Elasticsearch、BGE Embedding、React、ECharts、Docker

项目背景：针对业务人员"查数据慢、看报表难"的痛点，设计 NL2SQL + BI 分析 Agent 原型系统，覆盖 10+ 张业务表、50+ 个字段的 Chinook 音乐商店数仓，实现从自然语言提问到 SQL 查询、可视化图表、分析报告的全链路交付。

搭建多链路 Agent 编排框架：基于 LangGraph 构建自然语言问数、知识库问答和分析报告生成三类 Agent 流程，设计意图识别入口对用户问题进行分发；通过 State 传递中间结果、Context 隔离运行时依赖，结合 SSE 向前端推送执行进度与节点耗时，端到端查询响应时间从分钟级降至秒级。

构建 NL2SQL 可靠生成机制：针对 LLM 直接生成 SQL 准确率低、易产生幻觉字段和语法错误的问题，使用 YAML 维护表结构/字段别名/指标口径，构建 MySQL+Qdrant+ES 元数据知识库实现 Schema/指标/筛选值的语义召回；构建 12-case NL2SQL Eval 集覆盖简单查询、多表 JOIN、聚合分组、自连接等场景，通过 5 轮系统性迭代改进将准确率由 58.3% 提升至 91.7%，并通过 EXPLAIN 校验 + 自动修正 + sqlglot 只读审查将异常 SQL 执行风险降至零。

实现知识库问答检索模块：基于 BGE Embedding 完成文档向量化入库，结合 Qdrant 向量检索与 Elasticsearch BM25 关键词检索进行双路混合召回，支持千级文档的实时检索，Top-5 召回命中率 90%+，并在回答中返回来源文档和引用片段，增强结果可追溯性。

实现分析报告生成与可视化交付：基于 Report Agent 将用户分析需求拆解为数据查询、结果处理、图表生成和结论撰写等步骤，每次查询自动匹配柱状图/折线图/饼图，结合 SQL 查询结果生成 ECharts 图表和 Markdown 分析报告，将分析报告产出时间从天级降至分钟级。
