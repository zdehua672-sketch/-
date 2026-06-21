# -*- coding: utf-8 -*-
"""
=============================================================================
AI痕迹增强检测模块 - AI Trace Enhanced Detection
=============================================================================

检测AI生成论文的四大特征：
1. 通篇长句多，缺长短句穿插
2. 爱用双引号标概念
3. 习惯括号补充结果
4. 分层刻板模板化

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


# ============================================================================
# 第一部分：数据结构
# ============================================================================

class IssueLevel(Enum):
    """问题级别"""
    CRITICAL = 'CRITICAL'  # 致命问题
    MAJOR = 'MAJOR'        # 重大问题
    MINOR = 'MINOR'        # 小问题
    INFO = 'INFO'          # 提示信息


@dataclass
class TraceIssue:
    """AI痕迹问题"""
    feature: str           # 特征类型（长句/引号/括号/模板化）
    level: IssueLevel      # 问题级别
    location: str          # 位置描述
    problem: str           # 问题描述
    original: str          # 原文片段
    suggestion: str        # 修改建议
    auto_fix: str = ''     # 自动修复文本


@dataclass
class TraceReport:
    """AI痕迹检测报告"""
    issues: List[TraceIssue] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> Dict:
        """生成摘要"""
        by_feature = Counter(issue.feature for issue in self.issues)
        by_level = Counter(issue.level.value for issue in self.issues)
        return {
            'total': len(self.issues),
            'by_feature': dict(by_feature),
            'by_level': dict(by_level),
            'scores': self.scores,
        }


# ============================================================================
# 第二部分：句长分析器
# ============================================================================

class SentenceLengthAnalyzer:
    """
    句长分析器

    检测：
    1. 长句过多（>40字）
    2. 连续长句（3句以上）
    3. 句长分布不均匀
    4. 缺少短句穿插
    """

    # 阈值配置（针对中文学术论文优化）
    LONG_SENTENCE_THRESHOLD = 50      # 长句阈值（字）- 中文学术论文句子通常较长
    VERY_LONG_SENTENCE_THRESHOLD = 80 # 超长句阈值（字）- 中文允许更长的句子
    CONSECUTIVE_LONG_THRESHOLD = 4    # 连续长句阈值（句）
    SHORT_SENTENCE_RATIO_MIN = 0.15   # 短句比例下限 - 中文学术论文短句比例通常较低

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """分句（支持中文）"""
        # 按句号、问号、感叹号分句
        sentences = re.split(r'[。！？!?]', text)
        # 过滤空句
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    @staticmethod
    def get_sentence_length(sentence: str) -> int:
        """获取句子长度（去除空格和标点）"""
        # 去除空格和标点
        clean = re.sub(r'[，,；;：:（）()\[\]【】""\'\"\-—]', '', sentence)
        return len(clean)

    @classmethod
    def analyze(cls, text: str) -> Tuple[List[TraceIssue], Dict[str, float]]:
        """
        分析句长

        Returns
        -------
        issues : list of TraceIssue
        scores : dict, 评分
        """
        issues = []
        sentences = cls.split_sentences(text)

        if len(sentences) < 5:
            return issues, {'sentence_length_score': 100}

        # 统计句长
        lengths = [cls.get_sentence_length(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        long_count = sum(1 for l in lengths if l > cls.LONG_SENTENCE_THRESHOLD)
        very_long_count = sum(1 for l in lengths if l > cls.VERY_LONG_SENTENCE_THRESHOLD)
        short_count = sum(1 for l in lengths if l < 20)

        long_ratio = long_count / len(sentences)
        short_ratio = short_count / len(sentences)

        # 检测1: 长句过多
        if long_ratio > 0.5:
            issues.append(TraceIssue(
                feature='长句',
                level=IssueLevel.MAJOR,
                location=f'全文{len(sentences)}句',
                problem=f'长句比例过高（{long_ratio:.0%}），平均句长{avg_length:.0f}字',
                original=f'长句(>{cls.LONG_SENTENCE_THRESHOLD}字): {long_count}句, 超长句(>{cls.VERY_LONG_SENTENCE_THRESHOLD}字): {very_long_count}句',
                suggestion='将长句拆分为短句，使用长短句交替。建议：\n'
                          '1. 在逗号处拆分长句\n'
                          '2. 将并列结构拆为独立句\n'
                          '3. 每3-4个长句后插入1个短句',
            ))

        # 检测2: 超长句
        for i, (sentence, length) in enumerate(zip(sentences, lengths)):
            if length > cls.VERY_LONG_SENTENCE_THRESHOLD:
                # 找到可以拆分的位置（逗号）
                split_points = [m.start() for m in re.finditer(r'[，,]', sentence)]
                if split_points:
                    mid = split_points[len(split_points) // 2]
                    part1 = sentence[:mid+1].strip()
                    part2 = sentence[mid+1:].strip()
                    auto_fix = f'{part1}。{part2}'
                else:
                    auto_fix = ''

                issues.append(TraceIssue(
                    feature='长句',
                    level=IssueLevel.MINOR,
                    location=f'第{i+1}句',
                    problem=f'超长句（{length}字）',
                    original=sentence[:80] + '...' if len(sentence) > 80 else sentence,
                    suggestion='在逗号处拆分为两个短句',
                    auto_fix=auto_fix,
                ))

        # 检测3: 连续长句
        consecutive_long = 0
        consecutive_start = -1
        for i, length in enumerate(lengths):
            if length > cls.LONG_SENTENCE_THRESHOLD:
                if consecutive_long == 0:
                    consecutive_start = i
                consecutive_long += 1
            else:
                if consecutive_long >= cls.CONSECUTIVE_LONG_THRESHOLD:
                    issues.append(TraceIssue(
                        feature='长句',
                        level=IssueLevel.MAJOR,
                        location=f'第{consecutive_start+1}-{consecutive_start+consecutive_long}句',
                        problem=f'连续{consecutive_long}个长句，缺乏节奏感',
                        original=sentences[consecutive_start][:50] + '...',
                        suggestion='在连续长句中插入1-2个短句（<20字），形成长短交替',
                    ))
                consecutive_long = 0

        # 检测4: 短句过少
        if short_ratio < cls.SHORT_SENTENCE_RATIO_MIN and len(sentences) > 10:
            issues.append(TraceIssue(
                feature='长句',
                level=IssueLevel.MINOR,
                location=f'全文{len(sentences)}句',
                problem=f'短句比例过低（{short_ratio:.0%}），缺乏节奏变化',
                original=f'短句(<20字): {short_count}句, 占比{short_ratio:.0%}',
                suggestion='增加短句使用，建议每3-4个长句后插入1个短句',
            ))

        # 计算评分
        score = 100
        score -= long_ratio * 30  # 长句比例影响
        score -= very_long_count * 5  # 超长句影响
        score -= len([i for i in issues if i.feature == '长句']) * 10
        score = max(0, min(100, score))

        return issues, {'sentence_length_score': score}


# ============================================================================
# 第三部分：引号检测器
# ============================================================================

class QuoteDetector:
    """
    引号检测器

    检测：
    1. 双引号过多
    2. 不必要的引号（概念已普及）
    3. 引号内格式不统一
    """

    # 常见不需要引号的概念（已普及）
    COMMON_CONCEPTS = {
        '温室效应', '碳中和', '碳达峰', '可持续发展',
        '污水处理', '管网', '甲烷', '二氧化碳',
        '相关性', '显著性', 'p值', '回归分析',
        '主成分分析', '聚类分析', 'PCA', 'HCA',
        'greenhouse effect', 'carbon neutral', 'sustainability',
        'sewage treatment', 'correlation', 'significance',
    }

    @classmethod
    def analyze(cls, text: str) -> Tuple[List[TraceIssue], Dict[str, float]]:
        """
        分析引号使用

        Returns
        -------
        issues : list of TraceIssue
        scores : dict, 评分
        """
        issues = []

        # 统计双引号
        chinese_quotes = re.findall(r'[""]([^""]+)[""]', text)
        english_quotes = re.findall(r'"([^"]+)"', text)
        all_quotes = chinese_quotes + english_quotes

        quote_count = len(all_quotes)
        text_length = len(text)
        quote_density = quote_count / (text_length / 1000) if text_length > 0 else 0

        # 检测1: 引号过多
        if quote_density > 5:  # 每1000字超过5个引号
            issues.append(TraceIssue(
                feature='引号',
                level=IssueLevel.MAJOR,
                location=f'全文{quote_count}处引号',
                problem=f'引号密度过高（{quote_density:.1f}/千字），AI论文特征',
                original=f'检测到{quote_count}处双引号',
                suggestion='减少引号使用，建议：\n'
                          '1. 删除已普及概念的引号（如"温室效应"）\n'
                          '2. 将引号内容改为直接陈述\n'
                          '3. 仅在首次定义新概念时使用引号',
            ))

        # 检测2: 不必要的引号
        unnecessary_quotes = []
        for quote in all_quotes:
            quote_clean = quote.strip()
            if quote_clean in cls.COMMON_CONCEPTS:
                unnecessary_quotes.append(quote_clean)

        if unnecessary_quotes:
            issues.append(TraceIssue(
                feature='引号',
                level=IssueLevel.MINOR,
                location=f'{len(unnecessary_quotes)}处',
                problem=f'常见概念不需要引号',
                original=', '.join(unnecessary_quotes[:5]),
                suggestion='删除这些概念的引号，它们已经是学术界通用术语',
            ))

        # 检测3: 连续引号
        consecutive_quotes = re.findall(r'[""][^""]*[""].*?[""][^""]*[""]', text)
        if len(consecutive_quotes) > 3:
            issues.append(TraceIssue(
                feature='引号',
                level=IssueLevel.MINOR,
                location=f'{len(consecutive_quotes)}处连续引号',
                problem='连续使用引号，读起来像AI生成',
                original=consecutive_quotes[0][:80] if consecutive_quotes else '',
                suggestion='将部分引号内容改为直接陈述，减少引号密度',
            ))

        # 计算评分
        score = 100
        score -= quote_density * 10  # 引号密度影响
        score -= len(unnecessary_quotes) * 5  # 不必要引号影响
        score = max(0, min(100, score))

        return issues, {'quote_score': score}


# ============================================================================
# 第四部分：括号优化器
# ============================================================================

class ParenOptimizer:
    """
    括号优化器

    检测：
    1. 括号过多
    2. 括号内格式不统一
    3. 括号内容可以改为独立句子
    """

    @classmethod
    def analyze(cls, text: str) -> Tuple[List[TraceIssue], Dict[str, float]]:
        """
        分析括号使用

        Returns
        -------
        issues : list of TraceIssue
        scores : dict, 评分
        """
        issues = []

        # 统计括号
        chinese_parens = re.findall(r'（[^）]+）', text)
        english_parens = re.findall(r'\([^)]+\)', text)
        all_parens = chinese_parens + english_parens

        # 过滤文献引用格式的括号（如 (Author et al., Year) 或 (Year)）
        citation_patterns = [
            r'\([A-Z][a-z]+(?:\s+(?:et\s+al|and|[A-Z][a-z]+))*(?:\s+等)?,?\s*\d{4}\)',
            r'\(\d{4}\)',
            r'\([A-Z][a-z]+(?:\s+(?:et\s+al|and|[A-Z][a-z]+))*(?:\s+等)?,?\s*\d{4}(?:\s*;\s*[A-Z][a-z]+(?:\s+(?:et\s+al|and|[A-Z][a-z]+))*(?:\s+等)?,?\s*\d{4})*\)',
            r'（[^）]*\d{4}[^）]*）',  # 中文括号内的年份引用
        ]

        non_citation_parens = []
        for paren in all_parens:
            is_citation = False
            for pattern in citation_patterns:
                if re.match(pattern, paren):
                    is_citation = True
                    break
            if not is_citation:
                non_citation_parens.append(paren)

        paren_count = len(non_citation_parens)
        text_length = len(text)
        paren_density = paren_count / (text_length / 1000) if text_length > 0 else 0

        # 检测1: 括号过多（针对中文学术论文优化）
        # 中文学术论文中括号常用于标注英文术语、统计值、参考文献等
        if paren_density > 15:  # 每1000字超过15个括号（中文学术论文阈值更宽松）
            issues.append(TraceIssue(
                feature='括号',
                level=IssueLevel.MAJOR,
                location=f'全文{paren_count}处括号',
                problem=f'括号密度过高（{paren_density:.1f}/千字），AI论文特征',
                original=f'检测到{paren_count}处括号',
                suggestion='减少括号使用，建议：\n'
                          '1. 将括号内的补充说明改为独立句子\n'
                          '2. 将括号内的数据改为正文描述\n'
                          '3. 仅在必要时使用括号（如公式、缩写定义）',
            ))

        # 检测2: 括号内包含完整句子
        full_sentence_parens = []
        for paren in all_parens:
            content = paren[1:-1] if paren.startswith('(') or paren.startswith('（') else paren[1:-1]
            # 检查是否是完整句子（包含主谓宾）
            if len(content) > 20 and re.search(r'[，,].*[是为]', content):
                full_sentence_parens.append(paren)

        if full_sentence_parens:
            issues.append(TraceIssue(
                feature='括号',
                level=IssueLevel.MINOR,
                location=f'{len(full_sentence_parens)}处',
                problem='括号内包含完整句子，应改为正文',
                original=full_sentence_parens[0][:60] if full_sentence_parens else '',
                suggestion='将括号内的完整句子移到正文中，用句号分隔',
            ))

        # 检测3: 连续括号
        consecutive_parens = re.findall(r'[（(][^）)]*[）)].*?[（(][^）)]*[）)]', text)
        if len(consecutive_parens) > 5:
            issues.append(TraceIssue(
                feature='括号',
                level=IssueLevel.MINOR,
                location=f'{len(consecutive_parens)}处连续括号',
                problem='连续使用括号，读起来像AI生成',
                original=consecutive_parens[0][:80] if consecutive_parens else '',
                suggestion='将部分括号内容改为独立句子，减少括号密度',
            ))

        # 检测4: 括号内格式不统一
        has_chinese = any(p.startswith('（') for p in all_parens)
        has_english = any(p.startswith('(') for p in all_parens)
        if has_chinese and has_english:
            issues.append(TraceIssue(
                feature='括号',
                level=IssueLevel.INFO,
                location='全文',
                problem='中英文括号混用',
                original='同时使用（）和()',
                suggestion='统一使用中文括号（）或英文括号()，建议学术论文使用()',
            ))

        # 计算评分
        score = 100
        score -= paren_density * 8  # 括号密度影响
        score -= len(full_sentence_parens) * 5  # 完整句子括号影响
        score = max(0, min(100, score))

        return issues, {'paren_score': score}


# ============================================================================
# 第五部分：结构模板检测器
# ============================================================================

class StructureDetector:
    """
    结构模板检测器

    检测：
    1. 分层刻板（首先/其次/最后）
    2. 段落模式单一（主题句+论据+总结）
    3. 过渡句模板化
    4. 结论句模板化
    """

    # 刻板分层模式
    RIGID_PATTERNS = [
        # 中文
        r'首先[，,].*?其次[，,].*?最后',
        r'第一[，,].*?第二[，,].*?第三',
        r'一方面.*?另一方面',
        r'不仅.*?而且',
        r'一方面.*?同时',
        r'首先.*?然后.*?最后',
        # 英文
        r'First[,.].*?Second[,.].*?Third',
        r'First[,.]*?Then[,.]*?Finally',
        r'On the one hand.*?on the other hand',
        r'Not only.*?but also',
    ]

    # 模板化过渡句
    TEMPLATE_TRANSITIONS = [
        # 中文
        r'综上所述',
        r'总而言之',
        r'总的来说',
        r'简而言之',
        r'基于上述分析',
        r'由此可见',
        r'因此[，,]',
        r'鉴于此',
        # 英文
        r'In conclusion',
        r'To summarize',
        r'In summary',
        r'Based on the above analysis',
        r'Therefore[,.]',
        r'Hence[,.]',
        r'Consequently[,.]',
    ]

    # 模板化结论句
    TEMPLATE_CONCLUSIONS = [
        r'(?:本|该)(?:研究|发现).*(?:具有|有着?).*?(?:重要|深远|重大).*?(?:意义|价值)',
        r'(?:为).*(?:提供|奠定).*?(?:基础|依据|参考)',
        r'(?:填补|弥补).*?(?:了?).*?(?:研究)?空白',
        r'(?:首次|开创性).*?(?:发现|提出|证明)',
        r'(?:丰富|完善).*?(?:了?).*?(?:相关|该领域的?).*?(?:理论|研究)',
    ]

    @classmethod
    def analyze(cls, text: str) -> Tuple[List[TraceIssue], Dict[str, float]]:
        """
        分析结构模板化

        Returns
        -------
        issues : list of TraceIssue
        scores : dict, 评分
        """
        issues = []

        # 检测1: 刻板分层模式
        for pattern in cls.RIGID_PATTERNS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for m in matches[:2]:  # 只报告前2个
                context = text[max(0, m.start()-20):m.end()+20]
                issues.append(TraceIssue(
                    feature='模板化',
                    level=IssueLevel.MAJOR,
                    location=f'位置{m.start()}',
                    problem='使用刻板分层模式（首先/其次/最后）',
                    original=context[:80],
                    suggestion='打破刻板分层，建议：\n'
                              '1. 使用更自然的过渡（如"值得注意的是"）\n'
                              '2. 将并列结构改为递进结构\n'
                              '3. 使用数据或案例驱动的过渡',
                ))

        # 检测2: 模板化过渡句
        template_transition_count = 0
        for pattern in cls.TEMPLATE_TRANSITIONS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            template_transition_count += len(matches)
            for m in matches[:1]:  # 只报告前1个
                context = text[max(0, m.start()-10):m.end()+10]
                issues.append(TraceIssue(
                    feature='模板化',
                    level=IssueLevel.MINOR,
                    location=f'位置{m.start()}',
                    problem='使用模板化过渡句',
                    original=context[:60],
                    suggestion='使用更自然的过渡，避免"综上所述"等套话',
                ))

        # 检测3: 模板化结论句
        template_conclusion_count = 0
        for pattern in cls.TEMPLATE_CONCLUSIONS:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            template_conclusion_count += len(matches)
            for m in matches[:1]:
                context = text[max(0, m.start()-10):m.end()+10]
                issues.append(TraceIssue(
                    feature='模板化',
                    level=IssueLevel.MINOR,
                    location=f'位置{m.start()}',
                    problem='使用模板化结论句',
                    original=context[:60],
                    suggestion='用具体数据替代空洞表述，如"具有重要意义"改为"降低了30%"',
                ))

        # 检测4: 段落模式单一
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 5:
            # 检查段落开头模式
            starts = []
            for p in paragraphs:
                p = p.strip()
                if len(p) > 20:
                    starts.append(p[:20])

            # 统计开头重复
            start_counts = Counter(starts)
            repeated = [(k, v) for k, v in start_counts.items() if v >= 3]
            for pattern, count in repeated[:2]:
                issues.append(TraceIssue(
                    feature='模板化',
                    level=IssueLevel.MINOR,
                    location=f'{count}个段落',
                    problem=f'段落开头重复{count}次',
                    original=pattern,
                    suggestion='变换段落开头，避免模式化。交替使用：\n'
                              '- 数据开头（如"CO₂浓度..."）\n'
                              '- 方法开头（如"通过分析..."）\n'
                              '- 结论开头（如"结果表明..."）',
                ))

        # 计算评分
        score = 100
        score -= template_transition_count * 8  # 模板过渡句影响
        score -= template_conclusion_count * 10  # 模板结论句影响
        score -= len([i for i in issues if i.feature == '模板化']) * 5
        score = max(0, min(100, score))

        return issues, {'structure_score': score}


# ============================================================================
# 第六部分：综合检测器
# ============================================================================

class AITraceEnhancedDetector:
    """
    AI痕迹增强检测器

    综合检测四大特征：
    1. 长句多
    2. 引号多
    3. 括号多
    4. 模板化
    """

    @staticmethod
    def detect(text: str) -> TraceReport:
        """
        综合检测AI痕迹

        Parameters
        ----------
        text : str, 论文文本

        Returns
        -------
        TraceReport : 检测报告
        """
        all_issues = []
        all_scores = {}

        # 1. 句长分析
        issues, scores = SentenceLengthAnalyzer.analyze(text)
        all_issues.extend(issues)
        all_scores.update(scores)

        # 2. 引号检测
        issues, scores = QuoteDetector.analyze(text)
        all_issues.extend(issues)
        all_scores.update(scores)

        # 3. 括号优化
        issues, scores = ParenOptimizer.analyze(text)
        all_issues.extend(issues)
        all_scores.update(scores)

        # 4. 结构模板检测
        issues, scores = StructureDetector.analyze(text)
        all_issues.extend(issues)
        all_scores.update(scores)

        # 计算综合评分
        total_score = sum(all_scores.values()) / len(all_scores) if all_scores else 100
        all_scores['total_score'] = total_score

        return TraceReport(issues=all_issues, scores=all_scores)

    @staticmethod
    def auto_fix(text: str) -> Tuple[str, List[str]]:
        """
        自动修复AI痕迹

        Parameters
        ----------
        text : str, 论文文本

        Returns
        -------
        fixed_text : str, 修复后的文本
        fixes : list of str, 修复记录
        """
        fixed_text = text
        fixes = []

        # 1. 修复超长句（在逗号处拆分）
        sentences = SentenceLengthAnalyzer.split_sentences(fixed_text)
        for sentence in sentences:
            if SentenceLengthAnalyzer.get_sentence_length(sentence) > 60:
                # 找到中间的逗号
                split_points = [m.start() for m in re.finditer(r'[，,]', sentence)]
                if split_points:
                    mid = split_points[len(split_points) // 2]
                    part1 = sentence[:mid+1].strip()
                    part2 = sentence[mid+1:].strip()
                    if part1 and part2:
                        old = sentence
                        new = f'{part1}。{part2}'
                        fixed_text = fixed_text.replace(old, new)
                        fixes.append(f'拆分超长句: {old[:30]}...')

        # 2. 删除不必要的引号
        for concept in QuoteDetector.COMMON_CONCEPTS:
            if f'"{concept}"' in fixed_text:
                fixed_text = fixed_text.replace(f'"{concept}"', concept)
                fixes.append(f'删除不必要引号: "{concept}"')
            if f'" {concept}"' in fixed_text:
                fixed_text = fixed_text.replace(f'" {concept}"', concept)
                fixes.append(f'删除不必要引号: "{concept}"')

        # 3. 替换模板化表达
        template_replacements = [
            ('综上所述，', ''),
            ('总而言之，', ''),
            ('总的来说，', ''),
            ('简而言之，', ''),
            ('值得注意的是，', ''),
            ('需要指出的是，', ''),
        ]
        for old, new in template_replacements:
            if old in fixed_text:
                fixed_text = fixed_text.replace(old, new)
                fixes.append(f'删除模板化表达: {old}')

        return fixed_text, fixes


# ============================================================================
# 第七部分：便捷函数
# ============================================================================

def detect_ai_trace(text: str) -> TraceReport:
    """检测AI痕迹"""
    return AITraceEnhancedDetector.detect(text)


def fix_ai_trace(text: str) -> Tuple[str, List[str]]:
    """修复AI痕迹"""
    return AITraceEnhancedDetector.auto_fix(text)


# ============================================================================
# 第八部分：测试
# ============================================================================

if __name__ == '__main__':
    # 测试文本
    test_text = '''
    本研究以校园污水管网为对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。
    值得注意的是，研究发现CH₄与固相有机碳呈显著正相关（r=0.647，p=0.004），这一结果直接证实管壁沉积有机碳的厌氧矿化是管网CH₄产生的关键来源。
    综上所述，本研究具有重要的理论意义和实践价值。
    首先，碳污染物呈现显著的季节分异；其次，变量间存在多组显著关联；最后，上述发现为校园污水管网碳排放核算提供了数据支撑。
    '''

    print('=== AI痕迹增强检测测试 ===')
    print()

    report = detect_ai_trace(test_text)

    print(f'检测结果: {report.summary()}')
    print()

    for issue in report.issues:
        print(f'[{issue.level.value}] {issue.feature}: {issue.problem}')
        print(f'  原文: {issue.original[:50]}...')
        print(f'  建议: {issue.suggestion[:50]}...')
        print()

    print('=== 自动修复测试 ===')
    print()

    fixed_text, fixes = fix_ai_trace(test_text)
    print(f'修复记录: {len(fixes)}项')
    for fix in fixes:
        print(f'  - {fix}')
