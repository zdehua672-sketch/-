"""纯Python倒排索引"""
import json
import re
from collections import defaultdict
from pathlib import Path


class KeywordIndex:
    """
    纯Python倒排索引，支持中英文分词

    索引结构:
    {
        "term": [(doc_id, chunk_id, term_frequency), ...],
        ...
    }
    """

    def __init__(self):
        self._index = defaultdict(list)  # term -> [(doc_id, chunk_id, tf)]
        self._doc_lengths = {}  # chunk_id -> length
        self._total_chunks = 0

    def _tokenize(self, text: str) -> list:
        """简易中英文分词"""
        text = text.lower()
        # 提取英文单词
        tokens = re.findall(r'[a-z][a-z0-9\-]{1,}', text)
        # 提取中文字符序列（2-4字为一组，同时保留单字）
        for i in range(len(text)):
            if '一' <= text[i] <= '鿿':
                tokens.append(text[i])
                # 双字词
                if i + 1 < len(text) and '一' <= text[i + 1] <= '鿿':
                    tokens.append(text[i:i + 2])
                # 三字词
                if i + 2 < len(text) and '一' <= text[i + 1] <= '鿿' and '一' <= text[i + 2] <= '鿿':
                    tokens.append(text[i:i + 3])
        # 提取数字+单位组合
        tokens.extend(re.findall(r'\d+\.?\d*\s*(?:mg|ml|cm|mm|kg|m|l)\b', text.lower()))
        return tokens

    def add_chunk(self, doc_id: str, chunk_id: str, text: str):
        """添加一个文本块到索引"""
        tokens = self._tokenize(text)
        self._doc_lengths[chunk_id] = len(tokens)
        self._total_chunks += 1

        # 统计词频
        tf = defaultdict(int)
        for t in tokens:
            tf[t] += 1

        for term, freq in tf.items():
            self._index[term].append((doc_id, chunk_id, freq))

    def search(self, query: str, top_k: int = 10) -> list:
        """
        搜索相关文档块

        Returns
        -------
        list of (chunk_id, score)
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # 统计每个chunk的匹配分数
        scores = defaultdict(float)
        for token in query_tokens:
            if token not in self._index:
                continue
            for doc_id, chunk_id, tf in self._index[token]:
                scores[chunk_id] += tf

        # 排序返回
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:top_k]

    def get_doc_chunks(self, doc_id: str) -> list:
        """获取某文档的所有chunk_id"""
        chunk_ids = set()
        for postings in self._index.values():
            for did, cid, _ in postings:
                if did == doc_id:
                    chunk_ids.add(cid)
        return list(chunk_ids)

    def remove_doc(self, doc_id: str):
        """移除某文档的所有索引条目"""
        for term in list(self._index.keys()):
            self._index[term] = [(d, c, f) for d, c, f in self._index[term] if d != doc_id]
            if not self._index[term]:
                del self._index[term]

    @property
    def vocab_size(self) -> int:
        return len(self._index)

    @property
    def avg_doc_length(self) -> float:
        if not self._doc_lengths:
            return 0
        return sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def save(self, path: Path):
        """持久化到JSON"""
        data = {
            "index": {k: v for k, v in self._index.items()},
            "doc_lengths": self._doc_lengths,
            "total_chunks": self._total_chunks,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, path: Path):
        """从JSON加载"""
        if not path.exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._index = defaultdict(list)
        for k, v in data.get("index", {}).items():
            self._index[k] = [tuple(x) for x in v]
        self._doc_lengths = data.get("doc_lengths", {})
        self._total_chunks = data.get("total_chunks", 0)
