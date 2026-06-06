"""
论文阅读器 — 借鉴ml-intern的papers_tool架构

核心能力:
  1. 从arxiv URL/ID读取论文（HTML解析，不需要PDF）
  2. 从本地PDF/TXT/MD读取论文
  3. 提取IMRaD结构（摘要/引言/方法/结果/讨论）
  4. Semantic Scholar API获取引用图谱和元数据
  5. 存入KnowledgeStore实现持久化记忆
  6. 加入RAG引擎支持后续检索

借鉴自: huggingface/ml-intern agent/tools/papers_tool.py
"""
import re
import json
import os
import sys
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PaperMetadata:
    """论文元数据"""
    paper_id: str = ""              # arxiv ID 或本地文件名
    title: str = ""
    authors: list = field(default_factory=list)
    year: int = 0
    abstract: str = ""
    arxiv_url: str = ""
    doi: str = ""
    venue: str = ""                 # 发表期刊/会议
    citation_count: int = 0
    reference_count: int = 0
    fields_of_study: list = field(default_factory=list)
    source: str = ""                # arxiv / local_pdf / local_text


@dataclass
class PaperSection:
    """论文一个章节"""
    section_type: str = ""          # introduction / methods / results / discussion / conclusion / other
    title: str = ""
    level: int = 2                  # heading level (h1=1, h2=2, h3=3)
    text: str = ""
    key_findings: list = field(default_factory=list)  # 提取的关键发现


@dataclass
class PaperContent:
    """论文完整内容"""
    metadata: PaperMetadata = field(default_factory=PaperMetadata)
    sections: list = field(default_factory=list)  # list[PaperSection]
    references: list = field(default_factory=list)  # 引用列表
    read_time: str = ""
    word_count: int = 0


# ============================================================
# 1. arxiv HTML解析（借鉴ml-intern的_parse_paper_html）
# ============================================================

def extract_arxiv_id(text: str) -> str:
    """从文本/arxiv URL中提取arxiv ID"""
    # 匹配 arxiv.org/abs/XXXX.XXXXX 或 arxiv.org/html/XXXX.XXXXX
    match = re.search(r'arxiv\.org/(?:abs|html|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)', text)
    if match:
        return match.group(1)
    # 匹配纯ID格式
    match = re.search(r'(\d{4}\.\d{4,5})', text)
    if match:
        return match.group(1)
    return ""


def fetch_arxiv_html(arxiv_id: str, timeout: int = 15) -> str:
    """从arxiv获取论文HTML"""
    try:
        import urllib.request
        url = f"https://arxiv.org/html/{arxiv_id}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'AcademicAI/1.0 (research tool)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        logger.warning(f"Failed to fetch arxiv HTML for {arxiv_id}: {e}")
        return ""


def parse_arxiv_html(html: str) -> PaperContent:
    """
    解析arxiv HTML为结构化论文内容

    借鉴ml-intern的_parse_paper_html，但用纯Python实现（不依赖BeautifulSoup）
    """
    content = PaperContent()

    # 提取标题
    title_match = re.search(r'<h1[^>]*class="ltx_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        title = re.sub(r'^Title:\s*', '', title)
        content.metadata.title = title

    # 提取作者
    author_section = re.search(r'<div[^>]*class="ltx_authors"[^>]*>(.*?)</div>', html, re.DOTALL)
    if author_section:
        author_text = re.sub(r'<[^>]+>', ' ', author_section.group(1))
        authors = [a.strip() for a in re.split(r'[,;·]|\band\b', author_text) if a.strip()]
        content.metadata.authors = authors[:20]

    # 提取摘要
    abstract_match = re.search(r'<div[^>]*class="ltx_abstract"[^>]*>(.*?)</div>', html, re.DOTALL)
    if abstract_match:
        abstract = re.sub(r'<[^>]+>', ' ', abstract_match.group(1))
        abstract = re.sub(r'\s+', ' ', abstract).strip()
        abstract = re.sub(r'(?i)^abstract\s*', '', abstract)
        content.metadata.abstract = abstract

    # 提取章节（h2/h3标题 + 内容）
    # 先找到所有section标签
    section_pattern = re.compile(
        r'<section[^>]*id="([^"]*)"[^>]*>(.*?)</section>',
        re.DOTALL
    )
    heading_pattern = re.compile(
        r'<h([23])[^>]*class="ltx_title[^"]*"[^>]*>(.*?)</h[23]>',
        re.DOTALL
    )

    # 简化方式：逐行解析h2/h3标题及其后的内容
    headings = re.findall(
        r'<h([23])[^>]*class="ltx_title[^"]*"[^>]*>(.*?)</h[23]>',
        html, re.DOTALL
    )

    for level_str, heading_html in headings:
        level = int(level_str)
        heading_text = re.sub(r'<[^>]+>', '', heading_html).strip()
        heading_text = re.sub(r'^\d+\.?\s*', '', heading_text)  # 去掉编号

        if not heading_text or len(heading_text) < 2:
            continue

        # 提取该标题后到下一个同级标题之间的文本
        section_type = _classify_section(heading_text)
        section_text = _extract_section_text(html, heading_html, level)

        section = PaperSection(
            section_type=section_type,
            title=heading_text,
            level=level,
            text=section_text[:5000],  # 限制长度
        )
        content.sections.append(section)

    # 如果没有找到sections，尝试用paper_structurer
    if not content.sections and html:
        try:
            from rag_system.ingestion.paper_structurer import detect_imrad_sections
            plain_text = re.sub(r'<[^>]+>', '\n', html)
            plain_text = re.sub(r'\n{3,}', '\n\n', plain_text)
            imrad = detect_imrad_sections(plain_text)
            for idx, (stype, start, header) in enumerate(imrad):
                if idx + 1 < len(imrad):
                    end = imrad[idx + 1][1]
                else:
                    end = min(start + 5000, len(plain_text))
                section_text = plain_text[start:end].strip()
                # 去掉标题行
                lines = section_text.split('\n', 1)
                title = lines[0].strip()
                body = lines[1].strip() if len(lines) > 1 else ''
                content.sections.append(PaperSection(
                    section_type=stype, title=title, text=body[:5000],
                ))
        except Exception:
            pass

    content.metadata.source = 'arxiv'
    content.metadata.arxiv_url = f"https://arxiv.org/abs/{content.metadata.paper_id}"
    content.word_count = sum(len(s.text) for s in content.sections)
    content.read_time = datetime.now(timezone.utc).isoformat()

    return content


def _classify_section(title: str) -> str:
    """将章节标题分类为IMRaD类型"""
    title_lower = title.lower()
    mappings = {
        'introduction': ['introduction', '背景', '引言'],
        'methods': ['method', 'material', 'experimental', '实验', '方法', '数据'],
        'results': ['result', 'finding', 'finding', '结果'],
        'discussion': ['discussion', '讨论', '分析'],
        'conclusion': ['conclusion', 'summary', '总结', '结论'],
        'abstract': ['abstract', '摘要'],
        'related_work': ['related work', 'literature', 'prior', '相关工作', '文献'],
    }
    for section_type, keywords in mappings.items():
        if any(kw in title_lower for kw in keywords):
            return section_type
    return 'other'


def _extract_section_text(html: str, heading_html: str, level: int) -> str:
    """提取某标题后到下一个同级标题之间的文本"""
    # 找到标题位置
    start = html.find(heading_html)
    if start == -1:
        return ""

    # 找到下一个同级或更高级标题
    next_heading = re.search(
        rf'<h[{level}1][^>]*class="ltx_title',
        html[start + len(heading_html):]
    )
    if next_heading:
        end = start + len(heading_html) + next_heading.start()
    else:
        end = min(start + 20000, len(html))

    chunk = html[start:end]
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', ' ', chunk)
    text = re.sub(r'\s+', ' ', text).strip()
    # 去掉标题本身
    heading_plain = re.sub(r'<[^>]+>', '', heading_html).strip()
    if text.startswith(heading_plain):
        text = text[len(heading_plain):]
    return text.strip()


# ============================================================
# 2. Semantic Scholar API（借鉴ml-intern的S2 API调用）
# ============================================================

def fetch_s2_paper(arxiv_id: str, timeout: int = 10) -> dict:
    """
    从Semantic Scholar获取论文元数据

    Returns: {title, authors, year, citationCount, referenceCount, fieldsOfStudy, ...}
    """
    try:
        import urllib.request
        import urllib.error
        url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}"
        params = "fields=title,authors,year,citationCount,referenceCount,fieldsOfStudy,externalIds,abstract"
        req = urllib.request.Request(f"{url}?{params}", headers={
            'User-Agent': 'AcademicAI/1.0'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"S2 API error for {arxiv_id}: {e}")
        return {}


def fetch_s2_citations(paper_id: str, limit: int = 10, timeout: int = 10) -> list:
    """获取引用该论文的后续论文（下游引用图谱）"""
    try:
        import urllib.request
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
        params = f"fields=title,authors,year,citationCount&limit={limit}"
        req = urllib.request.Request(f"{url}?{params}", headers={
            'User-Agent': 'AcademicAI/1.0'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return [item.get('citingPaper', {}) for item in data.get('data', [])]
    except Exception as e:
        logger.warning(f"S2 citations error: {e}")
        return []


def fetch_s2_references(paper_id: str, limit: int = 10, timeout: int = 10) -> list:
    """获取该论文引用的参考文献（上游引用图谱）"""
    try:
        import urllib.request
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references"
        params = f"fields=title,authors,year,citationCount&limit={limit}"
        req = urllib.request.Request(f"{url}?{params}", headers={
            'User-Agent': 'AcademicAI/1.0'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return [item.get('citedPaper', {}) for item in data.get('data', [])]
    except Exception as e:
        logger.warning(f"S2 references error: {e}")
        return []


# ============================================================
# 3. 本地文件读取
# ============================================================

def read_local_text(file_path: str) -> PaperContent:
    """从本地TXT/MD文件读取论文"""
    path = Path(file_path)
    text = path.read_text(encoding='utf-8', errors='replace')
    content = PaperContent()
    content.metadata.paper_id = path.stem
    content.metadata.title = path.stem
    content.metadata.source = 'local_text'

    # 尝试用paper_structurer解析IMRaD结构
    try:
        from rag_system.ingestion.paper_structurer import detect_imrad_sections
        imrad = detect_imrad_sections(text)
        for idx, (stype, start, header) in enumerate(imrad):
            if idx + 1 < len(imrad):
                end = imrad[idx + 1][1]
            else:
                end = len(text)
            section_text = text[start:end].strip()
            lines = section_text.split('\n', 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            content.sections.append(PaperSection(
                section_type=stype, title=title, text=body[:5000],
            ))
    except Exception:
        # 退化为按空行分段
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        for i, para in enumerate(paragraphs):
            content.sections.append(PaperSection(
                section_type='other',
                title=f'Section {i+1}',
                text=para[:5000],
            ))

    content.word_count = len(text)
    content.read_time = datetime.now(timezone.utc).isoformat()
    return content


def read_local_pdf(file_path: str) -> PaperContent:
    """从本地PDF文件读取论文"""
    try:
        from rag_system.ingestion.pdf_parser import parse_pdf
        text = parse_pdf(file_path)
    except Exception as e:
        logger.warning(f"PDF parse error: {e}")
        text = ""

    if not text:
        return read_local_text(file_path)

    path = Path(file_path)
    content = PaperContent()
    content.metadata.paper_id = path.stem
    content.metadata.source = 'local_pdf'

    # 尝试提取标题（第一行非空文本）
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        content.metadata.title = lines[0][:200]

    # 尝试用paper_structurer解析
    try:
        from rag_system.ingestion.paper_structurer import detect_imrad_sections
        imrad = detect_imrad_sections(text)
        for idx, (stype, start, header) in enumerate(imrad):
            if idx + 1 < len(imrad):
                end = imrad[idx + 1][1]
            else:
                end = len(text)
            section_text = text[start:end].strip()
            lines = section_text.split('\n', 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            content.sections.append(PaperSection(
                section_type=stype, title=title, text=body[:5000],
            ))
    except Exception:
        content.sections.append(PaperSection(
            section_type='other', title='Full Text', text=text[:10000]
        ))

    content.word_count = len(text)
    content.read_time = datetime.now(timezone.utc).isoformat()
    return content


# ============================================================
# 4. 论文阅读器主类 — 统一入口
# ============================================================

class PaperReader:
    """
    论文阅读器 — 统一入口

    读取论文 → 解析结构 → 提取发现 → 存入记忆 → 加入索引

    用法:
        reader = PaperReader()
        paper = reader.read("https://arxiv.org/abs/2301.12345")
        paper = reader.read("local_paper.pdf")
        paper = reader.read("2301.12345")  # 纯arxiv ID

        # 搜索已读论文
        results = reader.search("dissolved oxygen methane")
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self._papers: dict[str, PaperContent] = {}  # 内存缓存

    def read(self, source: str, fetch_metadata: bool = True) -> PaperContent:
        """
        读取一篇论文

        Parameters
        ----------
        source : str
            arxiv URL / arxiv ID / 本地文件路径
        fetch_metadata : bool
            是否从Semantic Scholar获取元数据和引用图谱

        Returns
        -------
        PaperContent
        """
        print(f"[PaperReader] 读取: {source}")

        # 判断来源类型
        arxiv_id = extract_arxiv_id(source)

        if arxiv_id:
            # arxiv论文
            content = self._read_arxiv(arxiv_id)
        elif os.path.isfile(source):
            # 本地文件
            ext = Path(source).suffix.lower()
            if ext == '.pdf':
                content = read_local_pdf(source)
            else:
                content = read_local_text(source)
        else:
            logger.error(f"无法识别来源: {source}")
            return PaperContent()

        # 获取Semantic Scholar元数据
        if fetch_metadata and arxiv_id:
            self._enrich_with_s2(content, arxiv_id)

        # 提取关键发现
        self._extract_findings(content)

        # 缓存
        pid = content.metadata.paper_id or arxiv_id or source
        content.metadata.paper_id = pid
        self._papers[pid] = content

        # 保存到文件
        self._save_paper(content)

        # 加入RAG索引
        self._index_paper(content)

        # 存入KnowledgeStore
        self._store_memory(content)

        print(f"[PaperReader] 完成: {content.metadata.title[:50]}... "
              f"({len(content.sections)} sections, {content.word_count} chars)")
        return content

    def search(self, query: str, top_k: int = 5) -> list:
        """搜索已读论文"""
        try:
            from rag_system import RAGEngine
            engine = RAGEngine()
            results = engine.retrieve(query, max_results=top_k)
            return results
        except Exception:
            # 退化为内存搜索
            results = []
            query_lower = query.lower()
            for pid, paper in self._papers.items():
                score = 0
                if query_lower in paper.metadata.title.lower():
                    score += 3
                if query_lower in paper.metadata.abstract.lower():
                    score += 2
                for sec in paper.sections:
                    if query_lower in sec.text.lower():
                        score += 1
                if score > 0:
                    results.append({'paper_id': pid, 'title': paper.metadata.title, 'score': score})
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]

    def list_papers(self) -> list:
        """列出所有已读论文"""
        return [
            {
                'paper_id': pid,
                'title': p.metadata.title,
                'authors': ', '.join(p.metadata.authors[:3]),
                'year': p.metadata.year,
                'sections': len(p.sections),
                'source': p.metadata.source,
            }
            for pid, p in self._papers.items()
        ]

    # --- 内部方法 ---

    def _read_arxiv(self, arxiv_id: str) -> PaperContent:
        """从arxiv读取论文HTML"""
        html = fetch_arxiv_html(arxiv_id)
        if not html:
            logger.warning(f"无法获取arxiv HTML: {arxiv_id}")
            return PaperContent(metadata=PaperMetadata(paper_id=arxiv_id, source='arxiv'))
        content = parse_arxiv_html(html)
        content.metadata.paper_id = arxiv_id
        return content

    def _enrich_with_s2(self, content: PaperContent, arxiv_id: str):
        """用Semantic Scholar数据丰富元数据"""
        s2_data = fetch_s2_paper(arxiv_id)
        if not s2_data:
            return

        if not content.metadata.title and s2_data.get('title'):
            content.metadata.title = s2_data['title']
        if s2_data.get('authors'):
            content.metadata.authors = [a.get('name', '') for a in s2_data['authors']]
        if s2_data.get('year'):
            content.metadata.year = s2_data['year']
        if s2_data.get('abstract'):
            content.metadata.abstract = s2_data['abstract']
        content.metadata.citation_count = s2_data.get('citationCount', 0)
        content.metadata.reference_count = s2_data.get('referenceCount', 0)
        content.metadata.fields_of_study = s2_data.get('fieldsOfStudy', [])

        # 获取引用关系
        s2_id = f"ARXIV:{arxiv_id}"
        citations = fetch_s2_citations(s2_id, limit=5)
        references = fetch_s2_references(s2_id, limit=10)
        content.metadata.venue = s2_data.get('venue', '')

        # 把引用也作为参考文献
        for ref in references:
            if ref.get('title'):
                content.references.append({
                    'title': ref.get('title', ''),
                    'authors': ', '.join(a.get('name', '') for a in ref.get('authors', [])[:3]),
                    'year': ref.get('year', ''),
                    'citation_count': ref.get('citationCount', 0),
                })

    def _extract_findings(self, content: PaperContent):
        """从各章节提取关键发现句"""
        finding_signals = [
            'we found', 'we observed', 'results show', 'results indicate',
            'our results', 'this study', 'we demonstrate', 'findings',
            'significant', 'correlation', 'we show', 'the data suggest',
            '发现', '结果表明', '显著', '相关',
        ]
        for section in content.sections:
            sentences = re.split(r'(?<=[.!?。！？])\s+', section.text)
            for sent in sentences:
                sent_clean = sent.strip()
                if len(sent_clean) < 20 or len(sent_clean) > 500:
                    continue
                if any(sig in sent_clean.lower() for sig in finding_signals):
                    section.key_findings.append(sent_clean)
                    if len(section.key_findings) >= 5:
                        break

    def _save_paper(self, content: PaperContent):
        """保存论文内容到文件"""
        pid = re.sub(r'[^\w\-]', '_', content.metadata.paper_id)
        path = os.path.join(self.output_dir, f'paper_{pid}.md')

        lines = [
            f"# {content.metadata.title or 'Untitled'}",
            "",
        ]
        if content.metadata.authors:
            lines.append(f"**Authors**: {', '.join(content.metadata.authors[:5])}")
        if content.metadata.year:
            lines.append(f"**Year**: {content.metadata.year}")
        if content.metadata.citation_count:
            lines.append(f"**Citations**: {content.metadata.citation_count}")
        if content.metadata.abstract:
            lines.extend(["", "## Abstract", "", content.metadata.abstract])
        lines.append("")

        for sec in content.sections:
            lines.append(f"## {sec.title}")
            lines.append("")
            lines.append(sec.text[:3000])
            if sec.key_findings:
                lines.append("")
                lines.append("**Key Findings:**")
                for f in sec.key_findings[:3]:
                    lines.append(f"- {f}")
            lines.append("")

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _index_paper(self, content: PaperContent):
        """将论文加入RAG索引"""
        try:
            from rag_system import RAGEngine
            engine = RAGEngine()
            chunks = []
            for i, sec in enumerate(content.sections):
                if sec.text:
                    chunk_id = f"{content.metadata.paper_id}_sec_{i}"
                    chunks.append({
                        'chunk_id': chunk_id,
                        'text': sec.text[:2000],
                        'metadata': {
                            'chunk_type': sec.section_type,
                            'section_type': sec.section_type,
                            'section_path': sec.title,
                            'paper_id': content.metadata.paper_id,
                            'title': content.metadata.title,
                        }
                    })
            if chunks:
                engine.add_document(content.metadata.paper_id, chunks)
                logger.info(f"Indexed {len(chunks)} chunks from {content.metadata.paper_id}")
        except ImportError:
            logger.debug("RAG system not available, skipping indexing")
        except Exception as e:
            logger.warning(f"RAG indexing failed: {e}")

    def _store_memory(self, content: PaperContent):
        """将论文关键信息存入KnowledgeStore"""
        try:
            from self_evolving_engine import KnowledgeStore
            store = KnowledgeStore()
            entry_key = f"paper_{content.metadata.paper_id}"
            store.set("resources", entry_key, {
                "type": "paper",
                "title": content.metadata.title,
                "authors": content.metadata.authors[:5],
                "year": content.metadata.year,
                "source": content.metadata.source,
                "arxiv_id": extract_arxiv_id(content.metadata.paper_id),
                "citation_count": content.metadata.citation_count,
                "sections_count": len(content.sections),
                "abstract_snippet": content.metadata.abstract[:200],
                "read_at": content.read_time,
            }, source="paper_reader", confidence=0.9)
        except ImportError:
            logger.debug("KnowledgeStore not available, skipping memory storage")
        except Exception as e:
            logger.warning(f"KnowledgeStore save failed: {e}")


# ============================================================
# 5. CLI入口
# ============================================================

if __name__ == '__main__':
    if '--test' in sys.argv:
        # 测试本地文本读取
        reader = PaperReader()
        test_text = """Title: Dissolved Oxygen Controls on Methanogenesis in Urban Sewer Systems

Abstract
This study investigates the relationship between dissolved oxygen (DO)
and methane (CH4) production in campus sewage networks. Our results
indicate a significant negative correlation between DO and CH4 concentrations.

Introduction
Urban sewer systems are significant sources of greenhouse gas emissions.
Previous studies have shown that anaerobic conditions in sewers promote
methanogenic archaea activity.

Methods
We collected water samples from 15 monitoring points across the campus
sewage network over 12 months. DO, CH4, CO2, TOC and other parameters
were measured using standard methods.

Results
We found that DO and CH4 showed a significant negative correlation
(r=-0.72, p<0.001). The results indicate that dissolved oxygen is the
primary factor controlling methanogenic activity. TOC concentrations
were significantly higher in winter than in spring (p=0.023).

Discussion
Our findings demonstrate that maintaining DO above 2 mg/L can effectively
suppress CH4 production in sewer systems. This has practical implications
for reducing greenhouse gas emissions from urban infrastructure.

Conclusion
This study reveals the key role of dissolved oxygen in controlling
methane production in campus sewage networks.
"""
        # 写入临时文件
        tmp_path = os.path.join(os.getcwd(), '_test_paper.txt')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(test_text)

        paper = reader.read(tmp_path, fetch_metadata=False)
        print(f"\nTitle: {paper.metadata.title}")
        print(f"Sections: {len(paper.sections)}")
        for sec in paper.sections:
            print(f"  [{sec.section_type}] {sec.title}: {len(sec.text)} chars, {len(sec.key_findings)} findings")
            for f in sec.key_findings[:2]:
                print(f"    - {f[:80]}...")

        os.remove(tmp_path)
        print("\n测试通过!")
    else:
        print("用法:")
        print("  python paper_reader.py --test")
        print("  python paper_reader.py https://arxiv.org/abs/2301.12345")
        print("  python paper_reader.py paper.pdf")
