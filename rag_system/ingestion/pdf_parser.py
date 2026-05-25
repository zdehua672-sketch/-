"""PDF解析器（可选PyMuPDF依赖）"""
from pathlib import Path


def parse_pdf(pdf_path: str, doc_id: str = None) -> str:
    """
    解析PDF文件为纯文本

    Parameters
    ----------
    pdf_path : str, PDF文件路径
    doc_id : str, 文档ID（可选）

    Raises
    ------
    ImportError, 如果未安装PyMuPDF
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PDF解析需要PyMuPDF库。请运行: pip install PyMuPDF\n"
            "或使用parse_text()直接解析纯文本。"
        )

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

    if doc_id is None:
        import hashlib
        doc_id = hashlib.md5(path.name.encode()).hexdigest()[:12]

    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())

    return '\n'.join(text_parts)
