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
        """从文本中提取数值（支持科学计数法）"""
        values = []
        seen_contexts = set()  # 避免重复匹配

        # Unicode 上标数字映射
        superscript_map = {
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
            '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
            '⁻': '-', '+': '+'
        }

        # 匹配 p 值（支持科学计数法如 p=3.0×10⁻⁶, p=1.03e-4, p=1.03×10⁻⁴）
        # 按优先级排序：科学计数法优先，普通小数在后
        p_patterns = [
            # 科学计数法: p=3.0×10⁻⁶ 或 p=3.0×10^-6 (Unicode 上标)
            r'p\s*[<>=]\s*(\d+\.?\d*)\s*×\s*10\s*([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)',
            # 科学计数法: p=3.0×10⁻⁶ 或 p=3.0×10^-6 (普通字符)
            r'p\s*[<>=]\s*(\d+\.?\d*)\s*×\s*10\s*[\-]?\s*(\d+)',
            # 科学计数法: p=1.03e-4 或 p=1.03E-4
            r'p\s*[<>=]\s*(\d+\.?\d*)\s*[eE]\s*([+-]?\d+)',
            # 普通小数: p=0.0001 或 p<0.05 (必须排除已经被科学计数法匹配的)
            r'(?<![eE×])p\s*[<>=]\s*(\d+\.?\d*)(?![eE×])',
            r'[（(]\s*p\s*[<>=]\s*(\d+\.?\d*)\s*[）)]',
        ]
        for pattern in p_patterns:
            for match in re.finditer(pattern, text):
                try:
                    context = match.group(0)
                    # 避免重复匹配
                    if context in seen_contexts:
                        continue
                    seen_contexts.add(context)

                    if '×' in context or 'e' in context.lower():
                        # 科学计数法
                        mantissa = float(match.group(1))
                        exponent_str = match.group(2)
                        # 处理 Unicode 上标字符
                        if any(c in superscript_map for c in exponent_str):
                            exponent = int(''.join(superscript_map.get(c, c) for c in exponent_str))
                        else:
                            exponent = int(exponent_str)
                        val = mantissa * (10 ** exponent)
                    else:
                        val = float(match.group(1))
                    values.append({
                        'type': 'p',
                        'value': val,
                        'context': context,
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
        """检查显著性一致性（支持接近显著）"""
        issues = []

        # 显著性关键词（用于检查 detail 字段）
        # 注意：需要排除"接近显著"中的"显著"
        strong_sig_keywords = ['极显著', '非常显著', '显著差异', '显著正相关', '显著负相关', '显著相关']
        near_sig_keywords = ['接近显著', '边际显著', '临界显著']

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

            # 确定实际显著性水平
            is_sig = p < 0.05

            # 检查 detail 中是否包含显著性描述
            detail_has_strong_sig = False
            detail_has_near_sig = False

            for keyword in strong_sig_keywords:
                if keyword in detail:
                    detail_has_strong_sig = True
                    break

            for keyword in near_sig_keywords:
                if keyword in detail:
                    detail_has_near_sig = True
                    break

            # 如果 detail 中有"强显著"描述，但实际 p >= 0.05，则报告问题
            if detail_has_strong_sig and not detail_has_near_sig and not is_sig:
                # 区分接近显著和不显著
                if p < 0.10:
                    issues.append(FactCheckIssue(
                        severity='MINOR',
                        category='显著性描述不准确',
                        location=detail[:50],
                        problem=f"findings 显示 p={p:.4f}（接近显著），但描述为显著",
                        expected='接近显著/临界显著',
                        actual='显著',
                        suggestion='建议改为"接近显著"或"临界显著"',
                    ))
                else:
                    issues.append(FactCheckIssue(
                        severity='MAJOR',
                        category='显著性错误',
                        location=detail[:50],
                        problem=f"findings 显示 p={p:.4f}（不显著），但描述为显著",
                        expected='不显著',
                        actual='显著',
                        suggestion='请修正显著性描述，或删除显著性声明',
                    ))

        return issues

    def check_and_fix(self, text: str, findings: List[Dict]) -> Tuple[str, FactCheckResult]:
        """
        检查并自动修正数值不一致问题

        Parameters
        ----------
        text : str, 待检查文本
        findings : list of dict, 数据发现列表

        Returns
        -------
        tuple : (修正后文本, 检查结果)
        """
        result = self.check(text, findings)

        if not result.issues:
            return text, result

        # 自动修正数值不一致
        fixed_text = text
        for issue in result.issues:
            if issue.category == '数值不一致':
                # 尝试从findings中找到正确的值
                correct_value = self._find_correct_value(issue, findings)
                if correct_value is not None:
                    # 替换文本中的错误值
                    fixed_text = self._replace_value(fixed_text, issue.location, correct_value)

        return fixed_text, result

    def _find_correct_value(self, issue: FactCheckIssue, findings: List[Dict]) -> Optional[float]:
        """从findings中找到正确的值"""
        # 从issue.location中提取数值类型和值
        import re

        # 提取p值
        p_match = re.search(r'p\s*[<>=]\s*(\d+\.?\d*)', issue.location)
        if p_match:
            old_p = float(p_match.group(1))
            # 在findings中查找最接近的p值
            best_p = None
            best_diff = float('inf')
            for f in findings:
                data = f.get('data', {})
                if 'p' in data:
                    try:
                        p_val = float(data['p'])
                        diff = abs(p_val - old_p)
                        if diff < best_diff:
                            best_diff = diff
                            best_p = p_val
                    except:
                        pass
            # 如果找到了接近的值（差异小于50%），返回它
            if best_p is not None and best_diff < 0.5 * old_p:
                return best_p

        # 提取r值
        r_match = re.search(r'r\s*=\s*([-\d.]+)', issue.location)
        if r_match:
            old_r = float(r_match.group(1))
            # 在findings中查找最接近的r值
            best_r = None
            best_diff = float('inf')
            for f in findings:
                data = f.get('data', {})
                if 'r' in data:
                    try:
                        r_val = float(data['r'])
                        diff = abs(r_val - old_r)
                        if diff < best_diff:
                            best_diff = diff
                            best_r = r_val
                    except:
                        pass
            # 如果找到了接近的值（差异小于20%），返回它
            if best_r is not None and best_diff < 0.2 * abs(old_r):
                return best_r

        # 提取mean值
        mean_match = re.search(r'mean\s*=\s*(\d+\.?\d*)', issue.location)
        if mean_match:
            old_mean = float(mean_match.group(1))
            # 在findings中查找最接近的mean值
            best_mean = None
            best_diff = float('inf')
            for f in findings:
                data = f.get('data', {})
                if 'mean' in data:
                    try:
                        mean_val = float(data['mean'])
                        diff = abs(mean_val - old_mean)
                        if diff < best_diff:
                            best_diff = diff
                            best_mean = mean_val
                    except:
                        pass
            # 如果找到了接近的值（差异小于30%），返回它
            if best_mean is not None and best_diff < 0.3 * old_mean:
                return best_mean

        return None

    def _replace_value(self, text: str, location: str, correct_value: float) -> str:
        """替换文本中的错误值"""
        import re

        # 替换p值
        p_match = re.search(r'p\s*[<>=]\s*(\d+\.?\d*)', location)
        if p_match:
            old_value = p_match.group(1)
            # 格式化新值
            if correct_value < 0.001:
                new_value = f"{correct_value:.2e}"
            elif correct_value < 0.01:
                new_value = f"{correct_value:.4f}"
            else:
                new_value = f"{correct_value:.4f}"
            # 替换文本中的值
            text = re.sub(rf'p\s*[<>=]\s*{re.escape(old_value)}', f'p={new_value}', text)

        # 替换r值
        r_match = re.search(r'r\s*=\s*([-\d.]+)', location)
        if r_match:
            old_value = r_match.group(1)
            new_value = f"{correct_value:.3f}"
            text = re.sub(rf'r\s*=\s*{re.escape(old_value)}', f'r={new_value}', text)

        return text


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
