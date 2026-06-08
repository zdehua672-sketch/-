"""RAG引擎 - 检索增强生成编排器"""
import json
import logging
from pathlib import Path
from ..config import RAGConfig
from ..index.keyword_index import KeywordIndex
from ..index.vector_index import VectorIndex
from ..index.citation_graph import CitationGraph
from ..retrieval.keyword_search import BM25Searcher
from ..retrieval.query_expander import expand_query
from ..retrieval.context_assembler import ContextAssembler
from ..schema.document_schema import DocumentChunk

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    RAG检索引擎

    暴露两个核心接口:
    - retrieve(query, top_k) -> list of results
    - assemble_context(query, top_k, max_tokens) -> str
    """

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.config.ensure_index_dir()

        # 索引
        self.keyword_index = KeywordIndex()
        self.vector_index = VectorIndex(self.config.index_dir / "vector")
        self.citation_graph = CitationGraph()

        # 检索器
        self.bm25 = BM25Searcher(self.keyword_index, self.config.bm25_k1, self.config.bm25_b)
        self.assembler = ContextAssembler(self.config.default_max_tokens)

        # 文本存储 {chunk_id: text}
        self._chunk_texts = {}
        self._chunk_metadata = {}

        # 加载已有索引
        self._load_indices()

        # 向量索引可用性提示
        if not self.vector_index.is_available:
            logger.warning(
                "Vector index not available (sentence-transformers not installed). "
                "RAG retrieval degraded to BM25 keyword search only. "
                "Install sentence-transformers for better retrieval quality: "
                "pip install sentence-transformers"
            )

    def _load_indices(self):
        idx_path = self.config.index_dir / "keyword_index.json"
        if idx_path.exists():
            self.keyword_index.load(idx_path)
            logger.info(f"Loaded keyword index: {self.keyword_index.vocab_size} terms")

        graph_path = self.config.index_dir / "citation_graph.json"
        if graph_path.exists():
            self.citation_graph.load(graph_path)

        texts_path = self.config.index_dir / "chunk_texts.json"
        if texts_path.exists():
            with open(texts_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._chunk_texts = data.get("texts", {})
                self._chunk_metadata = data.get("metadata", {})

    def _save_indices(self):
        self.config.ensure_index_dir()
        self.keyword_index.save(self.config.index_dir / "keyword_index.json")
        self.citation_graph.save(self.config.index_dir / "citation_graph.json")
        with open(self.config.index_dir / "chunk_texts.json", 'w', encoding='utf-8') as f:
            json.dump({"texts": self._chunk_texts, "metadata": self._chunk_metadata}, f, ensure_ascii=False)

    def add_document(self, doc_id: str, chunks: list):
        """
        添加文档（由DocumentChunk列表或dict列表组成）

        Parameters
        ----------
        doc_id : str
        chunks : list of DocumentChunk or list of dict
            dict格式: {"text": str, "metadata": dict, "chunk_id": str(optional)}
        """
        import hashlib

        for i, chunk in enumerate(chunks):
            # 兼容 dict 和 DocumentChunk 两种格式
            if isinstance(chunk, dict):
                text = chunk.get("text", "")
                metadata = chunk.get("metadata", {})
                chunk_id = chunk.get("chunk_id") or f"{doc_id}_chunk_{i}"
                chunk_type = metadata.get("chunk_type", "text")
            else:
                # DocumentChunk 对象
                text = chunk.text
                chunk_id = chunk.chunk_id
                chunk_type = chunk.chunk_type
                metadata = {
                    "doc_id": doc_id,
                    "chunk_type": chunk.chunk_type,
                    "section_path": getattr(chunk, 'section_path', ''),
                }

            self.keyword_index.add_chunk(doc_id, chunk_id, text)
            self.vector_index.add_chunk(chunk_id, text, {
                "doc_id": doc_id,
                "chunk_type": chunk_type,
            })
            self._chunk_texts[chunk_id] = text
            self._chunk_metadata[chunk_id] = {
                "doc_id": doc_id,
                "chunk_type": chunk_type,
                "section_path": metadata.get("section_path", ""),
                "title": metadata.get("title", ""),
                "section_type": metadata.get("section_type", ""),
            }

        self._save_indices()
        logger.info(f"Added document {doc_id}: {len(chunks)} chunks indexed")

    def add_citation(self, source_doc_id: str, target_doc_id: str):
        """添加引用关系"""
        self.citation_graph.add_citation(source_doc_id, target_doc_id)
        self._save_indices()

    def retrieve(self, query: str, top_k: int = None) -> list:
        """
        检索相关文档块

        Returns
        -------
        list of dict: [{"chunk_id": str, "text": str, "score": float, "source": str}, ...]
        """
        top_k = top_k or self.config.default_top_k
        all_results = {}

        # 查询扩展
        queries = expand_query(query)

        # BM25检索
        for q in queries:
            bm25_results = self.bm25.search(q, top_k)
            for cid, score in bm25_results:
                if cid not in all_results or score > all_results[cid]:
                    all_results[cid] = score

        # 向量检索（如果可用）
        if self.vector_index.is_available and self.config.prefer_vector:
            for q in queries:
                vec_results = self.vector_index.search(q, top_k)
                for cid, score in vec_results:
                    combined = score * 0.6 + all_results.get(cid, 0) * 0.4
                    all_results[cid] = combined

        # 排序
        ranked = sorted(all_results.items(), key=lambda x: -x[1])[:top_k]

        # 组装结果
        results = []
        for cid, score in ranked:
            text = self._chunk_texts.get(cid, "")
            meta = self._chunk_metadata.get(cid, {})
            results.append({
                "chunk_id": cid,
                "text": text,
                "score": score,
                "source": meta.get("doc_id", ""),
                "chunk_type": meta.get("chunk_type", ""),
                "section_path": meta.get("section_path", ""),
            })

        return results

    def assemble_context(self, query: str, top_k: int = None, max_tokens: int = None) -> str:
        """
        检索并组装上下文字符串

        Parameters
        ----------
        query : str, 查询文本
        top_k : int, 返回结果数
        max_tokens : int, 最大token数
        """
        max_tokens = max_tokens or self.config.default_max_tokens
        self.assembler.max_tokens = max_tokens

        results = self.retrieve(query, top_k)
        chunks_with_scores = [(r["chunk_id"], r["score"]) for r in results]

        text_map = {}
        for r in results:
            text_map[r["chunk_id"]] = r["text"]

        return self.assembler.assemble(chunks_with_scores, text_map)

    def get_related_docs(self, doc_id: str) -> list:
        """获取引用相关的文档"""
        return self.citation_graph.get_related(doc_id)

    def remove_document(self, doc_id: str):
        """移除文档及其索引"""
        self.keyword_index.remove_doc(doc_id)
        self.citation_graph.remove_doc(doc_id)
        # 清理文本存储
        to_remove = [cid for cid, m in self._chunk_metadata.items() if m.get("doc_id") == doc_id]
        for cid in to_remove:
            self._chunk_texts.pop(cid, None)
            self._chunk_metadata.pop(cid, None)
            self.vector_index.remove_chunk(cid)
        self._save_indices()

    @property
    def stats(self) -> dict:
        return {
            "vocab_size": self.keyword_index.vocab_size,
            "total_chunks": self.keyword_index._total_chunks,
            "vector_available": self.vector_index.is_available,
            "citation_relations": self.citation_graph.num_relations,
            "citation_docs": self.citation_graph.num_docs,
        }
