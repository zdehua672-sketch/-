"""
=============================================================================
Academic Review & Proofreading Agent - 论文自动检查系统
10类检查 + AI痕迹识别 + 修改建议 + 审稿意见级报告
=============================================================================
"""

import re
import os
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from self_evolving_engine import FeedbackCollector, KnowledgeStore
except ImportError:
    FeedbackCollector = None
    KnowledgeStore = None

try:
    from citation_audit import audit_citations_batch
except ImportError:
    audit_citations_batch = None

# ============================================================================
# 数据结构
# ============================================================================


# AI标志符号和表达检测规则
AI_MARKER_RULES = {
    'symbols': ['**', '__', '~~'],  # Markdown格式符号
    'phrases': [
        '具有重要意义',
        '重要组成部分',
        '综上所述',
        '深入探讨',
        '驱动',
        '赋能',
        '闭环',
        '颗粒度',
        '抓手',
        '打法',
        '组合拳',
        '底层逻辑',
        '顶层设计',
        '不仅是...更是',
        '不仅...而且',
        '一方面...另一方面',
        '首先...其次...最后',
    ],
    'sentence_patterns': [
        r'本研究.*具有重要意义',
        r'综上所述.*',
        r'基于上述分析.*',
    ]
}

def detect_ai_markers(text: str) -> list:
    """
    检测文本中的AI标志符号和表达
    
    Parameters
    ----------
    text : str, 待检测文本
    
    Returns
    -------
    list of dict: 检测到的AI标志列表
    """
    import re
    
    issues = []
    
    # 检测符号
    for symbol in AI_MARKER_RULES['symbols']:
        if symbol in text:
            issues.append({
                'type': 'symbol',
                'content': symbol,
                'suggestion': f'删除AI标志符号: {symbol}'
            })
    
    # 检测短语
    for phrase in AI_MARKER_RULES['phrases']:
        if phrase in text:
            issues.append({
                'type': 'phrase',
                'content': phrase,
                'suggestion': f'替换AI标志表达: {phrase}'
            })
    
    # 检测句式
    for pattern in AI_MARKER_RULES['sentence_patterns']:
        matches = re.findall(pattern, text)
        for match in matches:
            issues.append({
                'type': 'pattern',
                'content': match[:50],
                'suggestion': f'改写AI标志句式: {match[:50]}...'
            })
    
    return issues


class Severity(Enum):
    CRITICAL = 'CRITICAL'   # 致命问题，拒稿级别
    MAJOR = 'MAJOR'         # 重大问题，需要修改
    MINOR = 'MINOR'         # 小问题，润色级
    INFO = 'INFO'           # 提示信息

class PaperType(Enum):
    SCI = 'sci'
    CHINESE_THESIS = 'chinese_thesis'
    CHINESE_JOURNAL = 'chinese_journal'

@dataclass
class Issue:
    """单个检查问题"""
    category: str           # 检查类别
    severity: Severity      # 严重级别
    section: str            # 所在章节
    location: str           # 具体位置描述
    problem: str            # 问题描述
    original: str           # 原文片段
    suggestion: str         # 修改建议
    fix: str = ''           # 自动修复文本
    # 教学导向字段（借鉴PaperSpine）
    root_cause: str = ''    # 根本原因
    fix_action: str = ''    # 修复动作
    downstream_impact: str = ''  # 下游影响
    teaching_note: str = '' # 教学提示

@dataclass
class SectionContent:
    """解析后的章节内容"""
    title: str = ''
    body: str = ''
    paragraphs: list = field(default_factory=list)
    sentences: list = field(default_factory=list)

@dataclass
class ReviewReport:
    """完整审稿报告"""
    issues: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    paper_type: str = ''
    language: str = ''

    def summary(self):
        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        for issue in self.issues:
            by_severity[issue.severity.value] += 1
            by_category[issue.category] += 1
        return {
            'total': len(self.issues),
            'by_severity': dict(by_severity),
            'by_category': dict(by_category),
        }


# ============================================================================
# 知识库：禁用词、规则、模板
# ============================================================================
class ReviewKB:
    """审稿知识库（从knowledge base文件提取的规则）"""

    # 英文禁用词 → 替换建议
    EN_FORBIDDEN = {
        'prove': 'demonstrate / suggest / indicate',
        'very': '删除，用具体数据替代',
        'a lot of': 'substantial / considerable',
        'get': 'obtain / acquire / derive',
        'big': 'significant / substantial / considerable',
        'good': 'favorable / effective / satisfactory',
        'bad': 'poor / unfavorable / inadequate',
        'nice': 'favorable / acceptable',
        'thing': 'factor / aspect / element',
        'stuff': 'material / substance',
        'lots of': 'numerous / considerable',
        'pretty': '相当 → moderately / relatively',
    }

    # 中文禁用词 → 替换建议
    ZH_FORBIDDEN = {
        '很多': '显著 / 大量 / 较高',
        '差不多': '近似 / 约 / 大约',
        '好': '良好 / 优良 / 较好',
        '坏': '较差 / 偏低 / 不足',
        '搞清楚': '阐明 / 揭示 / 探究',
        '用了': '采用 / 运用 / 利用',
        '一般来说': '通常 / 一般而言 / 总体而言',
        '跟': '与...呈显著相关',
        '比较大的': '显著的 / 较大的',
        '比较小的': '较小的 / 微弱的',
        '还行': '尚可 / 较为理想',
        '感觉': '认为 / 推测',
        '看起来': '表明 / 显示',
    }

    # AI痕迹特征词/句式
    AI_PATTERNS_EN = [
        r"It is (?:important|crucial|essential|worth noting) to (?:note|mention|emphasize)",
        r"(?:delve|dive) into",
        r"in the realm of",
        r"it'?s worth noting that",
        r"the (?:multifaceted|nuanced|intricate) (?:nature|interplay|landscape)",
        r"(?:further|more) research (?:is (?:needed|required|warranted))",
        r"plays a (?:crucial|pivotal|vital|key) role",
        r"(?:shed light|cast light) on",
        r"at the (?:forefront|intersection) of",
        r"(?:holistic|comprehensive|robust) (?:approach|framework|understanding)",
        r"in conclusion,? (?:this study|our (?:findings|results|study))",
        r"(?:tapestry|myriad|plethora|cornucopia)",
        r"(?:leveraging|harnessing|utilizing) (?:the|a) (?:power|potential)",
        r"(?:not only).+?(?:but also)",
        r"to (?:the best of|our knowledge)",
    ]

    AI_PATTERNS_ZH = [
        r"值得[注关]意的是",
        r"(?:深入|进[一壹]步)探讨",
        r"(?:扮演|起着)(?:关键|重要|核心)(?:角色|作用)",
        r"(?:揭示|阐明|展现了?).+(?:深刻|重要)(?:认识|理解|洞察)",
        r"(?:这[一壹]|该)(?:发现|结果)(?:具有|具有着?)(?:重要|深远)(?:意义|价值)",
        r"(?:填补|弥补)(?:了?)(?:研究)?空白",
        r"(?:首次|开创性|创新性地)(?:发现|提出|证明)",
        r"(?:尽管|虽然).+(?:但是|然而).+(?:局限|不足)",
        r"综上所述.{0,10}(?:本文|本研究)",
        r"(?:为).+(?:提供.{0,5}(?:理论|科学|数据)(?:支撑|依据|参考))",
        r"(?:具有|有着)(?:重大|深远|重要)(?:理论|实践)(?:意义|价值)",
    ]

    # 空洞表达（无实质内容的学术套话）
    HOLLOW_PATTERNS_ZH = [
        r"(?:为?).+(?:提供.{0,5}(?:参考|借鉴|依据))",
        r"(?:对?).+(?:具有.{0,5}(?:指导|参考)(?:意义|价值))",
        r"(?:研究|分析)(?:了?).+(?:的?.{0,5}(?:规律|特征|特点))",
        r"(?:丰富|完善)(?:了?)(?:相关|该领域的?)(?:理论|研究)",
        r"有待(?:进[一壹]步|深入)(?:研究|探讨|分析)",
    ]

    # ===== 中文核心期刊专项（借鉴 xiuneng0-collab） =====

    # 中文核心必删空话（来自中文核心期刊通用指令）
    CN_CORE_FORBIDDEN_PHRASES = {
        '需要进一步研究': '删除，或写具体后续方向',
        '具有重要意义': '写具体什么意义',
        '提供参考借鉴': '写具体参考什么',
        '状态良好': '给出具体指标',
        '有待完善': '写具体待完善什么',
        '一定程度上': '删除或写具体程度',
        '重要组成部分': '写具体贡献了什么',
        '起到了关键作用': '写具体什么作用',
        '取得了显著成效': '列出具体数据',
        '具有一定的创新性': '写具体创新点',
        '值得深入探讨': '删除，或直接探讨',
        '提供了新思路': '写具体思路',
        '效果明显': '给出具体数据',
        '综上所述': '删除，直接陈述结论',
        '填补了研究空白': '写具体填补了什么',
    }

    # 中文核心推荐用语
    CN_CORE_RECOMMENDED_PHRASES = {
        '数据表明': '代替"说明"或"表明"',
        '实测数据显示': '代替"可以发现"',
        '归档统计显示': '代替"据统计"',
        '可追溯至': '代替"来源于"',
        '据文献报道': '代替"有人研究过"',
    }

    # 中文核心AI痕迹增强检测
    CN_CORE_AI_PATTERNS = [
        r"(?:值得注意|值得关注|需要指出)(?:的?是)",
        r"(?:不仅|不仅仅).+(?:而且|更)(?:是|为|具有)",
        r"(?:总而言之|综上所述|总的来说|简而言之).{0,10}(?:本文|本研究|我们)",
        r"(?:在).+(?:背景下|基础上|条件下).{0,5}(?:开展|进行|实施)",
        r"(?:本文|本研究).{0,5}(?:旨在|目的在于|致力于)",
        r"(?:具有|拥有).{0,5}(?:重要的?|深远的?)(?:理论|实践|现实)(?:意义|价值)",
        r"(?:为).{0,10}(?:奠定了|提供了|创造了).{0,5}(?:基础|条件|可能)",
        r"(?:从).{0,5}(?:角度|层面|维度).{0,5}(?:出发|来看|分析)",
        r"(?:深度|广度|高度)(?:融?合|结合|交织)",
        r"(?:赋能|加持|助力|驱动|引领)",
        # humanizer-zh 补充模式
        r"(?:标志着?|见证了?).{0,10}(?:关键|重要)(?:时刻|转折|里程碑)",
        r"(?:作为|充当).{0,5}(?:一个?)(?:充满活力|丰富|重要)(?:的)",
        r"(?:象征着?|体现了?).{0,10}(?:深厚|深刻)(?:的?联系|的理解)",
        r"(?:为).{0,10}(?:奠定(?:了?)基础|做出(?:了?)重要贡献)",
        r"(?:尽管|虽然).{0,20}(?:面临|挑战).{0,10}(?:尽管|但是|然而).{0,10}(?:继续|仍然)",
        r"(?:此外|与此同时).{0,10}(?:关键(?:的|性)|至关重要|不可或缺)",
        r"(?:不断演变|不断变化)(?:的?格局|的?趋势|的?态势)",
        r"(?:深刻|深入)(?:的?认识|的?理解|的?洞察|探讨)",
        r"(?:不可磨灭)(?:的?印记|的?贡献|的影响)",
        r"(?:深深植根于|根植于)",
        r"(?:令人叹为观止|叹为观止|令人瞩目)(?:的|地)",
        r"(?:生态|闭环|链路|抓手|打法)",
    ]

    # 中文核心工程论文标题规范
    CN_CORE_TITLE_RULES = {
        'max_length': 25,  # 最长25个汉字
        'forbidden_prefixes': ['一种', '基于', '关于'],
        'recommended_format': 'XXX与XXX系统/平台/方法',
        'forbidden_vague': ['重要', '关键', '新型', '高效', '先进'],
    }

    HOLLOW_PATTERNS_EN = [
        r"(?:provides|offers|serves as) (?:a |an )?(?:valuable|useful|important) (?:reference|insight|foundation)",
        r"(?:further|additional|more) (?:research|study|investigation) (?:is |was )?(?:needed|required|warranted|necessary)",
        r"(?:shed[s]? light|cast[s]? light) on",
        r"(?:play[s]?|played) a (?:crucial|pivotal|vital|key|significant) role",
    ]

    # SCI各章节时态要求
    SCI_TENSE_RULES = {
        'abstract_background': 'present',
        'abstract_methods': 'past',
        'abstract_results': 'past',
        'abstract_conclusion': 'present',
        'introduction': 'present',
        'methods': 'past',
        'results': 'past',
        'discussion_own': 'past',
        'discussion_literature': 'present',
        'conclusion': 'present',
    }

    # 常见动词的过去式/现在式映射
    VERB_FORMS = {
        'present': ['shows', 'indicates', 'suggests', 'demonstrates', 'reveals',
                     'is', 'are', 'has', 'have', 'provides', 'plays'],
        'past': ['showed', 'indicated', 'suggested', 'demonstrated', 'revealed',
                 'was', 'were', 'had', 'provided', 'played'],
    }

    # 夸大词汇
    OVERCLAIM_EN = ['prove', 'confirm', 'definitive', 'unprecedented',
                    'groundbreaking', 'revolutionary', 'first ever',
                    'novel discovery', 'breakthrough']
    OVERCLAIM_ZH = ['首次发现', '证实', '确证', '重大突破', '开创性',
                    '革命性', '前所未有', '根本性']

    # ===== Nature 级替代表（来自 nature-polishing skill Phrasebank） =====

    # 证据强度动词分级（替代笼统的 "show/prove"）
    EVIDENCE_VERBS = {
        'strong': ['show', 'demonstrate', 'establish', 'reveal', 'identify'],
        'moderate': ['suggest', 'indicate', 'support the view that',
                     'are consistent with', 'point to'],
        'speculative': ['may reflect', 'could arise from', 'appears to',
                        'seems likely', 'might be explained by'],
    }

    # 差距语言（替代 "no one has ever studied"）
    GAP_LANGUAGE = {
        'good': ['remains poorly understood', 'has not been examined in ...',
                 'has received limited attention', 'few studies have addressed ...',
                 'evidence remains sparse for ...'],
        'avoid': ['no one has ever studied', 'completely unknown',
                  'ignored by all previous work'],
    }

    # 与前人工作的比较表达
    COMPARISON_LANGUAGE = {
        'align': ['These results are consistent with ...',
                  'This finding accords with ...',
                  'Our observations broadly support ...'],
        'diverge': ['In contrast to earlier reports, ...',
                    'This finding differs from ...',
                    'One possible reason for this discrepancy is ...'],
    }

    # 局限性语言（替代空洞的 "有待进一步研究"）
    LIMITATION_LANGUAGE = [
        'These findings should be interpreted with caution because ...',
        'A limitation of this study is that ...',
        'The generalisability of these results is limited by ...',
        'We cannot exclude the possibility that ...',
        'Another source of uncertainty is ...',
    ]

    # 段落间过渡（替代重复的 "This suggests"）
    PARAGRAPH_LINKS = {
        'restatement': 'Such heterogeneity ...',           # 重述名词
        'definite': 'The resulting gradient ...',          # 定指名词短语
        'participial': 'Taken together, ...',              # 分词总结
        'zero': '',                                         # 逻辑明显时不用连接词
    }

    # ===== 结构性失败模式诊断（来自 nature-polishing skill） =====
    STRUCTURAL_FAILURE_MODES = {
        'wrong_paper_type': '论文类型逻辑错误（如综述写成实验论文）',
        'missing_gap': '缺少研究空白或定位不清',
        'claim_without_evidence': '有论断无证据支撑',
        'evidence_without_claim': '有数据无论断统领',
        'missing_boundary': '缺少局限性或边界说明',
        'results_discussion_mixed': '结果与讨论混在一起',
        'weak_title_abstract': '标题或摘要信号弱',
        'terminology_inconsistent': '术语/缩写/单位/符号不一致',
        'sentence_clutter_only': '仅有句法层面的杂乱',
    }

    # 修复优先级顺序
    FIX_PRIORITY = [
        'paper_type', 'section_job', 'paragraph_logic',
        'claim_evidence_boundary', 'sentence_polish'
    ]


# ============================================================================
# 章节解析器
# ============================================================================
class SectionParser:
    """将论文解析为独立章节"""

    # 中文章节标题模式
    ZH_SECTION_PATTERNS = {
        'title': r'^(?!#)(?!\d+\.)(.{5,80})$',
        'abstract': r'(?:摘\s*要|摘要)',
        'keywords': r'(?:关键词|关键字)',
        'introduction': r'(?:1\s*[\.\、]\s*(?:引言|绪论|前言)|引言|绪论|前言)',
        'methods': r'(?:2\s*[\.\、]\s*(?:材料.*方法|研究方法|实验方法|方法)|材料.*方法|研究方法|实验方法)',
        'results': r'(?:3\s*[\.\、]\s*(?:结果|结果与分析|结果.*讨论|结果与讨论)|结果.*分析|结果与讨论)',
        'discussion': r'(?:4\s*[\.\、]\s*(?:讨论|讨论与分析)|讨论)',
        'conclusion': r'(?:5\s*[\.\、]\s*(?:结论|总结)|结论|总结)',
        'references': r'(?:参考文献|References)',
        'acknowledgments': r'(?:致谢|Acknowledgments?)',
    }

    # 英文章节标题模式
    EN_SECTION_PATTERNS = {
        'title': r'^(?!#)(.{10,120})$',
        'abstract': r'(?i)^(?:abstract|summary)\s*$',
        'keywords': r'(?i)^keywords?\s*[:\.]',
        'introduction': r'(?i)^(?:\d+[\.\)]\s*)?introduction\s*$',
        'methods': r'(?i)^(?:\d+[\.\)]\s*)?(?:materials?\s*(?:and|&)\s*methods?|methodology|experimental\s*(?:section|procedures?))\s*$',
        'results': r'(?i)^(?:\d+[\.\)]\s*)?results?\s*(?:(?:and|&)\s*(?:discussion|analysis))?\s*$',
        'discussion': r'(?i)^(?:\d+[\.\)]\s*)?discussion\s*$',
        'conclusion': r'(?i)^(?:\d+[\.\)]\s*)?(?:conclusions?|summary|concluding\s*remarks?)\s*$',
        'references': r'(?i)^(?:references|bibliography|literature\s*cited)\s*$',
        'acknowledgments': r'(?i)^(?:acknowledgments?|funding)\s*$',
    }

    @classmethod
    def detect_language(cls, text):
        """检测论文语言"""
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        total_alpha = len(re.findall(r'[a-zA-Z]', text))
        if chinese_chars > total_alpha * 0.3:
            return 'zh'
        return 'en'

    @classmethod
    def parse(cls, text, language=None):
        """
        解析论文为章节字典

        Returns
        -------
        dict: {section_name: SectionContent}
        """
        if language is None:
            language = cls.detect_language(text)

        patterns = cls.ZH_SECTION_PATTERNS if language == 'zh' else cls.EN_SECTION_PATTERNS

        # 按行扫描，识别章节标题
        lines = text.split('\n')
        sections = {}
        current_section = 'preamble'
        current_lines = []

        for line in lines:
            stripped = line.strip()
            matched_section = None

            for sec_name, pattern in patterns.items():
                if sec_name == 'title':
                    continue
                if re.search(pattern, stripped):
                    matched_section = sec_name
                    break

            if matched_section:
                # 保存之前的章节
                if current_lines:
                    sections[current_section] = cls._build_section(current_lines)
                current_section = matched_section
                current_lines = [stripped]
            else:
                current_lines.append(line)

        # 保存最后一个章节
        if current_lines:
            sections[current_section] = cls._build_section(current_lines)

        return sections

    @classmethod
    def _build_section(cls, lines):
        """构建SectionContent"""
        title = lines[0].strip() if lines else ''
        body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
        sentences = []
        for para in paragraphs:
            # 中文按句号分割，英文按句号+空格分割
            if re.search(r'[一-鿿]', para):
                sents = re.split(r'[。！？；]', para)
            else:
                sents = re.split(r'(?<=[.!?])\s+', para)
            sentences.extend([s.strip() for s in sents if s.strip() and len(s.strip()) > 5])

        return SectionContent(title=title, body=body, paragraphs=paragraphs, sentences=sentences)


# ============================================================================
# 10类检查器
# ============================================================================

# ---------- 1. SCI格式检查 ----------
class SCIChecker:
    """SCI论文格式检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        kb = ReviewKB

        # 标题检查
        if 'preamble' in sections:
            preamble = sections['preamble'].body
            first_line = preamble.split('\n')[0].strip() if preamble else ''

            # 缩写检查
            abbrevs = re.findall(r'\b(?:TOC|COD|BOD|DO|TN|TP|CH4|CO2|NH4|NO3|PCA|HCA)\b', first_line)
            if abbrevs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='标题', location='标题行',
                    problem=f'标题中使用了未展开的缩写: {", ".join(abbrevs)}',
                    original=first_line,
                    suggestion='标题中所有缩写应展开为全称，如 TOC → total organic carbon'
                ))

            # 字数检查
            words = first_line.split()
            if language == 'en' and len(words) > 20:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MINOR,
                    section='标题', location='标题行',
                    problem=f'标题过长({len(words)}词)，建议控制在15词以内',
                    original=first_line,
                    suggestion='精简标题，保留核心要素：[方法] of [对象] in [范围]'
                ))

        # 摘要检查
        if 'abstract' in sections:
            abstract = sections['abstract'].body
            # 引用检查
            refs = re.findall(r'\[\d+\]', abstract)
            if refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.CRITICAL,
                    section='摘要', location='摘要正文',
                    problem=f'摘要中包含参考文献引用 {refs}',
                    original=refs[0],
                    suggestion='摘要中不允许出现参考文献编号，删除所有[N]引用'
                ))

            # 图表引用检查
            fig_refs = re.findall(r'(?:Fig\.?\s*\d|Table\s*\d|图\s*\d|表\s*\d)', abstract)
            if fig_refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.CRITICAL,
                    section='摘要', location='摘要正文',
                    problem=f'摘要中包含图表引用: {fig_refs}',
                    original=fig_refs[0],
                    suggestion='摘要中不应引用图表，直接描述数据结果'
                ))

            # 定量数据检查
            has_numbers = bool(re.search(r'\d+\.?\d*\s*(?:mg|ppm|%|mg/L|±|p\s*[<=])', abstract))
            if not has_numbers and len(abstract) > 100:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='摘要', location='结果部分',
                    problem='摘要中缺少定量数据（数值、统计量）',
                    original=abstract[:100] + '...',
                    suggestion='摘要结果部分应包含关键定量数据，如浓度值、p值、R²等'
                ))

        # 结论检查
        if 'conclusion' in sections:
            conclusion = sections['conclusion'].body

            # 参考文献
            refs = re.findall(r'\[\d+\]', conclusion)
            if refs:
                issues.append(Issue(
                    category='SCI格式', severity=Severity.MAJOR,
                    section='结论', location='结论正文',
                    problem='结论中包含参考文献引用',
                    original=refs[0] if refs else '',
                    suggestion='结论中不应引用参考文献'
                ))

            # 夸大词汇
            for word in kb.OVERCLAIM_EN if language == 'en' else kb.OVERCLAIM_ZH:
                if word.lower() in conclusion.lower():
                    issues.append(Issue(
                        category='SCI格式', severity=Severity.MAJOR,
                        section='结论', location='结论正文',
                        problem=f'结论中使用了夸大词汇: "{word}"',
                        original=word,
                        suggestion=f'替换为更谨慎的表述，如 suggest / indicate / demonstrate'
                    ))

        return issues


# ---------- 2. 中文论文格式检查 ----------
class ChineseChecker:
    """中文论文格式检查"""

    @staticmethod
    def check(sections, language='zh'):
        if language != 'zh':
            return []
        issues = []

        # 摘要检查
        if 'abstract' in sections:
            abstract = sections['abstract'].body
            # "本文"检查
            if '本文' in abstract or '本论文' in abstract:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MINOR,
                    section='摘要', location='摘要正文',
                    problem='摘要中使用了"本文/本论文"',
                    original='本文',
                    suggestion='摘要中删除"本文"，直接陈述研究内容'
                ))

        # 引言检查
        if 'introduction' in sections:
            intro = sections['introduction'].body
            if len(intro) < 500:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MAJOR,
                    section='引言', location='引言全文',
                    problem=f'引言过短({len(intro)}字)，建议≥800字',
                    original=intro[:50] + '...',
                    suggestion='补充背景文献、研究现状和研究空白的论述'
                ))

            # 检查是否有"然而"等转折词标识研究空白
            gap_markers = ['然而', '但是', '但', '尽管', '目前']
            has_gap = any(m in intro for m in gap_markers)
            if not has_gap:
                issues.append(Issue(
                    category='中文格式', severity=Severity.MAJOR,
                    section='引言', location='引言中段',
                    problem='引言中缺少转折词（然而/但是/尽管），可能未明确指出研究空白',
                    original='',
                    suggestion='在引言中段用"然而"等转折词引出现有研究的不足'
                ))

        # GB/T 7714参考文献格式检查
        if 'references' in sections:
            ref_text = sections['references'].body
            refs = re.split(r'\n\s*\[\d+\]', ref_text)
            for i, ref in enumerate(refs[:5]):  # 检查前5条
                if not ref.strip():
                    continue
                # 检查期刊论文格式 [J]
                if '[J]' in ref:
                    # 检查是否有卷(期):页码格式
                    if not re.search(r'\d+\(\d+\):\s*\d+', ref):
                        issues.append(Issue(
                            category='中文格式', severity=Severity.MINOR,
                            section='参考文献', location=f'第{i+1}条',
                            problem='参考文献格式不完整，缺少"卷(期):起止页码"',
                            original=ref[:80] + '...',
                            suggestion='GB/T 7714格式: 作者. 题名[J]. 刊名, 年, 卷(期): 页码.'
                        ))

        # 标点规范检查
        for sec_name, sec in sections.items():
            body = sec.body
            # 中文文字段落中使用英文逗号
            cn_text_blocks = re.findall(r'[一-鿿，。；：]{10,}', body)
            for block in cn_text_blocks[:3]:
                if ',' in block and '，' not in block:
                    issues.append(Issue(
                        category='中文格式', severity=Severity.MINOR,
                        section=sec_name, location='正文',
                        problem='中文文段中使用了英文逗号',
                        original=block[:50],
                        suggestion='中文文段应使用全角逗号"，"'
                    ))
                    break

        return issues

    @staticmethod
    def check_cn_core_rules(sections, language='zh'):
        """
        中文核心期刊专项检查（借鉴 xiuneng0-collab）

        检查项:
          1. 禁用空话
          2. AI痕迹短语
          3. 标题规范
          4. 推荐用语替换
        """
        if language != 'zh':
            return []
        issues = []

        # 1. 禁用空话检测
        for sec_name, sec in sections.items():
            for phrase, suggestion in ReviewKB.CN_CORE_FORBIDDEN_PHRASES.items():
                if phrase in sec.body:
                    # 找到出现位置的上下文
                    idx = sec.body.find(phrase)
                    context = sec.body[max(0,idx-20):idx+len(phrase)+20]
                    issues.append(Issue(
                        category='中文核心-禁用空话', severity=Severity.MAJOR,
                        section=sec_name, location=f'发现"{phrase}"',
                        problem=f'中文核心期刊禁用空话: "{phrase}"',
                        original=context,
                        suggestion=f'替换为: {suggestion}',
                        teaching_note='中文核心要求表述具体，禁用套话和空洞表达'
                    ))

        # 2. AI痕迹短语检测
        for sec_name, sec in sections.items():
            for pattern in ReviewKB.CN_CORE_AI_PATTERNS:
                matches = re.findall(pattern, sec.body)
                if matches:
                    issues.append(Issue(
                        category='中文核心-AI痕迹', severity=Severity.MAJOR,
                        section=sec_name, location='正文',
                        problem=f'疑似AI生成短语: "{matches[0][:20]}"',
                        original=matches[0][:60],
                        suggestion='改写为更自然的学术表达，避免AI典型句式',
                        teaching_note='中文核心编辑对AI痕迹非常敏感，需彻底去除'
                    ))

        # 3. 标题检查
        if 'title' in sections:
            title = sections['title'].body.strip()
            rules = ReviewKB.CN_CORE_TITLE_RULES
            if len(title) > rules['max_length']:
                issues.append(Issue(
                    category='中文核心-标题规范', severity=Severity.MINOR,
                    section='标题', location='标题',
                    problem=f'标题过长({len(title)}字)，建议≤{rules["max_length"]}字',
                    original=title,
                    suggestion='精简标题，删除冗余修饰词'
                ))
            for prefix in rules['forbidden_prefixes']:
                if title.startswith(prefix):
                    issues.append(Issue(
                        category='中文核心-标题规范', severity=Severity.MINOR,
                        section='标题', location='标题开头',
                        problem=f'标题以"{prefix}"开头，中文核心建议避免',
                        original=title,
                        suggestion=f'去掉"{prefix}"前缀，直接用核心名词开头'
                    ))
            for word in rules['forbidden_vague']:
                if word in title:
                    issues.append(Issue(
                        category='中文核心-标题规范', severity=Severity.MINOR,
                        section='标题', location='标题',
                        problem=f'标题含模糊修饰词"{word}"',
                        original=title,
                        suggestion=f'去掉"{word}"或替换为具体描述'
                    ))

        return issues


# ---------- 3. 错别字检查 ----------
class TypoChecker:
    """错别字和拼写检查"""

    # 常见学术错别字
    ZH_TYPOS = {
        '分折': '分析', '研完': '研究', '现像': '现象',
        '原素': '元素', '幅射': '辐射', '融恰': '融洽',
        '气侯': '气候', '碳源': '碳源', '水份': '水分',
        '反映': '反应', '包函': '包含', '具全': '具体',
        '关连': '关联', '沿续': '延续', '消毁': '销毁',
    }

    EN_TYPOS = {
        'teh': 'the', 'recieve': 'receive', 'occurence': 'occurrence',
        'seperate': 'separate', 'definately': 'definitely',
        'occured': 'occurred', 'comparision': 'comparison',
        'analisis': 'analysis', 'paramaters': 'parameters',
        'significient': 'significant', 'concentrationn': 'concentration',
        'dissloved': 'dissolved', 'enviroment': 'environment',
        'polluant': 'pollutant', 'speciment': 'specimen',
    }

    @staticmethod
    def check(sections, language='en'):
        issues = []
        typos = TypoChecker.ZH_TYPOS if language == 'zh' else TypoChecker.EN_TYPOS

        for sec_name, sec in sections.items():
            body = sec.body
            for wrong, correct in typos.items():
                matches = [(m.start(), m.group()) for m in re.finditer(re.escape(wrong), body, re.IGNORECASE)]
                for pos, match in matches[:2]:  # 每个词最多报2次
                    context = body[max(0, pos-20):pos+20]
                    issues.append(Issue(
                        category='错别字', severity=Severity.MINOR,
                        section=sec_name, location=f'位置{pos}',
                        problem=f'疑似错别字/拼写错误: "{match}"',
                        original=context,
                        suggestion=f'修正为: "{correct}"',
                        fix=correct,
                    ))

        return issues


# ---------- 4. 学术语法检查 ----------
class ForbiddenWordChecker:
    """学术禁用词检查（禁用词+口语化）"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        forbidden = ReviewKB.EN_FORBIDDEN if language == 'en' else ReviewKB.ZH_FORBIDDEN

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments'):
                continue
            body = sec.body
            for word, suggestion in forbidden.items():
                if language == 'zh':
                    pattern = re.escape(word)
                else:
                    pattern = r'\b' + re.escape(word) + r'\b'
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:2]:
                    context = body[max(0, m.start()-15):m.end()+15]
                    issues.append(Issue(
                        category='学术语法', severity=Severity.MINOR,
                        section=sec_name, location=f'禁用词',
                        problem=f'非学术用语: "{word}"',
                        original=context,
                        suggestion=f'替换为: {suggestion}',
                    ))

        return issues


# ---------- 5. 引文规范检查 ----------
class CitationChecker:
    """引文规范检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 统计正文中引用次数
        all_text = ' '.join(sec.body for sec in sections.values() if sec.body)

        # 数字编号格式: [1], [1-3], [1,2,3]
        numeric_citations = re.findall(r'\[(\d+(?:[-,]\d+)*)\]', all_text)
        unique_numeric_refs = set()
        for c in numeric_citations:
            for part in re.split(r'[,]', c):
                if '-' in part:
                    start, end = part.split('-')
                    for i in range(int(start), int(end)+1):
                        unique_numeric_refs.add(i)
                else:
                    unique_numeric_refs.add(int(part))

        # 作者-年份格式: (Author et al., Year), (Author and Author, Year), Author等（Year）
        author_year_pattern = r'\(([A-Z][a-z]+(?:\s+(?:et\s+al|and|[A-Z][a-z]+))*(?:\s+等)?,?\s*\d{4}(?:\s*;\s*[A-Z][a-z]+(?:\s+(?:et\s+al|and|[A-Z][a-z]+))*(?:\s+等)?,?\s*\d{4})*)\)'
        author_year_citations = re.findall(author_year_pattern, all_text)

        # 也匹配中文格式: Author等（Year）
        cn_author_pattern = r'[A-Z][a-z]+等（\d{4}）'
        cn_author_citations = re.findall(cn_author_pattern, all_text)

        # 提取唯一的作者-年份引用
        unique_author_refs = set()
        for c in author_year_citations:
            # 分割多个引用
            refs = re.split(r';\s*', c)
            for ref in refs:
                ref = ref.strip()
                if ref:
                    unique_author_refs.add(ref)

        # 总引用数
        total_refs = len(unique_numeric_refs) + len(unique_author_refs) + len(cn_author_citations)

        # 引用数量检查
        if total_refs < 15:
            issues.append(Issue(
                category='引文规范', severity=Severity.MAJOR if total_refs < 10 else Severity.MINOR,
                section='全文', location='参考文献',
                problem=f'参考文献数量偏少({total_refs}篇)，SCI论文通常需要25-50篇',
                original=f'共引用{total_refs}篇文献（数字编号{len(unique_numeric_refs)}篇，作者-年份{len(unique_author_refs)+len(cn_author_citations)}篇）',
                suggestion='补充领域内近5年的重要文献'
            ))

        # 引用分布检查
        for sec_name in ['introduction', 'discussion']:
            if sec_name in sections:
                sec_text = sections[sec_name].body
                # 数字编号引用
                sec_numeric_refs = re.findall(r'\[\d+\]', sec_text)
                # 作者-年份引用
                sec_author_refs = re.findall(author_year_pattern, sec_text)
                sec_cn_refs = re.findall(cn_author_pattern, sec_text)
                total_sec_refs = len(sec_numeric_refs) + len(sec_author_refs) + len(sec_cn_refs)

                if total_sec_refs < 3:
                    issues.append(Issue(
                        category='引文规范', severity=Severity.MAJOR,
                        section=sec_name, location='正文',
                        problem=f'{sec_name}章节引用不足({total_sec_refs}处)',
                        original='',
                        suggestion=f'{sec_name}应充分引用文献支撑论述'
                    ))

        return issues


# ---------- 6. 图表规范检查 ----------
class FigureChecker:
    """图表规范检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        all_text = ' '.join(sec.body for sec in sections.values() if sec.body)

        # 图表引用格式检查
        if language == 'en':
            bad_refs = re.findall(r'as (?:shown|illustrated|depicted) in (?:Fig|Figure)\.?\s*\d', all_text, re.IGNORECASE)
            for ref in bad_refs[:3]:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='Results', location='图表引用',
                    problem=f'图表引用格式不规范: "{ref}"',
                    original=ref,
                    suggestion='使用括号引用: (Fig. X) 而非 "as shown in Fig. X"'
                ))
        else:
            bad_refs = re.findall(r'如图\d', all_text)
            for ref in bad_refs[:3]:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='结果', location='图表引用',
                    problem=f'图表引用格式不规范: "{ref}"',
                    original=ref,
                    suggestion='使用括号引用: (图X) 而非 "如图X所示"'
                ))

        # Results中是否引用了图表
        if 'results' in sections:
            results_text = sections['results'].body
            fig_refs = re.findall(r'(?:Fig|Figure|图)\.?\s*\d', results_text, re.IGNORECASE)
            if len(fig_refs) < 2:
                issues.append(Issue(
                    category='图表规范', severity=Severity.MAJOR,
                    section='Results', location='结果正文',
                    problem='结果部分图表引用过少，数据应与图表对应',
                    original='',
                    suggestion='在Results中逐一引用图表，如 "The TOC concentrations varied... (Fig. 1)"'
                ))

        # 坐标轴单位检查（从图注推断）
        caption_pattern = r'(?:Fig\.?\s*\d|图\s*\d)[^\n]+'
        captions = re.findall(caption_pattern, all_text, re.IGNORECASE)
        for cap in captions[:5]:
            if not re.search(r'\(.+\)', cap) and not re.search(r'（.+）', cap):
                issues.append(Issue(
                    category='图表规范', severity=Severity.MINOR,
                    section='图表', location='图注',
                    problem='图注可能缺少单位信息',
                    original=cap,
                    suggestion='图注应包含统计方法和单位，如 "(Mean±SD, n=15)"'
                ))

        return issues


# ---------- 7. 数据逻辑检查 ----------
class DataLogicChecker:
    """数据逻辑一致性检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 检查Results中的p值是否合理
        if 'results' in sections:
            results = sections['results'].body
            p_values = re.findall(r'p\s*[=<>≤≥]\s*0\.?\d*', results, re.IGNORECASE)

            for pv in p_values[:5]:
                num_match = re.search(r'0\.?\d*', pv)
                if num_match:
                    val = float(num_match.group())
                    if val > 0.05 and 'significant' in results.lower():
                        # 检查上下文
                        idx = results.find(pv)
                        context = results[max(0, idx-50):idx+50]
                        if 'significant' in context.lower():
                            issues.append(Issue(
                                category='数据逻辑', severity=Severity.CRITICAL,
                                section='Results', location='统计检验',
                                problem=f'数据矛盾: p={val} ≥ 0.05 但描述为 "significant"',
                                original=context,
                                suggestion='p ≥ 0.05 时应使用 "not significant" 或 "no significant difference"'
                            ))

            # 检查百分比加总
            pcts = re.findall(r'(\d+\.?\d*)\s*%', results)
            if len(pcts) >= 3:
                try:
                    pct_vals = [float(p) for p in pcts[:10]]
                    total = sum(pct_vals)
                    if 95 < total < 105 and len(pct_vals) >= 3:
                        # 这可能是分类百分比，需要加总100
                        pass  # 只提示不报错
                except ValueError:
                    pass

        # 检查Results和Discussion的数据一致性
        if 'results' in sections and 'discussion' in sections:
            results_nums = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%)', sections['results'].body))
            discussion_nums = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%)', sections['discussion'].body))
            # Discussion中引用的结果数据应在Results中出现
            unique_in_disc = discussion_nums - results_nums
            for num in list(unique_in_disc)[:3]:
                issues.append(Issue(
                    category='数据逻辑', severity=Severity.MINOR,
                    section='Discussion', location='数据引用',
                    problem=f'Discussion中的数据 "{num}" 在Results中未找到',
                    original=num,
                    suggestion='确保Discussion引用的数据与Results一致'
                ))

        return issues


# ---------- 8. Discussion逻辑检查 ----------
class DiscussionChecker:
    """Discussion逻辑质量检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        if 'discussion' not in sections:
            return issues

        disc = sections['discussion'].body
        paragraphs = sections['discussion'].paragraphs

        # 检查是否只是复述结果
        if 'results' in sections:
            results = sections['results'].body
            # 提取Results中的数据句式
            result_patterns = re.findall(r'(?:was|were|ranged from|mean|average|±)\s', results, re.IGNORECASE)
            disc_patterns = re.findall(r'(?:was|were|ranged from|mean|average|±)\s', disc, re.IGNORECASE)

            if len(disc_patterns) > len(disc.split()) * 0.05:  # Discussion中描述性语句过多
                issues.append(Issue(
                    category='Discussion逻辑', severity=Severity.MAJOR,
                    section='Discussion', location='整体',
                    problem='Discussion可能只是复述了Results，缺少机制解释',
                    original='',
                    suggestion='Discussion应解释"为什么"而不仅是"是什么"。每个发现应有：\n'
                               '1. 发现描述（简短）\n2. 机制解释（为什么）\n3. 文献对比（与谁一致/不同）'
                ))

        # 检查是否有机制解释
        mechanism_keywords_en = [
            'because', 'due to', 'attributed to', 'resulted from',
            'mechanism', 'pathway', 'process', 'metabolism',
            'anaerobic', 'aerobic', 'microbial', 'degradation',
        ]
        mechanism_keywords_zh = [
            '因为', '由于', '归因于', '源于', '机制', '途径',
            '过程', '代谢', '厌氧', '好氧', '微生物', '降解',
        ]
        keywords = mechanism_keywords_zh if language == 'zh' else mechanism_keywords_en

        mech_count = sum(1 for k in keywords if k.lower() in disc.lower())
        if mech_count < 3:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.CRITICAL,
                section='Discussion', location='全文',
                problem=f'Discussion缺少机制解释（仅检测到{mech_count}个机制关键词）',
                original='',
                suggestion='每个发现都需要机制解释：\n'
                           '- 从微生物/化学/物理过程角度解释原因\n'
                           '- 引用支持该机制的文献\n'
                           '- 例如："CH4浓度升高可归因于厌氧条件下产甲烷菌活性增强"'
            ))

        # 检查是否有文献对比
        lit_compare = re.findall(r'(?:consistent with|similar to|in agreement|in line with|'
                                  r'与.*一致|与.*类似|与.*相符|'
                                  r'differed from|contrary to|unlike|'
                                  r'与.*不同|不同于)', disc, re.IGNORECASE)
        if len(lit_compare) < 2:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.MAJOR,
                section='Discussion', location='文献对比',
                problem='Discussion缺少与文献的对比讨论',
                original='',
                suggestion='至少每个主要发现应与1-2篇文献对比：\n'
                           '- "与XX等[ref]的研究一致，本研究发现..."\n'
                           '- "不同于XX等[ref]的报道，本研究中..."'
            ))

        # 检查是否有局限性讨论
        limitation_keywords = ['limit', 'caveat', 'shortcoming', 'drawback',
                               '局限', '不足', '限制', '有待']
        has_limitations = any(k.lower() in disc.lower() for k in limitation_keywords)
        if not has_limitations:
            issues.append(Issue(
                category='Discussion逻辑', severity=Severity.MINOR,
                section='Discussion', location='文末',
                problem='Discussion缺少研究局限性讨论',
                original='',
                suggestion='在Discussion末尾添加1段局限性：\n'
                           '"本研究存在以下局限：(1) 采样时间有限；(2) ..."'
            ))

        return issues


# ---------- 9. AI痕迹检查 ----------
class AIDetector:
    """AI生成文本痕迹检查（增强版）"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        patterns = ReviewKB.AI_PATTERNS_EN if language == 'en' else ReviewKB.AI_PATTERNS_ZH
        hollow = ReviewKB.HOLLOW_PATTERNS_EN if language == 'en' else ReviewKB.HOLLOW_PATTERNS_ZH

        # 合并全文用于增强检测
        full_text = '\n\n'.join(sec.body for sec in sections.values() if hasattr(sec, 'body'))

        # 统计每个类别的问题数量，避免重复报告
        category_counts = {}
        max_per_category = 5  # 每个类别最多报告5个问题

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments', 'preamble'):
                continue
            body = sec.body

            # AI套话模式匹配（限制每个章节最多2个）
            ai_pattern_count = 0
            for pattern in patterns:
                if ai_pattern_count >= 2:
                    break
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:1]:  # 每个模式只报告1个
                    if ai_pattern_count >= 2:
                        break
                    context = body[max(0, m.start()-10):m.end()+10]
                    issues.append(Issue(
                        category='AI痕迹', severity=Severity.MAJOR,
                        section=sec_name, location='疑似AI句式',
                        problem=f'检测到AI常用句式',
                        original=context.strip(),
                        suggestion='替换为更自然的学术表达，避免模板化套话'
                    ))
                    ai_pattern_count += 1

            # 空洞表达检查（限制每个章节最多1个）
            hollow_count = 0
            for pattern in hollow:
                if hollow_count >= 1:
                    break
                matches = list(re.finditer(pattern, body, re.IGNORECASE))
                for m in matches[:1]:
                    if hollow_count >= 1:
                        break
                    context = body[max(0, m.start()-10):m.end()+10]
                    issues.append(Issue(
                        category='AI痕迹', severity=Severity.MINOR,
                        section=sec_name, location='空洞表达',
                        problem='空洞学术套话，缺乏实质内容',
                        original=context.strip(),
                        suggestion='删除或替换为有具体数据支撑的表述'
                    ))
                    hollow_count += 1

        # ========== 增强检测：四大AI特征 ==========
        try:
            from ai_trace_enhanced import detect_ai_trace
            trace_report = detect_ai_trace(full_text)

            # 将增强检测结果转换为 Issue 格式（限制每个特征最多3个问题）
            level_map = {
                'CRITICAL': Severity.CRITICAL,
                'MAJOR': Severity.MAJOR,
                'MINOR': Severity.MINOR,
                'INFO': Severity.INFO,
            }

            feature_counts = {}
            for trace_issue in trace_report.issues:
                feature = trace_issue.feature
                if feature_counts.get(feature, 0) >= 3:
                    continue  # 每个特征最多3个问题

                issues.append(Issue(
                    category=f'AI痕迹-{feature}',
                    severity=level_map.get(trace_issue.level.value, Severity.MINOR),
                    section='全文',
                    location=trace_issue.location,
                    problem=trace_issue.problem,
                    original=trace_issue.original,
                    suggestion=trace_issue.suggestion,
                    fix=trace_issue.auto_fix,
                ))
                feature_counts[feature] = feature_counts.get(feature, 0) + 1

            # 记录评分
            if trace_report.scores:
                logger.info(f"AI痕迹评分: {trace_report.scores}")

        except ImportError:
            logger.debug("ai_trace_enhanced 模块未安装，跳过增强检测")
        except Exception as e:
            logger.debug(f"AI痕迹增强检测失败: {e}")

        # 检查全文句式重复度（限制最多3个）
        all_sentences = []
        for sec in sections.values():
            all_sentences.extend(sec.sentences)

        if len(all_sentences) > 10:
            # 检查句式开头重复
            starts = [s[:15] for s in all_sentences if len(s) > 15]
            from collections import Counter
            start_counts = Counter(starts)
            repeated = [(k, v) for k, v in start_counts.items() if v >= 3]
            for pattern, count in repeated[:3]:
                issues.append(Issue(
                    category='AI痕迹', severity=Severity.MINOR,
                    section='全文', location='句式重复',
                    problem=f'句式开头重复{count}次: "{pattern}..."',
                    original=pattern,
                    suggestion='变换句式开头，避免单调重复。交替使用：\n'
                               '- 主动句/被动句\n'
                               '- 长句/短句\n'
                               '- 数据开头/方法开头/结论开头'
                ))

        return issues


# ---------- 10. 学术重复表达检查 ----------
class RepetitionChecker:
    """学术重复表达检查"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        # 检查Abstract与Conclusion重复
        if 'abstract' in sections and 'conclusion' in sections:
            abstract = sections['abstract'].body
            conclusion = sections['conclusion'].body

            # 提取数字和关键词
            abs_nums = set(re.findall(r'\d+\.?\d*', abstract))
            con_nums = set(re.findall(r'\d+\.?\d*', conclusion))

            if abs_nums and con_nums:
                overlap = abs_nums & con_nums
                if len(overlap) > 3 and len(abs_nums) > 3:
                    overlap_ratio = len(overlap) / min(len(abs_nums), len(con_nums))
                    if overlap_ratio > 0.7:
                        issues.append(Issue(
                            category='学术重复', severity=Severity.MAJOR,
                            section='结论', location='全文',
                            problem=f'结论与摘要高度重复（数据重叠率{overlap_ratio:.0%}）',
                            original='',
                            suggestion='结论应比摘要更精炼，侧重研究贡献而非重复数据'
                        ))

        # 检查章节内部重复段落
        for sec_name, sec in sections.items():
            if len(sec.paragraphs) < 3:
                continue
            for i in range(len(sec.paragraphs)):
                for j in range(i+1, len(sec.paragraphs)):
                    p1_words = set(sec.paragraphs[i].split())
                    p2_words = set(sec.paragraphs[j].split())
                    if len(p1_words) > 10 and len(p2_words) > 10:
                        similarity = len(p1_words & p2_words) / min(len(p1_words), len(p2_words))
                        if similarity > 0.6:
                            issues.append(Issue(
                                category='学术重复', severity=Severity.MINOR,
                                section=sec_name, location=f'第{i+1}段与第{j+1}段',
                                problem=f'段落间内容重复度高({similarity:.0%})',
                                original=sec.paragraphs[i][:60] + '...',
                                suggestion='合并或删除重复段落，确保每段有独特的贡献'
                            ))

        # 检查高频词（学术八股）
        if language == 'zh':
            overused = ['研究表明', '结果显示', '分析发现', '可以发现']
        else:
            overused = ['the results showed', 'it was found that', 'the analysis revealed',
                        'as shown in', 'it can be seen that']

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments', 'preamble'):
                continue
            body = sec.body.lower() if language == 'en' else sec.body
            for phrase in overused:
                count = body.count(phrase.lower() if language == 'en' else phrase)
                if count >= 4:
                    issues.append(Issue(
                        category='学术重复', severity=Severity.MINOR,
                        section=sec_name, location='高频表达',
                        problem=f'表达重复: "{phrase}" 出现{count}次',
                        original=phrase,
                        suggestion='交替使用同义表达：\n'
                                   + '\n'.join(f'  - {p}' for p in overused if p != phrase)
                    ))

        return issues


class RationaleChecker:
    """推理链完整性检查 - 验证每个主张是否有支撑"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        for sec_name in ['discussion', 'introduction', 'results']:
            if sec_name not in sections:
                continue
            sec = sections[sec_name]
            for i, para in enumerate(sec.paragraphs):
                if len(para) < 30:
                    continue

                # 检查是否有主张但无支撑
                has_claim = any(kw in para.lower() for kw in
                    ['表明', '显示', '揭示', '发现', 'suggest', 'indicate', 'reveal', 'demonstrate', 'show that'])
                has_evidence = any(kw in para.lower() for kw in
                    ['r=', 'p<', 'p=', '显著', 'significant', 'significant', 'correlation', '相关'])
                has_citation = bool(re.search(r'\([A-Z][a-z]+\s+et\s+al\.|[\d{4}]\)|\[\d+\]', para))
                has_mechanism = any(kw in para.lower() for kw in
                    ['因为', '由于', '机制', '原因', 'because', 'mechanism', 'due to', 'attribute', '导致', '导致'])

                if has_claim and not has_evidence and not has_citation:
                    issues.append(Issue(
                        category='推理链完整性', severity=Severity.MAJOR,
                        section=sec_name, location=f'第{i+1}段',
                        problem='有主张但缺少数据证据或文献引用',
                        original=para[:80] + '...',
                        suggestion='为每个主张添加数据支撑（统计结果）或文献引用',
                        root_cause='段落只提出了结论，没有提供支撑依据',
                        fix_action='在主张句后添加: (1)统计证据如r=X, p<Y; (2)文献引用如(作者, 年份)',
                        downstream_impact='读者无法判断结论的可信度',
                        teaching_note='学术写作的核心原则: 每个主张都需要有据可查。'
                                      '好的模式是: 主张 + 数据证据 + 机制解释 + 文献对比。',
                    ))

                if has_claim and has_evidence and not has_mechanism and sec_name == 'discussion':
                    issues.append(Issue(
                        category='推理链完整性', severity=Severity.MINOR,
                        section=sec_name, location=f'第{i+1}段',
                        problem='有数据证据但缺少机制解释',
                        original=para[:80] + '...',
                        suggestion='在数据支撑后添加机制解释（为什么会出现这种结果）',
                        root_cause='Discussion段落只罗列了发现，没有解释原因',
                        fix_action='添加机制解释句，如"这一现象的可能机制是..."',
                        downstream_impact='Discussion沦为Results的重复，缺乏深度',
                        teaching_note='Discussion ≠ Results的重复。Discussion要回答"为什么"和"意味着什么"。',
                    ))

        return issues


class LogicalLeapChecker:
    """逻辑跳跃密度检查 - 借鉴PaperSpine的integrity_audit"""

    @staticmethod
    def check(sections, language='en'):
        issues = []

        if language == 'zh':
            connectors = ['因此', '所以', '由此可见', '综上', '这说明', '这表明']
        else:
            connectors = ['therefore', 'thus', 'hence', 'consequently', 'it follows that',
                         'this suggests', 'this indicates', 'accordingly']

        for sec_name in ['discussion', 'introduction']:
            if sec_name not in sections:
                continue
            sec = sections[sec_name]
            for i, para in enumerate(sec.paragraphs):
                if len(para) < 50:
                    continue

                connector_count = sum(
                    para.lower().count(c.lower()) for c in connectors
                )
                sentences = re.split(r'[。！？.!?]', para)
                sentence_count = max(1, len([s for s in sentences if len(s.strip()) > 5]))
                density = connector_count / sentence_count

                if density > 1.5:
                    found = [c for c in connectors if c.lower() in para.lower()]
                    issues.append(Issue(
                        category='逻辑跳跃', severity=Severity.MINOR,
                        section=sec_name, location=f'第{i+1}段',
                        problem=f'逻辑连接词密度过高({density:.1f}/句): {", ".join(found[:3])}',
                        original=para[:80] + '...',
                        suggestion='减少逻辑连接词的使用，用数据和证据代替强行推理',
                        root_cause='过多使用"因此/所以"暗示推理链条不扎实',
                        fix_action='删除部分连接词，改用证据自然过渡',
                        downstream_impact='读者感觉作者在"强行推论"',
                        teaching_note='逻辑跳跃密度高意味着推理不扎实。'
                                      '好的论证用数据说话，不需要频繁声明"因此"。',
                    ))

        # 检查弱断言词
        weak_assertions_zh = ['显然', '毫无疑问', '众所周知', '不言而喻']
        weak_assertions_en = ['clearly', 'obviously', 'undoubtedly', 'of course', 'without doubt']
        weak_assertions = weak_assertions_zh if language == 'zh' else weak_assertions_en

        for sec_name, sec in sections.items():
            if sec_name in ('references', 'acknowledgments', 'preamble'):
                continue
            for i, para in enumerate(sec.paragraphs):
                for weak in weak_assertions:
                    if weak.lower() in para.lower():
                        issues.append(Issue(
                            category='逻辑跳跃', severity=Severity.MINOR,
                            section=sec_name, location=f'第{i+1}段',
                            problem=f'使用了弱断言词"{weak}"',
                            original=para[:80] + '...',
                            suggestion=f'删除"{weak}"，用数据支撑代替空洞断言',
                            root_cause=f'"{weak}"是主观判断，学术写作应基于客观证据',
                            fix_action=f'删除"{weak}"，在该位置添加具体数据或文献引用',
                            downstream_impact='削弱论文的客观性和可信度',
                            teaching_note='学术写作应避免主观判断词。'
                                          '"显然"对作者来说显然，对读者未必。',
                        ))

        return issues


class CitationQualityChecker:
    """引用质量深度审计 - 借鉴PaperSpine的citation_quality_audit"""

    @staticmethod
    def check(sections, language='en'):
        issues = []
        if audit_citations_batch is None:
            return issues

        # 从正文提取引用列表
        all_text = ' '.join(sec.body for sec in sections.values() if sec.body)
        # 匹配 [1], [2,3], (Author, 2020) 等格式的引用
        ref_patterns = re.findall(r'\[(\d+(?:[-,]\d+)*)\]', all_text)
        author_refs = re.findall(r'\([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&|and))?\s*,?\s*\d{4}[a-z]?\)', all_text)

        # 从references章节提取完整引用文本
        ref_section = sections.get('references', None)
        if ref_section and ref_section.body:
            ref_lines = [l.strip() for l in ref_section.body.split('\n')
                         if l.strip() and len(l.strip()) > 20 and not l.startswith('#')]
        else:
            ref_lines = []

        if not ref_lines and not ref_patterns:
            return issues

        # 孤儿引用检测：正文中引用了但参考文献列表中没有的编号
        if ref_lines and ref_patterns:
            cited_nums = set()
            for c in ref_patterns:
                for part in re.split(r'[,]', c):
                    if '-' in part:
                        start, end = part.split('-')
                        for i in range(int(start), int(end) + 1):
                            cited_nums.add(i)
                    else:
                        cited_nums.add(int(part))

            # 参考文献列表中的编号
            ref_nums = set()
            for line in ref_lines:
                m = re.match(r'\[(\d+)\]', line)
                if m:
                    ref_nums.add(int(m.group(1)))

            orphan_cites = cited_nums - ref_nums
            unused_refs = ref_nums - cited_nums

            if orphan_cites:
                sorted_orphans = sorted(orphan_cites)[:10]
                issues.append(Issue(
                    category='引用质量', severity=Severity.CRITICAL,
                    section='正文', location='引用编号',
                    problem=f'正文中引用了{len(orphan_cites)}个参考文献列表中不存在的编号: {sorted_orphans}',
                    original=f'孤立引用: {sorted_orphans}',
                    suggestion='检查引用编号是否正确，或补充缺失的参考文献条目',
                    root_cause='引用编号与参考文献列表不匹配',
                    fix_action='逐一核对孤立引用编号，补充或修正参考文献列表',
                    downstream_impact='审稿人会认为论文不严谨，可能直接拒稿',
                    teaching_note='每一条正文引用都必须在参考文献列表中有对应条目。',
                ))

            if unused_refs:
                sorted_unused = sorted(unused_refs)[:10]
                issues.append(Issue(
                    category='引用质量', severity=Severity.MINOR,
                    section='references', location='参考文献',
                    problem=f'参考文献列表中有{len(unused_refs)}篇未在正文中引用: {sorted_unused}',
                    original=f'未使用引用: {sorted_unused}',
                    suggestion='在正文中引用这些文献，或从参考文献列表中删除',
                    root_cause='参考文献列表包含未使用的条目',
                    fix_action='删除未使用的参考文献，或在合适位置添加引用',
                    downstream_impact='冗余参考文献影响论文精炼度',
                ))

        # 如果有完整的参考文献列表，做深度审计
        if ref_lines:
            try:
                result = audit_citations_batch(ref_lines[:50], verify=True)
                overall = result['overall_score']
                dead = result['dead_count']
                gap = result.get('gap_analysis', {})

                # 综合评分太低
                if overall < 50:
                    issues.append(Issue(
                        category='引用质量', severity=Severity.MAJOR,
                        section='references', location='参考文献',
                        problem=f'引用综合质量偏低(评分{overall}/100)',
                        original=f'已验证{result["verified_count"]}/{len(ref_lines)}篇',
                        suggestion='检查DOI有效性、补充近期文献、增加引用类型多样性',
                        root_cause='引用来源质量不均衡或过于陈旧',
                        fix_action='优先修复失效DOI，补充近3-5年的文献',
                        downstream_impact='审稿人可能质疑文献综述的全面性和准确性',
                        teaching_note='引用不是越多越好，每条引用都应有质量保证。'
                                      '高质量引用 = 可验证DOI + 近5年 + 类型多样。',
                    ))

                # 失效DOI
                if dead > 0:
                    issues.append(Issue(
                        category='引用质量', severity=Severity.CRITICAL,
                        section='references', location='参考文献',
                        problem=f'{dead}篇文献的DOI无法解析',
                        original='DOI验证失败',
                        suggestion='核实DOI或删除失效引用，替换为同主题的有效文献',
                        root_cause='DOI拼写错误或文献已被撤回',
                        fix_action='逐一检查失效DOI，通过Crossref或Google Scholar验证',
                        downstream_impact='读者无法核实引用来源，严重损害论文可信度',
                        teaching_note='死链DOI是审稿人最容易发现的问题之一。',
                    ))

                # 引用类型多样性差距
                for g in gap.get('gaps', []):
                    issues.append(Issue(
                        category='引用质量', severity=Severity.MINOR,
                        section='references', location='参考文献',
                        problem=f'缺少{g["type"]}类型引用(实际{g["actual"]}，期望{g["expected"]})',
                        original=f'{g["type"]}占比不足',
                        suggestion=gap.get('teaching_notes', ['补充相关类型文献'])[0] if gap.get('teaching_notes') else '补充相关类型文献',
                        root_cause='引用来源不够全面',
                        fix_action=f'补充{g["type"]}类型的文献',
                        downstream_impact='引用结构单一，可能遗漏重要视角',
                    ))

            except Exception as e:
                logger.debug(f"CitationQualityChecker error: {e}")

        return issues


# ============================================================================
# Nature 结构性诊断（来自 nature-polishing skill failure-modes）
# ============================================================================
class StructuralDiagnosisChecker:
    """
    基于 nature-polishing skill 的结构性失败模式诊断。
    优先级：paper_type → section_job → paragraph_logic → claim/evidence/boundary → sentence_polish
    不在句法层面修补结构问题。
    """

    @staticmethod
    def check(sections, language='en'):
        issues = []
        section_names = list(sections.keys())
        section_bodies = {k: v.body if hasattr(v, 'body') else str(v) for k, v in sections.items()}

        # 1. 检查必要章节是否存在
        required_sections = {
            'en': ['introduction', 'methods', 'results', 'discussion', 'conclusion'],
            'zh': ['引言', '方法', '结果', '讨论', '结论'],
        }
        # 同时检查中英文章节名
        en_required = required_sections['en']
        zh_required = required_sections['zh']
        present = [s.lower() for s in section_names]

        # 中英文映射
        zh_en_map = {
            '引言': 'introduction',
            '方法': 'methods',
            '结果': 'results',
            '讨论': 'discussion',
            '结论': 'conclusion',
        }

        for en_name, zh_name in zip(en_required, zh_required):
            # 检查是否包含英文或中文名称
            found = False
            for p in present:
                if en_name in p or zh_name in p:
                    found = True
                    break
            # 也检查中英文混合的情况（如 "results_discussion"）
            if not found:
                for p in present:
                    if 'result' in p and 'discussion' in p:
                        # results_discussion 同时包含结果和讨论
                        if en_name in ['results', 'discussion']:
                            found = True
                            break
            if not found:
                issues.append(Issue(
                    category='Nature结构诊断',
                    severity=Severity.MAJOR,
                    section='全局',
                    location='章节结构',
                    problem=f'缺少必要章节: {zh_name}({en_name})',
                    original='',
                    suggestion=f'补充{zh_name}章节',
                    root_cause='wrong_paper_type',
                    fix_action='补充缺失章节',
                    downstream_impact='审稿人可能直接拒稿',
                    teaching_note='Nature 系列要求完整的 IMRaD 结构',
                ))

        # 2. 检查 Introduction 是否包含 gap 语句
        intro_key = None
        for k in section_names:
            if 'intro' in k.lower() or '引言' in k:
                intro_key = k
                break
        if intro_key:
            intro_text = section_bodies[intro_key].lower()
            gap_indicators = ['however', 'remains', 'poorly understood', 'few studies',
                              'limited', 'gap', 'not yet', 'has not been',
                              '然而', '尚不清楚', '研究不足', '空白', '鲜有', '尚未']
            has_gap = any(g in intro_text for g in gap_indicators)
            if not has_gap:
                issues.append(Issue(
                    category='Nature结构诊断',
                    severity=Severity.MAJOR,
                    section=intro_key,
                    location='Introduction',
                    problem='Introduction 缺少明确的研究空白（gap）陈述',
                    original='',
                    suggestion='在 Introduction 中明确指出 "However, ... remains poorly understood" 或类似 gap 语句',
                    root_cause='missing_gap',
                    fix_action='在 Introduction 末段前插入 gap 段落',
                    downstream_impact='读者无法理解本研究的必要性',
                    teaching_note='Nature-polishing: Introduction 必须回答 "What is still missing?"',
                ))

        # 3. 检查 Results 是否混入讨论
        results_key = None
        for k in section_names:
            if 'result' in k.lower() or '结果' in k:
                results_key = k
                break
        if results_key:
            results_text = section_bodies[results_key].lower()
            discussion_markers = ['this suggests', 'this indicates', 'one explanation',
                                  'a possible reason', 'this may be due to',
                                  'the mechanism', 'we speculate',
                                  '这表明', '可能原因', '机制可能是', '推测']
            mixed_count = sum(1 for m in discussion_markers if m in results_text)
            if mixed_count >= 3:
                issues.append(Issue(
                    category='Nature结构诊断',
                    severity=Severity.MAJOR,
                    section=results_key,
                    location='Results',
                    problem=f'Results 中发现 {mixed_count} 处讨论性表述，结果与讨论混合',
                    original='',
                    suggestion='将解释性语句移至 Discussion，Results 只陈述观察到的事实',
                    root_cause='results_discussion_mixed',
                    fix_action='分离 Results 和 Discussion',
                    downstream_impact='混淆事实与推测，降低可信度',
                    teaching_note='Nature-polishing: Results 回答 "What was observed?"，Discussion 回答 "What does it mean?"',
                ))

        # 4. 检查 Discussion 是否有边界/局限性
        disc_key = None
        for k in section_names:
            if 'discuss' in k.lower() or '讨论' in k:
                disc_key = k
                break
        if disc_key:
            disc_text = section_bodies[disc_key].lower()
            boundary_indicators = ['limitation', 'caveat', 'caution', 'cannot exclude',
                                   'should be interpreted', 'generalisability',
                                   '局限', '限制', '谨慎', '不能排除', '推广性']
            has_boundary = any(b in disc_text for b in boundary_indicators)
            if not has_boundary:
                issues.append(Issue(
                    category='Nature结构诊断',
                    severity=Severity.MINOR,
                    section=disc_key,
                    location='Discussion',
                    problem='Discussion 缺少局限性或边界说明',
                    original='',
                    suggestion='添加 "These findings should be interpreted with caution because ..." 或 "A limitation of this study is that ..."',
                    root_cause='missing_boundary',
                    fix_action='在 Discussion 末段前插入 Limitations 段落',
                    downstream_impact='审稿人会质疑作者的学术严谨性',
                    teaching_note='Nature-polishing: Discussion 必须回答 "What limitations constrain interpretation?"',
                ))

        # 5. 术语一致性检查（跨章节）
        all_text = ' '.join(section_bodies.values())
        # 检测常见不一致模式
        inconsistencies = [
            (['CO₂', 'CO2', 'CO_2'], 'CO₂ 写法不一致'),
            (['CH₄', 'CH4', 'CH_4'], 'CH₄ 写法不一致'),
            (['N₂O', 'N2O', 'N_2O'], 'N₂O 写法不一致'),
        ]
        for variants, msg in inconsistencies:
            found = [v for v in variants if v in all_text]
            if len(found) > 1:
                issues.append(Issue(
                    category='Nature结构诊断',
                    severity=Severity.MINOR,
                    section='全局',
                    location='术语一致性',
                    problem=f'{msg}: 使用了 {found}',
                    original=str(found),
                    suggestion=f'统一为 {found[0]}',
                    root_cause='terminology_inconsistent',
                    fix_action=f'全文替换为 {found[0]}',
                    downstream_impact='显得不专业',
                    teaching_note='Nature-polishing: 构建 Terminology Ledger，全文强制一致',
                ))

        return issues


# ============================================================================
# 综合评分系统
# ============================================================================
class Scorer:
    """论文质量评分"""

    DIMENSIONS = {
        'SCI格式': {'weight': 0.08, 'description': '格式规范性'},
        '中文格式': {'weight': 0.06, 'description': '中文格式规范'},
        '错别字': {'weight': 0.05, 'description': '拼写正确性'},
        '学术语法': {'weight': 0.05, 'description': '语言学术性'},
        '引文规范': {'weight': 0.06, 'description': '引用规范性'},
        '图表规范': {'weight': 0.06, 'description': '图表规范性'},
        '数据逻辑': {'weight': 0.08, 'description': '数据一致性'},
        'Discussion逻辑': {'weight': 0.07, 'description': '讨论深度'},
        'AI痕迹': {'weight': 0.04, 'description': '自然度'},
        '学术重复': {'weight': 0.04, 'description': '原创性'},
        '推理链完整性': {'weight': 0.07, 'description': '推理链完整性'},
        '逻辑跳跃': {'weight': 0.05, 'description': '逻辑严谨性'},
        '引用质量': {'weight': 0.07, 'description': 'DOI有效性+引用类型多样性'},
        'Nature结构诊断': {'weight': 0.10, 'description': '结构完整性（Nature标准）'},
    }

    @classmethod
    def score(cls, issues):
        """根据问题计算各维度得分(0-10)"""
        scores = {}
        penalty = defaultdict(float)

        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                penalty[issue.category] += 2.0
            elif issue.severity == Severity.MAJOR:
                penalty[issue.category] += 1.0
            elif issue.severity == Severity.MINOR:
                penalty[issue.category] += 0.3

        for dim, config in cls.DIMENSIONS.items():
            p = penalty.get(dim, 0)
            score = max(1.0, 10.0 - p)
            scores[dim] = round(score, 1)

        # 加权总分
        total = sum(scores.get(dim, 10) * config['weight']
                    for dim, config in cls.DIMENSIONS.items())
        scores['总分'] = round(total, 1)

        return scores


# ============================================================================
# 主Agent
# ============================================================================
class AcademicReviewAgent:
    """
    论文自动检查Agent

    10类检查 → 评分 → 修改建议 → 审稿意见级报告
    """

    CHECKERS = [
        ('SCI格式', SCIChecker),
        ('中文格式', ChineseChecker),
        ('中文核心专项', ChineseChecker),  # check_cn_core_rules
        ('错别字', TypoChecker),
        ('学术语法', ForbiddenWordChecker),
        ('引文规范', CitationChecker),
        ('图表规范', FigureChecker),
        ('数据逻辑', DataLogicChecker),
        ('Discussion逻辑', DiscussionChecker),
        ('AI痕迹', AIDetector),
        ('学术重复', RepetitionChecker),
        ('推理链完整性', RationaleChecker),
        ('逻辑跳跃', LogicalLeapChecker),
        ('引用质量', CitationQualityChecker),
        ('Nature结构诊断', StructuralDiagnosisChecker),  # nature-polishing skill
    ]

    def __init__(self, paper_type='sci', language='auto'):
        self.paper_type = paper_type
        self.language = language

    def review(self, text_or_path):
        """
        审稿入口

        Parameters
        ----------
        text_or_path : str
            论文文本或文件路径（.md/.txt）

        Returns
        -------
        ReviewReport
        """
        # 加载文本
        if os.path.isfile(text_or_path):
            with open(text_or_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = text_or_path

        # 检测语言
        if self.language == 'auto':
            self.language = SectionParser.detect_language(text)

        # 解析章节
        sections = SectionParser.parse(text, self.language)

        print(f"\n{'='*60}")
        print(f"Academic Review Agent - 论文自动检查")
        print(f"语言: {self.language} | 类型: {self.paper_type}")
        print(f"检测到{len(sections)}个章节: {', '.join(sections.keys())}")
        print(f"{'='*60}\n")

        # 运行所有检查器
        all_issues = []
        for name, checker in self.CHECKERS:
            try:
                if name == '中文核心专项':
                    issues = checker.check_cn_core_rules(sections, self.language)
                else:
                    issues = checker.check(sections, self.language)
                all_issues.extend(issues)
                if issues:
                    print(f"  [{name}] 发现{len(issues)}个问题")
                else:
                    print(f"  [{name}] 通过")
            except Exception as e:
                print(f"  [{name}] 检查出错: {e}")

        # 评分
        scores = Scorer.score(all_issues)

        # 生成报告
        report = ReviewReport(
            issues=all_issues,
            scores=scores,
            paper_type=self.paper_type,
            language=self.language,
        )

        return report

    def generate_report(self, report, output_path=None):
        """生成可读的审稿报告"""
        lines = []
        lines.append('=' * 60)
        lines.append('论文审稿报告 - Academic Review Report')
        lines.append('=' * 60)

        # 评分摘要
        lines.append('')
        lines.append('## 评分 Summary')
        lines.append('')
        for dim, config in Scorer.DIMENSIONS.items():
            score = report.scores.get(dim, 10)
            bar = '#' * int(score) + '.' * (10 - int(score))
            status = 'OK' if score >= 7 else ('--' if score >= 5 else '!!')
            lines.append(f'  {status} {dim:12s} [{bar}] {score:.1f}/10  {config["description"]}')
        lines.append(f'  {"-"*45}')
        lines.append(f'  ★ 加权总分: {report.scores.get("总分", 0):.1f}/10')

        # 总结
        summary = report.summary()
        lines.append('')
        lines.append(f'## 问题统计: 共{summary["total"]}个')
        for sev, count in sorted(summary['by_severity'].items()):
            lines.append(f'  {sev}: {count}个')
        lines.append('')

        # 按严重级别排列问题
        lines.append('## 详细问题列表')
        severity_order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.INFO: 3}
        sorted_issues = sorted(report.issues, key=lambda x: severity_order.get(x.severity, 9))

        for i, issue in enumerate(sorted_issues, 1):
            sev_icon = {'CRITICAL': '🔴', 'MAJOR': '🟡', 'MINOR': '🔵', 'INFO': 'ℹ️'}
            lines.append('')
            lines.append(f'--- [{i}/{len(sorted_issues)}] {sev_icon.get(issue.severity.value, "")} {issue.severity.value} ---')
            lines.append(f'类别: {issue.category}')
            lines.append(f'章节: {issue.section}')
            lines.append(f'问题: {issue.problem}')
            if issue.original:
                lines.append(f'原文: {issue.original}')
            lines.append(f'建议: {issue.suggestion}')
            if issue.fix:
                lines.append(f'修复: {issue.fix}')

        # 终稿审稿意见模板
        lines.append('')
        lines.append('=' * 60)
        lines.append('## 模拟审稿意见 (Reviewer Comments)')
        lines.append('')

        critical = [i for i in report.issues if i.severity == Severity.CRITICAL]
        major = [i for i in report.issues if i.severity == Severity.MAJOR]

        if critical:
            lines.append('### Major Issues (必须修改)')
            for i, issue in enumerate(critical, 1):
                lines.append(f'{i}. [{issue.category}] {issue.problem}')
                lines.append(f'   Suggestion: {issue.suggestion}')
                lines.append('')

        if major:
            lines.append('### Minor Issues (建议修改)')
            for i, issue in enumerate(major, 1):
                lines.append(f'{i}. [{issue.category}] {issue.problem}')
                lines.append(f'   Suggestion: {issue.suggestion}')
                lines.append('')

        if not critical and not major:
            lines.append('No major issues found. The manuscript is in good shape.')

        # 综合评价
        total = report.scores.get('总分', 0)
        lines.append('### Overall Assessment')
        if total >= 8.5:
            lines.append('The manuscript is well-written and ready for submission with minor polishing.')
        elif total >= 7.0:
            lines.append('The manuscript is generally acceptable but needs moderate revision.')
        elif total >= 5.0:
            lines.append('The manuscript requires substantial revision before it can be considered for publication.')
        else:
            lines.append('The manuscript requires major restructuring and rewriting.')

        report_text = '\n'.join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n报告已保存至: {output_path}")

        return report_text

    def submit_feedback(self, report: ReviewReport,
                        accepted_indices: list = None,
                        rejected_indices: list = None,
                        comment: str = ""):
        """
        提交审稿反馈，驱动知识库进化。

        Parameters
        ----------
        report : ReviewReport, 上次review()的结果
        accepted_indices : list of int, 被接受的issue序号(从1开始)
        rejected_indices : list of int, 被拒绝的issue序号(从1开始)
        comment : str, 用户评论
        """
        accepted = []
        rejected = []
        for i, issue in enumerate(report.issues, 1):
            entry = {"category": issue.category, "severity": issue.severity.value}
            if accepted_indices and i in accepted_indices:
                accepted.append(entry)
            elif rejected_indices and i in rejected_indices:
                rejected.append(entry)

        # 写入knowledge_store
        if FeedbackCollector is None:
            return False
        try:
            store = KnowledgeStore()
            fb = FeedbackCollector(store)
            fb.log_review_feedback(
                paper_text="", report_issues=[],
                accepted=accepted, rejected=rejected, comment=comment
            )
            return True
        except Exception as e:
            logger.debug(f"Failed to submit feedback: {e}")
            return False


# ============================================================================
# 便捷入口
# ============================================================================
def review_paper(text_or_path, paper_type='sci', language='auto', output_path=None):
    """
    一键审稿

    Parameters
    ----------
    text_or_path : str, 论文文本或文件路径
    paper_type : 'sci' | 'chinese_thesis' | 'chinese_journal'
    language : 'auto' | 'zh' | 'en'
    output_path : str, 报告输出路径

    Returns
    -------
    ReviewReport, report_text: str
    """
    agent = AcademicReviewAgent(paper_type=paper_type, language=language)
    report = agent.review(text_or_path)
    report_text = agent.generate_report(report, output_path=output_path)
    return report, report_text


# ============================================================================
# 知识库桥接：从knowledge_store加载进化后的知识
# ============================================================================
def _load_evolved_knowledge():
    """从knowledge_store加载进化后的知识，覆盖硬编码默认值。失败时静默跳过。"""
    import json
    from pathlib import Path

    store_dir = Path(__file__).parent / "knowledge_store"
    if not store_dir.exists():
        return

    # 1. 加载审稿规则
    rules_path = store_dir / "review_rules.json"
    if rules_path.exists():
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entries = data.get("entries", {})

            evolved_forbidden_en = {}
            evolved_forbidden_zh = {}
            evolved_ai_en = []
            evolved_ai_zh = []
            evolved_hollow_en = []
            evolved_hollow_zh = []
            evolved_overclaim_en = []
            evolved_overclaim_zh = []

            for key, entry in entries.items():
                val = entry.get("value", entry)
                if key.startswith("forbidden_en_") and isinstance(val, dict):
                    evolved_forbidden_en[val["word"]] = val["suggestion"]
                elif key.startswith("forbidden_zh_") and isinstance(val, dict):
                    evolved_forbidden_zh[val["word"]] = val["suggestion"]
                elif key.startswith("ai_pattern_en_") and isinstance(val, str):
                    evolved_ai_en.append(val)
                elif key.startswith("ai_pattern_zh_") and isinstance(val, str):
                    evolved_ai_zh.append(val)
                elif key.startswith("hollow_en_") and isinstance(val, str):
                    evolved_hollow_en.append(val)
                elif key.startswith("hollow_zh_") and isinstance(val, str):
                    evolved_hollow_zh.append(val)
                elif key.startswith("overclaim_en_") and isinstance(val, str):
                    evolved_overclaim_en.append(val)
                elif key.startswith("overclaim_zh_") and isinstance(val, str):
                    evolved_overclaim_zh.append(val)

            if evolved_forbidden_en:
                ReviewKB.EN_FORBIDDEN = evolved_forbidden_en
            if evolved_forbidden_zh:
                ReviewKB.ZH_FORBIDDEN = evolved_forbidden_zh
            if evolved_ai_en:
                ReviewKB.AI_PATTERNS_EN = evolved_ai_en
            if evolved_ai_zh:
                ReviewKB.AI_PATTERNS_ZH = evolved_ai_zh
            if evolved_hollow_en:
                ReviewKB.HOLLOW_PATTERNS_EN = evolved_hollow_en
            if evolved_hollow_zh:
                ReviewKB.HOLLOW_PATTERNS_ZH = evolved_hollow_zh
            if evolved_overclaim_en:
                ReviewKB.OVERCLAIM_EN = evolved_overclaim_en
            if evolved_overclaim_zh:
                ReviewKB.OVERCLAIM_ZH = evolved_overclaim_zh
        except Exception as e:
            logger.debug(f"Failed to load evolved review rules: {e}")

    # 2. 加载评分权重
    params_path = store_dir / "parameters.json"
    if params_path.exists():
        try:
            with open(params_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entries = data.get("entries", {})

            for key, entry in entries.items():
                if not key.startswith("score_weight_"):
                    continue
                dim = key.replace("score_weight_", "")
                val = entry.get("value", entry)
                if isinstance(val, dict) and dim in Scorer.DIMENSIONS:
                    new_weight = val.get("weight", val.get("value"))
                    if new_weight is not None and isinstance(new_weight, (int, float)):
                        Scorer.DIMENSIONS[dim]["weight"] = float(new_weight)

            # 归一化权重确保总和为1.0
            total_weight = sum(c['weight'] for c in Scorer.DIMENSIONS.values())
            if total_weight > 0 and abs(total_weight - 1.0) > 1e-6:
                for config in Scorer.DIMENSIONS.values():
                    config['weight'] = round(config['weight'] / total_weight, 4)
        except Exception as e:
            logger.debug(f"Failed to load evolved parameters: {e}")


# 模块加载时自动桥接进化知识
_load_evolved_knowledge()
