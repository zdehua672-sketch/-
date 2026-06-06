"""
PDF解析器

优先使用增强版解析器（带清洗+章节识别），
回退到基础 PyMuPDF 解析。
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_pdf(pdf_path: str, doc_id: str = None) -> str:
    """
    解析PDF文件为纯文本

    优先使用 enhanced_pdf_parser（带清洗+页眉页脚去除+噪声过滤），
    回退到基础 PyMuPDF 解析。

    Parameters
    ----------
    pdf_path : str, PDF文件路径
    doc_id : str, 文档ID（可选）

    Returns
    -------
    str, 清洗后的纯文本
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

    # 优先使用增强版解析器
    try:
        import sys
        import os
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from enhanced_pdf_parser import EnhancedPDFParser
        parser = EnhancedPDFParser()
        content = parser.parse(str(path))
        if content.parse_success and content.full_text:
            logger.info(f"Enhanced parser: {content.page_count} pages, {content.char_count} chars")
            return content.full_text
    except ImportError:
        logger.debug("enhanced_pdf_parser not available, using basic parser")
    except Exception as e:
        logger.warning(f"Enhanced parser failed: {e}, using basic parser")

    # 回退到基础解析器
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PDF解析需要PyMuPDF库。请运行: pip install PyMuPDF\n"
            "或 pip install pymupdf\n"
            "或使用parse_text()直接解析纯文本。"
        )

    if doc_id is None:
        import hashlib
        doc_id = hashlib.md5(path.name.encode()).hexdigest()[:12]

    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())

    return '\n'.join(text_parts)
