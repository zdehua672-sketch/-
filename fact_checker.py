# -*- coding: utf-8 -*-
"""
=============================================================================
事实一致性检查器 - Fact Checker
=============================================================================

自动比对模型输出中涉及的数值/p/r/均值与 findings 数据源，检测幻觉。

检查维度：
1. 数值一致性 - 文中数值是否与数据源匹配
2. 统计一致性 - p值、r值是否正确
3. 方向一致性 - 正相关/负相关是否正确
4. 显著性一致性 - 显著/不显著是否正确

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class FactCheckIssue:
    """事实检查问题"""
    severity: str = 'MAJOR'            # 严重程度
    category: str = ''                 # 问题类别
    location: str = ''                 # 位置
    problem: str = ''                  # 问题描述
    expected: str = ''                 # 期望值
    actual: str = ''                   # 实际值
    suggestion: str = ''               # 建议


@dataclass
class FactCheckResult:
    """事实检查结果"""
    passed: bool = True                # 是否通过
    score: float = 100.0               # 分数（0-100）
    issues: List[FactCheckIssue] = field(default_factory=list)
    checked_count: int = 0             # 检查的数值数量
    mismatch_count: int = 0            # 不匹配的数量

    def to_dict(self) -> Dict:
        return {
            'passed': self.passed,
            'score': self.score,
            'issues': [
                {
                    'severity': i.severity,
                    'category': i.category,
                    'problem': i.problem,
                    'expected': i.expected,
                    'actual': i.actual,
                }
                for i in self.issues
            ],
            'checked_count': self.checked_count,
            'mismatch_count': self.mismatch_count,
        }


class FactChecker:
    """
    事实一致性检查器

    用法:
        checker = FactChecker()
        result = checker.check(text, findings)
        if not result.passed:
            print(result.issues)
    """

    # 数值容差
    TOLERANCE = 0.01  # 1% 容差

    def check(self, text: str, findings: List[Dict]) -> FactCheckResult:
        """
        检查文本与 findings 的一致性

        Parameters
        ----------
        text : str, 待检查文本
        findings : list of dict, 数据发现列表

        Returns
        -------
        FactCheckResult : 检查结果
        """
        result = FactCheckResult()

        if not findings:
            return result

        # 1. 提取文本中的数值
        text_values = self._extract_values(text)

        # 2. 提取 findings 中的数值
        findings_values = self._extract_findings_values(findings)

        # 3. 比对数值
        result.checked_count = len(text_values)
        for text_val in text_values:
            issue = self._check_value_consistency(text_val, findings_values)
            if issue:
                result.issues.append(issue)
                result.mismatch_count += 1

        # 4. 检查方向一致性
        direction_issues = self._check_direction_consistency(text, findings)
        result.issues.extend(direction_issues)

        # 5. 检查显著性一致性
        significance_issues = self._check_significance_consistency(text, findings)
        result.issues.extend(significance_issues)

        # 计算分数
        if result.checked_count > 0:
            mismatch_rate = result.mismatch_count / result.checked_count
            result.score = max(0, 100 - mismatch_rate * 100)
            result.passed = result.score >= 70  # 70分以上认为通过
        else:
            result.passed = True
            result.score = 100.0

        return result

    def _extract_values(self, text: str) -> List[Dict]:
        """从文本中提取数值"""
        values = []

        # 匹配 p 值
        p_patterns = [
            r'p\s*[<>=]\s*(\d+\.?\d*)',
            r'p\s*=\s*(\d+\.?\d*)',
            r'[（(]\s*p\s*[<>=]\s*(\d+\.?\d*)\s*[）)]',
        ]
        for pattern in p_patterns:
            for match in re.finditer(pattern, text):
                try:
                    val = float(match.group(1))
                    values.append({
                        'type': 'p',
                        'value': val,
                        'context': match.group(0),
                    })
                except:
                    pass

        # 匹配 r 值
        r_patterns = [
            r'r\s*=\s*([-\d.]+)',
            r'R\s*=\s*([-\d.]+)',
        ]
        for pattern in r_patterns:
            for match in re.finditer(pattern, text):
                try:
                    val = float(match.group(1))
                    values.append({
                        'type': 'r',
                        'value': val,
                        'context': match.group(0),
                    })
                except:
                    pass

        # 匹配均值
        mean_patterns = [
            r'均值[为是]\s*(\d+\.?\d*)',
            r'平均[为是]\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*±\s*(\d+\.?\d*)',
        ]
        for pattern in mean_patterns:
            for match in re.finditer(pattern, text):
                try:
                    val = float(match.group(1))
                    values.append({
                        'type': 'mean',
                        'value': val,
                        'context': match.group(0),
                    })
                except:
                    pass

        return values

    def _extract_findings_values(self, findings: List[Dict]) -> Dict:
        """从 findings 中提取数值"""
        values = {
            'p': [],
            'r': [],
            'mean': [],
        }

        for f in findings:
            data = f.get('data', {})
            if 'p' in data:
                try:
                    values['p'].append(float(data['p']))
                except:
                    pass
            if 'r' in data:
                try:
                    values['r'].append(float(data['r']))
                except:
                    pass
            if 'mean' in data:
                try:
                    values['mean'].append(float(data['mean']))
                except:
                    pass

        return values

    def _check_value_consistency(self, text_val: Dict, findings_values: Dict) -> Optional[FactCheckIssue]:
        """检查单个数值的一致性"""
        val_type = text_val['type']
        val = text_val['value']

        if val_type not in findings_values:
            return None

        # 检查是否在 findings 中有相近的值
        for finding_val in findings_values[val_type]:
            if abs(val - finding_val) <= self.TOLERANCE * abs(finding_val):
                return None  # 匹配成功

        # 没有匹配的值
        if findings_values[val_type]:
            expected_range = f"{min(findings_values[val_type]):.3f} - {max(findings_values[val_type]):.3f}"
            return FactCheckIssue(
                severity='MAJOR',
                category='数值不一致',
                location=text_val['context'],
                problem=f"文中 {val_type}={val} 在 findings 中未找到匹配",
                expected=expected_range,
                actual=str(val),
                suggestion=f"请检查 {val_type} 值是否正确",
            )

        return None

    def _check_direction_consistency(self, text: str, findings: List[Dict]) -> List[FactCheckIssue]:
        """检查方向一致性（正相关/负相关）"""
        issues = []

        # 提取文本中的方向描述
        positive_patterns = ['正相关', '显著高于', '增加', '上升', '升高']
        negative_patterns = ['负相关', '显著低于', '减少', '下降', '降低']

        text_lower = text.lower()

        for f in findings:
            data = f.get('data', {})
            r = data.get('r')
            if r is None:
                continue

            try:
                r = float(r)
            except:
                continue

            detail = f.get('detail', '')

            # 检查方向是否一致
            if r > 0:
                # 正相关
                for pattern in negative_patterns:
                    if pattern in detail and pattern in text:
                        # findings 说正相关，但文本说负相关
                        issues.append(FactCheckIssue(
                            severity='CRITICAL',
                            category='方向错误',
                            location=detail[:50],
                            problem=f"findings 显示 r={r}（正相关），但文中描述为负相关",
                            expected='正相关',
                            actual='负相关',
                            suggestion='请修正相关性方向描述',
                        ))
            elif r < 0:
                # 负相关
                for pattern in positive_patterns:
                    if pattern in detail and pattern in text:
                        # findings 说负相关，但文本说正相关
                        issues.append(FactCheckIssue(
                            severity='CRITICAL',
                            category='方向错误',
                            location=detail[:50],
                            problem=f"findings 显示 r={r}（负相关），但文中描述为正相关",
                            expected='负相关',
                            actual='正相关',
                            suggestion='请修正相关性方向描述',
                        ))

        return issues

    def _check_significance_consistency(self, text: str, findings: List[Dict]) -> List[FactCheckIssue]:
        """检查显著性一致性"""
        issues = []

        # 提取文本中的显著性描述
        sig_patterns = ['显著', 'p<0.05', 'p<0.01', 'p<0.001']
        not_sig_patterns = ['不显著', '无显著差异', 'p>0.05']

        for f in findings:
            data = f.get('data', {})
            p = data.get('p')
            if p is None:
                continue

            try:
                p = float(p)
            except:
                continue

            detail = f.get('detail', '')

            # 检查显著性是否一致
            if p < 0.05:
                # 显著
                for pattern in not_sig_patterns:
                    if pattern in detail and pattern in text:
                        issues.append(FactCheckIssue(
                            severity='MAJOR',
                            category='显著性错误',
                            location=detail[:50],
                            problem=f"findings 显示 p={p}（显著），但文中描述为不显著",
                            expected='显著',
                            actual='不显著',
                            suggestion='请修正显著性描述',
                        ))
            else:
                # 不显著
                for pattern in sig_patterns:
                    if pattern in detail and pattern in text:
                        issues.append(FactCheckIssue(
                            severity='MAJOR',
                            category='显著性错误',
                            location=detail[:50],
                            problem=f"findings 显示 p={p}（不显著），但文中描述为显著",
                            expected='不显著',
                            actual='显著',
                            suggestion='请修正显著性描述',
                        ))

        return issues


# 全局单例
_checker = None

def get_fact_checker() -> FactChecker:
    """获取事实检查器单例"""
    global _checker
    if _checker is None:
        _checker = FactChecker()
    return _checker


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    checker = FactChecker()

    test_text = """
    结果表明，CH4浓度与pH呈显著负相关（r=-0.534, p=0.022）。
    冬季CH4浓度显著高于春季（p<0.05）。
    """

    test_findings = [
        {
            'type': 'correlation',
            'detail': 'CH4与pH显著负相关',
            'data': {'r': -0.534, 'p': 0.022},
        },
        {
            'type': 'group_difference',
            'detail': '冬季CH4浓度显著高于春季',
            'data': {'p': 0.015},
        },
    ]

    result = checker.check(test_text, test_findings)
    print(f"检查结果: {'通过' if result.passed else '未通过'}")
    print(f"分数: {result.score:.1f}")
    print(f"检查数值: {result.checked_count}")
    print(f"不匹配: {result.mismatch_count}")
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.problem}")
