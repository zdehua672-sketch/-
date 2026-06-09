"""向量索引（可选ChromaDB）"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorIndex:
    """
    ChromaDB向量索引封装
    不可用时所有操作降级为no-op
    """

    def __init__(self, persist_dir: Path = None):
        self._available = False
        self._collection = None
        self._persist_dir = persist_dir

        try:
            import chromadb
            if persist_dir:
                persist_dir.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(persist_dir))
            else:
                client = chromadb.Client()
            self._collection = client.get_or_create_collection("academic_rag")
            self._available = True
            logger.info("ChromaDB vector index initialized")
        except ImportError:
            logger.debug("ChromaDB not installed, vector index disabled")
        except Exception as e:
            logger.debug(f"Failed to initialize ChromaDB: {e}")

    @property
    def is_available(self) -> bool:
        return self._available

    def add_chunk(self, chunk_id: str, text: str, metadata: dict = None):
        """添加文本块到向量索引"""
        if not self._available:
            return
        try:
            self._collection.add(
                documents=[text],
                ids=[chunk_id],
                metadatas=[metadata or {}],
            )
        except Exception as e:
            logger.debug(f"Vector index add failed: {e}")

    def search(self, query: str, top_k: int = 10) -> list:
        """
        向量相似度搜索

        Returns
        -------
        list of (chunk_id, score)
        """
        if not self._available:
            return []
        try:
            results = self._collection.query(query_texts=[query], n_results=top_k)
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            # ChromaDB返回距离，转换为相似度分数
            return [(cid, 1.0 - d) for cid, d in zip(ids, distances)] if ids else []
        except Exception as e:
            logger.debug(f"Vector index search failed: {e}")
            return []

    def remove_chunk(self, chunk_id: str):
        """移除文本块"""
        if not self._available:
            return
        try:
            self._collection.delete(ids=[chunk_id])
        except Exception:
            pass
