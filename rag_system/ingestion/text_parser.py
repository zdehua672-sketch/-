"""纯文本/Markdown文档解析器"""
import re
import hashlib
from pathlib import Path
from ..schema.document_schema import PaperMetadata, DocumentChunk


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def parse_text(text: str, doc_id: str = None, metadata: dict = None) -> list:
    """
    解析纯文本为DocumentChunk列表

    Parameters
    ----------
    text : str, 文档全文
    doc_id : str, 文档ID（可选，自动生成）
    metadata : dict, 附加元数据
    """
    if doc_id is None:
        doc_id = _make_id(text[:200])

    chunks = []
    # 按段落分割
    paragraphs = re.split(r'\n\s*\n', text.strip())

    offset = 0
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_c{i:04d}",
            doc_id=doc_id,
            text=para,
            chunk_type="body",
            index_in_doc=i,
            char_offset=offset,
            metadata=metadata or {},
        )
        chunks.append(chunk)
        offset += len(para) + 2

    return chunks


def parse_markdown(text: str, doc_id: str = None, metadata: dict = None) -> list:
    """
    解析Markdown文档，识别标题层级和章节类型
    """
    if doc_id is None:
        doc_id = _make_id(text[:200])

    chunks = []
    # 按标题分割
    sections = re.split(r'(^#{1,3}\s+.+$)', text, flags=re.MULTILINE)

    current_type = "body"
    current_path = ""
    offset = 0
    idx = 0

    for part in sections:
        part = part.strip()
        if not part:
            continue

        # 检测标题
        header_match = re.match(r'^(#{1,3})\s+(.+)$', part)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_type = _detect_section_type(title)
            current_path = title
            continue

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_c{idx:04d}",
            doc_id=doc_id,
            text=part,
            chunk_type=current_type,
            section_path=current_path,
            index_in_doc=idx,
            char_offset=offset,
            metadata=metadata or {},
        )
        chunks.append(chunk)
        idx += 1
        offset += len(part) + 2

    return chunks


def _detect_section_type(title: str) -> str:
    """根据标题文字检测章节类型"""
    title_lower = title.lower()

    mapping = {
        'abstract': 'abstract', '摘要': 'abstract',
        'introduction': 'introduction', '绪论': 'introduction', '引言': 'introduction', '背景': 'introduction',
        'methods': 'methods', 'method': 'methods', '材料': 'methods', '方法': 'methods', '实验': 'methods',
        'results': 'results', 'result': 'results', '结果': 'results',
        'discussion': 'discussion', '讨论': 'discussion',
        'conclusion': 'conclusion', 'conclusions': 'conclusion', '结论': 'conclusion',
        'literature': 'introduction', '文献': 'introduction', '综述': 'introduction',
    }

    for keyword, stype in mapping.items():
        if keyword in title_lower:
            return stype

    return "body"
