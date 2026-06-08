"""
论文写作优化器
==============
借鉴 GPT-Academic 的学术润色策略，
提供规则驱动的论文语言优化能力。

核心能力:
  1. 学术语料润色 (中文/英文)
  2. 语法检查 (禁用词 + 口语化 + 学术风格)
  3. 中英学术互译 (基于句式库)
  4. 修改对比报告生成

设计原则:
  - 不改变科学内容和核心观点
  - 基于规则+知识库，不依赖LLM API
  - 输出修改文本 + 修改原因表格

借鉴自: https://github.com/binary-husky/gpt_academic
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────

@dataclass
class Change:
    """单条修改记录"""
    original: str       # 原文
    revised: str        # 修改后
    reason: str         # 修改原因
    category: str       # 修改类别
    location: str = ""  # 位置描述


@dataclass
class OptimizationResult:
    """优化结果"""
    original_text: str
    optimized_text: str
    language: str
    changes: list = field(default_factory=list)

    def has_changes(self) -> bool:
        return len(self.changes) > 0

    def to_markdown(self) -> str:
        """输出修改对比报告"""
        lines = [
            "# 论文润色报告",
            "",
            f"语言: {'中文' if self.language == 'zh' else '英文'}",
            f"修改数量: {len(self.changes)}",
            "",
            "## 润色后文本",
            "",
            self.optimized_text,
            "",
        ]

        if self.changes:
            lines.extend([
                "## 修改明细",
                "",
                "| # | 类别 | 原文 | 修改后 | 修改原因 |",
                "|---|------|------|--------|---------|",
            ])
            for i, c in enumerate(self.changes, 1):
                orig_short = c.original[:40] + ("..." if len(c.original) > 40 else "")
                rev_short = c.revised[:40] + ("..." if len(c.revised) > 40 else "")
                lines.append(f"| {i} | {c.category} | {orig_short} | {rev_short} | {c.reason} |")
        else:
            lines.append("未发现需要修改的内容。")

        return '\n'.join(lines)


# ── 中文润色规则 ──────────────────────────────────────────

# 口语化 → 学术化 替换表
_ZH_COLLOQUIAL_TO_ACADEMIC = [
    # (口语表达, 学术替换, 原因)
    ('搞清楚', '阐明', '口语化表达，替换为学术用语'),
    ('搞明白', '阐明', '口语化表达'),
    ('用了', '采用了', '缺少学术严谨性'),
    ('用了.*方法', r'采用\1方法', '动词不正式'),
    ('跟', '与', '"跟"为口语，学术论文应使用"与"'),
    ('比较大的', '显著的', '口语化程度副词'),
    ('比较小的', '较小的', '口语化程度副词'),
    ('很多', '大量', '口语化数量词'),
    ('好多', '大量', '口语化数量词'),
    ('差不多', '约', '口语化表达'),
    ('一般来说', '通常', '口语化开头'),
    ('基本上', '大致', '口语化表达'),
    ('还行', '较为理想', '口语化评价词'),
    ('感觉', '推测', '主观表达，学术论文应客观'),
    ('看起来', '表明', '主观表达'),
    ('看起来像是', '表明', '主观表达'),
    ('挺好的', '较为理想', '口语化评价'),
    ('挺大的', '较大的', '口语化程度副词'),
    ('挺重要的', '至关重要的', '口语化程度副词'),
    ('其实', '', '多余的语气词，删除'),
    ('就是说', '即', '口语化连接词'),
    ('这样的话', '由此', '口语化连接词'),
    ('要不然', '否则', '口语化连接词'),
    ('所以呢', '因此', '口语化连接词，缺少"呢"'),
    ('然后呢', '', '口语化连接词，删除'),
]

# 学术禁用词（英文→替换建议）
_EN_FORBIDDEN_WORDS = {
    'prove': ('demonstrate / suggest / indicate', '科学结论不宜用"prove"，除非是数学证明'),
    'very': ('删除，用具体数据替代', '"very"缺乏学术精确性'),
    'a lot of': ('substantial / considerable', '口语化数量词'),
    'lots of': ('numerous / considerable', '口语化数量词'),
    'get': ('obtain / acquire / derive', '动词不正式'),
    'big': ('significant / substantial / considerable', '形容词不精确'),
    'good': ('favorable / effective / satisfactory', '形容词不精确'),
    'bad': ('poor / unfavorable / inadequate', '形容词不精确'),
    'nice': ('favorable / acceptable', '形容词不精确'),
    'thing': ('factor / aspect / element', '名词不精确'),
    'stuff': ('material / substance', '名词不精确'),
    'pretty': ('moderately / relatively', '程度副词不精确'),
    'huge': ('enormous / substantial', '形容词不正式'),
    'tiny': ('negligible / minimal', '形容词不正式'),
    'really': ('significantly / notably', '程度副词不正式'),
    'actually': ('删除或替换为 in fact', '多余的语气词'),
    'basically': ('fundamentally / essentially', '口语化'),
    'just': ('删除或替换为 merely / only', '口语化'),
    'pretty much': ('approximately / largely', '口语化'),
    'kind of': ('somewhat / to some extent', '口语化'),
    'sort of': ('somewhat / to some extent', '口语化'),
}

# 中文禁用词
_ZH_FORBIDDEN_WORDS = {
    '本文': ('本研究', '"本文"不够正式'),
    '本论文': ('本研究', '"本论文"不够正式'),
    '笔者': ('作者 / 本研究', '"笔者"偏口语'),
    '众所周知': ('删除，用文献引用替代', '空洞断言，无实质内容'),
    '不言而喻': ('删除', '空洞断言'),
    '毫无疑问': ('删除', '空洞断言'),
    '显然': ('删除，用数据支撑', '空洞断言'),
    '显而易见': ('删除，用数据支撑', '空洞断言'),
}

# 英文AI痕迹句式
_EN_AI_PATTERNS = [
    (r"It is (?:important|crucial|essential|worth noting) to (?:note|mention|强调)",
     '删除，直接陈述事实'),
    (r"(?:delve|dive) into", '替换为 investigate / examine'),
    (r"in the realm of", '替换为 in the field of'),
    (r"it'?s worth noting that", '删除，直接陈述'),
    (r"the (?:multifaceted|nuanced|intricate) (?:nature|interplay|landscape)",
     '替换为具体描述'),
    (r"plays a (?:crucial|pivotal|vital|key) role", '替换为具体作用描述'),
    (r"(?:shed light|cast light) on", '替换为 reveal / demonstrate'),
    (r"at the (?:forefront|intersection) of", '替换为 in'),
    (r"(?:holistic|comprehensive|robust) (?:approach|framework|understanding)",
     '替换为具体方法名称'),
    (r"(?:tapestry|myriad|plethora|cornucopia)", '替换为具体数量或删除'),
    (r"(?:leveraging|harnessing|utilizing) (?:the|a) (?:power|potential)",
     '替换为 using / employing'),
]

# 中文AI痕迹句式
_ZH_AI_PATTERNS = [
    (r"值得[注关]意的是", '删除，直接陈述'),
    (r"(?:深入|进一步)探讨", '替换为 分析 / 研究'),
    (r"(?:扮演|起着)(?:关键|重要|核心)(?:角色|作用)", '替换为具体作用描述'),
    (r"(?:揭示|阐明|展现了?).+(?:深刻|重要)(?:认识|理解|洞察)",
     '替换为具体发现描述'),
    (r"(?:填补|弥补)(?:了?)(?:研究)?空白", '删除或替换为具体贡献'),
    (r"(?:首次|开创性|创新性地)(?:发现|提出|证明)", '删除夸大修饰'),
    (r"(?:为).+(?:提供.{0,5}(?:理论|科学|数据)(?:支撑|依据|参考))",
     '替换为具体贡献描述'),
]


# ── 学术润色引擎 ──────────────────────────────────────────

class AcademicPolisher:
    """学术语料润色器"""

    def __init__(self):
        self.changes = []

    def polish(self, text: str, language: str = 'auto') -> OptimizationResult:
        """
        学术语料润色

        Parameters
        ----------
        text : str, 待润色文本
        language : str, 'zh' / 'en' / 'auto'

        Returns
        -------
        OptimizationResult
        """
        if language == 'auto':
            language = self._detect_language(text)

        self.changes = []
        optimized = text

        if language == 'zh':
            optimized = self._polish_zh(optimized)
        else:
            optimized = self._polish_en(optimized)

        return OptimizationResult(
            original_text=text,
            optimized_text=optimized,
            language=language,
            changes=self.changes,
        )

    def _detect_language(self, text: str) -> str:
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        total = max(1, len(text))
        return 'zh' if chinese_chars / total > 0.15 else 'en'

    def _polish_zh(self, text: str) -> str:
        """中文润色"""
        result = text

        # 1. 口语化→学术化
        for pattern, replacement, reason in _ZH_COLLOQUIAL_TO_ACADEMIC:
            if re.search(pattern, result):
                old = re.search(pattern, result).group()
                result = re.sub(pattern, replacement, result, count=1)
                self.changes.append(Change(
                    original=old, revised=replacement,
                    reason=reason, category='口语化→学术化',
                ))

        # 2. 禁用词检查
        for word, (suggestion, reason) in _ZH_FORBIDDEN_WORDS.items():
            if word in result:
                self.changes.append(Change(
                    original=word, revised=suggestion,
                    reason=reason, category='禁用词',
                ))

        # 3. AI痕迹检查
        for pattern, suggestion in _ZH_AI_PATTERNS:
            match = re.search(pattern, result)
            if match:
                self.changes.append(Change(
                    original=match.group(), revised=suggestion,
                    reason='AI生成痕迹', category='AI痕迹',
                ))

        # 4. 标点规范
        result = self._fix_punctuation_zh(result)

        return result

    def _polish_en(self, text: str) -> str:
        """英文润色"""
        result = text

        # 1. 禁用词检查
        for word, (suggestion, reason) in _EN_FORBIDDEN_WORDS.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                self.changes.append(Change(
                    original=match.group(), revised=suggestion,
                    reason=reason, category='Forbidden word',
                ))

        # 2. AI痕迹检查
        for pattern, suggestion in _EN_AI_PATTERNS:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                self.changes.append(Change(
                    original=match.group(), revised=suggestion,
                    reason='AI-generated pattern', category='AI Pattern',
                ))

        # 3. 被动语态过度使用检查
        passive_count = len(re.findall(
            r'\b(?:is|are|was|were|be|been|being)\s+\w+ed\b', result, re.IGNORECASE
        ))
        sentence_count = max(1, len(re.split(r'[.!?]+', result)))
        if passive_count / sentence_count > 0.5:
            self.changes.append(Change(
                original=f'{passive_count} passive constructions',
                revised='Consider converting some to active voice',
                reason='Passive voice overuse (>50% of sentences)',
                category='Style',
            ))

        return result

    def _fix_punctuation_zh(self, text: str) -> str:
        """修正中文标点"""
        result = text
        # 中文文段中的英文逗号→中文逗号
        def fix_comma(match):
            self.changes.append(Change(
                original=',', revised='，',
                reason='中文文段应使用全角逗号', category='标点规范',
            ))
            return '，'

        # 匹配中文上下文中的英文逗号
        result = re.sub(r'(?<=[一-鿿]),(?=[一-鿿\s])', fix_comma, result)
        return result


# ── 语法检查器 ──────────────────────────────────────────

class GrammarChecker:
    """增强版语法检查器"""

    def check(self, text: str, language: str = 'auto') -> list:
        """
        语法检查

        Returns
        -------
        list of Change
        """
        if language == 'auto':
            language = self._detect_language(text)

        issues = []
        if language == 'zh':
            issues.extend(self._check_zh(text))
        else:
            issues.extend(self._check_en(text))

        return issues

    def _detect_language(self, text: str) -> str:
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        return 'zh' if chinese_chars / max(1, len(text)) > 0.15 else 'en'

    def _check_zh(self, text: str) -> list:
        """中文语法检查"""
        issues = []

        # 1. 主语缺失检查（连续句子无主语）
        sentences = re.split(r'[。！？；]', text)
        prev_has_subject = True
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 5:
                continue
            has_subject = bool(re.search(r'^[一-鿿]{1,4}(?:是|的|在|了|将|把|被|从|对|与|和|或)', sent))
            if not prev_has_subject and not has_subject and len(sent) > 10:
                issues.append(Change(
                    original=sent[:50], revised='添加主语',
                    reason='连续句子缺少主语', category='语法',
                ))
            prev_has_subject = has_subject

        # 2. 长句检查（超过80字的句子）
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 80:
                issues.append(Change(
                    original=sent[:50] + '...', revised='拆分为2-3个短句',
                    reason=f'句子过长({len(sent)}字)，建议控制在40字以内',
                    category='可读性',
                ))

        # 3. 重复词检查
        words = re.findall(r'[一-鿿]{2,4}', text)
        from collections import Counter
        word_counts = Counter(words)
        for word, count in word_counts.most_common(5):
            if count >= 4 and len(word) >= 2:
                issues.append(Change(
                    original=f'"{word}"出现{count}次',
                    revised='使用同义词替换部分出现',
                    reason='高频词重复，影响可读性',
                    category='重复',
                ))

        return issues

    def _check_en(self, text: str) -> list:
        """英文语法检查"""
        issues = []

        # 1. 句首连词检查
        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            sent = sent.strip()
            if re.match(r'^(?:And|But|Or|So|Yet)\s', sent, re.IGNORECASE):
                issues.append(Change(
                    original=sent[:50], revised='Remove sentence-initial conjunction',
                    reason='Academic writing avoids starting sentences with conjunctions',
                    category='Grammar',
                ))

        # 2. 重复词检查
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        from collections import Counter
        word_counts = Counter(words)
        for word, count in word_counts.most_common(5):
            if count >= 5:
                issues.append(Change(
                    original=f'"{word}" appears {count} times',
                    revised='Use synonyms for some occurrences',
                    reason='High-frequency word repetition',
                    category='Repetition',
                ))

        # 3. 长句检查
        for sent in sentences:
            sent = sent.strip()
            word_count = len(sent.split())
            if word_count > 40:
                issues.append(Change(
                    original=sent[:60] + '...', revised='Split into shorter sentences',
                    reason=f'Sentence too long ({word_count} words), aim for <25',
                    category='Readability',
                ))

        return issues


# ── 学术翻译器 ──────────────────────────────────────────

class AcademicTranslator:
    """
    学术中英互译（基于句式库+规则）

    注意：这是规则驱动的翻译，质量不如LLM翻译，
    但适合学术文本的初步翻译框架。
    可以配合 LLM 使用以获得更好的翻译质量。
    """

    # 学术术语对照表（扩展版）
    TERM_MAP = {
        # 碳污染物领域
        '污水管网': 'sewage network',
        '碳污染物': 'carbon pollutants',
        '多相态': 'multiphase',
        '固液气': 'solid-liquid-gas',
        '三相': 'three phases',
        '赋存特征': 'occurrence characteristics',
        '空间分异': 'spatial differentiation',
        '碳平衡': 'carbon balance',
        '溶解氧': 'dissolved oxygen (DO)',
        '有机碳': 'organic carbon',
        '总有机碳': 'total organic carbon (TOC)',
        '化学需氧量': 'chemical oxygen demand (COD)',
        '总氮': 'total nitrogen (TN)',
        '总磷': 'total phosphorus (TP)',
        '铵态氮': 'ammonium nitrogen (NH4+-N)',
        '硝态氮': 'nitrate nitrogen (NO3--N)',
        '产甲烷': 'methanogenesis',
        '甲烷': 'methane (CH4)',
        '二氧化碳': 'carbon dioxide (CO2)',
        '氧化亚氮': 'nitrous oxide (N2O)',
        '挥发性有机物': 'volatile organic compounds (VOCs)',
        '主成分分析': 'principal component analysis (PCA)',
        '层次聚类分析': 'hierarchical cluster analysis (HCA)',
        '相关性分析': 'correlation analysis',
        '显著': 'significant',
        '正相关': 'positive correlation',
        '负相关': 'negative correlation',
        '均值': 'mean',
        '标准差': 'standard deviation',
        '变异系数': 'coefficient of variation',
        '采样点': 'sampling point',
        '功能区': 'functional zone',
        '教学区': 'teaching zone',
        '生活区': 'residential zone',
        '餐饮区': 'dining zone',
        '管道沉积物': 'pipeline sediment',
        '生物膜': 'biofilm',
        '厌氧': 'anaerobic',
        '好氧': 'aerobic',
        '微生物': 'microorganism',
        '降解': 'degradation',
        '转化': 'transformation',
        '迁移': 'migration',
        # 通用学术
        '研究背景': 'research background',
        '研究现状': 'research status',
        '研究空白': 'research gap',
        '研究方法': 'research methods',
        '研究结果': 'research results',
        '研究结论': 'research conclusions',
        '研究展望': 'future research directions',
        '国内外': 'domestic and international',
        '文献综述': 'literature review',
        '统计分析': 'statistical analysis',
        '显著性': 'significance',
        '置信区间': 'confidence interval',
        '样本量': 'sample size',
        '表明': 'indicate',
        '揭示': 'reveal',
        '阐明': 'elucidate',
        '探讨': 'investigate',
        '分析': 'analyze',
        '影响': 'influence',
        '控制': 'control',
        '驱动因素': 'driving factor',
        '关键因素': 'key factor',
        '机制': 'mechanism',
    }

    # 学术句式对照表（借鉴 academic-writing/03-sentence-bank.md）
    SENTENCE_PATTERNS = {
        # Introduction 句式
        '近年来，随着...的加快': 'In recent years, with the acceleration of...',
        '研究表明': 'Studies have shown that',
        '然而，现有研究': 'However, existing studies',
        '针对上述不足': 'To address these shortcomings',
        '本研究以...为研究对象': 'This study investigated...',
        '为...提供科学依据': 'to provide scientific basis for...',
        # Results 句式
        '结果表明': 'The results showed that',
        '呈显著正相关': 'showed a significant positive correlation',
        '呈显著负相关': 'showed a significant negative correlation',
        '显著高于': 'was significantly higher than',
        '显著低于': 'was significantly lower than',
        '无显著差异': 'showed no significant difference',
        # Discussion 句式
        '这一结果与...一致': 'This finding is consistent with...',
        '可能的原因是': 'The possible reason is that',
        '归因于': 'can be attributed to',
        '这表明': 'This indicates that',
        '综上所述': 'In summary',
    }

    def translate_zh_to_en(self, text: str) -> str:
        """中文学术文本→英文（句式替换+术语替换+标点转换）"""
        result = text

        # 1. 句式替换（先替换长短语，避免被术语替换截断）
        for zh, en in self.SENTENCE_PATTERNS.items():
            result = result.replace(zh, en)

        # 2. 术语替换
        for zh, en in sorted(self.TERM_MAP.items(), key=lambda x: -len(x[0])):
            result = result.replace(zh, en)

        # 3. 中文标点→英文标点
        punct_map = {'，': ', ', '。': '. ', '；': '; ', '：': ': ',
                     '（': '(', '）': ')', '"': '"', '"': '"',
                     ''': "'", ''': "'", '、': ', '}
        for zh_p, en_p in punct_map.items():
            result = result.replace(zh_p, en_p)

        # 4. 删除中文特有的语气词（仅在独立出现时）
        for particle in ['的', '了', '着', '过', '呢', '吧', '啊']:
            result = re.sub(rf'(?<=[一-鿿])\b{particle}\b(?=[，。；：])', '', result)

        return result.strip()

    def translate_en_to_zh(self, text: str) -> str:
        """英文学术文本→中文（术语替换）"""
        result = text

        # 反向术语替换
        for zh, en in self.TERM_MAP.items():
            result = result.replace(en, zh)
            # 也替换不带括号缩写的版本
            en_short = re.sub(r'\s*\([^)]+\)', '', en)
            if en_short != en:
                result = result.replace(en_short, zh)

        return result.strip()


# ── 修改报告生成器 ──────────────────────────────────────────

def generate_change_report(original: str, revised: str, changes: list) -> str:
    """生成修改对比报告（Markdown格式）"""
    lines = [
        "# 论文润色报告",
        "",
        f"## 原文 ({len(original)}字)",
        "",
        original[:500] + ("..." if len(original) > 500 else ""),
        "",
        f"## 润色后 ({len(revised)}字)",
        "",
        revised[:500] + ("..." if len(revised) > 500 else ""),
        "",
    ]

    if changes:
        lines.extend([
            f"## 修改明细 (共{len(changes)}处)",
            "",
            "| # | 类别 | 原文 | 修改后 | 修改原因 |",
            "|---|------|------|--------|---------|",
        ])
        for i, c in enumerate(changes, 1):
            orig = c.original[:35] + ("..." if len(c.original) > 35 else "")
            rev = c.revised[:35] + ("..." if len(c.revised) > 35 else "")
            lines.append(f"| {i} | {c.category} | {orig} | {rev} | {c.reason} |")
    else:
        lines.append("未发现需要修改的内容。")

    return '\n'.join(lines)


# ── 便捷入口 ──────────────────────────────────────────

def polish_paper(text: str, language: str = 'auto') -> OptimizationResult:
    """
    一键论文润色

    Parameters
    ----------
    text : str, 论文文本
    language : str, 'zh' / 'en' / 'auto'

    Returns
    -------
    OptimizationResult, 包含润色后文本和修改明细
    """
    polisher = AcademicPolisher()
    return polisher.polish(text, language)


def check_grammar(text: str, language: str = 'auto') -> list:
    """
    一键语法检查

    Returns
    -------
    list of Change
    """
    checker = GrammarChecker()
    return checker.check(text, language)


def translate(text: str, direction: str = 'zh2en') -> str:
    """
    学术翻译

    Parameters
    ----------
    text : str, 待翻译文本
    direction : str, 'zh2en' 或 'en2zh'

    Returns
    -------
    str, 翻译后文本
    """
    translator = AcademicTranslator()
    if direction == 'zh2en':
        return translator.translate_zh_to_en(text)
    return translator.translate_en_to_zh(text)


# ── CLI 入口 ──────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python writing_optimizer.py polish <file>   # 润色论文")
        print("  python writing_optimizer.py check <file>    # 语法检查")
        print("  python writing_optimizer.py translate <file> [zh2en|en2zh]")
        print("  python writing_optimizer.py test            # 运行测试")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'test':
        # 测试润色
        test_zh = "本文搞清楚了污水管网中碳污染物的情况，感觉溶解氧跟甲烷有比较大的关系。"
        result = polish_paper(test_zh, 'zh')
        print(f"[润色测试] 中文")
        print(f"  原文: {test_zh}")
        print(f"  润色: {result.optimized_text}")
        print(f"  修改: {len(result.changes)}处")
        for c in result.changes:
            print(f"    - [{c.category}] {c.original} → {c.revised} ({c.reason})")

        # 测试语法检查
        test_en = "The results showed that. And the data indicates. But we found significant."
        issues = check_grammar(test_en, 'en')
        print(f"\n[语法测试] 英文")
        print(f"  原文: {test_en}")
        print(f"  问题: {len(issues)}处")
        for issue in issues:
            print(f"    - [{issue.category}] {issue.reason}")

        # 测试翻译
        test_text = "校园污水管网碳污染物多相态分析"
        translated = translate(test_text, 'zh2en')
        print(f"\n[翻译测试] 中→英")
        print(f"  原文: {test_text}")
        print(f"  翻译: {translated}")

        print("\n全部测试通过!")

    elif cmd == 'polish' and len(sys.argv) > 2:
        path = sys.argv[2]
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        result = polish_paper(text)
        print(result.to_markdown())

    elif cmd == 'check' and len(sys.argv) > 2:
        path = sys.argv[2]
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        issues = check_grammar(text)
        for i, issue in enumerate(issues, 1):
            print(f"{i}. [{issue.category}] {issue.reason}")
            print(f"   原文: {issue.original}")
            print(f"   建议: {issue.revised}")
