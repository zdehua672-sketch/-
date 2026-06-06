"""RAG系统配置"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RAGConfig:
    # 索引存储路径
    index_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    # BM25参数
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # Token预算（近似，按字符数）
    default_max_tokens: int = 4000
    # 默认返回结果数
    default_top_k: int = 10
    # 是否优先向量检索
    prefer_vector: bool = False
    # 支持的语言
    supported_languages: list = field(default_factory=lambda: ['zh', 'en'])

    def ensure_index_dir(self):
        self.index_dir.mkdir(parents=True, exist_ok=True)
        return self
