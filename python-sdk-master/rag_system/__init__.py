"""
RAG System - 轻量级学术文献检索增强生成系统
纯Python优先，重依赖可选
"""
from .config import RAGConfig
from .retrieval.rag_engine import RAGEngine
from .schema.document_schema import PaperMetadata, DocumentChunk
