"""BM25检索算法（纯Python实现）"""
import math
from collections import defaultdict


class BM25Searcher:
    """
    BM25评分算法

    score(D, Q) = sum(IDF(qi) * f(qi,D) * (k1+1) / (f(qi,D) + k1 * (1-b + b*|D|/avgdl)))
    """

    def __init__(self, keyword_index, k1: float = 1.5, b: float = 0.75):
        self.index = keyword_index
        self.k1 = k1
        self.b = b

    def _idf(self, term: str) -> float:
        """计算IDF"""
        if term not in self.index._index:
            return 0
        df = len(self.index._index[term])
        n = self.index._total_chunks
        if n == 0 or df == 0:
            return 0
        return math.log((n - df + 0.5) / (df + 0.5) + 1)

    def score(self, query: str, chunk_id: str) -> float:
        """计算单个chunk对query的BM25分数"""
        from ..index.keyword_index import KeywordIndex
        tokens = self.index._tokenize(query)
        if not tokens:
            return 0

        doc_len = self.index._doc_lengths.get(chunk_id, 0)
        avg_dl = self.index.avg_doc_length
        if avg_dl == 0:
            return 0

        total_score = 0
        for token in tokens:
            if token not in self.index._index:
                continue
            # 找到该chunk的词频
            tf = 0
            for did, cid, freq in self.index._index[token]:
                if cid == chunk_id:
                    tf = freq
                    break
            if tf == 0:
                continue

            idf = self._idf(token)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_dl)
            total_score += idf * numerator / denominator

        return total_score

    def search(self, query: str, top_k: int = 10) -> list:
        """
        BM25搜索

        Returns
        -------
        list of (chunk_id, bm25_score)
        """
        tokens = self.index._tokenize(query)
        if not tokens:
            return []

        # 获取所有匹配的chunk
        candidate_chunks = set()
        for token in tokens:
            if token in self.index._index:
                for _, cid, _ in self.index._index[token]:
                    candidate_chunks.add(cid)

        # 计算每个candidate的BM25分数
        scores = []
        for chunk_id in candidate_chunks:
            s = self.score(query, chunk_id)
            if s > 0:
                scores.append((chunk_id, s))

        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]
