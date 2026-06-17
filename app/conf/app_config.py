"""
应用主配置

定义 conf/app_config.yaml 在程序中的结构化配置对象
项目启动后会在这里一次性完成配置文件加载和类型化转换，其他模块只需要导入 app_config
就可以按属性方式读取日志 MySQL Qdrant Embedding Elasticsearch 和 LLM 配置
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf


@dataclass
class File:
    """文件日志配置"""

    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    """控制台日志配置"""

    enable: bool
    level: str


@dataclass
class LoggingConfig:
    """日志总配置"""

    file: File
    console: Console


@dataclass
class DBConfig:
    """MySQL 连接配置"""

    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    """Qdrant 连接与向量维度配置"""

    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    """Embedding 服务配置"""

    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    """Elasticsearch 配置"""

    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    """大模型调用配置"""

    model_name: str
    api_key: str
    base_url: str


@dataclass
class RetrievalConfig:
    """检索参数配置"""
    vector_weight: float
    bm25_weight: float
    exact_weight: float
    top_k: int
    score_threshold: float


@dataclass
class ContextConfig:
    """上下文窗口配置"""
    max_tokens: int
    history_max_tokens: int
    history_max_rounds: int


@dataclass
class MemoryConfig:
    """记忆配置"""
    short_term_rounds: int
    intent_cosine_threshold: float


@dataclass
class ChunkConfig:
    """切片配置"""
    max_tokens: int
    sentence_delimiters: str
    comma_delimiters: str


@dataclass
class RagQdrantConfig:
    """RAG 的 Qdrant collection 配置"""
    parent_collection: str
    sub_collection: str


@dataclass
class RagESConfig:
    """RAG 的 ES index 配置"""
    index_name: str


@dataclass
class RerankerConfig:
    """重排序配置"""
    model: str
    endpoint: str
    enabled: bool


@dataclass
class AuthConfig:
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    rate_limit_per_minute: int


@dataclass
class RagConfig:
    """RAG 模块总配置"""
    retrieval: RetrievalConfig
    context: ContextConfig
    memory: MemoryConfig
    chunk: ChunkConfig
    qdrant: RagQdrantConfig
    es: RagESConfig
    reranker: RerankerConfig


@dataclass
class AppConfig:
    """项目级总配置入口"""

    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig
    auth: AuthConfig
    rag: RagConfig


# 从当前文件位置回到项目根目录，再定位到 conf/app_config.yaml
project_root = Path(__file__).parents[2]
config_file = project_root / "conf" / "app_config.yaml"

# 先读取本地 .env，让 YAML 中的 ${oc.env:...} 可以解析到敏感配置
load_dotenv(project_root / ".env")

# 读取 YAML 配置内容
context = OmegaConf.load(config_file)

# 根据 AppConfig 生成结构化配置 schema
schema = OmegaConf.structured(AppConfig)

# 把配置结构和配置值合并，再转换成可以直接按属性访问的对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

if __name__ == "__main__":
    # 简单测试：验证配置是否能正常读取
    print(app_config.es.host)
