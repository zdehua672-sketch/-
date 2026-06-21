# -*- coding: utf-8 -*-
"""
=============================================================================
可控断言控制 - Assertion Control
=============================================================================

控制学术论文中的断言强度，避免过度断言：
1. 识别强描述词（证明、必然、总是等）
2. 替换为弱描述词（表明、可能、通常等）
3. 根据数据支撑强度调整断言级别

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class AssertionIssue:
    """断言问题"""
    severity: str = 'MINOR'            # 严重程度
    location: str = ''                 # 位置
    original: str = ''                 # 原文
    suggestion: str = ''               # 建议替换
    reason: str = ''                   # 原因


@dataclass
class AssertionControlResult:
    """断言控制结果"""
    modified_text: str = ''            # 修改后的文本
    issues: List[AssertionIssue] = field(default_factory=list)
    modification_count: int = 0        # 修改数量

    def to_dict(self) -> Dict:
        return {
            'modified_text': self.modified_text,
            'issues': [
                {
                    'severity': i.severity,
                    'location': i.location,
                    'original': i.original,
                    'suggestion': i.suggestion,
                }
                for i in self.issues
            ],
            'modification_count': self.modification_count,
        }


class AssertionController:
    """
    可控断言控制器

    用法:
        controller = AssertionController()
        result = controller.control(text, findings)
        print(result.modified_text)
    """

    # 强描述词 → 弱描述词映射
    STRONG_TO_WEAK = {
        # 证明类
        '证明': '表明',
        '证实': '提示',
        '确认': '提示',
        '确定': '提示',

        # 必然类
        '必然': '可能',
        '一定': '可能',
        '肯定': '可能',
        '绝对': '可能',

        # 总是类
        '总是': '通常',
        '始终': '通常',
        '一贯': '通常',

        # 完全类
        '完全': '在一定程度上',
        '彻底': '在一定程度上',
        '充分': '在一定程度上',

        # 显著类（需要数据支撑）
        '极其显著': '显著',
        '非常显著': '显著',
        '高度显著': '显著',

        # 因果类
        '导致': '与...相关',
        '引起': '与...相关',
        '造成': '与...相关',
        '决定': '影响',

        # 英文
        'prove': 'suggest',
        'confirm': 'indicate',
        'demonstrate': 'indicate',
        'always': 'typically',
        'never': 'rarely',
        'definitely': 'possibly',
        'cause': 'is associated with',
    }

    # 弱描述词（可接受的表达）
    WEAK_EXPRESSIONS = [
        '表明', '提示', '显示', '发现', '观察到',
        '可能', '或许', '推测', '倾向于',
        '通常', '一般', '往往', '常常',
        'suggest', 'indicate', 'show', 'reveal',
        'may', 'might', 'possibly', 'likely',
    ]

    # 数据支撑强度关键词
    STRONG_EVIDENCE = ['p<0.001', 'p<0.01', 'p<0.05', 'r>0.7', 'r<-0.7']
    WEAK_EVIDENCE = ['p>0.05', '接近显著', '边际显著', 'n.s.']

    def control(self, text: str, findings: List[Dict] = None,
                confidence_threshold: float = 0.7) -> AssertionControlResult:
        """
        控制断言强度

        Parameters
        ----------
        text : str, 待处理文本
        findings : list of dict, 数据发现（用于判断证据强度）
        confidence_threshold : float, 置信度阈值

        Returns
        -------
        AssertionControlResult : 处理结果
        """
        result = AssertionControlResult()
        modified_text = text

        # 判断整体证据强度
        evidence_strength = self._assess_evidence_strength(findings)

        # 找出所有强描述词
        for strong_word, weak_word in self.STRONG_TO_WEAK.items():
            # 检查是否在文本中出现
            pattern = re.escape(strong_word)
            matches = list(re.finditer(pattern, modified_text, re.IGNORECASE))

            for match in matches:
                # 获取上下文
                start = max(0, match.start() - 20)
                end = min(len(modified_text), match.end() + 20)
                context = modified_text[start:end]

                # 判断是否需要替换
                should_replace = self._should_replace(
                    strong_word, context, evidence_strength, confidence_threshold
                )

                if should_replace:
                    # 记录问题
                    issue = AssertionIssue(
                        severity='MINOR',
                        location=context,
                        original=strong_word,
                        suggestion=weak_word,
                        reason=f'强描述词"{strong_word}"建议替换为"{weak_word}"',
                    )
                    result.issues.append(issue)

                    # 替换
                    modified_text = modified_text.replace(strong_word, weak_word, 1)
                    result.modification_count += 1

        result.modified_text = modified_text
        return result

    def _assess_evidence_strength(self, findings: List[Dict] = None) -> str:
        """
        评估证据强度

        Returns
        -------
        str : 'strong', 'moderate', 'weak'
        """
        if not findings:
            return 'weak'

        strong_count = 0
        weak_count = 0

        for f in findings:
            data = f.get('data', {})
            p = data.get('p')
            r = data.get('r')

            if p is not None:
                try:
                    p = float(p)
                    if p < 0.01:
                        strong_count += 1
                    elif p < 0.05:
                        strong_count += 1
                    else:
                        weak_count += 1
                except:
                    pass

            if r is not None:
                try:
                    r = abs(float(r))
                    if r > 0.7:
                        strong_count += 1
                    elif r > 0.3:
                        strong_count += 1
                    else:
                        weak_count += 1
                except:
                    pass

        if strong_count > weak_count * 2:
            return 'strong'
        elif strong_count > weak_count:
            return 'moderate'
        else:
            return 'weak'

    def _should_replace(self, strong_word: str, context: str,
                        evidence_strength: str, confidence_threshold: float) -> bool:
        """
        判断是否应该替换

        Parameters
        ----------
        strong_word : str, 强描述词
        context : str, 上下文
        evidence_strength : str, 证据强度
        confidence_threshold : float, 置信度阈值

        Returns
        -------
        bool : 是否应该替换
        """
        # 如果证据强度为强，且置信度高，可以保留强描述
        if evidence_strength == 'strong' and confidence_threshold > 0.8:
            # 检查上下文是否有强证据支撑
            for evidence in self.STRONG_EVIDENCE:
                if evidence in context:
                    return False  # 有强证据支撑，不替换

        # 其他情况都替换
        return True

    def control_conclusion(self, text: str, findings: List[Dict] = None) -> str:
        """
        控制结论章节的断言强度

        结论章节应该更谨慎，避免过度断言

        Parameters
        ----------
        text : str, 结论文本
        findings : list of dict, 数据发现

        Returns
        -------
        str : 处理后的文本
        """
        result = self.control(text, findings, confidence_threshold=0.8)

        # 额外处理：在结论开头添加谨慎性声明
        cautious_prefix = "基于本研究的数据分析，"
        if not text.startswith(cautious_prefix):
            result.modified_text = cautious_prefix + result.modified_text

        return result.modified_text


# 全局单例
_controller = None

def get_assertion_controller() -> AssertionController:
    """获取断言控制器单例"""
    global _controller
    if _controller is None:
        _controller = AssertionController()
    return _controller


def control_assertions(text: str, findings: List[Dict] = None) -> str:
    """
    快捷函数：控制断言强度

    Parameters
    ----------
    text : str, 待处理文本
    findings : list of dict, 数据发现

    Returns
    -------
    str : 处理后的文本
    """
    controller = get_assertion_controller()
    result = controller.control(text, findings)
    return result.modified_text


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    controller = AssertionController()

    test_text = """
    本研究证明，CH4浓度与pH必然存在负相关关系。
    这一发现证实了温度总是影响产甲烷菌活性。
    结果表明，管网中碳污染物的分布完全由水文条件决定。
    """

    test_findings = [
        {
            'type': 'correlation',
            'data': {'r': -0.534, 'p': 0.022},
        },
    ]

    result = controller.control(test_text, test_findings)
    print("原文:", test_text)
    print("\n修改后:", result.modified_text)
    print(f"\n修改数量: {result.modification_count}")
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.original} -> {issue.suggestion}")
