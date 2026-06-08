"""
PDF解析器 — 强化版
==================
在原有纯文本提取基础上，新增：
- 多栏拼接（双栏论文正确排序）
- 参考文献自动提取
- 元数据提取（标题/作者/DOI/摘要）
- 表格文本提取
- 页眉页脚过滤
"""

import re
from pathlib import Path
from typing import Optional


def parse_pdf(pdf_path: str, doc_id: str = None) -> str:
    """
    解析PDF文件为纯文本（兼容旧接口）

    Parameters
    ----------
    pdf_path : str, PDF文件路径
    doc_id : str, 文档ID（可选）

    Returns
    -------
    str, 提取的纯文本
    """
    result = parse_pdf_advanced(pdf_path, doc_id)
    return result["text"]


def parse_pdf_advanced(pdf_path: str, doc_id: str = None) -> dict:
    """
    高级PDF解析，提取结构化信息

    Parameters
    ----------
    pdf_path : str, PDF文件路径
    doc_id : str, 文档ID（可选）

    Returns
    -------
    dict, 包含:
        - text: 纯文本（多栏已拼接）
        - title: 提取的标题
        - authors: 提取的作者列表
        - doi: 提取的DOI
        - abstract: 提取的摘要
        - references: 提取的参考文献列表
        - tables: 提取的表格文本列表
        - doc_id: 文档ID
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

    result = {
        "text": "",
        "title": "",
        "authors": [],
        "doi": "",
        "abstract": "",
        "references": [],
        "tables": [],
        "doc_id": doc_id,
    }

    with fitz.open(str(path)) as doc:
        # 提取元数据
        meta = doc.metadata or {}
        result["title"] = meta.get("title", "").strip()

        # 提取文本（多栏拼接）
        all_text_parts = []
        header_footer_lines = _detect_header_footer(doc)

        for page_num, page in enumerate(doc):
            # 尝试多栏拼接
            page_text = _extract_page_text(page, page_num, header_footer_lines)
            all_text_parts.append(page_text)

            # 提取表格
            try:
                tables = page.find_tables()
                for table in tables.tables:
                    table_text = _table_to_text(table)
                    if table_text.strip():
                        result["tables"].append(table_text)
            except Exception:
                pass

        raw_text = '\n'.join(all_text_parts)

        # 从文本中提取元数据（补充/覆盖PDF元数据）
        if not result["title"]:
            result["title"] = _extract_title_from_text(raw_text)

        result["authors"] = _extract_authors_from_text(raw_text)
        result["doi"] = _extract_doi_from_text(raw_text)
        result["abstract"] = _extract_abstract_from_text(raw_text)
        result["references"] = _extract_references_from_text(raw_text)

        # 清理文本：移除页眉页脚、参考文献之后的内容（可选）
        cleaned_text = _clean_text(raw_text, header_footer_lines)
        result["text"] = cleaned_text

    return result


# ── 多栏拼接 ──────────────────────────────────────────────

def _extract_page_text(page, page_num: int, header_footer_lines: set) -> str:
    """提取单页文本，处理多栏布局"""
    try:
        # 获取文本块（带位置信息）
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        return page.get_text()

    # 收集所有文本块及其位置
    text_blocks = []
    for block in blocks:
        if block.get("type") != 0:  # 只处理文本块
            continue
        lines_text = []
        for line in block.get("lines", []):
            spans_text = "".join(span.get("text", "") for span in line.get("spans", []))
            if spans_text.strip():
                lines_text.append(spans_text.strip())
        if lines_text:
            block_text = " ".join(lines_text)
            bbox = block.get("bbox", (0, 0, 0, 0))
            text_blocks.append({
                "text": block_text,
                "x0": bbox[0],
                "y0": bbox[1],
                "x1": bbox[2],
                "y1": bbox[3],
            })

    if not text_blocks:
        return page.get_text()

    # 检测是否多栏：分析 x0 分布
    x_positions = [b["x0"] for b in text_blocks]
    page_width = page.rect.width

    # 简单多栏检测：如果大部分文本块的 x0 > 页面宽度的 40%，可能是双栏
    left_count = sum(1 for x in x_positions if x < page_width * 0.5)
    right_count = sum(1 for x in x_positions if x >= page_width * 0.5)

    is_two_column = (
        left_count > 3 and right_count > 3
        and min(left_count, right_count) / max(left_count, right_count) > 0.3
    )

    if is_two_column:
        # 双栏：先排左栏，再排右栏
        mid_x = page_width * 0.5
        left_blocks = sorted(
            [b for b in text_blocks if b["x0"] < mid_x],
            key=lambda b: b["y0"]
        )
        right_blocks = sorted(
            [b for b in text_blocks if b["x0"] >= mid_x],
            key=lambda b: b["y0"]
        )
        ordered_blocks = left_blocks + right_blocks
    else:
        # 单栏：按 y0 排序
        ordered_blocks = sorted(text_blocks, key=lambda b: b["y0"])

    # 过滤页眉页脚
    lines = []
    for block in ordered_blocks:
        for line_text in block["text"].split("\n"):
            cleaned = line_text.strip()
            if cleaned and cleaned not in header_footer_lines:
                lines.append(cleaned)

    return "\n".join(lines)


def _detect_header_footer(doc) -> set:
    """检测重复出现的页眉页脚"""
    page_count = len(doc)
    if page_count < 3:
        return set()

    # 采样前几页和后几页的首尾行
    first_lines = {}
    last_lines = {}

    for page_num in range(min(5, page_count)):
        text = doc[page_num].get_text().strip()
        if not text:
            continue
        lines = text.split("\n")
        if lines:
            first = lines[0].strip()[:80]
            first_lines[first] = first_lines.get(first, 0) + 1
        if len(lines) > 1:
            last = lines[-1].strip()[:80]
            last_lines[last] = last_lines.get(last, 0) + 1

    # 出现 3 次以上的首尾行视为页眉页脚
    hf = set()
    for text, count in first_lines.items():
        if count >= 3 and len(text) > 3:
            hf.add(text)
    for text, count in last_lines.items():
        if count >= 3 and len(text) > 3:
            # 页脚常含页码，用正则匹配
            if re.match(r'^\d+$', text.strip()):
                hf.add(text)
            elif re.search(r'page\s*\d+', text, re.I):
                hf.add(text)
    return hf


# ── 表格提取 ──────────────────────────────────────────────

def _table_to_text(table) -> str:
    """将 PyMuPDF Table 对象转为可读文本"""
    try:
        rows = []
        for row in table.extract():
            cells = [str(cell).strip() if cell else "" for cell in row]
            rows.append(" | ".join(cells))
        return "\n".join(rows)
    except Exception:
        return ""


# ── 元数据提取 ──────────────────────────────────────────────

def _extract_title_from_text(text: str) -> str:
    """从文本中提取标题（第一个有效非空行）"""
    lines = text.strip().split("\n")
    for line in lines[:10]:
        line = line.strip()
        # 跳过过短、纯数字、常见无用行
        if len(line) < 5:
            continue
        if re.match(r'^[\d\s]+$', line):
            continue
        if re.match(r'^(abstract|摘要|keywords|关键词|received|accepted|doi)', line, re.I):
            continue
        # 跳过包含期刊名特征的行
        if re.search(r'(journal|proceedings|transactions|issn|volume)', line, re.I):
            continue
        return line
    return ""


def _extract_authors_from_text(text: str) -> list:
    """从文本中提取作者列表"""
    lines = text.strip().split("\n")
    # 作者通常在标题之后、摘要之前
    title_idx = -1
    abstract_idx = -1

    for i, line in enumerate(lines[:20]):
        stripped = line.strip()
        if re.match(r'^(abstract|摘要|摘\s*要)', stripped, re.I):
            abstract_idx = i
            break
        if len(stripped) > 20 and not re.match(r'^[\d\s]+$', stripped):
            if title_idx < 0:
                title_idx = i

    if title_idx >= 0 and abstract_idx > title_idx:
        # 标题和摘要之间通常是作者行
        author_block = " ".join(lines[title_idx + 1:abstract_idx]).strip()
        return _parse_author_string(author_block)

    return []


def _parse_author_string(text: str) -> list:
    """解析作者字符串"""
    # 移除上标数字和机构标记
    text = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§¶]+', '', text)
    text = re.sub(r'\d+', '', text)

    # 常见分隔模式
    # "Author1, Author2, Author3" 或 "Author1 and Author2"
    # 中文："张三, 李四, 王五" 或 "张三 李四 王五"

    authors = []

    # 尝试逗号分隔
    if ',' in text:
        parts = text.split(',')
        for part in parts:
            name = part.strip()
            if 2 <= len(name) <= 40 and not re.search(r'(university|institute|school|college|大学|学院|研究所)', name, re.I):
                authors.append(name)
    # 尝试 and 分隔
    elif ' and ' in text.lower():
        parts = re.split(r'\s+and\s+', text, flags=re.I)
        for part in parts:
            name = part.strip()
            if 2 <= len(name) <= 40:
                authors.append(name)

    return authors[:10]  # 最多10个作者


def _extract_doi_from_text(text: str) -> str:
    """从文本中提取DOI"""
    # 匹配 DOI 模式
    patterns = [
        r'(?:doi|DOI)\s*[:：]?\s*(10\.\d{4,}/[^\s,;)\]\"<]+)',
        r'(10\.\d{4,}/[^\s,;)\]\"<]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:3000])  # 只在前3000字符中搜索
        if match:
            doi = match.group(1).rstrip('.')
            return doi
    return ""


def _extract_abstract_from_text(text: str) -> str:
    """从文本中提取摘要"""
    # 查找 Abstract/摘要 标记
    match = re.search(
        r'(?:^|\n)\s*(?:abstract|摘\s*要)\s*[:：]?\s*\n?(.*?)(?:\n\s*(?:keywords|关键词|1[\s\.]|introduction|引言|I\.\s))',
        text[:5000],
        re.I | re.S
    )
    if match:
        abstract = match.group(1).strip()
        # 清理：移除多余空白
        abstract = re.sub(r'\s+', ' ', abstract)
        if len(abstract) > 50:
            return abstract[:1000]

    return ""


def _extract_references_from_text(text: str) -> list:
    """
    从文本中提取参考文献列表

    Returns
    -------
    list[dict], 每个元素包含:
        - raw: 原始文本
        - authors: 作者列表
        - year: 年份
        - title: 标题
        - doi: DOI
    """
    # 查找参考文献区域
    ref_start = None
    patterns = [
        r'\n\s*(?:References|参考文献|Bibliography|Literature Cited)\s*\n',
        r'\n\s*(?:REFERENCES|REFERENCES)\s*\n',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            ref_start = match.end()
            break

    if ref_start is None:
        return []

    ref_text = text[ref_start:]

    # 按编号分割参考文献
    # 匹配 [1], [2], 1., 2. 等格式
    ref_pattern = r'(?:^|\n)\s*(?:\[(\d+)\]|(\d+)\.)\s+'
    splits = list(re.finditer(ref_pattern, ref_text))

    references = []
    if splits:
        for i, match in enumerate(splits):
            start = match.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(ref_text)
            raw = ref_text[start:end].strip()
            raw = re.sub(r'\s+', ' ', raw)  # 合并多余空白
            if len(raw) > 20:
                ref = _parse_single_reference(raw)
                references.append(ref)
    else:
        # 没有编号，尝试按空行分割
        paragraphs = re.split(r'\n\s*\n', ref_text[:10000])
        for para in paragraphs:
            raw = para.strip()
            raw = re.sub(r'\s+', ' ', raw)
            if len(raw) > 30:
                ref = _parse_single_reference(raw)
                references.append(ref)

    return references[:100]  # 最多100条


def _parse_single_reference(raw: str) -> dict:
    """解析单条参考文献"""
    ref = {
        "raw": raw,
        "authors": [],
        "year": 0,
        "title": "",
        "doi": "",
    }

    # 提取年份
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw)
    if year_match:
        ref["year"] = int(year_match.group(1))

    # 提取 DOI
    doi_match = re.search(r'(10\.\d{4,}/[^\s,;)\]\"<]+)', raw)
    if doi_match:
        ref["doi"] = doi_match.group(1).rstrip('.')

    # 提取作者（年份之前的部分）
    if year_match:
        author_part = raw[:year_match.start()].strip()
        # 移除开头的编号
        author_part = re.sub(r'^[\[\]\d\.\s]+', '', author_part)
        ref["authors"] = _parse_author_string(author_part)

    # 提取标题（年份之后、期刊/出版社之前的部分）
    if year_match:
        after_year = raw[year_match.end():]
        # 常见分隔：句号、逗号后跟期刊名
        title_match = re.match(r'[\.\s,]*(.+?)(?:\.\s*(?:Journal|Proceedings|In:|Vol|https?://|doi|10\.)|\.\s*$)',
                               after_year, re.I)
        if title_match:
            ref["title"] = title_match.group(1).strip().rstrip('.')

    return ref


# ── 文本清理 ──────────────────────────────────────────────

def _clean_text(text: str, header_footer_lines: set) -> str:
    """清理提取的文本"""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # 跳过页眉页脚
        if stripped in header_footer_lines:
            continue
        # 跳过纯页码
        if re.match(r'^\d{1,3}$', stripped):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)
