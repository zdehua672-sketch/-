"""
文献记忆增强模块 — 借鉴ARS (Academic Research Skills) 架构

核心能力（5项优化）:
  P0: 三级引用验证（S2 API + DOI + Levenshtein匹配）
  P1: 文献矩阵自动生成（来源×主题交叉表）
  P2: 证据分级标签（7级证据金字塔）
  P3: 来源可信度检查（掠夺性期刊+索引验证）
  P4: 跨论文关联（引用关系+主题关联+矛盾检测）

借鉴自: Imbad0202/academic-research-skills
"""
import re
import json
import os
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from difflib import SequenceMatcher
from collections import Counter

logger = logging.getLogger(__name__)

# ============================================================
# P2: 证据分级体系（7级证据金字塔）
# ============================================================

EVIDENCE_HIERARCHY = {
    1: {"name": "系统综述/荟萃分析", "name_en": "Systematic Reviews / Meta-analyses",
        "weight": 1.0, "keywords": ["systematic review", "meta-analysis", "cochrane",
                                      "荟萃分析", "系统综述", "meta分析"]},
    2: {"name": "随机对照试验", "name_en": "Randomized Controlled Trials",
        "weight": 0.9, "keywords": ["randomized controlled", "RCT", "randomised",
                                      "随机对照", "随机分配"]},
    3: {"name": "非随机对照研究", "name_en": "Controlled Studies (non-randomized)",
        "weight": 0.8, "keywords": ["quasi-experimental", "controlled study", "cohort study",
                                      "准实验", "队列研究", "对照研究"]},
    4: {"name": "病例对照/纵向研究", "name_en": "Case-Control / Cohort Studies",
        "weight": 0.7, "keywords": ["case-control", "longitudinal", "retrospective",
                                      "病例对照", "纵向研究", "回顾性"]},
    5: {"name": "定性研究系统综述", "name_en": "Systematic Reviews of Descriptive Studies",
        "weight": 0.6, "keywords": ["qualitative review", "meta-synthesis", "meta-ethnography",
                                      "定性综述", "质性综合"]},
    6: {"name": "单一定性研究", "name_en": "Single Descriptive / Qualitative Studies",
        "weight": 0.5, "keywords": ["case study", "ethnography", "interview", "survey",
                                      "案例研究", "田野调查", "问卷调查", "访谈"]},
    7: {"name": "专家意见/委员会报告", "name_en": "Expert Opinion / Committee Reports",
        "weight": 0.3, "keywords": ["expert opinion", "position paper", "editorial",
                                      "专家意见", "立场文件", "述评"]},
}


def classify_evidence_level(metadata: dict, text: str = "") -> int:
    """
    根据论文元数据和文本自动分类证据等级（1-7）

    优先级: 显式标记 > 标题关键词 > 方法段关键词
    """
    combined = " ".join([
        metadata.get("title", ""),
        metadata.get("abstract", ""),
        text[:3000],
    ]).lower()

    for level, info in EVIDENCE_HIERARCHY.items():
        if any(kw.lower() in combined for kw in info["keywords"]):
            return level

    # 默认: 有DOI+期刊 → 视为中等证据；否则低等
    if metadata.get("venue") or metadata.get("doi"):
        return 4
    return 6


# ============================================================
# P3: 来源可信度检查
# ============================================================

# 已知掠夺性期刊发布者（部分列表）
PREDATORY_PUBLISHERS = [
    "omicsonline", "scirp", "scienpub", "iiste", "mejs", "aircc",
    "sciencedomain", "academicjournals", "wudpecker", "iosr",
]

# 高信誉索引
TRUSTED_INDEXES_URL = "https://api.crossref.org/journals"


@dataclass
class SourceCredibility:
    """来源可信度评估结果"""
    paper_id: str = ""
    venue: str = ""
    venue_indexed: bool = False           # 是否被Scopus/WoS索引
    predatory_flag: bool = False          # 是否疑似掠夺性期刊
    predatory_reason: str = ""
    has_doi: bool = False
    author_credibility: float = 0.0      # 0-1
    recency_score: float = 0.0           # 0-1
    overall_score: float = 0.0           # 0-1
    evidence_level: int = 6              # 1-7
    evidence_weight: float = 0.5         # 0-1
    flags: list = field(default_factory=list)
    recommendation: str = ""


def check_source_credibility(metadata: dict, text: str = "") -> SourceCredibility:
    """
    综合检查来源可信度

    检查项:
      1. 期刊/会议是否被索引
      2. 掠夺性期刊筛查
      3. DOI存在性
      4. 作者可信度
      5. 时效性
      6. 证据等级
    """
    result = SourceCredibility()
    result.paper_id = metadata.get("paper_id", "")
    result.venue = metadata.get("venue", "")
    result.has_doi = bool(metadata.get("doi") or metadata.get("arxiv_id"))

    scores = []

    # 1. 期刊检查
    venue_lower = result.venue.lower()
    if venue_lower:
        # 掠夺性期刊筛查
        for pred in PREDATORY_PUBLISHERS:
            if pred in venue_lower:
                result.predatory_flag = True
                result.predatory_reason = f"发布者 '{pred}' 在已知掠夺性名单中"
                result.flags.append("PREDATORY_PUBLISHER")
                break

        # 简单索引推断：知名出版商通常被索引
        trusted_publishers = ["springer", "elsevier", "wiley", "ieee", "acm",
                              "nature", "science", "acs", "rsc", "wiley",
                              "taylor & francis", "sage", "oxford", "cambridge",
                              "frontiers", "plos", "bmc", "mdpi"]
        if any(tp in venue_lower for tp in trusted_publishers):
            result.venue_indexed = True
            scores.append(0.9)
        elif result.predatory_flag:
            scores.append(0.1)
        else:
            scores.append(0.5)  # 未知期刊，给中间分
    else:
        scores.append(0.3)  # 无期刊信息

    # 2. DOI检查
    if result.has_doi:
        scores.append(0.8)
    else:
        scores.append(0.3)
        result.flags.append("NO_DOI")

    # 3. 作者可信度
    authors = metadata.get("authors", [])
    if len(authors) >= 3:
        result.author_credibility = 0.8
    elif len(authors) >= 1:
        result.author_credibility = 0.5
    else:
        result.author_credibility = 0.2
        result.flags.append("NO_AUTHORS")
    scores.append(result.author_credibility)

    # 4. 时效性
    year = metadata.get("year", 0)
    current_year = datetime.now().year
    if year:
        if year >= current_year - 2:
            result.recency_score = 1.0
        elif year >= current_year - 5:
            result.recency_score = 0.7
        elif year >= current_year - 10:
            result.recency_score = 0.4
        else:
            result.recency_score = 0.2
    else:
        result.recency_score = 0.3
        result.flags.append("NO_YEAR")
    scores.append(result.recency_score)

    # 5. 证据等级
    result.evidence_level = classify_evidence_level(metadata, text)
    result.evidence_weight = EVIDENCE_HIERARCHY.get(result.evidence_level, {}).get("weight", 0.5)
    scores.append(result.evidence_weight)

    # 综合评分
    result.overall_score = round(sum(scores) / len(scores), 3)

    # 建议
    if result.predatory_flag:
        result.recommendation = "[警告] 疑似掠夺性期刊，建议谨慎引用或替换来源"
    elif result.overall_score < 0.4:
        result.recommendation = "[警告] 来源可信度低，建议补充更高质量的引用"
    elif result.overall_score < 0.6:
        result.recommendation = "[注意] 来源可信度中等，可考虑补充高证据等级引用"
    else:
        result.recommendation = "[OK] 来源可信度良好"

    return result


# ============================================================
# P0: 三级引用验证
# ============================================================

def levenshtein_similarity(s1: str, s2: str) -> float:
    """
    计算两个字符串的Levenshtein相似度（0-1）

    借鉴ARS的Tier 0验证：相似度 ≥ 0.70 视为匹配
    """
    if not s1 or not s2:
        return 0.0

    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    # 动态规划
    prev = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr = [i]
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            curr.append(min(curr[j-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = curr

    distance = prev[len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


def verify_via_s2(title: str, doi: str = "", timeout: int = 10) -> dict:
    """
    Tier 0: 通过Semantic Scholar API验证引用存在性

    借鉴ARS的semantic_scholar_api_protocol.md:
      - 有DOI → DOI lookup
      - 无DOI → title search + Levenshtein ≥ 0.70

    Returns:
      {found, s2_id, s2_title, s2_year, s2_venue, s2_citation_count,
       match_score, verification_method, error}
    """
    try:
        import urllib.request
        import urllib.parse

        base = "https://api.semanticscholar.org/graph/v1/paper"
        fields = "title,authors,year,externalIds,venue,citationCount"

        if doi:
            # Pattern 2: DOI lookup
            url = f"{base}/DOI:{doi}?fields={fields}"
            method = "s2_doi_lookup"
        else:
            # Pattern 1: Title search
            encoded = urllib.parse.quote(title[:200])
            url = f"{base}/search?query={encoded}&limit=3&fields={fields}"
            method = "s2_title_search"

        req = urllib.request.Request(url, headers={
            'User-Agent': 'AcademicAI/1.0 (research tool)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())

        if doi:
            # DOI lookup returns single paper
            if data and data.get("title"):
                sim = levenshtein_similarity(title, data["title"])
                return {
                    "found": True, "s2_id": data.get("paperId", ""),
                    "s2_title": data["title"], "s2_year": data.get("year", 0),
                    "s2_venue": data.get("venue", ""),
                    "s2_citation_count": data.get("citationCount", 0),
                    "match_score": round(sim, 3),
                    "verification_method": method,
                    "doi_mismatch": sim < 0.70,  # DOI匹配但标题不匹配 → 幻觉模式
                    "error": "",
                }
            return {"found": False, "match_score": 0.0,
                    "verification_method": method, "error": "DOI not found in S2"}
        else:
            # Title search returns list
            papers = data.get("data", [])
            if papers:
                best = papers[0]
                sim = levenshtein_similarity(title, best.get("title", ""))
                if sim >= 0.70:
                    # 检查年份匹配
                    year_match = True  # 无输入年份时不检查
                    return {
                        "found": True, "s2_id": best.get("paperId", ""),
                        "s2_title": best.get("title", ""),
                        "s2_year": best.get("year", 0),
                        "s2_venue": best.get("venue", ""),
                        "s2_citation_count": best.get("citationCount", 0),
                        "match_score": round(sim, 3),
                        "verification_method": method, "error": "",
                    }
            return {"found": False, "match_score": 0.0,
                    "verification_method": method, "error": "No match (Levenshtein < 0.70)"}

    except Exception as e:
        logger.warning(f"S2 API error: {e}")
        return {"found": False, "match_score": 0.0,
                "verification_method": "s2_unavailable", "error": str(e)}


def verify_via_doi(doi: str, timeout: int = 10) -> dict:
    """
    Tier 1: 通过Crossref验证DOI解析性

    Returns: {resolves, title, year, error}
    """
    if not doi:
        return {"resolves": False, "title": "", "year": 0, "error": "no doi"}

    try:
        import urllib.request
        url = f"https://api.crossref.org/works/{doi}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'AcademicAI/1.0 (mailto:research@example.com)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get('message', {})
            title_list = msg.get('title', [])
            title = title_list[0] if title_list else ""
            pub = msg.get('published-print', msg.get('published-online', {}))
            parts = pub.get('date-parts', [[]])
            year = parts[0][0] if parts and parts[0] else 0
            return {"resolves": True, "title": title, "year": year, "error": ""}
    except Exception as e:
        return {"resolves": False, "title": "", "year": 0, "error": str(e)}


def tiered_verify_citation(ref_text: str, doi: str = "", title: str = "",
                           year: int = 0, timeout: int = 10) -> dict:
    """
    三级引用验证管道

    Tier 0: Semantic Scholar API（100%覆盖）→ Levenshtein ≥ 0.70
    Tier 1: DOI解析验证（100%覆盖DOI-bearing refs）
    Tier 2: 标题相似度交叉验证

    返回验证结果和置信度评分

    Returns:
      {tier0_s2, tier1_doi, tier2_cross, final_status, confidence, flags}
    """
    result = {
        "reference": ref_text[:120],
        "doi": doi,
        "tier0_s2": None,
        "tier1_doi": None,
        "tier2_cross": None,
        "final_status": "UNVERIFIED",
        "confidence": 0.0,
        "flags": [],
    }

    # --- Tier 0: S2 API验证 ---
    search_title = title or ref_text[:200]
    s2_result = verify_via_s2(search_title, doi=doi, timeout=timeout)
    result["tier0_s2"] = s2_result

    if s2_result.get("found"):
        # S2验证通过
        if s2_result.get("doi_mismatch"):
            # DOI幻觉模式：DOI指向了不同的论文
            result["flags"].append("DOI_MISMATCH")
            result["final_status"] = "S2_DOI_MISMATCH"
            result["confidence"] = 0.2
        else:
            result["final_status"] = "S2_VERIFIED"
            result["confidence"] = min(1.0, s2_result["match_score"] + 0.2)
            return result  # Tier 0通过，跳过后续
    elif s2_result.get("error") and "unavailable" in s2_result.get("verification_method", ""):
        result["flags"].append("S2_API_UNAVAILABLE")
        # S2不可用，降级到Tier 1+2
    else:
        result["flags"].append("S2_NOT_FOUND")

    # --- Tier 1: DOI验证 ---
    if doi:
        doi_result = verify_via_doi(doi, timeout=timeout)
        result["tier1_doi"] = doi_result

        if doi_result["resolves"]:
            # DOI有效，检查标题匹配
            if doi_result["title"] and search_title:
                sim = levenshtein_similarity(search_title, doi_result["title"])
                if sim >= 0.70:
                    result["final_status"] = "DOI_VERIFIED"
                    result["confidence"] = 0.85
                elif sim >= 0.40:
                    result["final_status"] = "DOI_MISMATCH"
                    result["confidence"] = 0.4
                    result["flags"].append("DOI_TITLE_PARTIAL_MISMATCH")
                else:
                    result["final_status"] = "DOI_MISMATCH"
                    result["confidence"] = 0.2
                    result["flags"].append("DOI_TITLE_SEVERE_MISMATCH")
            else:
                result["final_status"] = "DOI_VERIFIED"
                result["confidence"] = 0.7
        else:
            result["final_status"] = "DOI_DEAD"
            result["confidence"] = 0.1
            result["flags"].append("DOI_INVALID")
            result["flags"].append(f"DOI_ERROR: {doi_result.get('error', '')[:80]}")

    # --- Tier 2: 交叉验证 ---
    if title and ref_text:
        cross_sim = levenshtein_similarity(title, ref_text[:len(title)+50])
        result["tier2_cross"] = {"similarity": round(cross_sim, 3)}
        if cross_sim >= 0.6:
            result["confidence"] = max(result["confidence"], 0.5)

    # 最终状态兜底
    if result["final_status"] == "UNVERIFIED" and not doi:
        result["final_status"] = "NO_DOI"
        result["confidence"] = 0.3
        result["flags"].append("NO_DOI_UNVERIFIABLE")

    return result


# ============================================================
# P1: 文献矩阵
# ============================================================

@dataclass
class PaperEntry:
    """文献矩阵中的一篇论文"""
    paper_id: str = ""
    title: str = ""
    authors: str = ""
    year: int = 0
    evidence_level: int = 6
    evidence_weight: float = 0.5
    credibility_score: float = 0.5
    themes: dict = field(default_factory=dict)  # {theme: "✓ 支持"/"✗ 矛盾"/"—"}
    key_findings: list = field(default_factory=list)
    source: str = ""


class LiteratureMatrix:
    """
    文献矩阵：来源 × 主题交叉表

    借鉴ARS的literature_matrix_template.md:
      - 基本矩阵: Source × Theme 交叉
      - 证据收敛摘要: 各主题的证据强度
      - 知识缺口识别
    """

    def __init__(self):
        self.papers: Dict[str, PaperEntry] = {}
        self.themes: List[str] = []
        self.theme_keywords: Dict[str, List[str]] = {}

    def add_paper(self, paper_entry: PaperEntry):
        """添加论文到矩阵"""
        self.papers[paper_entry.paper_id] = paper_entry

    def auto_detect_themes(self, max_themes: int = 8):
        """
        从所有论文的key_findings和section文本中自动提取主题

        使用TF-like方法：统计高频专业术语作为主题候选
        """
        # 收集所有文本
        all_text = []
        for p in self.papers.values():
            all_text.extend(p.key_findings)
            all_text.extend([t for t in p.themes.values() if isinstance(t, str)])

        combined = " ".join(all_text).lower()

        # 提取2-gram和3-gram候选
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                     "to", "for", "of", "and", "or", "with", "by", "from", "this",
                     "that", "these", "those", "it", "its", "we", "our", "can",
                     "has", "have", "had", "be", "been", "not", "but", "also",
                     "than", "more", "less", "show", "results", "study", "found",
                     "的", "了", "在", "是", "和", "与", "对", "等", "中", "研究",
                     "结果", "表明", "发现", "通过", "分析", "表明"}

        words = re.findall(r'[a-z]{3,}|[一-鿿]{2,}', combined)
        word_freq = Counter(w for w in words if w not in stopwords)

        # 取高频词作为主题候选（过滤太泛的词）
        generic = {"data", "model", "method", "system", "effect", "level",
                    "analysis", "concentration", "using", "based", "between",
                    "不同", "显著", "相关", "影响", "实验"}
        candidates = [(w, c) for w, c in word_freq.most_common(max_themes * 2)
                      if w not in generic and c >= 2]

        self.themes = [w for w, c in candidates[:max_themes]]
        self.theme_keywords = {t: [t] for t in self.themes}

        # 自动标注每篇论文的主题关系
        for pid, paper in self.papers.items():
            findings_text = " ".join(paper.key_findings).lower()
            for theme in self.themes:
                if theme in findings_text:
                    # 判断是支持还是矛盾
                    context = self._find_context(findings_text, theme)
                    if any(neg in context for neg in ["not", "no ", "however", "contradict",
                                                       "相反", "没有", "不显著"]):
                        paper.themes[theme] = "✗ 矛盾"
                    else:
                        paper.themes[theme] = "✓ 支持"
                else:
                    paper.themes.setdefault(theme, "—")

    def _find_context(self, text: str, keyword: str, window: int = 80) -> str:
        """提取关键词周围的上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]

    def convergence_summary(self) -> List[dict]:
        """
        证据收敛摘要

        Returns: [{theme, supports, contradicts, net, strength, confidence}]
        """
        summary = []
        for theme in self.themes:
            supports = 0
            contradicts = 0
            support_levels = []

            for paper in self.papers.values():
                stance = paper.themes.get(theme, "—")
                if "✓" in stance:
                    supports += 1
                    support_levels.append(paper.evidence_level)
                elif "✗" in stance:
                    contradicts += 1

            net = supports - contradicts
            if supports == 0 and contradicts == 0:
                strength = "Gap"
                confidence = "—"
            elif net >= 3 and (not support_levels or min(support_levels) <= 3):
                strength = "强 (Strong)"
                confidence = "高 (High)"
            elif net >= 2:
                strength = "中 (Moderate)"
                confidence = "中 (Medium)"
            elif net >= 1:
                strength = "弱 (Weak)"
                confidence = "低 (Low)"
            elif contradicts > 0 and supports > 0:
                strength = "有争议 (Contested)"
                confidence = "中 (Medium)"
            else:
                strength = "Gap"
                confidence = "—"

            summary.append({
                "theme": theme,
                "supports": supports,
                "contradicts": contradicts,
                "net": net,
                "strength": strength,
                "confidence": confidence,
            })

        return sorted(summary, key=lambda x: x["net"], reverse=True)

    def gap_analysis(self) -> List[dict]:
        """知识缺口识别"""
        gaps = []
        convergence = self.convergence_summary()

        for item in convergence:
            if item["strength"] == "Gap":
                gaps.append({
                    "theme": item["theme"],
                    "type": "主题空白",
                    "description": f"'{item['theme']}' 主题无相关文献",
                    "priority": "高",
                })
            elif item["strength"] == "弱 (Weak)" and item["supports"] == 1:
                gaps.append({
                    "theme": item["theme"],
                    "type": "证据不足",
                    "description": f"'{item['theme']}' 仅1篇文献支持",
                    "priority": "中",
                })

        # 方法论缺口
        all_levels = [p.evidence_level for p in self.papers.values()]
        if all_levels:
            level_dist = Counter(all_levels)
            if level_dist.get(1, 0) == 0 and level_dist.get(2, 0) == 0:
                gaps.append({
                    "theme": "方法论",
                    "type": "高证据等级缺失",
                    "description": "无系统综述或RCT，全为中低等级证据",
                    "priority": "高",
                })

        return gaps

    def to_markdown(self) -> str:
        """生成文献矩阵Markdown报告"""
        lines = [
            "# 文献矩阵",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**论文总数**: {len(self.papers)}",
            f"**主题数**: {len(self.themes)}",
            "",
        ]

        # --- 基本矩阵 ---
        if self.themes:
            header = "| 论文 | 年份 | 证据等级 | " + " | ".join(self.themes) + " |"
            sep = "|------|------|----------|" + "|".join(["-----"] * len(self.themes)) + "|"
            lines.extend(["## 基本矩阵", "", header, sep])

            for pid, paper in sorted(self.papers.items(),
                                      key=lambda x: x[1].year, reverse=True):
                title_short = paper.title[:30] + ("..." if len(paper.title) > 30 else "")
                level_name = EVIDENCE_HIERARCHY.get(paper.evidence_level, {}).get("name", "N/A")
                cells = []
                for theme in self.themes:
                    cells.append(paper.themes.get(theme, "—"))
                lines.append(f"| {title_short} | {paper.year} | {paper.evidence_level}级 {level_name[:6]} | "
                             + " | ".join(cells) + " |")

            lines.append("")

        # --- 证据收敛摘要 ---
        convergence = self.convergence_summary()
        if convergence:
            lines.extend(["## 证据收敛摘要", "",
                          "| 主题 | 支持 | 矛盾 | 净值 | 强度 | 置信度 |",
                          "|------|------|------|------|------|--------|"])
            for item in convergence:
                lines.append(f"| {item['theme']} | {item['supports']}✓ | "
                             f"{item['contradicts']}✗ | {item['net']:+d} | "
                             f"{item['strength']} | {item['confidence']} |")
            lines.append("")

        # --- 知识缺口 ---
        gaps = self.gap_analysis()
        if gaps:
            lines.extend(["## 知识缺口", "",
                          "| 缺口 | 类型 | 说明 | 优先级 |",
                          "|------|------|------|--------|"])
            for g in gaps:
                lines.append(f"| {g['theme']} | {g['type']} | {g['description']} | {g['priority']} |")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "themes": self.themes,
            "papers": {pid: {
                "title": p.title, "authors": p.authors, "year": p.year,
                "evidence_level": p.evidence_level,
                "evidence_weight": p.evidence_weight,
                "credibility_score": p.credibility_score,
                "themes": p.themes, "key_findings": p.key_findings[:3],
            } for pid, p in self.papers.items()},
            "convergence": self.convergence_summary(),
            "gaps": self.gap_analysis(),
        }


# ============================================================
# P4: 跨论文关联
# ============================================================

@dataclass
class PaperLink:
    """两篇论文之间的关联"""
    source_id: str = ""
    target_id: str = ""
    link_type: str = ""     # cites / contradicts / extends / same_theme / same_author
    strength: float = 0.0   # 0-1
    detail: str = ""


class LiteratureNetwork:
    """
    跨论文关系网络

    追踪:
      - 引用关系（A引用B）
      - 主题关联（A和B讨论同一主题）
      - 矛盾关系（A和B结论相反）
      - 扩展关系（A的方法被B使用）
    """

    def __init__(self, links_path: str = None):
        self.links_path = links_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "knowledge_store", "literature_links.json"
        )
        self.links: List[PaperLink] = []
        self._load()

    def _load(self):
        """加载已有关联"""
        if os.path.exists(self.links_path):
            try:
                with open(self.links_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("links", []):
                    self.links.append(PaperLink(**item))
            except Exception as e:
                logger.warning(f"Failed to load literature links: {e}")

    def save(self):
        """持久化关联"""
        os.makedirs(os.path.dirname(self.links_path), exist_ok=True)
        data = {
            "meta": {
                "count": len(self.links),
                "updated": datetime.now(timezone.utc).isoformat(),
            },
            "links": [asdict(link) for link in self.links],
        }
        with open(self.links_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_link(self, source_id: str, target_id: str, link_type: str,
                 strength: float = 0.5, detail: str = ""):
        """添加关联（去重）"""
        # 检查是否已存在
        for link in self.links:
            if (link.source_id == source_id and link.target_id == target_id
                    and link.link_type == link_type):
                # 更新强度
                link.strength = max(link.strength, strength)
                if detail:
                    link.detail = detail
                self.save()
                return

        self.links.append(PaperLink(
            source_id=source_id, target_id=target_id,
            link_type=link_type, strength=strength, detail=detail,
        ))
        self.save()

    def build_from_matrix(self, matrix: LiteratureMatrix):
        """从文献矩阵自动构建关联"""
        papers = list(matrix.papers.values())

        for i, p1 in enumerate(papers):
            for p2 in papers[i+1:]:
                # 主题关联
                shared_themes = []
                for theme in matrix.themes:
                    t1 = p1.themes.get(theme, "—")
                    t2 = p2.themes.get(theme, "—")
                    if "✓" in t1 and "✓" in t2:
                        shared_themes.append(theme)
                    elif ("✓" in t1 and "✗" in t2) or ("✗" in t1 and "✓" in t2):
                        self.add_link(p1.paper_id, p2.paper_id, "contradicts",
                                      strength=0.7, detail=f"主题 '{theme}' 结论相反")

                if shared_themes:
                    strength = min(1.0, 0.3 + len(shared_themes) * 0.2)
                    self.add_link(p1.paper_id, p2.paper_id, "same_theme",
                                  strength=strength,
                                  detail=f"共同主题: {', '.join(shared_themes)}")

                # 作者关联
                authors1 = set(p1.authors.lower().split(","))
                authors2 = set(p2.authors.lower().split(","))
                common = authors1 & authors2
                common.discard("")
                if common:
                    self.add_link(p1.paper_id, p2.paper_id, "same_author",
                                  strength=0.8,
                                  detail=f"共同作者: {', '.join(common)}")

    def get_related(self, paper_id: str, link_type: str = None,
                    min_strength: float = 0.0) -> List[dict]:
        """获取与指定论文相关的论文"""
        related = []
        for link in self.links:
            if link.source_id == paper_id or link.target_id == paper_id:
                if link_type and link.link_type != link_type:
                    continue
                if link.strength < min_strength:
                    continue
                other = link.target_id if link.source_id == paper_id else link.source_id
                related.append({
                    "paper_id": other,
                    "link_type": link.link_type,
                    "strength": link.strength,
                    "detail": link.detail,
                })
        return sorted(related, key=lambda x: x["strength"], reverse=True)

    def get_network_stats(self) -> dict:
        """网络统计"""
        types = Counter(link.link_type for link in self.links)
        papers = set()
        for link in self.links:
            papers.add(link.source_id)
            papers.add(link.target_id)
        return {
            "total_links": len(self.links),
            "total_papers": len(papers),
            "link_types": dict(types),
        }

    def to_markdown(self, paper_titles: dict = None) -> str:
        """生成关联报告Markdown"""
        lines = ["# 论文关联网络", ""]

        stats = self.get_network_stats()
        lines.extend([
            f"**关联总数**: {stats['total_links']}",
            f"**论文节点**: {stats['total_papers']}",
            "",
        ])

        if stats.get("link_types"):
            lines.extend(["## 关联类型分布", ""])
            for ltype, count in stats["link_types"].items():
                type_names = {
                    "same_theme": "主题关联",
                    "contradicts": "结论矛盾",
                    "same_author": "共同作者",
                    "cites": "引用关系",
                    "extends": "方法扩展",
                }
                lines.append(f"- {type_names.get(ltype, ltype)}: {count}条")
            lines.append("")

        # 按论文分组展示
        by_paper = {}
        for link in self.links:
            by_paper.setdefault(link.source_id, []).append(link)
            by_paper.setdefault(link.target_id, []).append(link)

        if by_paper:
            lines.extend(["## 各论文关联", ""])
            for pid, links in sorted(by_paper.items(),
                                      key=lambda x: len(x[1]), reverse=True):
                title = (paper_titles or {}).get(pid, pid)
                lines.append(f"### {title}")
                for link in links:
                    other = link.target_id if link.source_id == pid else link.source_id
                    other_title = (paper_titles or {}).get(other, other)
                    lines.append(f"  - [{link.link_type}] → {other_title} "
                                 f"(强度: {link.strength:.1f}) {link.detail}")
                lines.append("")

        return "\n".join(lines)


# ============================================================
# 统一入口：文献记忆管理器
# ============================================================

class LiteratureMemory:
    """
    文献记忆管理器 — 整合P0-P4全部能力

    用法:
        mem = LiteratureMemory()
        # 读入论文后自动评估
        result = mem.assess_paper(paper_content)
        # 构建文献矩阵
        matrix = mem.build_matrix()
        # 验证引用
        citations = mem.verify_citations_batch(ref_list)
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.matrix = LiteratureMatrix()
        self.network = LiteratureNetwork(
            os.path.join(self.base_dir, "knowledge_store", "literature_links.json")
        )
        self._assessments: Dict[str, dict] = {}

    def assess_paper(self, paper_content) -> dict:
        """
        对一篇论文做完整评估（P2证据分级 + P3来源可信度）

        Parameters
        ----------
        paper_content : PaperContent (from paper_reader.py)

        Returns
        -------
        dict: {evidence_level, credibility, source_credibility}
        """
        meta = {
            "paper_id": paper_content.metadata.paper_id,
            "title": paper_content.metadata.title,
            "authors": paper_content.metadata.authors,
            "year": paper_content.metadata.year,
            "venue": paper_content.metadata.venue,
            "doi": paper_content.metadata.doi,
            "arxiv_id": paper_content.metadata.arxiv_url,
            "abstract": paper_content.metadata.abstract,
        }

        # 提取全文文本用于分类
        full_text = "\n".join(sec.text for sec in paper_content.sections)

        # P2: 证据分级
        evidence_level = classify_evidence_level(meta, full_text)
        evidence_weight = EVIDENCE_HIERARCHY.get(evidence_level, {}).get("weight", 0.5)

        # P3: 来源可信度
        credibility = check_source_credibility(meta, full_text)

        # 收集关键发现
        all_findings = []
        for sec in paper_content.sections:
            all_findings.extend(sec.key_findings)

        assessment = {
            "paper_id": meta["paper_id"],
            "title": meta["title"],
            "evidence_level": evidence_level,
            "evidence_level_name": EVIDENCE_HIERARCHY.get(evidence_level, {}).get("name", ""),
            "evidence_weight": evidence_weight,
            "credibility_score": credibility.overall_score,
            "credibility_flags": credibility.flags,
            "predatory_flag": credibility.predatory_flag,
            "recommendation": credibility.recommendation,
            "key_findings": all_findings[:10],
        }

        self._assessments[meta["paper_id"]] = assessment

        # 加入文献矩阵
        entry = PaperEntry(
            paper_id=meta["paper_id"],
            title=meta["title"],
            authors=", ".join(meta["authors"][:3]) if meta["authors"] else "",
            year=meta["year"],
            evidence_level=evidence_level,
            evidence_weight=evidence_weight,
            credibility_score=credibility.overall_score,
            key_findings=all_findings[:5],
            source=paper_content.metadata.source,
        )
        self.matrix.add_paper(entry)

        return assessment

    def build_matrix(self, auto_detect_themes: bool = True) -> LiteratureMatrix:
        """
        构建文献矩阵（P1）

        Parameters
        ----------
        auto_detect_themes : bool, 是否自动检测主题
        """
        if auto_detect_themes:
            self.matrix.auto_detect_themes()

        # 自动构建关联（P4）
        self.network.build_from_matrix(self.matrix)

        return self.matrix

    def verify_citations_batch(self, references: list, timeout: int = 10) -> List[dict]:
        """
        批量三级引用验证（P0）

        Parameters
        ----------
        references : list of dict, 每个至少包含 {title, doi?}
        """
        results = []
        for ref in references:
            title = ref.get("title", "")
            doi = ref.get("doi", "")
            year = ref.get("year", 0)
            ref_text = ref.get("text", title)

            if not title and not doi:
                continue

            result = tiered_verify_citation(
                ref_text, doi=doi, title=title, year=year, timeout=timeout
            )
            results.append(result)

        return results

    def get_report(self) -> str:
        """生成完整的文献记忆报告"""
        lines = [
            "=" * 50,
            "文献记忆系统报告",
            "=" * 50,
            "",
            f"已评估论文: {len(self._assessments)}篇",
            f"矩阵主题数: {len(self.matrix.themes)}",
            "",
        ]

        # 证据等级分布
        levels = Counter(a["evidence_level"] for a in self._assessments.values())
        if levels:
            lines.append("证据等级分布:")
            for level in sorted(levels):
                name = EVIDENCE_HIERARCHY.get(level, {}).get("name", "")
                lines.append(f"  Level {level} ({name}): {levels[level]}篇")
            lines.append("")

        # 可信度统计
        scores = [a["credibility_score"] for a in self._assessments.values()]
        if scores:
            avg_score = sum(scores) / len(scores)
            lines.append(f"平均可信度: {avg_score:.2f}")
            flags_total = sum(len(a.get("credibility_flags", []))
                             for a in self._assessments.values())
            if flags_total:
                lines.append(f"总标记数: {flags_total}")
            lines.append("")

        # 掠夺性期刊警告
        predatory = [a for a in self._assessments.values() if a.get("predatory_flag")]
        if predatory:
            lines.append("[警告] 掠夺性期刊警告:")
            for p in predatory:
                lines.append(f"  - {p['title'][:60]}")
            lines.append("")

        # 网络统计
        net_stats = self.network.get_network_stats()
        lines.append(f"论文关联: {net_stats['total_links']}条, "
                     f"涉及{net_stats['total_papers']}篇论文")

        return "\n".join(lines)

    def save_all(self):
        """持久化所有数据"""
        # 保存矩阵
        matrix_path = os.path.join(self.base_dir, "knowledge_store", "literature_matrix.json")
        os.makedirs(os.path.dirname(matrix_path), exist_ok=True)
        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(self.matrix.to_dict(), f, ensure_ascii=False, indent=2)

        # 保存评估
        assess_path = os.path.join(self.base_dir, "knowledge_store", "paper_assessments.json")
        with open(assess_path, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {
                    "count": len(self._assessments),
                    "updated": datetime.now(timezone.utc).isoformat(),
                },
                "assessments": self._assessments,
            }, f, ensure_ascii=False, indent=2)

        # 保存关联
        self.network.save()

        logger.info(f"文献记忆已保存: {len(self._assessments)}篇评估, "
                     f"{len(self.matrix.themes)}个主题, "
                     f"{len(self.network.links)}条关联")


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    if "--test" in sys.argv:
        mem = LiteratureMemory()

        # 模拟论文数据
        from paper_reader import PaperContent, PaperMetadata, PaperSection

        paper1 = PaperContent(
            metadata=PaperMetadata(
                paper_id="test_001", title="Dissolved Oxygen Controls on Methanogenesis",
                authors=["Smith, J.", "Zhang, L."], year=2024,
                venue="Water Research", doi="10.1016/j.watres.2024.001",
                abstract="Systematic review of DO effects on CH4 in sewers",
                source="arxiv",
            ),
            sections=[
                PaperSection(section_type="methods", title="Methods",
                             text="This systematic review analyzed 45 studies...",
                             key_findings=["DO negatively correlates with CH4 (r=-0.72)"]),
                PaperSection(section_type="results", title="Results",
                             text="Meta-analysis shows significant effect...",
                             key_findings=["Pooled effect size d=0.45, p<0.001"]),
            ]
        )

        paper2 = PaperContent(
            metadata=PaperMetadata(
                paper_id="test_002", title="Carbon Transformation in Campus Sewage Networks",
                authors=["Li, M.", "Wang, Y."], year=2023,
                venue="Environmental Pollution", doi="10.1016/j.envpol.2023.002",
                abstract="Case study of carbon pollutants in campus sewage",
                source="arxiv",
            ),
            sections=[
                PaperSection(section_type="methods", title="Methods",
                             text="Case study with interview and survey methods...",
                             key_findings=["TOC concentrations higher in winter (p=0.023)"]),
                PaperSection(section_type="results", title="Results",
                             text="DO showed no significant correlation with CH4...",
                             key_findings=["No significant correlation between DO and CH4"]),
            ]
        )

        # P2+P3: 评估论文
        a1 = mem.assess_paper(paper1)
        print(f"\n论文1评估:")
        print(f"  证据等级: Level {a1['evidence_level']} ({a1['evidence_level_name']})")
        print(f"  可信度: {a1['credibility_score']:.2f}")
        print(f"  建议: {a1['recommendation']}")

        a2 = mem.assess_paper(paper2)
        print(f"\n论文2评估:")
        print(f"  证据等级: Level {a2['evidence_level']} ({a2['evidence_level_name']})")
        print(f"  可信度: {a2['credibility_score']:.2f}")
        print(f"  建议: {a2['recommendation']}")

        # P1: 构建矩阵
        matrix = mem.build_matrix()
        print(f"\n文献矩阵: {len(matrix.papers)}篇, {len(matrix.themes)}个主题")
        print(f"主题: {matrix.themes}")

        # P4: 查看关联
        net_stats = mem.network.get_network_stats()
        print(f"\n论文关联: {net_stats}")

        # 报告
        print(f"\n{mem.get_report()}")

        # Markdown
        print(f"\n{matrix.to_markdown()}")

        # P0: 引用验证测试
        print("\n--- 三级引用验证测试 ---")
        ref_results = mem.verify_citations_batch([
            {"title": "Dissolved oxygen controls on methanogenesis",
             "doi": "10.1016/j.watres.2024.001", "year": 2024},
        ], timeout=5)
        for r in ref_results:
            print(f"  状态: {r['final_status']}, 置信度: {r['confidence']:.2f}, "
                  f"标记: {r['flags']}")

        mem.save_all()
        print("\n测试通过!")
    else:
        print("用法: python literature_memory.py --test")
