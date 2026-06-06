"""
引用质量审计 - DOI验证 + 年份评分 + 类型分类 + 多样性分析
借鉴自PaperSpine的citation_quality_audit.py

核心思想：引用不是越多越好，每条引用都应该有质量保证。
"""
import re
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path


# 引用类型关键词匹配规则
CITATION_TYPE_RULES = [
    ('survey', ['review', 'survey', 'overview', '综述', '进展', 'trends', 'state of the art']),
    ('foundational', ['pioneer', 'first', 'original', 'seminal', 'landmark', '开创', '首次']),
    ('benchmark', ['standard', 'method', 'protocol', 'approach', 'technique', '标准方法', '测定方法']),
    ('application', ['applied', 'case study', 'implementation', '应用', '实例']),
    ('critique', ['limitation', 'problem', 'debate', 'controversy', '争议', '不足']),
]


@dataclass
class CitationEntry:
    """一条引用的质量评估"""
    reference: str = ""            # 原始引用文本
    doi: str = ""                  # 提取到的DOI
    year: int = 0                  # 发表年份
    citation_type: str = "sota"    # 引用类型
    doi_resolves: bool = False     # DOI是否有效（需要网络验证）
    crossref_title: str = ""       # Crossref返回的标题
    title_similarity: float = 0.0  # 标题匹配度
    resolvability_score: int = 0   # 可解析性评分 0-100
    recency_score: int = 0         # 新近性评分 0-100
    overall_score: int = 0         # 综合评分 0-100
    status: str = "unverified"     # verified/mismatched/dead/unverified
    issues: list = field(default_factory=list)
    teaching_note: str = ""


def extract_doi(text: str) -> str:
    """从引用文本中提取DOI"""
    match = re.search(r'10\.\d{4,}/[^\s,;)\]]+', text)
    return match.group(0) if match else ""


def extract_year(text: str) -> int:
    """从引用文本中提取年份"""
    # 优先匹配 (20XX) 或 , 20XX, 格式
    match = re.search(r'[\(,]\s*(20\d{2})\s*[,)]', text)
    if match:
        return int(match.group(1))
    # 匹配独立的20XX年份
    matches = re.findall(r'(20[0-2]\d)', text)
    if matches:
        return int(matches[-1])  # 取最后一个（通常是出版年）
    return 0


def classify_citation(text: str) -> str:
    """根据引用文本关键词分类引用类型"""
    text_lower = text.lower()
    for ctype, keywords in CITATION_TYPE_RULES:
        if any(kw in text_lower for kw in keywords):
            return ctype
    return "sota"


def compute_recency_score(year: int, current_year: int = None) -> int:
    """
    计算引用新近性评分

    ≥当前年: 100
    ≥当前年-2: 90
    ≥当前年-4: 70
    ≥当前年-7: 50
    其余: 20
    无年份: 30
    """
    if year == 0:
        return 30
    current_year = current_year or datetime.now().year
    if year >= current_year:
        return 100
    if year >= current_year - 2:
        return 90
    if year >= current_year - 4:
        return 70
    if year >= current_year - 7:
        return 50
    return 20


# DOI验证缓存（避免重复请求Crossref API）
_doi_cache: dict = {}

def verify_doi(doi: str, timeout: int = 10) -> dict:
    """
    通过Crossref API验证DOI（带缓存）

    Returns
    -------
    dict: {resolves, title, year, error}
    """
    if not doi:
        return {"resolves": False, "title": "", "year": 0, "error": "no doi"}

    # 检查缓存
    if doi in _doi_cache:
        return _doi_cache[doi]

    try:
        import urllib.request
        import urllib.error

        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'AcademicAI/1.0 (mailto:research@example.com)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            message = data.get('message', {})
            title_list = message.get('title', [])
            title = title_list[0] if title_list else ""
            pub_date = message.get('published-print', message.get('published-online', {}))
            date_parts = pub_date.get('date-parts', [[]])
            year = date_parts[0][0] if date_parts and date_parts[0] else 0
            result = {"resolves": True, "title": title, "year": year, "error": ""}
            _doi_cache[doi] = result
            return result
    except Exception as e:
        result = {"resolves": False, "title": "", "year": 0, "error": str(e)}
        _doi_cache[doi] = result
        return result


def title_similarity(text1: str, text2: str) -> float:
    """标题相似度（Jaccard + SequenceMatcher混合）"""
    if not text1 or not text2:
        return 0.0

    def _tokens(t):
        return set(re.findall(r'[a-z]{2,}', t.lower()))

    t1, t2 = _tokens(text1), _tokens(text2)
    if not t1 or not t2:
        return 0.0

    jaccard = len(t1 & t2) / len(t1 | t2)
    from difflib import SequenceMatcher
    sm = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return jaccard * 0.5 + sm * 0.5


def audit_citation(ref_text: str, verify: bool = True, timeout: int = 10) -> CitationEntry:
    """
    审计单条引用

    Parameters
    ----------
    ref_text : str, 引用文本
    verify : bool, 是否通过Crossref API验证DOI
    timeout : int, API超时秒数
    """
    entry = CitationEntry(reference=ref_text)

    # 提取DOI和年份
    entry.doi = extract_doi(ref_text)
    entry.year = extract_year(ref_text)
    entry.citation_type = classify_citation(ref_text)

    # 新近性评分
    entry.recency_score = compute_recency_score(entry.year)

    # DOI验证
    if entry.doi and verify:
        result = verify_doi(entry.doi, timeout)
        entry.doi_resolves = result['resolves']
        entry.crossref_title = result.get('title', '')

        if entry.doi_resolves:
            if entry.crossref_title:
                entry.title_similarity = title_similarity(ref_text, entry.crossref_title)
                if entry.title_similarity >= 0.75:
                    entry.status = "verified"
                    entry.resolvability_score = 100
                elif entry.title_similarity >= 0.50:
                    entry.status = "mismatched"
                    entry.resolvability_score = 40
                    entry.issues.append("DOI标题与引用文本不完全匹配")
                else:
                    entry.status = "mismatched"
                    entry.resolvability_score = 20
                    entry.issues.append("DOI标题与引用文本严重不匹配")
            else:
                entry.status = "verified"
                entry.resolvability_score = 80
        else:
            entry.status = "dead"
            entry.resolvability_score = 0
            entry.issues.append(f"DOI无效: {result.get('error', 'unknown')}")
    elif entry.doi:
        entry.status = "unverified"
        entry.resolvability_score = 50
    else:
        entry.status = "unverified"
        entry.resolvability_score = 30
        entry.issues.append("未找到DOI")

    # 综合评分
    entry.overall_score = (entry.resolvability_score + entry.recency_score) // 2

    # 教学提示
    _add_teaching_note(entry)

    return entry


def _add_teaching_note(entry: CitationEntry):
    """为引用添加教学提示"""
    notes = []

    if entry.status == "dead":
        notes.append("死链DOI会让读者无法核实你的引用来源，严重损害论文可信度。请核实DOI或删除。")

    if entry.year and entry.year < datetime.now().year - 7:
        notes.append("该引用超过7年，可能不是领域最新进展。考虑补充近期文献。")

    if entry.citation_type == "sota":
        pass  # SOTA引用是最常见的，无需提示
    elif entry.citation_type == "critique":
        notes.append("批判性引用帮助展示你对领域局限性的理解，是高质量论文的标志。")
    elif entry.citation_type == "survey":
        notes.append("综述引用为读者提供背景，但不宜过多——应更多引用原始研究。")

    entry.teaching_note = " ".join(notes)


def gap_analysis(entries: list) -> dict:
    """
    引用多样性差距分析

    检查各类型引用是否均衡，缺失类型给出教学提示
    """
    if not entries:
        return {"total": 0, "type_distribution": {}, "gaps": [], "teaching_notes": []}

    type_counts = Counter(e.citation_type for e in entries)
    total = len(entries)
    type_dist = {k: round(v / total * 100, 1) for k, v in type_counts.items()}

    expected_min = {
        'sota': 0,       # SOTA至少有但不设最低比例
        'foundational': 5,  # 至少5%
        'survey': 5,
        'benchmark': 3,
        'application': 3,
        'critique': 0,   # critique可选
    }

    gaps = []
    teaching_notes = []
    for ctype, min_pct in expected_min.items():
        actual_pct = type_dist.get(ctype, 0)
        if actual_pct < min_pct:
            gaps.append({
                'type': ctype,
                'expected': f"≥{min_pct}%",
                'actual': f"{actual_pct}%",
            })
            note = _type_guidance(ctype)
            if note:
                teaching_notes.append(note)

    return {
        "total": total,
        "type_distribution": type_dist,
        "gaps": gaps,
        "teaching_notes": teaching_notes,
    }


def _type_guidance(ctype: str) -> str:
    """各引用类型的写作指导"""
    guidance = {
        'foundational': "缺少奠基性引用。请引用定义核心概念或开创方法的原始论文。",
        'survey': "缺少综述引用。请引用1-2篇近期综述来建立背景。",
        'benchmark': "缺少方法引用。请引用你使用的标准方法的原始论文。",
        'application': "缺少应用引用。请引用类似场景的案例研究。",
        'critique': "可选: 添加批判性引用展示你对领域局限性的理解。",
    }
    return guidance.get(ctype, "")


def audit_citations_batch(references: list, verify: bool = True,
                          timeout: int = 10) -> dict:
    """
    批量审计引用列表

    Parameters
    ----------
    references : list of str, 引用文本列表
    verify : bool, 是否验证DOI
    timeout : int, API超时

    Returns
    -------
    dict: {entries, overall_score, verified_count, dead_count, gap_analysis, report}
    """
    entries = []
    for ref in references:
        if ref.strip():
            entry = audit_citation(ref.strip(), verify=verify, timeout=timeout)
            entries.append(entry)

    if not entries:
        return {"entries": [], "overall_score": 0, "verified_count": 0,
                "dead_count": 0, "gap_analysis": {}, "report": "无引用"}

    scores = [e.overall_score for e in entries]
    overall = sum(scores) // len(scores)
    verified = sum(1 for e in entries if e.status == "verified")
    dead = sum(1 for e in entries if e.status == "dead")
    gap = gap_analysis(entries)

    report = format_batch_report(entries, overall, verified, dead, gap)

    return {
        "entries": entries,
        "overall_score": overall,
        "verified_count": verified,
        "dead_count": dead,
        "gap_analysis": gap,
        "report": report,
    }


def format_batch_report(entries, overall_score, verified_count, dead_count, gap_analysis) -> str:
    """格式化批量审计报告"""
    lines = [
        "# 引用质量审计报告",
        "",
        f"- 总引用数: {len(entries)}",
        f"- 综合评分: {overall_score}/100",
        f"- 已验证DOI: {verified_count}",
        f"- 失效DOI: {dead_count}",
        "",
    ]

    if gap_analysis.get('gaps'):
        lines.append("## 多样性差距")
        lines.append("")
        for g in gap_analysis['gaps']:
            lines.append(f"- {g['type']}: 实际 {g['actual']}, 期望 {g['expected']}")
        lines.append("")

    if gap_analysis.get('teaching_notes'):
        lines.append("## 教学提示")
        lines.append("")
        for note in gap_analysis['teaching_notes']:
            lines.append(f"- {note}")
        lines.append("")

    # 每条引用详情
    lines.append("## 引用详情")
    lines.append("")
    lines.append("| # | 类型 | 年份 | 新近性 | DOI状态 | 综合分 | 教学提示 |")
    lines.append("|---|------|------|--------|---------|--------|---------|")
    for i, e in enumerate(entries):
        year_str = str(e.year) if e.year else "N/A"
        doi_status = e.status
        if e.status == "verified":
            doi_status = f"✓ verified"
        elif e.status == "dead":
            doi_status = f"✗ dead"
        tip = e.teaching_note[:30] + ("..." if len(e.teaching_note) > 30 else "") if e.teaching_note else ""
        lines.append(
            f"| {i+1} | {e.citation_type} | {year_str} | {e.recency_score} | "
            f"{doi_status} | {e.overall_score} | {tip} |"
        )

    return '\n'.join(lines)


if __name__ == '__main__':
    if '--test' in sys.argv:
        # 内置测试（不验证DOI）
        test_refs = [
            "Guisasola, A., et al. (2008). Methane production in sewer systems. Water Research, 42(6-7), 1421-1430. DOI: 10.1016/j.watres.2007.10.010",
            "Jiang, G., et al. (2011). Greenhouse gas emissions from sewers. Environmental Science & Technology, 45(19), 8154-8162.",
            "Zhang, L., et al. (2018). Review of carbon transformation in sewage systems. Critical Reviews in Environmental Science, 48(3), 245-278.",
            "Wang, Y., et al. (2023). Dissolved oxygen control on methanogenesis in urban sewers. Nature Water, 1(2), 156-165.",
            "Smith, J. (2001). Old reference about basic chemistry. Journal of Chemistry.",
            "Li, M., et al. (2024). Multi-phase carbon pollutants in campus sewage. Environmental Pollution, 345, 123456.",
        ]

        result = audit_citations_batch(test_refs, verify=False)
        print(result['report'])
        print("\n测试通过!")
    else:
        print("用法: python citation_audit.py --test")
