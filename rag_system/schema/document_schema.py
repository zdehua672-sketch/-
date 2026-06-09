"""文档数据结构"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class PaperMetadata:
    """论文元数据"""
    doc_id: str
    title: str = ""
    authors: list = field(default_factory=list)
    year: Optional[int] = None
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    keywords: list = field(default_factory=list)
    language: str = "en"
    source_path: str = ""


@dataclass
class DocumentChunk:
    """文档分块"""
    chunk_id: str
    doc_id: str
    text: str
    chunk_type: str = "body"  # abstract / introduction / methods / results / discussion / conclusion / body
    section_path: str = ""
    index_in_doc: int = 0
    char_offset: int = 0
    metadata: dict = field(default_factory=dict)

    def token_estimate(self) -> int:
        """粗略估计token数（中英文混合）"""
        return len(self.text)
