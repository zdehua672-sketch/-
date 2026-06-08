"""引用图 - 基于邻接表的简单引用关系管理"""
import json
from pathlib import Path
from collections import defaultdict


class CitationGraph:
    """
    引用关系图
    {doc_id: [cited_doc_ids]}
    """

    def __init__(self):
        self._forward = defaultdict(set)   # doc_id -> {cited_doc_ids}
        self._backward = defaultdict(set)  # doc_id -> {citing_doc_ids}

    def add_citation(self, source_id: str, target_id: str):
        """添加一条引用关系"""
        self._forward[source_id].add(target_id)
        self._backward[target_id].add(source_id)

    def get_cited_by(self, doc_id: str) -> list:
        """获取doc_id引用的文档列表"""
        return list(self._forward.get(doc_id, set()))

    def get_citing(self, doc_id: str) -> list:
        """获取引用了doc_id的文档列表"""
        return list(self._backward.get(doc_id, set()))

    def get_co_cited(self, doc_id: str) -> list:
        """获取与doc_id共同被引用的文档"""
        citing_docs = self._backward.get(doc_id, set())
        co_cited = set()
        for citing in citing_docs:
            co_cited.update(self._forward.get(citing, set()))
        co_cited.discard(doc_id)
        return list(co_cited)

    def get_related(self, doc_id: str, max_results: int = 20) -> list:
        """获取相关文档（引用+被引+共被引）"""
        related = set()
        related.update(self._forward.get(doc_id, set()))
        related.update(self._backward.get(doc_id, set()))
        related.update(self.get_co_cited(doc_id))
        related.discard(doc_id)
        return list(related)[:max_results]

    def remove_doc(self, doc_id: str):
        """移除某文档的所有引用关系"""
        for target in self._forward.get(doc_id, set()):
            self._backward.get(target, set()).discard(doc_id)
        for source in self._backward.get(doc_id, set()):
            self._forward.get(source, set()).discard(doc_id)
        self._forward.pop(doc_id, None)
        self._backward.pop(doc_id, None)

    @property
    def num_relations(self) -> int:
        return sum(len(v) for v in self._forward.values())

    @property
    def num_docs(self) -> int:
        return len(set(self._forward.keys()) | set(self._backward.keys()))

    def save(self, path: Path):
        """持久化到JSON"""
        data = {
            "forward": {k: list(v) for k, v in self._forward.items()},
            "backward": {k: list(v) for k, v in self._backward.items()},
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
        self._forward = defaultdict(set)
        self._backward = defaultdict(set)
        for k, v in data.get("forward", {}).items():
            self._forward[k] = set(v)
        for k, v in data.get("backward", {}).items():
            self._backward[k] = set(v)
