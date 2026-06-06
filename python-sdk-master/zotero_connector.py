"""
Zotero 文献库连接器
===================
从 Zotero 本地 SQLite 数据库读取文献元数据和 PDF 附件路径。

借鉴自 LitMind (https://github.com/meishiwhy/Literature-Mind) 的 litmind-zotero 模块，
适配到本项目的 PaperReader 体系。

只读操作，绝不修改 Zotero 数据库。

用法:
    from zotero_connector import discover_zotero, export_zotero_papers

    # 自动发现 Zotero 数据库
    db_path = discover_zotero()

    # 导出所有文献元数据
    papers = export_zotero_papers(db_path)

    # 导出并过滤（只有PDF的）
    papers_with_pdf = [p for p in papers if p['pdfPath']]

    # 配合 PaperReader 批量导入
    from paper_reader import PaperReader
    reader = PaperReader()
    for p in papers_with_pdf:
        if p['pdfPath']:
            reader.read(p['pdfPath'])
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────

@dataclass
class ZoteroAuthor:
    """作者信息"""
    firstName: str = ""
    lastName: str = ""

    def __str__(self) -> str:
        if self.firstName and self.lastName:
            return f"{self.lastName}, {self.firstName}"
        return self.lastName or self.firstName

    def to_dict(self):
        return asdict(self)


@dataclass
class ZoteroPaper:
    """Zotero 文献元数据"""
    key: str = ""                           # Zotero item key
    title: str = ""
    authors: list = field(default_factory=list)  # list[ZoteroAuthor]
    year: int = 0
    doi: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    abstract: str = ""
    pdfPath: str = ""                       # 主 PDF 路径
    pdfPaths: list = field(default_factory=list)  # 所有 PDF 路径
    tags: list = field(default_factory=list)
    collections: list = field(default_factory=list)
    url: str = ""
    dateAdded: str = ""
    dateModified: str = ""
    itemType: str = "journalArticle"

    def to_dict(self):
        d = asdict(self)
        d['authors'] = [a.to_dict() if isinstance(a, ZoteroAuthor) else a
                        for a in self.authors]
        return d


@dataclass
class ZoteroExportReport:
    """导出统计报告"""
    total: int = 0
    standalone_pdfs: int = 0
    with_pdf: int = 0
    with_doi: int = 0
    with_abstract: int = 0
    errors: list = field(default_factory=list)

    def print_report(self):
        total_all = self.total + self.standalone_pdfs
        print(f"\n{'=' * 50}")
        print(f"  Zotero 文献库导出报告")
        print(f"{'=' * 50}")
        print(f"  有元数据的文献:   {self.total}")
        print(f"  独立 PDF 附件:    {self.standalone_pdfs}")
        print(f"  总导出文献数:     {total_all}")
        if total_all > 0:
            print(f"  有 PDF:           {self.with_pdf} ({self.with_pdf / total_all * 100:.1f}%)")
            print(f"  有 DOI:           {self.with_doi}")
            print(f"  有摘要:           {self.with_abstract}")
        if self.errors:
            print(f"\n  错误 ({len(self.errors)}):")
            for e in self.errors[:5]:
                print(f"    - {e}")
        print(f"{'=' * 50}\n")


# ── 内部字段映射 ──────────────────────────────────────────

_FIELD_NAMES: dict[int, str] = {}


# ── 路径解析 ──────────────────────────────────────────────

def _resolve_attachment_path(raw: str) -> str:
    """将 Zotero 存储路径转为真实文件路径"""
    if not raw:
        return ""
    if raw.startswith("storage:"):
        return raw[len("storage:"):]
    if raw.startswith("attachments:"):
        return raw[len("attachments:"):]
    if raw.startswith("file://"):
        return raw[len("file://"):].lstrip("/")
    return raw


def _extract_meta_from_filename(filename: str) -> dict:
    """从 PDF 文件名尽量提取标题、作者、年份"""
    name = Path(filename).stem.strip()
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", name)
    year_str = years[0] if years else ""
    cleaned = re.sub(
        r"[\s_\-]*(\.pdf|英文|中文|全文|终稿|修改稿|定稿)\s*$", "", name, flags=re.I
    ).strip()
    return {
        "title": cleaned,
        "year": int(year_str) if year_str.isdigit() else 0,
        "filename": filename,
    }


# ── 数据库发现 ──────────────────────────────────────────────

def discover_zotero(custom_path: Optional[str] = None) -> Path:
    """
    自动发现 Zotero 数据库路径

    Parameters
    ----------
    custom_path : str, 自定义路径（可选）

    Returns
    -------
    Path, zotero.sqlite 的路径

    Raises
    ------
    FileNotFoundError, 如果找不到数据库
    """
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"指定路径不存在: {custom_path}")

    candidates: list[Path] = []

    # Windows: APPDATA
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for base in [Path(appdata) / "Zotero" / "Zotero" / "Profiles",
                     Path(appdata) / "Zotero" / "Profiles"]:
            if base.exists():
                candidates.extend(sorted(base.glob("*/zotero.sqlite")))

    # macOS / Linux: HOME
    home = os.environ.get("HOME", "")
    if home:
        for p in [Path(home) / "Zotero" / "zotero.sqlite",
                  Path(home) / ".zotero" / "zotero.sqlite"]:
            if p.exists():
                candidates.append(p)

    if candidates:
        logger.info(f"Found Zotero database: {candidates[0]}")
        return candidates[0]

    raise FileNotFoundError(
        "未找到 zotero.sqlite。请通过 custom_path 参数指定路径，"
        "或确认 Zotero 已安装并至少打开过一次。"
    )


# ── 数据库连接 ──────────────────────────────────────────────

def _connect(db_path: Path) -> sqlite3.Connection:
    """只读连接 Zotero 数据库"""
    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    conn.execute("PRAGMA query_only = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _load_field_names(conn: sqlite3.Connection) -> None:
    """加载字段ID→名称映射"""
    _FIELD_NAMES.clear()
    for row in conn.execute("SELECT fieldID, fieldName FROM fields"):
        _FIELD_NAMES[row["fieldID"]] = row["fieldName"]


# ── 数据提取 ──────────────────────────────────────────────

def _get_creators(conn: sqlite3.Connection, item_id: int) -> list[ZoteroAuthor]:
    cur = conn.execute("""
        SELECT c.firstName, c.lastName, ic.orderIndex
        FROM itemCreators ic JOIN creators c ON ic.creatorID = c.creatorID
        WHERE ic.itemID = ? ORDER BY ic.orderIndex
    """, (item_id,))
    return [ZoteroAuthor(firstName=r["firstName"] or "", lastName=r["lastName"] or "")
            for r in cur]


def _get_item_data(conn: sqlite3.Connection, item_id: int) -> dict[str, str]:
    cur = conn.execute("""
        SELECT id.fieldID, idv.value
        FROM itemData id JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE id.itemID = ?
    """, (item_id,))
    return {_FIELD_NAMES.get(r["fieldID"], f"f{r['fieldID']}"): r["value"] for r in cur}


def _get_attachments(conn: sqlite3.Connection, item_id: int) -> list[str]:
    cur = conn.execute("""
        SELECT path FROM itemAttachments
        WHERE parentItemID = ? AND contentType = 'application/pdf'
        ORDER BY itemID
    """, (item_id,))
    paths = []
    for row in cur:
        raw = row["path"] or ""
        if raw.startswith("attachments:"):
            raw = raw[len("attachments:"):]
        elif raw.startswith("file://"):
            raw = raw[len("file://"):].lstrip("/")
        paths.append(raw)
    return paths


def _get_tags(conn: sqlite3.Connection, item_id: int) -> list[str]:
    cur = conn.execute("""
        SELECT t.name FROM itemTags it JOIN tags t ON it.tagID = t.tagID
        WHERE it.itemID = ? ORDER BY t.name
    """, (item_id,))
    return [r["name"] for r in cur]


def _get_collections(conn: sqlite3.Connection, item_id: int) -> list[str]:
    cur = conn.execute("""
        SELECT c.collectionName
        FROM collectionItems ci JOIN collections c ON ci.collectionID = c.collectionID
        WHERE ci.itemID = ?
    """, (item_id,))
    return [r["collectionName"] for r in cur]


# ── 主导出流程 ──────────────────────────────────────────────

def export_zotero_papers(
    db_path: Path = None,
    report: ZoteroExportReport = None,
    library_id: int = 1,
) -> list[ZoteroPaper]:
    """
    从 Zotero 数据库导出所有文献元数据

    Parameters
    ----------
    db_path : Path, 数据库路径（None则自动发现）
    report : ZoteroExportReport, 统计报告（可选）
    library_id : int, Zotero library ID（默认1）

    Returns
    -------
    list[ZoteroPaper], 文献列表
    """
    if db_path is None:
        db_path = discover_zotero()
    if report is None:
        report = ZoteroExportReport()

    conn = _connect(db_path)
    _load_field_names(conn)

    # 查询所有非附件、非笔记的条目
    cur = conn.execute("""
        SELECT itemID, key, dateAdded, dateModified FROM items
        WHERE itemTypeID NOT IN (1, 14) AND libraryID = ?
        ORDER BY dateAdded DESC
    """, (library_id,))

    results: list[ZoteroPaper] = []
    for row in cur:
        item_id, key = row["itemID"], row["key"]
        try:
            data = _get_item_data(conn, item_id)
            year_str = re.sub(r"[^0-9].*", "", data.get("date", ""))
            pdfs = _get_attachments(conn, item_id)
            meta = ZoteroPaper(
                key=key,
                title=data.get("title", ""),
                authors=_get_creators(conn, item_id),
                year=int(year_str) if year_str.isdigit() else 0,
                doi=data.get("DOI", ""),
                journal=data.get("publicationTitle", "") or data.get("journalAbbreviation", ""),
                volume=data.get("volume", ""),
                issue=data.get("issue", ""),
                pages=data.get("pages", ""),
                abstract=(data.get("abstractNote", "") or "")[:500],
                pdfPath=pdfs[0] if pdfs else "",
                pdfPaths=pdfs,
                tags=_get_tags(conn, item_id),
                collections=_get_collections(conn, item_id),
                url=data.get("url", ""),
                dateAdded=row["dateAdded"] or "",
                dateModified=row["dateModified"] or "",
            )
            results.append(meta)
            report.total += 1
            if meta.pdfPath:
                report.with_pdf += 1
            if meta.doi:
                report.with_doi += 1
            if meta.abstract:
                report.with_abstract += 1
        except Exception as e:
            report.errors.append(f"[{key}] {e}")

    # 导出独立 PDF 附件（没有父条目的 PDF）
    standalone_cur = conn.execute("""
        SELECT i.itemID, i.key, i.dateAdded, i.dateModified,
               ia.title AS filename, ia.path, ia.contentType
        FROM items i
        JOIN itemAttachments ia ON i.itemID = ia.itemID
        WHERE i.itemTypeID = 14
          AND i.libraryID = ?
          AND ia.contentType = 'application/pdf'
          AND (ia.parentItemID IS NULL
               OR NOT EXISTS (
                   SELECT 1 FROM items pi
                   WHERE pi.itemID = ia.parentItemID
                     AND pi.itemTypeID NOT IN (1, 14)
               ))
        ORDER BY i.dateAdded DESC
    """, (library_id,))

    for row in standalone_cur:
        try:
            raw_path = row["path"] or ""
            resolved = _resolve_attachment_path(raw_path)
            filename = row["filename"] or Path(resolved).name
            meta_from_name = _extract_meta_from_filename(filename)

            meta = ZoteroPaper(
                key=row["key"],
                title=meta_from_name["title"],
                year=meta_from_name.get("year", 0),
                pdfPath=resolved,
                pdfPaths=[resolved] if resolved else [],
                itemType="standalone_pdf",
                dateAdded=row["dateAdded"] or "",
                dateModified=row["dateModified"] or "",
            )
            results.append(meta)
            report.standalone_pdfs += 1
            if meta.pdfPath:
                report.with_pdf += 1
        except Exception as e:
            report.errors.append(f"[{row['key']}] {e}")

    conn.close()
    return results


def export_zotero_to_json(papers: list[ZoteroPaper], output_path: str) -> None:
    """导出为JSON文件"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([p.to_dict() for p in papers], f, ensure_ascii=False, indent=2)
    print(f"  导出完成: {output_path} ({len(papers)}篇)")


# ── CLI 入口 ──────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    args = sys.argv[1:]
    cmd = args[0] if args else "export"

    if cmd == "discover":
        db = discover_zotero(args[1] if len(args) > 1 else None)
        print(f"Zotero 数据库: {db}")

    elif cmd == "export":
        report = ZoteroExportReport()
        papers = export_zotero_papers(report=report)
        report.print_report()

        output = args[1] if len(args) > 1 else "zotero_papers.json"
        export_zotero_to_json(papers, output)

    elif cmd == "stats":
        report = ZoteroExportReport()
        papers = export_zotero_papers(report=report)
        report.print_report()

        # 按年份统计
        years = {}
        for p in papers:
            y = p.year or 0
            years[y] = years.get(y, 0) + 1
        print("年份分布:")
        for y in sorted(years.keys()):
            if y > 0:
                print(f"  {y}: {years[y]}篇")

        # 按期刊统计
        journals = {}
        for p in papers:
            j = p.journal or "未知"
            journals[j] = journals.get(j, 0) + 1
        print("\n期刊分布 (Top 10):")
        for j, c in sorted(journals.items(), key=lambda x: -x[1])[:10]:
            print(f"  {j}: {c}篇")

    else:
        print("用法:")
        print("  python zotero_connector.py discover     # 发现Zotero数据库")
        print("  python zotero_connector.py export       # 导出为JSON")
        print("  python zotero_connector.py stats        # 查看统计")
