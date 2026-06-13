# 项目职责描述 — 多智能体论文助手

**技术栈**：Python, DeepAgents, LangGraph, LlamaIndex, FastAPI, WebSocket, MySQL, SearXNG, Transformers, Docker

---

- 基于 **DeepAgents + LangGraph** 设计并实现"一主三从"多智能体编排架构：主 Agent 负责任务规划与综述生成，子 Agent 分别负责论文库检索、Web 公开搜索和元数据查询，实现复杂科研调研任务的自动拆解与协同执行。

- 基于 **LlamaIndex** 构建论文混合检索 RAG 链路，融合向量召回（Embedding）、BM25 全文检索与重排序（Reranker），返回带来源片段、页码和相关性分数的证据结果，提升检索精准度与可追溯性。

- 通过 Docker 部署 **SearXNG** 聚合搜索引擎，扩展系统对 arXiv、GitHub 和论文主页等公开资源的实时检索能力；设计并实现基于持久化存储的长期记忆模块，支持跨会话复用历史调研结果。

- 基于 **FastAPI + WebSocket** 搭建异步服务端架构，实现论文上传、检索、综述生成等耗时任务的异步执行与实时进度推送；通过 thread_id、ContextVar 与会话目录隔离并发任务，确保多用户/多任务场景下的数据安全。

- 构建标准评测集与自动化评估流程，支持对检索质量、综述完整性和端到端耗时进行定量分析，为模型迭代与系统优化提供数据依据。

- 基于 **Transformers** 集成开源 embedding 与 reranker 模型（BGE 系列），实现本地化语义检索，降低对外部 API 的依赖与调用成本。
