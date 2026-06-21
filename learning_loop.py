# -*- coding: utf-8 -*-
"""
=============================================================================
可回溯学习环路 - Learning Loop
=============================================================================

将高质量段落回写到记忆系统，实现持续学习：
1. 评估段落质量
2. 提取句式模式和机制知识
3. 回写到 KnowledgeStore
4. 版本化和置信度管理

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass
class LearnedPattern:
    """学到的模式"""
    pattern_type: str = ''             # 模式类型（sentence/discussion/mechanism）
    skeleton: str = ''                 # 句式骨架
    example: str = ''                  # 示例
    section_type: str = ''             # 关联章节
    confidence: float = 0.5            # 置信度
    source: str = ''                   # 来源


@dataclass
class LearningResult:
    """学习结果"""
    patterns_learned: int = 0          # 学到的模式数量
    mechanisms_learned: int = 0        # 学到的机制数量
    confidence_updates: int = 0        # 置信度更新数量

    def to_dict(self) -> Dict:
        return {
            'patterns_learned': self.patterns_learned,
            'mechanisms_learned': self.mechanisms_learned,
            'confidence_updates': self.confidence_updates,
        }


class LearningLoop:
    """
    可回溯学习环路

    用法:
        loop = LearningLoop(memory)
        result = loop.learn_from_accepted(section_type, text, quality_score)
    """

    # 句式骨架提取模式
    SKELETON_PATTERNS = [
        # "X与Y呈显著正/负相关"
        r'([\w]+)与([\w]+)呈(显著)?(正|负)相关',
        # "X显著高于/低于Y"
        r'([\w]+)显著(高于|低于)([\w]+)',
        # "X表明/显示/提示..."
        r'([\w]+)(表明|显示|提示|发现)',
        # "X可能与Y有关"
        r'([\w]+)可能与([\w]+)有关',
    ]

    # 机制提取模式
    MECHANISM_PATTERNS = [
        # "由于X，导致Y"
        r'由于([\w]+)，([\w]+)(导致|引起|造成)([\w]+)',
        # "X通过Y影响Z"
        r'([\w]+)通过([\w]+)(影响|作用于)([\w]+)',
        # "X是Y的原因"
        r'([\w]+)是([\w]+)的原因',
    ]

    def __init__(self, memory=None):
        """
        初始化学习环路

        Parameters
        ----------
        memory : KnowledgeMemory, 记忆系统
        """
        self.memory = memory

    def learn_from_accepted(self, section_type: str, text: str,
                            quality_score: float) -> LearningResult:
        """
        从被采纳的文本中学习

        Parameters
        ----------
        section_type : str, 章节类型
        text : str, 被采纳的文本
        quality_score : float, 质量分数

        Returns
        -------
        LearningResult : 学习结果
        """
        result = LearningResult()

        # 只从高质量文本中学习
        if quality_score < 60:
            return result

        # 计算置信度（基于质量分数）
        confidence = min(0.9, quality_score / 100)

        # 1. 提取句式模式
        patterns = self._extract_patterns(text, section_type)
        for pattern in patterns:
            pattern.confidence = confidence
            if self.memory:
                self.memory.remember(
                    content={
                        'skeleton': pattern.skeleton,
                        'example': pattern.example,
                        'section_type': pattern.section_type,
                    },
                    category='writing_templates',
                    source='learning_loop',
                    confidence=confidence,
                )
                result.patterns_learned += 1

        # 2. 提取机制知识
        mechanisms = self._extract_mechanisms(text)
        for mechanism in mechanisms:
            if self.memory:
                self.memory.remember(
                    content=mechanism,
                    category='mechanisms',
                    source='learning_loop',
                    confidence=confidence,
                )
                result.mechanisms_learned += 1

        return result

    def _extract_patterns(self, text: str, section_type: str) -> List[LearnedPattern]:
        """提取句式模式"""
        patterns = []

        # 分句
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        for sentence in sentences:
            # 检查是否匹配句式模式
            for pattern in self.SKELETON_PATTERNS:
                match = re.search(pattern, sentence)
                if match:
                    # 提取骨架
                    skeleton = self._extract_skeleton(sentence, match)
                    patterns.append(LearnedPattern(
                        pattern_type='sentence',
                        skeleton=skeleton,
                        example=sentence[:100],
                        section_type=section_type,
                    ))
                    break  # 每个句子只提取一个模式

        return patterns

    def _extract_skeleton(self, sentence: str, match: re.Match) -> str:
        """提取句式骨架"""
        # 将具体变量替换为占位符
        skeleton = sentence
        for i, group in enumerate(match.groups(), 1):
            if group:
                skeleton = skeleton.replace(group, f'{{var{i}}}', 1)
        return skeleton

    def _extract_mechanisms(self, text: str) -> List[Dict]:
        """提取机制知识"""
        mechanisms = []

        for pattern in self.MECHANISM_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 3:
                    mechanisms.append({
                        'var1': groups[0],
                        'relation': groups[2] if len(groups) > 2 else '',
                        'var2': groups[1],
                        'context': match.group(0),
                    })

        return mechanisms

    def update_confidence(self, key: str, category: str,
                          accepted: bool) -> int:
        """
        更新置信度

        Parameters
        ----------
        key : str, 知识键
        category : str, 知识分类
        accepted : bool, 是否被采纳

        Returns
        -------
        int : 更新数量
        """
        if not self.memory:
            return 0

        # 获取当前条目
        entry = self.memory.store.get(category, key)
        if not entry:
            return 0

        current_confidence = entry.get('confidence', 0.5)

        # 更新置信度
        if accepted:
            new_confidence = min(0.95, current_confidence + 0.1)
        else:
            new_confidence = max(0.1, current_confidence - 0.1)

        # 保存更新
        self.memory.store.set(
            category, key, entry.get('value', entry),
            source=entry.get('source', 'unknown'),
            confidence=new_confidence,
        )

        return 1

    def decay_confidence(self, category: str, decay_rate: float = 0.95) -> int:
        """
        置信度衰减

        Parameters
        ----------
        category : str, 知识分类
        decay_rate : float, 衰减率

        Returns
        -------
        int : 衰减的条目数量
        """
        if not self.memory:
            return 0

        count = 0
        entries = self.memory.store.get(category, {})
        for key, entry in entries.items():
            if isinstance(entry, dict):
                current_confidence = entry.get('confidence', 0.5)
                new_confidence = current_confidence * decay_rate

                # 低于阈值的条目标记为待清理
                if new_confidence < 0.1:
                    new_confidence = 0.1

                if new_confidence != current_confidence:
                    self.memory.store.set(
                        category, key, entry.get('value', entry),
                        source=entry.get('source', 'unknown'),
                        confidence=new_confidence,
                    )
                    count += 1

        return count


# 全局单例
_loop = None

def get_learning_loop(memory=None) -> LearningLoop:
    """获取学习环路单例"""
    global _loop
    if _loop is None:
        _loop = LearningLoop(memory)
    return _loop


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    loop = LearningLoop()

    test_text = """
    结果表明，CH4浓度与pH呈显著负相关（r=-0.534, p=0.022）。
    冬季CH4浓度显著高于春季，这可能与温度影响产甲烷菌活性有关。
    由于管网内厌氧条件，有机物通过微生物作用产生CH4。
    """

    result = loop.learn_from_accepted('results', test_text, 75.0)
    print(f"学到句式模式: {result.patterns_learned}")
    print(f"学到机制知识: {result.mechanisms_learned}")
