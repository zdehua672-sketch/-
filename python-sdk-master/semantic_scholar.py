"""
Semantic Scholar API 集成
=========================
从 Semantic Scholar 自动发现和检索学术文献。

借鉴自: AutoSurvey (gersteinlab/auto-survey)

功能:
  1. 按关键词搜索论文
  2. 获取论文元数据（标题/作者/年份/摘要/引用数）
  3. 获取引用图谱（被引/参考文献）
  4. 批量搜索+去重

用法:
    from semantic_scholar import SemanticScholarClient

    client = SemanticScholarClient()
    papers = client.search("carbon pollutants sewage network", limit=10)
    for p in papers:
        print(f"{p['authors']} ({p['year']}) {p['title']}")

    # 获取引用该论文的后续研究
    citations = client.get_citations(papers[0]['paperId'], limit=5)

    # 获取该论文的参考文献
    references = client.get_references(papers[0]['paperId'], limit=5)
"""

import json
import logging
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,abstract,citationCount,referenceCount,venue,externalIds,fieldsOfStudy"


@dataclass
class ScholarPaper:
    """Semantic Scholar 论文元数据"""
    paperId: str = ""
    title: str = ""
    authors: list = field(default_factory=list)  # list of str
    year: int = 0
    abstract: str = ""
    citationCount: int = 0
    referenceCount: int = 0
    venue: str = ""
    doi: str = ""
    fieldsOfStudy: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class SemanticScholarClient:
    """
    Semantic Scholar API 客户端

    注意: 免费 API 有速率限制（100 requests/5 minutes），
    建议在批量搜索时添加延时。
    """

    def __init__(self, timeout=15):
        self.timeout = timeout
        self._cache = {}  # 简单缓存

    def search(self, query: str, limit: int = 10, year_range: str = None) -> list:
        """
        按关键词搜索论文

        Parameters
        ----------
        query : str, 搜索关键词
        limit : int, 返回数量（默认10）
        year_range : str, 年份范围，如 "2020-2025"

        Returns
        -------
        list of ScholarPaper
        """
        cache_key = f"search:{query}:{limit}:{year_range}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = f"query={urllib.parse.quote(query)}&limit={limit}&fields={FIELDS}"
        if year_range:
            params += f"&year={year_range}"

        url = f"{API_BASE}/paper/search?{params}"
        papers = self._request(url, 'data')

        result = []
        for p in papers or []:
            paper = self._parse_paper(p)
            if paper.title:
                result.append(paper)

        self._cache[cache_key] = result
        logger.info(f"S2 search '{query}': {len(result)} results")
        return result

    def get_paper(self, paper_id: str) -> Optional[ScholarPaper]:
        """获取单篇论文详情"""
        cache_key = f"paper:{paper_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{API_BASE}/paper/{paper_id}?fields={FIELDS}"
        data = self._request(url)
        if data:
            paper = self._parse_paper(data)
            self._cache[cache_key] = paper
            return paper
        return None

    def get_citations(self, paper_id: str, limit: int = 10) -> list:
        """获取引用该论文的后续研究"""
        url = f"{API_BASE}/paper/{paper_id}/citations?fields={FIELDS}&limit={limit}"
        data = self._request(url, 'data')
        result = []
        for item in (data or []):
            citing = item.get('citingPaper', {})
            paper = self._parse_paper(citing)
            if paper.title:
                result.append(paper)
        return result

    def get_references(self, paper_id: str, limit: int = 10) -> list:
        """获取该论文的参考文献"""
        url = f"{API_BASE}/paper/{paper_id}/references?fields={FIELDS}&limit={limit}"
        data = self._request(url, 'data')
        result = []
        for item in (data or []):
            cited = item.get('citedPaper', {})
            paper = self._parse_paper(cited)
            if paper.title:
                result.append(paper)
        return result

    def search_multi(self, queries: list, limit_per_query: int = 5) -> list:
        """
        多关键词批量搜索+去重

        Parameters
        ----------
        queries : list of str, 搜索关键词列表
        limit_per_query : int, 每个关键词返回数量

        Returns
        -------
        list of ScholarPaper, 去重后按引用数排序
        """
        seen_ids = set()
        all_papers = []

        for query in queries:
            papers = self.search(query, limit=limit_per_query)
            for p in papers:
                if p.paperId not in seen_ids:
                    seen_ids.add(p.paperId)
                    all_papers.append(p)

        # 按引用数排序
        all_papers.sort(key=lambda x: x.citationCount, reverse=True)
        logger.info(f"S2 multi-search: {len(queries)} queries → {len(all_papers)} unique papers")
        return all_papers

    def _request(self, url: str, key: str = None):
        """发送 API 请求"""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'AcademicAI/1.0 (research tool)'
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                return data.get(key, data) if key else data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning("S2 API rate limited, try again later")
            else:
                logger.warning(f"S2 API error {e.code}: {e.reason}")
            return None
        except Exception as e:
            logger.warning(f"S2 API request failed: {e}")
            return None

    def _parse_paper(self, data: dict) -> ScholarPaper:
        """解析 API 返回的论文数据"""
        authors = []
        for a in data.get('authors', []):
            name = a.get('name', '')
            if name:
                authors.append(name)

        doi = ''
        ext_ids = data.get('externalIds', {})
        if ext_ids:
            doi = ext_ids.get('DOI', '')

        return ScholarPaper(
            paperId=data.get('paperId', ''),
            title=data.get('title', ''),
            authors=authors,
            year=data.get('year', 0) or 0,
            abstract=(data.get('abstract', '') or '')[:500],
            citationCount=data.get('citationCount', 0) or 0,
            referenceCount=data.get('referenceCount', 0) or 0,
            venue=data.get('venue', '') or '',
            doi=doi,
            fieldsOfStudy=data.get('fieldsOfStudy', []) or [],
        )


# 便捷导入
import urllib.parse  # noqa: E402


def search_papers(query: str, limit: int = 10) -> list:
    """便捷函数：搜索论文"""
    client = SemanticScholarClient()
    return client.search(query, limit=limit)


def discover_literature(topic: str, variables: list = None, limit: int = 20) -> list:
    """
    为研究主题自动发现相关文献

    Parameters
    ----------
    topic : str, 研究主题
    variables : list, 相关变量列表（如 ['DO', 'CH4', 'TOC']）
    limit : int, 总返回数量

    Returns
    -------
    list of ScholarPaper
    """
    client = SemanticScholarClient()

    # 构建多组搜索关键词
    queries = [topic]
    if variables:
        for var in variables[:3]:
            queries.append(f"{topic} {var}")
            queries.append(f"{var} mechanism")

    # 批量搜索
    papers = client.search_multi(queries, limit_per_query=5)

    return papers[:limit]


if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        client = SemanticScholarClient()
        papers = client.search("carbon pollutants sewage network", limit=3)
        print(f"Found {len(papers)} papers:")
        for p in papers:
            print(f"  [{p.year}] {p.title[:60]}... (citations: {p.citationCount})")
            print(f"    Authors: {', '.join(p.authors[:3])}")
            print(f"    Venue: {p.venue}")
        print("\nTest passed!")
    else:
        print("用法: python semantic_scholar.py --test")
