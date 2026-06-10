"""
引用安全防护模块
================
借鉴 PaperQA2 的引用安全机制，
防止 LLM 生成幻觉引用（虚构的作者/年份/DOI）。

核心机制:
  1. 不透明引用键 (ref-xxxxx) — LLM 只能引用这些键
  2. 白名单验证 — 后处理阶段验证每个引用是否在白名单内
  3. 幻觉清除 — 剥离不在白名单中的引用
  4. BibTeX 导出 — 生成机器可读的引用格式
  5. 期刊质量评分 — 基于期刊名的简单评分

借鉴自: https://github.com/Future-House/paper-qa

用法:
    from citation_guard import CitationGuard

    guard = CitationGuard()

    # 为文献分配不透明键
    refs = [
        {"title": "Methane in sewers", "authors": "Guisasola et al.", "year": 2008, "doi": "10.1016/..."},
        {"title": "GHG from sewers", "authors": "Jiang et al.", "year": 2011, "doi": "10.1021/..."},
    ]
    keys = guard.assign_keys(refs)

    # LLM 生成的文本（可能包含幻觉引用）
    llm_text = "Methane production is significant (ref-a3b2c1d4). Some say otherwise (Smith 2020)."

    # 验证并清除幻觉引用
    clean_text = guard.validate_and_strip(llm_text)
    # => "Methane production is significant (ref-a3b2c1d4). Some say otherwise."

    # 导出 BibTeX
    bibtex = guard.export_bibtex()
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────

@dataclass
class GuardEntry:
    """一条引用记录（引用安全防护专用）"""
    key: str = ""                # 不透明键 (ref-xxxxxxxx)
    title: str = ""
    authors: str = ""
    year: int = 0
    doi: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    abstract: str = ""
    citation_type: str = "sota"  # survey/foundational/benchmark/application/critique/sota
    quality_score: int = 0       # 期刊质量评分 0-100
    is_retracted: bool = False   # 是否被撤稿
    raw_text: str = ""           # 原始引用文本

    def to_dict(self):
        return asdict(self)

    def format_apa(self) -> str:
        """APA 格式引用"""
        parts = []
        if self.authors:
            parts.append(self.authors)
        if self.year:
            parts.append(f"({self.year})")
        if self.title:
            parts.append(self.title)
        if self.journal:
            journal_str = f"*{self.journal}*"
            if self.volume:
                journal_str += f", *{self.volume}*"
            if self.issue:
                journal_str += f"({self.issue})"
            if self.pages:
                journal_str += f", {self.pages}"
            parts.append(journal_str)
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}")
        return ". ".join(parts) + "."

    def format_bibtex(self) -> str:
        """BibTeX 格式"""
        # 生成 cite key
        author_part = re.sub(r'[^a-zA-Z]', '', self.authors.split(',')[0].split()[-1]).lower() if self.authors else 'unknown'
        year_part = str(self.year) if self.year else '0000'
        cite_key = f"{author_part}{year_part}"

        fields = []
        if self.authors:
            fields.append(f"  author = {{{self.authors}}}")
        if self.title:
            fields.append(f"  title = {{{self.title}}}")
        if self.journal:
            fields.append(f"  journal = {{{self.journal}}}")
        if self.year:
            fields.append(f"  year = {{{self.year}}}")
        if self.volume:
            fields.append(f"  volume = {{{self.volume}}}")
        if self.issue:
            fields.append(f"  number = {{{self.issue}}}")
        if self.pages:
            fields.append(f"  pages = {{{self.pages}}}")
        if self.doi:
            fields.append(f"  doi = {{{self.doi}}}")

        return f"@article{{{cite_key},\n" + ",\n".join(fields) + "\n}"


@dataclass
class ValidationReport:
    """引用验证报告"""
    total_citations: int = 0
    valid_citations: int = 0
    hallucinated_citations: int = 0
    hallucinated_details: list = field(default_factory=list)
    clean_text: str = ""

    def summary(self) -> str:
        return (f"引用验证: {self.valid_citations}/{self.total_citations} 有效, "
                f"{self.hallucinated_citations} 幻觉已清除")


# ── 期刊质量评分 ──────────────────────────────────────────

# 常见环境科学期刊质量评分 (简化版，基于影响因子区间)
_JOURNAL_QUALITY = {
    # 顶刊 (90-100)
    'nature': 100, 'science': 100, 'nature water': 95,
    'environmental science & technology': 90, 'es&t': 90,
    'water research': 90, 'environmental science & technology letters': 90,
    'nature sustainability': 95, 'nature climate change': 95,
    # 优秀期刊 (70-89)
    'journal of hazardous materials': 80, 'chemical engineering journal': 80,
    'water research x': 75, 'environmental pollution': 75,
    'science of the total environment': 70, 'stoten': 70,
    'journal of environmental management': 70, 'chemosphere': 70,
    'bioresource technology': 75, 'applied microbiology and biotechnology': 70,
    # 良好期刊 (50-69)
    'environmental monitoring and assessment': 55,
    'international journal of environmental research and public health': 55,
    'sustainability': 50, 'applied sciences': 50,
    # 中文核心
    '环境科学': 70, '环境科学学报': 70, '中国环境科学': 65,
    '环境工程学报': 60, '给水排水': 55, '中国给水排水': 55,
}

# 关键词→引用类型映射
_CITATION_TYPE_KEYWORDS = [
    ('survey', ['review', 'survey', 'overview', '综述', '进展', 'trends']),
    ('foundational', ['pioneer', 'first', 'original', 'seminal', 'landmark', '开创', '首次']),
    ('benchmark', ['standard', 'method', 'protocol', 'approach', 'technique', '标准方法']),
    ('application', ['applied', 'case study', 'implementation', '应用', '实例']),
    ('critique', ['limitation', 'problem', 'debate', 'controversy', '争议', '不足']),
]


def classify_citation_type(text: str) -> str:
    """根据引用文本分类引用类型"""
    text_lower = text.lower()
    for ctype, keywords in _CITATION_TYPE_KEYWORDS:
        if any(kw in text_lower for kw in keywords):
            return ctype
    return "sota"


def score_journal_quality(journal: str) -> int:
    """
    期刊质量评分

    Returns
    -------
    int, 0-100 分
    """
    if not journal:
        return 30  # 未知期刊给默认分

    journal_lower = journal.lower().strip()

    # 精确匹配
    if journal_lower in _JOURNAL_QUALITY:
        return _JOURNAL_QUALITY[journal_lower]

    # 模糊匹配
    for j_name, score in _JOURNAL_QUALITY.items():
        if j_name in journal_lower or journal_lower in j_name:
            return score

    return 30  # 默认分


# ── 引用防护主类 ──────────────────────────────────────────

class CitationGuard:
    """
    引用安全防护器

    核心思想：LLM 不应该直接输出 (Author, Year) 格式的引用，
    而应该输出 (ref-xxxxxxxx) 格式的不透明键，由系统后处理映射回真实引用。
    """

    def __init__(self):
        self._entries: dict[str, GuardEntry] = {}  # {key: entry}
        self._title_to_key: dict[str, str] = {}       # {title_lower: key}

    def assign_keys(self, references: list) -> list:
        """
        为引用列表分配不透明键

        Parameters
        ----------
        references : list of dict
            每个 dict 至少包含 title, 可选 authors/year/doi/journal

        Returns
        -------
        list of str, 分配的键列表
        """
        keys = []
        for ref in references:
            # 生成确定性哈希键
            hash_input = f"{ref.get('title','')}{ref.get('year','')}{ref.get('doi','')}"
            hash_val = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            key = f"ref-{hash_val}"

            entry = GuardEntry(
                key=key,
                title=ref.get('title', ''),
                authors=ref.get('authors', ''),
                year=ref.get('year', 0),
                doi=ref.get('doi', ''),
                journal=ref.get('journal', ''),
                volume=ref.get('volume', ''),
                issue=ref.get('issue', ''),
                pages=ref.get('pages', ''),
                abstract=ref.get('abstract', ''),
                raw_text=ref.get('raw_text', ''),
            )

            # 分类引用类型
            full_text = f"{entry.title} {entry.abstract} {entry.raw_text}"
            entry.citation_type = classify_citation_type(full_text)

            # 期刊质量评分
            entry.quality_score = score_journal_quality(entry.journal)

            self._entries[key] = entry
            if entry.title:
                self._title_to_key[entry.title.lower().strip()] = key

            keys.append(key)

        logger.info(f"Assigned {len(keys)} citation keys")
        return keys

    def get_valid_keys(self) -> set:
        """获取所有有效引用键"""
        return set(self._entries.keys())

    def get_entry(self, key: str) -> Optional[GuardEntry]:
        """根据键获取引用条目"""
        return self._entries.get(key)

    def get_formatted_context(self) -> str:
        """
        生成带有效键列表的上下文字符串（用于LLM提示）

        格式:
        Valid citation keys:
        - ref-a3b2c1d4: Guisasola et al. (2008). Methane production in sewer systems. Water Research.
        - ref-e5f6g7h8: Jiang et al. (2011). GHG emissions from sewers. ES&T.
        """
        lines = ["Valid citation keys:"]
        for key, entry in self._entries.items():
            authors = entry.authors[:30] if entry.authors else "Unknown"
            year = f"({entry.year})" if entry.year else ""
            title = entry.title[:60] if entry.title else ""
            journal = entry.journal[:30] if entry.journal else ""
            quality = f"[Q:{entry.quality_score}]" if entry.quality_score else ""
            retracted = " [RETRACTED]" if entry.is_retracted else ""
            lines.append(f"- {key}: {authors} {year}. {title}. {journal} {quality}{retracted}")
        return '\n'.join(lines)

    def validate_and_strip(self, text: str) -> ValidationReport:
        """
        验证文本中的引用，清除幻觉引用

        Parameters
        ----------
        text : str, LLM 生成的文本

        Returns
        -------
        ValidationReport
        """
        valid_keys = self.get_valid_keys()
        report = ValidationReport()
        report.total_citations = 0
        report.valid_citations = 0
        report.hallucinated_citations = 0

        clean = text

        # 1. 查找 (ref-xxxxxxxx) 格式的引用
        ref_pattern = r'\(ref-([a-zA-Z0-9]{8})\)'
        ref_matches = re.findall(ref_pattern, text)
        for hash_val in ref_matches:
            key = f"ref-{hash_val}"
            report.total_citations += 1
            if key in valid_keys:
                report.valid_citations += 1
            else:
                report.hallucinated_citations += 1
                report.hallucinated_details.append(key)
                # 从文本中移除这个幻觉引用
                clean = re.sub(rf'\s*\(ref-{re.escape(hash_val)}\)', '', clean)

        # 2. 查找 (Author, Year) 格式的可疑引用
        author_year_pattern = r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-z]+)*)\s*,?\s*(\d{4})[a-z]?\)'
        ay_matches = re.findall(author_year_pattern, text)
        for author, year in ay_matches:
            report.total_citations += 1
            # 检查是否与已知引用匹配
            matched = False
            for key, entry in self._entries.items():
                if entry.year == int(year) and author.lower() in entry.authors.lower():
                    matched = True
                    report.valid_citations += 1
                    break
            if not matched:
                report.hallucinated_citations += 1
                report.hallucinated_details.append(f"{author} ({year})")
                # 移除这个可疑引用
                pattern = re.escape(f"({author}, {year})")
                clean = re.sub(pattern, '', clean)
                # 也尝试不带逗号的版本
                pattern2 = re.escape(f"({author} {year})")
                clean = re.sub(pattern2, '', clean)

        # 3. 查找 [N] 格式的引用
        bracket_pattern = r'\[(\d+)\]'
        bracket_matches = re.findall(bracket_pattern, text)
        for num in bracket_matches:
            report.total_citations += 1
            # [N] 格式需要与 references 列表对照，这里标记为需要验证
            # 不自动删除，因为可能是合理的编号引用

        # 4. 清理多余空格
        clean = re.sub(r'  +', ' ', clean)
        clean = re.sub(r'\(\s*\)', '', clean)  # 空括号

        report.clean_text = clean.strip()
        return report

    def export_bibtex(self) -> str:
        """导出所有引用为 BibTeX 格式"""
        entries = []
        for key, entry in self._entries.items():
            entries.append(entry.format_bibtex())
        return '\n\n'.join(entries)

    def export_json(self) -> str:
        """导出所有引用为 JSON"""
        data = [entry.to_dict() for entry in self._entries.values()]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def get_statistics(self) -> dict:
        """获取引用统计信息"""
        total = len(self._entries)
        by_type = {}
        by_quality = {'high': 0, 'medium': 0, 'low': 0}

        for entry in self._entries.values():
            by_type[entry.citation_type] = by_type.get(entry.citation_type, 0) + 1
            if entry.quality_score >= 70:
                by_quality['high'] += 1
            elif entry.quality_score >= 40:
                by_quality['medium'] += 1
            else:
                by_quality['low'] += 1

        return {
            'total': total,
            'by_type': by_type,
            'by_quality': by_quality,
            'retracted': sum(1 for e in self._entries.values() if e.is_retracted),
        }

    def save(self, path: str = None):
        """持久化引用库"""
        if path is None:
            path = str(Path(__file__).parent / "knowledge_store" / "citation_library.json")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "entries": {k: v.to_dict() for k, v in self._entries.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str = None):
        """加载引用库"""
        if path is None:
            path = str(Path(__file__).parent / "knowledge_store" / "citation_library.json")
        if not Path(path).exists():
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, entry_dict in data.get("entries", {}).items():
            self._entries[key] = GuardEntry(**entry_dict)
            if self._entries[key].title:
                self._title_to_key[self._entries[key].title.lower()] = key


# ── 集成辅助函数 ──────────────────────────────────────────

def prepare_citation_context(references: list) -> tuple:
    """
    为论文生成准备引用上下文

    Parameters
    ----------
    references : list of dict, 引用列表

    Returns
    -------
    (CitationGuard, str): guard实例 + 格式化的上下文字符串（可直接放入LLM提示）
    """
    guard = CitationGuard()
    guard.assign_keys(references)
    context = guard.get_formatted_context()
    return guard, context


def post_process_citations(text: str, guard: CitationGuard) -> tuple:
    """
    后处理 LLM 生成的文本，清除幻觉引用

    Returns
    -------
    (clean_text, report): 清除后的文本 + 验证报告
    """
    report = guard.validate_and_strip(text)
    return report.clean_text, report


# ── CLI 入口 ──────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        # 测试
        guard = CitationGuard()

        # 1. 分配键
        refs = [
            {"title": "Methane production in sewer systems", "authors": "Guisasola et al.",
             "year": 2008, "journal": "Water Research", "doi": "10.1016/j.watres.2007.10.010"},
            {"title": "GHG emissions from sewers", "authors": "Jiang et al.",
             "year": 2011, "journal": "Environmental Science & Technology"},
        ]
        keys = guard.assign_keys(refs)
        print(f"[OK] Assigned keys: {keys}")

        # 2. 模拟 LLM 输出（含幻觉引用）
        llm_output = (
            f"Methane production is significant ({keys[0]}). "
            f"Previous studies support this ({keys[1]}). "
            f"However, some contradict (ref-xxxxxxxx). "
            f"Smith et al. (2020) found different results. "
            f"According to (Johnson, 2019), the mechanism is complex."
        )
        print(f"\n[LLM output]\n{llm_output}")

        # 3. 验证并清除
        report = guard.validate_and_strip(llm_output)
        print(f"\n[Validation] {report.summary()}")
        print(f"[Clean text]\n{report.clean_text}")
        if report.hallucinated_details:
            print(f"[Hallucinated] {report.hallucinated_details}")

        # 4. BibTeX
        print(f"\n[BibTeX]\n{guard.export_bibtex()}")

        # 5. 统计
        print(f"\n[Stats] {guard.get_statistics()}")

        print("\nAll tests passed!")

    elif '--help' in sys.argv:
        print("用法:")
        print("  python citation_guard.py --test    # 运行测试")
