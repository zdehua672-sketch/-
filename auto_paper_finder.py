# -*- coding: utf-8 -*-
"""
自动文献搜索器 - AutoPaperFinder
从 arxiv + Semantic Scholar 自动搜索相关论文，不靠人工输入。

三个核心类:
  ArxivSearcher         - arxiv API 搜索（带速率限制）
  SemanticScholarSearcher - S2 API 搜索（带速率限制+退避）
  AutoPaperFinder       - 协调器，合并去重，自动存入知识库
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1. 速率限制基类
# ============================================================================

class RateLimitedClient:
    """带速率限制的 HTTP 客户端"""

    def __init__(self, min_interval=1.0, max_retries=3):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._last_request_time = 0

    def _wait(self):
        """等待直到可以发起下一次请求"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def _fetch(self, url, headers=None, timeout=15):
        """带重试和退避的 HTTP GET"""
        for attempt in range(self.max_retries):
            self._wait()
            try:
                req = urllib.request.Request(url, headers=headers or {})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read().decode('utf-8', errors='replace')
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # 速率限制：指数退避
                    wait = (2 ** attempt) * self.min_interval
                    logger.warning(f"429 rate limited, waiting {wait:.1f}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                elif e.code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    logger.warning(f"HTTP {e.code}: {url}")
                    return None
            except Exception as e:
                logger.warning(f"Request failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None
        return None


# ============================================================================
# 2. ArxivSearcher - arxiv API 搜索
# ============================================================================

class ArxivSearcher(RateLimitedClient):
    """
    arxiv API 搜索器。
    使用 http://export.arxiv.org/api/query
    """

    API_URL = 'http://export.arxiv.org/api/query'

    def __init__(self, min_interval=3.0):
        super().__init__(min_interval=min_interval)

    def search(self, query: str, max_results: int = 10,
               sort_by: str = 'relevance',
               sort_order: str = 'descending',
               categories: list = None) -> List[Dict]:
        """
        搜索 arxiv 论文。

        Parameters
        ----------
        query : str, 搜索关键词
        max_results : int, 最大结果数
        sort_by : str, 'relevance' / 'lastUpdatedDate' / 'submittedDate'
        sort_order : str, 'ascending' / 'descending'
        categories : list or None, arxiv 分类过滤如 ['cs.AI', 'stat.ML']

        Returns
        -------
        list of dict
        """
        # 构建查询
        search_query = f'all:{query}'
        if categories:
            cat_filter = ' OR '.join(f'cat:{c}' for c in categories)
            search_query = f'({search_query}) AND ({cat_filter})'

        params = urllib.parse.urlencode({
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order,
        })
        url = f"{self.API_URL}?{params}"

        xml_data = self._fetch(url)
        if not xml_data:
            return []

        return self._parse_response(xml_data)

    def search_latest(self, query: str, max_results: int = 10,
                      days: int = 90) -> List[Dict]:
        """搜索最近 N 天的论文"""
        results = self.search(query, max_results=max_results * 2,
                              sort_by='submittedDate', sort_order='descending')
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [r for r in results
                if self._parse_date(r.get('published', '')) > cutoff
                ][:max_results]

    def _parse_response(self, xml_data: str) -> List[Dict]:
        """解析 arxiv API 的 Atom XML 响应"""
        papers = []
        ns = {'atom': 'http://www.w3.org/2005/Atom',
              'arxiv': 'http://arxiv.org/schemas/atom'}

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            logger.warning("Failed to parse arxiv XML response")
            return []

        for entry in root.findall('atom:entry', ns):
            paper = {}
            # 标题
            title_el = entry.find('atom:title', ns)
            paper['title'] = title_el.text.strip().replace('\n', ' ') if title_el is not None else ''

            # 摘要
            summary_el = entry.find('atom:summary', ns)
            paper['abstract'] = summary_el.text.strip().replace('\n', ' ') if summary_el is not None else ''

            # 作者
            authors = []
            for author in entry.findall('atom:author', ns):
                name_el = author.find('atom:name', ns)
                if name_el is not None:
                    authors.append(name_el.text.strip())
            paper['authors'] = authors

            # arxiv ID
            id_el = entry.find('atom:id', ns)
            if id_el is not None:
                arxiv_url = id_el.text.strip()
                paper['arxiv_id'] = arxiv_url.split('/abs/')[-1].split('v')[0] if '/abs/' in arxiv_url else ''
                paper['url'] = arxiv_url

            # 发布日期
            published_el = entry.find('atom:published', ns)
            paper['published'] = published_el.text.strip() if published_el is not None else ''

            # 更新日期
            updated_el = entry.find('atom:updated', ns)
            paper['updated'] = updated_el.text.strip() if updated_el is not None else ''

            # 分类
            categories = []
            for cat in entry.findall('atom:category', ns):
                term = cat.get('term', '')
                if term:
                    categories.append(term)
            paper['categories'] = categories

            # PDF 链接
            for link in entry.findall('atom:link', ns):
                if link.get('title') == 'pdf':
                    paper['pdf_url'] = link.get('href', '')

            paper['source'] = 'arxiv'
            paper['year'] = self._parse_date(paper.get('published', '')).year if paper.get('published') else None
            paper['citation_count'] = 0  # arxiv API 不提供引用数

            if paper.get('title'):
                papers.append(paper)

        return papers

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """解析 ISO 8601 日期"""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return datetime(1970, 1, 1, tzinfo=timezone.utc)


# ============================================================================
# 3. SemanticScholarSearcher - S2 API 搜索
# ============================================================================

class SemanticScholarSearcher(RateLimitedClient):
    """
    Semantic Scholar API 搜索器。
    使用 https://api.semanticscholar.org/graph/v1/paper/search
    """

    API_URL = 'https://api.semanticscholar.org/graph/v1/paper/search'
    RECOMMEND_URL = 'https://api.semanticscholar.org/recommendations/v1/papers'

    FIELDS = 'title,authors,year,abstract,citationCount,referenceCount,externalIds,url,venue,fieldsOfStudy'

    def __init__(self, min_interval=1.0):
        super().__init__(min_interval=min_interval)

    def search(self, query: str, limit: int = 10,
               year_range: str = None,
               fields_of_study: list = None,
               min_citation_count: int = 0) -> List[Dict]:
        """
        搜索 Semantic Scholar 论文。

        Parameters
        ----------
        query : str, 搜索关键词
        limit : int, 最大结果数
        year_range : str, 年份范围如 '2020-2026'
        fields_of_study : list, 领域过滤如 ['Computer Science']
        min_citation_count : int, 最低引用数

        Returns
        -------
        list of dict
        """
        params = {
            'query': query,
            'limit': min(limit, 100),
            'fields': self.FIELDS,
        }
        if year_range:
            params['year'] = year_range
        if fields_of_study:
            params['fieldsOfStudy'] = ','.join(fields_of_study)
        if min_citation_count > 0:
            params['minCitationCount'] = min_citation_count

        url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
        data = self._fetch(url)
        if not data:
            return []

        try:
            result = json.loads(data)
        except json.JSONDecodeError:
            return []

        papers = []
        for item in result.get('data', []):
            paper = self._normalize(item)
            if paper.get('title'):
                papers.append(paper)

        return papers

    def get_recommendations(self, paper_ids: list, limit: int = 10) -> List[Dict]:
        """
        基于已有论文获取推荐论文。

        Parameters
        ----------
        paper_ids : list, S2 paper ID 列表
        limit : int, 推荐数量

        Returns
        -------
        list of dict
        """
        if not paper_ids:
            return []

        # S2 recommendations API 使用 POST，但我们用 GET 的方式
        # 通过 positivePaperIds 参数
        ids_str = ','.join(paper_ids[:5])  # 最多5个种子论文
        url = (f"{self.RECOMMEND_URL}?positivePaperIds={ids_str}"
               f"&limit={limit}&fields={self.FIELDS}")

        data = self._fetch(url)
        if not data:
            return []

        try:
            result = json.loads(data)
        except json.JSONDecodeError:
            return []

        papers = []
        for item in result.get('recommendedPapers', []):
            paper = self._normalize(item)
            if paper.get('title'):
                papers.append(paper)

        return papers

    def get_citations(self, paper_id: str, limit: int = 20) -> List[Dict]:
        """获取引用该论文的论文（下游）"""
        url = (f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
               f"/citations?fields={self.FIELDS}&limit={limit}")
        data = self._fetch(url)
        if not data:
            return []
        try:
            result = json.loads(data)
            return [self._normalize(item.get('citingPaper', {}))
                    for item in result.get('data', [])
                    if item.get('citingPaper', {}).get('title')]
        except json.JSONDecodeError:
            return []

    def get_references(self, paper_id: str, limit: int = 20) -> List[Dict]:
        """获取该论文引用的论文（上游）"""
        url = (f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
               f"/references?fields={self.FIELDS}&limit={limit}")
        data = self._fetch(url)
        if not data:
            return []
        try:
            result = json.loads(data)
            return [self._normalize(item.get('citedPaper', {}))
                    for item in result.get('data', [])
                    if item.get('citedPaper', {}).get('title')]
        except json.JSONDecodeError:
            return []

    def _normalize(self, item: dict) -> dict:
        """标准化 S2 论文数据"""
        paper_id = item.get('paperId', '')
        ext_ids = item.get('externalIds', {}) or {}

        return {
            'paper_id': paper_id,
            'title': item.get('title', ''),
            'authors': [a.get('name', '') for a in (item.get('authors') or [])],
            'year': item.get('year'),
            'abstract': item.get('abstract', ''),
            'citation_count': item.get('citationCount', 0),
            'reference_count': item.get('referenceCount', 0),
            'venue': item.get('venue', ''),
            'fields_of_study': item.get('fieldsOfStudy', []),
            'url': item.get('url', ''),
            'arxiv_id': ext_ids.get('ArXiv', ''),
            'doi': ext_ids.get('DOI', ''),
            'source': 'semantic_scholar',
        }


# ============================================================================
# 4. AutoPaperFinder - 协调器
# ============================================================================

class AutoPaperFinder:
    """
    自动文献搜索协调器。
    合并 arxiv + Semantic Scholar 结果，去重，排序。
    结果自动存入知识库。
    """

    def __init__(self, store=None):
        """
        Parameters
        ----------
        store : KnowledgeStore or None, 知识库实例。None 时不自动存储。
        """
        self.arxiv = ArxivSearcher()
        self.s2 = SemanticScholarSearcher()
        self.store = store

    def find_papers(self, topic: str, max_results: int = 20,
                    min_citations: int = 0,
                    year_range: str = None) -> List[Dict]:
        """
        综合搜索 arxiv + Semantic Scholar。

        Parameters
        ----------
        topic : str, 研究主题
        max_results : int, 最大结果数
        min_citations : int, 最低引用数
        year_range : str, 年份范围如 '2020-2026'

        Returns
        -------
        list of dict: 去重排序后的论文列表
        """
        all_papers = {}

        # 1. arxiv 搜索
        logger.info(f"Searching arxiv: {topic}")
        try:
            arxiv_results = self.arxiv.search(topic, max_results=max_results)
            for p in arxiv_results:
                key = self._dedup_key(p)
                all_papers[key] = p
        except Exception as e:
            logger.warning(f"arxiv search failed: {e}")

        # 2. Semantic Scholar 搜索
        logger.info(f"Searching Semantic Scholar: {topic}")
        try:
            s2_results = self.s2.search(topic, limit=max_results,
                                        year_range=year_range,
                                        min_citation_count=min_citations)
            for p in s2_results:
                key = self._dedup_key(p)
                if key not in all_papers or p.get('citation_count', 0) > all_papers[key].get('citation_count', 0):
                    all_papers[key] = p
        except Exception as e:
            logger.warning(f"S2 search failed: {e}")

        # 3. 排序（引用数降序）
        papers = sorted(all_papers.values(),
                        key=lambda x: x.get('citation_count', 0),
                        reverse=True)

        papers = papers[:max_results]

        # 4. 存入知识库
        if self.store:
            self._store_papers(papers, topic)

        logger.info(f"Found {len(papers)} papers for '{topic}'")
        return papers

    def find_related(self, paper_id: str, max_results: int = 10) -> List[Dict]:
        """
        基于已有论文找相关论文。

        Parameters
        ----------
        paper_id : str, S2 paper ID 或 arxiv ID
        max_results : int, 最大结果数

        Returns
        -------
        list of dict
        """
        # 先尝试 S2 recommendations
        papers = self.s2.get_recommendations([paper_id], limit=max_results)

        # 如果推荐不够，补充引用该论文的论文
        if len(papers) < max_results:
            citations = self.s2.get_citations(paper_id, limit=max_results - len(papers))
            papers.extend(citations)

        # 去重
        seen = set()
        unique = []
        for p in papers:
            key = self._dedup_key(p)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        if self.store:
            self._store_papers(unique, f"related_to:{paper_id[:20]}")

        return unique[:max_results]

    def find_latest(self, topic: str, days: int = 90,
                    max_results: int = 10) -> List[Dict]:
        """
        搜索最近 N 天的相关论文。

        Parameters
        ----------
        topic : str, 研究主题
        days : int, 最近天数
        max_results : int, 最大结果数

        Returns
        -------
        list of dict
        """
        # arxiv 按时间排序
        arxiv_results = []
        try:
            arxiv_results = self.arxiv.search_latest(topic, max_results=max_results, days=days)
        except Exception as e:
            logger.warning(f"arxiv latest search failed: {e}")

        # S2 按年份过滤
        current_year = datetime.now().year
        year_range = f"{current_year - 1}-{current_year}"
        s2_results = []
        try:
            s2_results = self.s2.search(topic, limit=max_results, year_range=year_range)
        except Exception as e:
            logger.warning(f"S2 latest search failed: {e}")

        # 合并去重
        all_papers = {}
        for p in arxiv_results + s2_results:
            key = self._dedup_key(p)
            if key not in all_papers:
                all_papers[key] = p

        papers = sorted(all_papers.values(),
                        key=lambda x: x.get('published', x.get('year', '')),
                        reverse=True)[:max_results]

        if self.store:
            self._store_papers(papers, f"latest:{topic[:30]}")

        return papers

    def _dedup_key(self, paper: dict) -> str:
        """生成去重键"""
        # 优先用 arxiv ID
        if paper.get('arxiv_id'):
            return f"arxiv:{paper['arxiv_id']}"
        # 其次用 DOI
        if paper.get('doi'):
            return f"doi:{paper['doi']}"
        # 最后用标题（小写去空格）
        title = re.sub(r'\s+', ' ', paper.get('title', '').lower().strip())
        return f"title:{title[:80]}"

    def _store_papers(self, papers: list, search_topic: str):
        """将搜索结果存入知识库的 resources 分类"""
        if not self.store:
            return
        for p in papers:
            key = f"paper_{self._dedup_key(p).replace(':', '_').replace('/', '_')[:60]}"
            self.store.set("resources", key, {
                "type": "academic_paper",
                "search_topic": search_topic,
                "title": p.get('title', ''),
                'authors': p.get('authors', [])[:5],
                'year': p.get('year'),
                'abstract': (p.get('abstract', '') or '')[:500],
                'citation_count': p.get('citation_count', 0),
                'url': p.get('url', ''),
                'arxiv_id': p.get('arxiv_id', ''),
                'doi': p.get('doi', ''),
                'venue': p.get('venue', ''),
                'source': p.get('source', ''),
                "status": "discovered",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            }, source="auto_paper_finder",
               confidence=min(1.0, max(0.3, p.get('citation_count', 0) / 100)))


# ============================================================================
# 5. 便捷函数
# ============================================================================

def search_papers(topic: str, max_results: int = 20) -> List[Dict]:
    """快捷搜索（不存储到知识库）"""
    finder = AutoPaperFinder()
    return finder.find_papers(topic, max_results=max_results)


def search_and_store(topic: str, store, max_results: int = 20) -> List[Dict]:
    """搜索并存入知识库"""
    finder = AutoPaperFinder(store)
    return finder.find_papers(topic, max_results=max_results)
