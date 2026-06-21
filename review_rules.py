# -*- coding: utf-8 -*-
"""
=============================================================================
审稿规则库 - Review Rules
=============================================================================

记录和管理系统在审稿过程中发现的错误样式和负样本：
1. 记录被拒绝/标注为错误的输出
2. 提供查询接口供写作模块参考
3. 支持规则的持久化存储
4. 支持规则的自动学习和更新

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ReviewRule:
    """审稿规则"""
    id: str = ''                           # 规则ID
    category: str = ''                     # 规则类别（ai_trace/citation/language/structure）
    pattern: str = ''                      # 错误模式（正则表达式或关键词）
    description: str = ''                  # 错误描述
    suggestion: str = ''                   # 修改建议
    severity: str = 'MINOR'                # 严重程度（CRITICAL/MAJOR/MINOR/INFO）
    examples: List[str] = field(default_factory=list)  # 错误示例
    counter_examples: List[str] = field(default_factory=list)  # 正确示例
    created_at: str = ''                   # 创建时间
    updated_at: str = ''                   # 更新时间
    hit_count: int = 0                     # 命中次数
    is_active: bool = True                 # 是否启用


@dataclass
class NegativeSample:
    """负样本"""
    id: str = ''                           # 样本ID
    text: str = ''                         # 错误文本
    error_type: str = ''                   # 错误类型
    error_detail: str = ''                 # 错误详情
    correct_text: str = ''                 # 正确文本（如果有）
    section_type: str = ''                 # 章节类型
    created_at: str = ''                   # 创建时间
    source: str = ''                       # 来源（review/auto/manual）


class ReviewRuleStore:
    """
    审稿规则存储

    用法:
        store = ReviewRuleStore('review_rules.json')
        store.add_rule(rule)
        rules = store.get_rules_by_category('ai_trace')
        store.record_negative_sample(sample)
    """

    def __init__(self, filepath: str = None):
        """
        初始化规则存储

        Parameters
        ----------
        filepath : str, 规则文件路径（JSON格式）
        """
        if filepath is None:
            filepath = os.path.join(os.path.dirname(__file__), 'review_rules.json')
        self.filepath = filepath
        self.rules: Dict[str, ReviewRule] = {}
        self.negative_samples: List[NegativeSample] = []
        self._load()

    def _load(self):
        """从文件加载规则"""
        if not os.path.exists(self.filepath):
            self._init_default_rules()
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载规则
            for rule_data in data.get('rules', []):
                rule = ReviewRule(**rule_data)
                self.rules[rule.id] = rule

            # 加载负样本
            for sample_data in data.get('negative_samples', []):
                sample = NegativeSample(**sample_data)
                self.negative_samples.append(sample)

        except Exception as e:
            print(f"加载审稿规则失败: {e}")
            self._init_default_rules()

    def _save(self):
        """保存规则到文件"""
        data = {
            'rules': [asdict(r) for r in self.rules.values()],
            'negative_samples': [asdict(s) for s in self.negative_samples],
            'updated_at': datetime.now().isoformat(),
        }

        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存审稿规则失败: {e}")

    def _init_default_rules(self):
        """初始化默认规则"""
        default_rules = [
            ReviewRule(
                id='ai_trace_meta_comment',
                category='ai_trace',
                pattern='如需写入|如需调整|请在弹出',
                description='Claude元评论残留',
                suggestion='删除元评论，保留正文内容',
                severity='CRITICAL',
                examples=['如需写入文件，请授予写入权限'],
                created_at=datetime.now().isoformat(),
            ),
            ReviewRule(
                id='ai_trace_long_sentence',
                category='ai_trace',
                pattern='.{80,}',
                description='超长句子（>80字）',
                suggestion='在逗号处拆分为两个短句',
                severity='MINOR',
                created_at=datetime.now().isoformat(),
            ),
            ReviewRule(
                id='citation_orphan',
                category='citation',
                pattern=r'\[\d+\]',
                description='孤立引用（引用编号不在参考文献列表中）',
                suggestion='检查引用编号是否正确，或补充缺失的参考文献',
                severity='MAJOR',
                created_at=datetime.now().isoformat(),
            ),
            ReviewRule(
                id='language_colloquial',
                category='language',
                pattern='其实|然后就是| basically',
                description='口语化表达',
                suggestion='使用正式的学术语言',
                severity='MINOR',
                examples=['其实这个结果很有意思', '然后就是说'],
                counter_examples=['值得注意的是', '结果表明'],
                created_at=datetime.now().isoformat(),
            ),
            ReviewRule(
                id='structure_no_evidence',
                category='structure',
                pattern='',
                description='主张缺少数据支撑',
                suggestion='为每个主张添加数据支撑或文献引用',
                severity='MAJOR',
                created_at=datetime.now().isoformat(),
            ),
        ]

        for rule in default_rules:
            self.rules[rule.id] = rule

        self._save()

    def add_rule(self, rule: ReviewRule):
        """添加规则"""
        if not rule.id:
            rule.id = f"rule_{len(self.rules) + 1}"
        if not rule.created_at:
            rule.created_at = datetime.now().isoformat()
        rule.updated_at = datetime.now().isoformat()
        self.rules[rule.id] = rule
        self._save()

    def update_rule(self, rule_id: str, **kwargs):
        """更新规则"""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            rule.updated_at = datetime.now().isoformat()
            self._save()

    def delete_rule(self, rule_id: str):
        """删除规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self._save()

    def get_rule(self, rule_id: str) -> Optional[ReviewRule]:
        """获取规则"""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[ReviewRule]:
        """按类别获取规则"""
        return [r for r in self.rules.values() if r.category == category and r.is_active]

    def get_all_rules(self) -> List[ReviewRule]:
        """获取所有规则"""
        return [r for r in self.rules.values() if r.is_active]

    def check_text(self, text: str) -> List[Dict]:
        """
        检查文本是否违反规则

        Parameters
        ----------
        text : str, 待检查文本

        Returns
        -------
        list of dict : 违反的规则列表
        """
        import re
        violations = []

        for rule in self.get_all_rules():
            if not rule.pattern:
                continue

            matches = re.findall(rule.pattern, text)
            if matches:
                violations.append({
                    'rule_id': rule.id,
                    'category': rule.category,
                    'severity': rule.severity,
                    'description': rule.description,
                    'suggestion': rule.suggestion,
                    'matches': matches[:3],  # 最多返回3个匹配
                })
                # 更新命中次数
                rule.hit_count += 1

        if violations:
            self._save()

        return violations

    def record_negative_sample(self, sample: NegativeSample):
        """记录负样本"""
        if not sample.id:
            sample.id = f"neg_{len(self.negative_samples) + 1}"
        if not sample.created_at:
            sample.created_at = datetime.now().isoformat()
        self.negative_samples.append(sample)
        self._save()

    def get_negative_samples(self, error_type: str = None,
                             section_type: str = None, limit: int = 100) -> List[NegativeSample]:
        """获取负样本"""
        samples = self.negative_samples

        if error_type:
            samples = [s for s in samples if s.error_type == error_type]
        if section_type:
            samples = [s for s in samples if s.section_type == section_type]

        return samples[-limit:]

    def get_avoid_patterns(self, section_type: str = None) -> List[str]:
        """
        获取应避免的模式（供写作模块参考）

        Parameters
        ----------
        section_type : str, 章节类型

        Returns
        -------
        list of str : 应避免的模式列表
        """
        patterns = []

        # 从规则中提取模式
        for rule in self.get_all_rules():
            if rule.pattern and rule.severity in ['CRITICAL', 'MAJOR']:
                patterns.append(rule.pattern)

        # 从负样本中提取模式
        samples = self.get_negative_samples(section_type=section_type, limit=50)
        for sample in samples:
            if sample.text and len(sample.text) > 10:
                # 提取关键词作为模式
                keywords = sample.text[:50]
                patterns.append(keywords)

        return patterns


# 全局单例
_store = None

def get_review_rules() -> ReviewRuleStore:
    """获取审稿规则存储单例"""
    global _store
    if _store is None:
        _store = ReviewRuleStore()
    return _store


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    store = get_review_rules()

    print("审稿规则库:")
    for rule in store.get_all_rules():
        print(f"  [{rule.severity}] {rule.id}: {rule.description}")

    # 测试文本检查
    test_text = "如需写入文件，请授予权限。本研究结果表明..."
    violations = store.check_text(test_text)
    print(f"\n检查结果: {len(violations)} 个违规")
    for v in violations:
        print(f"  [{v['severity']}] {v['description']}")
