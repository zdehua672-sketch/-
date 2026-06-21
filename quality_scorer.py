# -*- coding: utf-8 -*-
"""
=============================================================================
文本质量评分器 - Quality Scorer
=============================================================================

为学术文本提供多维度质量评分：
1. 引用一致性 - 引用是否在参考文献中存在
2. 信息覆盖度 - 关键信息是否被覆盖
3. 语言质量 - 句式多样性、长度分布
4. 学术规范 - 是否符合学术写作规范

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import Counter


@dataclass
class QualityScore:
    """质量评分结果"""
    total: float = 0.0              # 总分（0-100）
    citation_score: float = 0.0     # 引用一致性分数（0-100）
    coverage_score: float = 0.0     # 信息覆盖度分数（0-100）
    language_score: float = 0.0     # 语言质量分数（0-100）
    academic_score: float = 0.0     # 学术规范分数（0-100）
    details: Dict = field(default_factory=dict)  # 详细评分信息

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 1),
            'citation': round(self.citation_score, 1),
            'coverage': round(self.coverage_score, 1),
            'language': round(self.language_score, 1),
            'academic': round(self.academic_score, 1),
            'details': self.details,
        }


class QualityScorer:
    """
    文本质量评分器

    用法:
        scorer = QualityScorer()
        score = scorer.score(text, findings=findings, references=refs)
        print(score.total)  # 总分
    """

    def __init__(self, config=None):
        """
        初始化评分器

        Parameters
        ----------
        config : WritingQualityConfig or None
            质量控制配置，None 时使用默认配置
        """
        if config:
            self.config = config
        else:
            from domain_config import WritingQualityConfig
            self.config = WritingQualityConfig()

    def score(self, text: str, findings: List[Dict] = None,
              references: List[str] = None, section_type: str = 'general') -> QualityScore:
        """
        计算文本质量分数

        Parameters
        ----------
        text : str, 待评估文本
        findings : list of dict, 数据发现列表
        references : list of str, 参考文献列表
        section_type : str, 章节类型（introduction/methods/results/discussion/conclusion）

        Returns
        -------
        QualityScore : 质量评分结果
        """
        result = QualityScore()

        # 1. 引用一致性分数
        result.citation_score = self._score_citation_consistency(text, references)

        # 2. 信息覆盖度分数
        result.coverage_score = self._score_information_coverage(text, findings)

        # 3. 语言质量分数
        result.language_score = self._score_language_quality(text)

        # 4. 学术规范分数
        result.academic_score = self._score_academic_norms(text, section_type)

        # 计算总分（加权平均）
        weights = {
            'citation': 0.25,
            'coverage': 0.30,
            'language': 0.25,
            'academic': 0.20,
        }
        result.total = (
            result.citation_score * weights['citation'] +
            result.coverage_score * weights['coverage'] +
            result.language_score * weights['language'] +
            result.academic_score * weights['academic']
        )

        return result

    def _score_citation_consistency(self, text: str, references: List[str] = None) -> float:
        """
        评分引用一致性

        检查：
        1. 正文中的引用是否在参考文献列表中存在
        2. 引用格式是否正确
        3. 引用数量是否充足
        """
        score = 50.0  # 基础分

        # 提取正文中的引用
        numeric_refs = set(re.findall(r'\[(\d+)\]', text))
        author_year_refs = set(re.findall(r'\([A-Z][a-z]+(?:\s+et\s+al)?,?\s*\d{4}\)', text))

        total_citations = len(numeric_refs) + len(author_year_refs)

        # 引用数量评分
        if total_citations >= 10:
            score += 30
        elif total_citations >= 5:
            score += 20
        elif total_citations >= 1:
            score += 10

        # 如果有参考文献列表，检查一致性
        if references:
            # 检查数字引用是否在参考文献范围内
            max_ref_num = len(references)
            orphan_refs = [int(r) for r in numeric_refs if int(r) > max_ref_num]
            if not orphan_refs:
                score += 20
            else:
                score -= len(orphan_refs) * 5

        return min(100.0, max(0.0, score))

    def _score_information_coverage(self, text: str, findings: List[Dict] = None) -> float:
        """
        评分信息覆盖度

        检查：
        1. 关键发现是否被提及
        2. 数据是否被引用
        3. 结论是否有支撑
        """
        if not findings:
            return 50.0  # 无发现时返回中等分数

        score = 0.0
        covered_count = 0

        for finding in findings:
            # 检查发现是否被提及
            finding_text = finding.get('text', '') or finding.get('description', '')
            if not finding_text:
                continue

            # 提取关键词
            keywords = self._extract_keywords(finding_text)
            if any(kw in text for kw in keywords):
                covered_count += 1

        # 覆盖率评分
        coverage_rate = covered_count / len(findings) if findings else 0
        score = coverage_rate * 100

        return min(100.0, max(0.0, score))

    def _score_language_quality(self, text: str) -> float:
        """
        评分语言质量

        检查：
        1. 句式多样性
        2. 句子长度分布
        3. 段落结构
        4. 连接词使用
        """
        score = 50.0  # 基础分

        # 分句
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return 30.0  # 句子太少

        # 1. 句式多样性（检查句首多样性）
        starts = [s[:10] for s in sentences if len(s) > 10]
        unique_starts = len(set(starts))
        if unique_starts >= len(starts) * 0.7:
            score += 15
        elif unique_starts >= len(starts) * 0.5:
            score += 10

        # 2. 句子长度分布
        lengths = [len(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        if 20 <= avg_length <= 60:
            score += 15
        elif 15 <= avg_length <= 80:
            score += 10

        # 3. 段落结构
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 3:
            score += 10

        # 4. 连接词使用
        connectors = ['因此', '然而', '此外', '同时', '另外', '首先', '其次', '最后',
                      'however', 'therefore', 'moreover', 'furthermore']
        connector_count = sum(1 for c in connectors if c in text.lower())
        if connector_count >= 3:
            score += 10
        elif connector_count >= 1:
            score += 5

        return min(100.0, max(0.0, score))

    def _score_academic_norms(self, text: str, section_type: str = 'general') -> float:
        """
        评分学术规范

        检查：
        1. 学术特征词
        2. 章节特定规范
        3. 避免口语化表达
        """
        score = 50.0  # 基础分

        # 1. 学术特征词
        academic_words = [
            '研究', '分析', '结果', '发现', '表明', '显示',
            '显著', '相关', '差异', '影响', '因素', '机制',
            '数据', '样本', '统计', '检验', '假设',
        ]
        academic_count = sum(1 for w in academic_words if w in text)
        if academic_count >= 8:
            score += 20
        elif academic_count >= 5:
            score += 15
        elif academic_count >= 3:
            score += 10

        # 2. 章节特定规范
        if section_type == 'introduction':
            # 引言应有研究背景、研究空白、研究目的
            if '背景' in text or '现状' in text:
                score += 5
            if '空白' in text or '不足' in text or 'gap' in text.lower():
                score += 5
            if '目的' in text or '目标' in text:
                score += 5
        elif section_type == 'results':
            # 结果应有数据支撑
            numbers = re.findall(r'\d+\.?\d*', text)
            if len(numbers) >= 5:
                score += 10
        elif section_type == 'discussion':
            # 讨论应有机制解释
            if '机制' in text or '原因' in text or '解释' in text:
                score += 10

        # 3. 避免口语化表达
        colloquial_words = ['其实', '然后', '就是', ' basically', ' actually']
        colloquial_count = sum(1 for w in colloquial_words if w in text.lower())
        score -= colloquial_count * 5

        return min(100.0, max(0.0, score))

    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """提取关键词"""
        # 简单的基于词频的关键词提取
        words = re.findall(r'[一-鿿]+|[a-zA-Z]+', text)
        word_counts = Counter(words)
        # 过滤停用词
        stopwords = {'的', '了', '在', '是', '和', '与', '对', '等', '中', '为'}
        keywords = [w for w, c in word_counts.most_common(top_n * 2) if w not in stopwords]
        return keywords[:top_n]


def select_best_candidate(candidates: List[str], scorer: QualityScorer,
                          findings: List[Dict] = None, references: List[str] = None,
                          section_type: str = 'general') -> Tuple[str, QualityScore]:
    """
    从多个候选中选择最佳文本

    Parameters
    ----------
    candidates : list of str, 候选文本列表
    scorer : QualityScorer, 评分器
    findings : list of dict, 数据发现
    references : list of str, 参考文献
    section_type : str, 章节类型

    Returns
    -------
    tuple : (最佳文本, 最佳分数)
    """
    if not candidates:
        return '', QualityScore()

    best_text = candidates[0]
    best_score = QualityScore()

    for candidate in candidates:
        score = scorer.score(candidate, findings, references, section_type)
        if score.total > best_score.total:
            best_text = candidate
            best_score = score

    return best_text, best_score


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    # 测试评分器
    scorer = QualityScorer()

    test_text = """
    本研究以某校园污水管网为研究对象，系统分析了固-液-气三相碳污染物的分布特征。
    结果表明，CH4浓度在冬季显著高于春季（p<0.05），而CO2浓度在不同季节间无显著差异。
    这一发现与Guisasola等（2008）的研究一致，证实了温度对产甲烷菌活性的影响。
    """

    score = scorer.score(test_text, section_type='results')
    print(f"总分: {score.total:.1f}")
    print(f"引用一致性: {score.citation_score:.1f}")
    print(f"信息覆盖度: {score.coverage_score:.1f}")
    print(f"语言质量: {score.language_score:.1f}")
    print(f"学术规范: {score.academic_score:.1f}")
