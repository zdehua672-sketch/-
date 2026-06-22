# -*- coding: utf-8 -*-
"""
论文清洗器 — 移除写作残留、验证章节完整性

解决两大顽疾：
1. Claude 输出混入 prompt/元数据/规划文本
2. 章节只有标题没有内容
"""

import re
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 1. 写作残留模式（必须移除的文本）
# ============================================================

ARTIFACT_PATTERNS = [
    # Claude 对话残留
    r'以下是为您撰写的.*?(?=\n|$)',
    r'我已仔细审阅了.*?(?=\n|$)',
    r'作为.*?领域的学者.*?(?=\n|$)',
    r'以上为.*?第\d部分.*?(?=\n|$)',
    r'后续部分规划.*?(?=\n|$)',
    r'请授权文件写入.*?(?=\n|$)',
    r'文件写入需要.*?(?=\n|$)',
    r'I have all.*?(?=\n|$)',
    r'Since file writing.*?(?=\n|$)',
    r'请直接输出.*?(?=\n|$)',
    r'不要加说明.*?(?=\n|$)',
    r'约\d+字.*?要求.*?(?=\n|$)',
    r'全文约\s*\d+字.*?(?=\n|$)',
    r'数据均取自.*?未做虚构.*?(?=\n|$)',
    r'按照.*?结构组织.*?(?=\n|$)',
    r'包含以下逻辑层次.*?(?=\n|$)',
    r'补充了具体数据.*?(?=\n|$)',
    r'各claim均有.*?(?=\n|$)',
    r'解决了原版.*?(?=\n|$)',
    r'引言结构说明.*?(?=\n|$)',
    r'请授权.*?(?=\n|$)',
    r'您可以.*?复制.*?(?=\n|$)',

    # 论文评审残留
    r'建议的改进优先级.*?(?=\n|$)',
    r'需要重点改进.*?(?=\n|$)',
    r'论文现状评估.*?(?=\n|$)',
    r'已完成的工作.*?(?=\n|$)',
    r'论文框架基本完整.*?(?=\n|$)',
    r'数据基础扎实.*?(?=\n|$)',
    r'需要重点改进的问题.*?(?=\n|$)',
    r'我们可以讨论.*?(?=\n|$)',

    # 分段规划残留
    r'第\d部分[：:]\s*\d+\.\d+.*?(?=\n|$)',
    r'第\d部分.*?包含.*?(?=\n|$)',
    r'后续部分规划[：:].*?(?=\n|$)',
    r'小节\).*?(?=\n|$)',

    # 英文残留
    r'here for you to copy.*?(?=\n|$)',
    r'Please authorize.*?(?=\n|$)',
    r'I will save.*?(?=\n|$)',

    # 评估报告残留
    r'论文评估报告.*?(?=\n|$)',
    r'整体评估.*?(?=\n|$)',
    r'改进方向.*?(?=\n|$)',
]

# 编译正则
_ARTIFACT_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in ARTIFACT_PATTERNS]


def clean_artifacts(text: str) -> str:
    """移除所有写作残留"""
    if not text:
        return text

    original_len = len(text)

    # 逐行检查，移除匹配行
    lines = text.split('\n')
    clean_lines = []
    skip_until_next_heading = False

    for line in lines:
        stripped = line.strip()

        # 检查是否是残留文本
        is_artifact = False
        for pattern in _ARTIFACT_RE:
            if pattern.search(stripped):
                is_artifact = True
                break

        # 额外检查：纯英文的元评论行
        if re.match(r'^(I have|Since|Please|Here is|The following)', stripped):
            is_artifact = True

        # 检查 "以下是" 开头的行（但排除正常学术文本）
        if stripped.startswith('以下是') and ('撰写' in stripped or '部分' in stripped or '为您' in stripped):
            is_artifact = True

        # 检查 "以上为" 开头的行
        if stripped.startswith('以上为') and ('部分' in stripped or '涵盖' in stripped):
            is_artifact = True

        if is_artifact:
            logger.debug(f"移除残留: {stripped[:60]}...")
            continue

        clean_lines.append(line)

    result = '\n'.join(clean_lines)

    # 移除连续空行（超过2个）
    result = re.sub(r'\n{4,}', '\n\n\n', result)

    removed = original_len - len(result)
    if removed > 100:
        logger.info(f"清洗完成: 移除 {removed} 字残留文本")

    return result


# ============================================================
# 2. 章节完整性验证
# ============================================================

def validate_sections(sections: dict) -> list:
    """
    验证章节完整性，返回问题列表

    检查：
    - 章节是否存在
    - 章节是否有实际内容（不只是标题）
    - 是否有空白小节
    """
    problems = []

    required_sections = {
        'abstract': ('摘要', 300),
        'introduction': ('引言', 1500),
        'methods': ('材料与方法', 500),
        'results_discussion': ('结果与讨论', 3000),
        'conclusion': ('结论', 200),
    }

    for key, (name, min_chars) in required_sections.items():
        text = sections.get(key, '')

        if not text:
            problems.append(f'❌ 缺少章节: {name}')
            continue

        # 去除标题后的纯内容长度
        content = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()
        content_len = len(content)

        if content_len < min_chars:
            problems.append(f'⚠️ {name} 内容过短: {content_len}字 (最少{min_chars}字)')

        # 检查是否有空白小节（标题后没有内容）
        headings = re.findall(r'^(#{2,4})\s+(.+)$', text, re.MULTILINE)
        for level, heading in headings:
            # 找这个标题到下一个标题之间的内容
            pattern = re.escape(level + ' ' + heading) + r'(.*?)(?=^#{1,4}\s|\Z)'
            match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                # 去除子标题后的内容
                sub_content = re.sub(r'^#{2,4}\s+.*$', '', section_content, flags=re.MULTILINE).strip()
                if len(sub_content) < 20:
                    problems.append(f'⚠️ {name} > "{heading}" 小节内容为空')

    return problems


def validate_figure_references(sections: dict, figures: dict) -> list:
    """验证图表引用是否完整"""
    problems = []

    # 检查是否有 "图X" 占位符残留
    for key, text in sections.items():
        if not text:
            continue

        # 检查 "图X" 占位符
        fig_x_refs = re.findall(r'图X', text)
        if fig_x_refs:
            problems.append(f'⚠️ {key} 中有 {len(fig_x_refs)} 处 "图X" 占位符未替换')

        # 检查 "表X" 占位符
        table_x_refs = re.findall(r'表X', text)
        if table_x_refs:
            problems.append(f'⚠️ {key} 中有 {len(table_x_refs)} 处 "表X" 占位符未替换')

    return problems


def validate_references(sections: dict) -> list:
    """验证参考文献格式"""
    problems = []

    # 检查是否有文件名式的引用（如 "10-domain-knowledge. ."）
    for key, text in sections.items():
        if not text:
            continue

        # 检查参考文献列表中的文件名式引用
        if key == 'references' or '参考文献' in text:
            file_refs = re.findall(r'\[\d+\]\s+[\w\-]+\.\s+\.\s', text)
            if file_refs:
                problems.append(f'⚠️ {key} 中有 {len(file_refs)} 条文件名式引用需要格式化')

    return problems


# ============================================================
# 3. 主清洗函数
# ============================================================

def clean_and_validate_paper(sections: dict, figures: dict = None) -> tuple:
    """
    清洗并验证论文

    Returns
    -------
    tuple: (cleaned_sections, problems)
    """
    # 清洗每个章节
    cleaned = {}
    for key, text in sections.items():
        if text:
            cleaned[key] = clean_artifacts(text)
        else:
            cleaned[key] = text

    # 验证
    problems = []
    problems.extend(validate_sections(cleaned))
    if figures:
        problems.extend(validate_figure_references(cleaned, figures))
    problems.extend(validate_references(cleaned))

    return cleaned, problems
