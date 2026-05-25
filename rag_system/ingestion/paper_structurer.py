"""论文结构化器 - IMRaD章节检测"""
import re
from ..schema.document_schema import DocumentChunk


# IMRaD章节关键词（中英文）
IMRAD_PATTERNS = {
    'abstract': [
        r'(?i)^#{1,3}\s*abstract',
        r'(?i)^#{1,3}\s*摘\s*要',
        r'(?i)^abstract\s*$',
        r'^摘要\s*$',
    ],
    'introduction': [
        r'(?i)^#{1,3}\s*(?:1\.?\s*)?introduction',
        r'(?i)^#{1,3}\s*(?:1\.?\s*)?(?:绪论|引言|研究背景)',
        r'(?i)^(?:1\.?\s*)?introduction\s*$',
    ],
    'methods': [
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?(?:materials?\s*(?:and|&)\s*)?methods?',
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?(?:材料|方法|实验方法|实验设计)',
    ],
    'results': [
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?results?(?:\s*(?:and|&)\s*discussion)?',
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?(?:结果|实验结果)',
    ],
    'discussion': [
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?discussion',
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?(?:讨论|分析讨论)',
    ],
    'conclusion': [
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?conclusions?',
        r'(?i)^#{1,3}\s*(?:\d\.?\s*)?(?:结论|总结)',
    ],
}


def detect_imrad_sections(text: str) -> list:
    """
    检测文本中的IMRaD章节边界

    Returns
    -------
    list of (section_type, start_pos, header_text)
    """
    sections = []
    lines = text.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        for section_type, patterns in IMRAD_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, stripped):
                    char_pos = sum(len(lines[j]) + 1 for j in range(i))
                    sections.append((section_type, char_pos, stripped))
                    break
            else:
                continue
            break

    return sections


def structure_paper(text: str, doc_id: str) -> list:
    """
    将论文全文结构化为带章节标签的DocumentChunk列表
    """
    sections = detect_imrad_sections(text)

    if not sections:
        # 没有检测到章节，退化为段落分割
        from .text_parser import parse_text
        return parse_text(text, doc_id)

    chunks = []
    for idx, (stype, start, header) in enumerate(sections):
        # 确定本章节的文本范围
        if idx + 1 < len(sections):
            end = sections[idx + 1][1]
            section_text = text[start:end].strip()
        else:
            section_text = text[start:].strip()

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_s{idx:02d}",
            doc_id=doc_id,
            text=section_text,
            chunk_type=stype,
            section_path=header,
            index_in_doc=idx,
            char_offset=start,
        )
        chunks.append(chunk)

    return chunks
