"""引用关系数据结构"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CitationRelation:
    """引用关系"""
    source_doc_id: str
    target_doc_id: str
    relation_type: str = "cites"  # cites / cited_by / co_cited
    context: str = ""  # 引用上下文
    confidence: float = 1.0
