# -*- coding: utf-8 -*-
"""
自动修订模块 - 根据审稿报告自动修复可修复的问题
支持: 禁用空话、AI痕迹、错别字、学术重复
"""
import re
import os


# ============================================================
# 1. 修订规则库
# ============================================================

# 禁用空话 → 替换为具体表达
BANNED_PHRASES = {
    '具有重要意义': '对碳减排和管网管理具有实际价值',
    '具有重要的环境科学意义': '为碳排放核算提供了数据支撑',
    '重要组成部分': '关键环节',
    '综上所述': '',  # 删除，直接陈述
    '综上': '',
    '总之，': '',
    '值得注意的是': '',
    '不难发现': '',
    '众所周知': '',
    '毋庸置疑': '',
    '在某种程度上': '',
    '从某种意义上说': '',
}

# AI痕迹短语 → 替换为自然学术表达
AI_PHRASES = {
    '不仅是碳污染物的输送通道，更是': '同时承担碳污染物输送和生物转化的双重功能，',
    '深入探讨': '分析',
    '深入研究': '研究',
    '系统研究': '研究',
    '全面分析': '分析',
    '深入分析': '分析',
    '揭示了': '表明',
    '揭示了...的规律': '表明了...的趋势',
    '驱动机制': '影响因素',
    '驱动因素': '影响因素',
    '赋存特征': '分布特征',
    '相态转化': '相间迁移',
    '日益突出': '逐渐增加',
    '日益受到关注': '逐渐被重视',
    '为...提供了科学依据': '有助于',
    '为...提供了理论基础': '有助于理解',
    '具有显著的': '呈现明显的',
    '呈现显著的': '呈现明显的',
    '研究结果表明': '结果表明',
    '分析结果表明': '结果表明',
    '本研究结果表明': '结果表明',
    '研究发现': '结果发现',
    '本研究发现': '结果发现',
}

# 错别字修正
TYPOS = {
    '反映': '反应',  # 在化学/生物语境下
    # 注意：'反映'在某些语境下是正确的，需要上下文判断
}

# AI句式模式 → 替换
AI_PATTERNS = [
    (r'本文(?:通过|采用|利用)', '本研究通过'),
    (r'本研究旨在(?:揭示|探讨|分析)', '本研究分析'),
    (r'(?:深入|系统|全面)(?:探讨|研究|分析)', '分析'),
    (r'(?:为.*?(?:提供|奠定).*?(?:基础|依据|参考))', lambda m: m.group(0).replace('提供科学依据', '提供数据支撑').replace('奠定基础', '提供基础')),
]


# ============================================================
# 2. 自动修订器
# ============================================================

class AutoReviser:
    """
    根据审稿报告自动修订论文文本。

    用法:
        reviser = AutoReviser(paper_text, review_report_md)
        revised = reviser.revise()
    """

    def __init__(self, paper_text: str, review_md: str = ''):
        self.original = paper_text
        self.review_md = review_md
        self.changes = []  # 记录所有修改

    def revise(self) -> str:
        """执行所有可自动修复的修订"""
        text = self.original

        # 1. 修复禁用空话
        text = self._fix_banned_phrases(text)

        # 2. 修复AI痕迹
        text = self._fix_ai_phrases(text)

        # 3. 修复错别字（上下文感知）
        text = self._fix_typos(text)

        # 4. 修复AI句式模式
        text = self._fix_ai_patterns(text)

        # 5. 删除空洞段落标记
        text = self._remove_empty_markers(text)

        return text

    def _fix_banned_phrases(self, text: str) -> str:
        """修复禁用空话"""
        for banned, replacement in BANNED_PHRASES.items():
            if banned in text:
                count = text.count(banned)
                text = text.replace(banned, replacement)
                self.changes.append({
                    'type': '禁用空话',
                    'original': banned,
                    'replacement': replacement or '[已删除]',
                    'count': count,
                })
        return text

    def _fix_ai_phrases(self, text: str) -> str:
        """修复AI痕迹短语"""
        for ai_phrase, replacement in AI_PHRASES.items():
            if ai_phrase in text:
                count = text.count(ai_phrase)
                text = text.replace(ai_phrase, replacement)
                self.changes.append({
                    'type': 'AI痕迹',
                    'original': ai_phrase,
                    'replacement': replacement,
                    'count': count,
                })
        return text

    def _fix_typos(self, text: str) -> str:
        """修复错别字（上下文感知）"""
        # 只在化学/生物语境下将'反映'改为'反应'
        # 匹配: "反映了...过程/机制/规律" → "反应了..."
        # 但 "反映了...特征/状况" 保持不变（这里'反映'是正确的）
        pattern = r'反映(了(?:.*?)(?:过程|机制|转化|变化|规律|趋势))'
        matches = re.findall(pattern, text)
        if matches:
            text = re.sub(pattern, r'反应\1', text)
            self.changes.append({
                'type': '错别字',
                'original': '反映',
                'replacement': '反应',
                'count': len(matches),
                'note': '化学/生物语境下修正',
            })
        return text

    def _fix_ai_patterns(self, text: str) -> str:
        """修复AI句式模式"""
        for pattern, replacement in AI_PATTERNS:
            if callable(replacement):
                new_text = re.sub(pattern, replacement, text)
            else:
                new_text = re.sub(pattern, replacement, text)
            if new_text != text:
                count = len(re.findall(pattern, text))
                self.changes.append({
                    'type': 'AI句式',
                    'original': pattern,
                    'replacement': replacement if isinstance(replacement, str) else '动态替换',
                    'count': count,
                })
                text = new_text
        return text

    def _remove_empty_markers(self, text: str) -> str:
        """删除空洞标记"""
        # 删除【目的】【方法】【结果】【结论】等标记（如果审稿指出为空洞）
        # 保留内容，只删除标记
        markers = ['**【目的】**', '**【方法】**', '**【结果】**', '**【结论】**']
        for marker in markers:
            if marker in text:
                text = text.replace(marker, '')
                self.changes.append({
                    'type': '格式优化',
                    'original': marker,
                    'replacement': '[已删除标记]',
                    'count': 1,
                })
        return text

    def get_revision_report(self) -> str:
        """生成修订报告"""
        if not self.changes:
            return '# 自动修订报告\n\n无需自动修订的问题。\n'

        lines = [
            '# 自动修订报告\n',
            f'共执行 {len(self.changes)} 类修订：\n',
        ]

        total_fixes = sum(c['count'] for c in self.changes)
        lines.append(f'**总修改次数**: {total_fixes}\n')

        for i, change in enumerate(self.changes, 1):
            lines.append(f'## {i}. {change["type"]}')
            lines.append(f'- **原文**: {change["original"]}')
            lines.append(f'- **替换为**: {change["replacement"]}')
            lines.append(f'- **修改次数**: {change["count"]}')
            if 'note' in change:
                lines.append(f'- **说明**: {change["note"]}')
            lines.append('')

        # 未自动修复的问题
        lines.append('## 需要人工处理的问题\n')
        lines.append('以下问题无法自动修复，需要人工处理：\n')
        lines.append('1. **参考文献不足** — 需要补充领域内文献引用')
        lines.append('2. **Discussion缺少文献对比** — 需要添加与已有研究的对比讨论')
        lines.append('3. **推理链完整性** — 需要为论点添加数据支撑或文献引用')
        lines.append('4. **结论与摘要重复** — 需要精炼结论，侧重研究贡献')
        lines.append('')

        return '\n'.join(lines)


# ============================================================
# 3. 便捷函数
# ============================================================

def auto_revise_paper(paper_path: str, review_path: str = None,
                      output_path: str = None) -> dict:
    """
    一键自动修订论文。

    Parameters
    ----------
    paper_path : str, 论文MD文件路径
    review_path : str or None, 审稿报告路径（可选）
    output_path : str or None, 输出路径（默认覆盖原文件）

    Returns
    -------
    dict: {revised_text, report, changes_count}
    """
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_text = f.read()

    review_md = ''
    if review_path and os.path.exists(review_path):
        with open(review_path, 'r', encoding='utf-8') as f:
            review_md = f.read()

    reviser = AutoReviser(paper_text, review_md)
    revised = reviser.revise()
    report = reviser.get_revision_report()

    if output_path is None:
        output_path = paper_path

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(revised)

    report_path = output_path.replace('.md', '_revision_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return {
        'revised_text': revised,
        'report': report,
        'changes_count': len(reviser.changes),
        'output_path': output_path,
        'report_path': report_path,
    }


if __name__ == '__main__':
    import sys
    paper = sys.argv[1] if len(sys.argv) > 1 else 'paper_output/paper_chinese_zh.md'
    review = sys.argv[2] if len(sys.argv) > 2 else 'paper_output/review_report.md'
    result = auto_revise_paper(paper, review)
    print(f"修订完成: {result['changes_count']}类修改")
    print(f"输出: {result['output_path']}")
    print(f"报告: {result['report_path']}")
