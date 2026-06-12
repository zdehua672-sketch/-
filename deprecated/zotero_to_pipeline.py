"""
Zotero -> 主系统 Pipeline 桥梁
==============================
将 Zotero storage 中的污水管网文献通过 PaperReader 正确接入系统管道：
  PDF -> PaperReader -> SQLite + RAG + KnowledgeStore + LiteratureMemory

用法:
    python zotero_to_pipeline.py                  # 读取 sewer_network_papers.json 中的 15 篇
    python zotero_to_pipeline.py --all            # 读取 zotero_storage_papers.json 中全部 63 篇
    python zotero_to_pipeline.py --rebuild-matrix # 读取后重建文献矩阵
"""

import json
import sys
from pathlib import Path


def load_paper_list(filter_sewer: bool = True) -> list:
    """加载文献路径列表"""
    if filter_sewer:
        src = Path("sewer_network_papers.json")
    else:
        src = Path("zotero_storage_papers.json")

    if not src.exists():
        print(f"[错误] {src} 不存在")
        return []

    with open(src, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 只保留实际存在的 PDF
    valid = []
    for p in papers:
        pdf_path = p.get("pdf_path", "")
        if pdf_path and Path(pdf_path).exists():
            valid.append(pdf_path)
        else:
            print(f"  [跳过] 文件不存在: {pdf_path}")

    return valid


def read_papers_into_system(pdf_paths: list, rebuild_matrix: bool = False):
    """通过 orchestrator 的 step1_read_batch 将文献接入系统"""
    from orchestrator import AcademicPipeline

    pipe = AcademicPipeline()

    # Step 1: 批量读取 -> SQLite + RAG + KnowledgeStore
    papers = pipe.step1_read_batch(pdf_paths, fetch_metadata=False)

    # Step 2: 构建文献矩阵
    if rebuild_matrix and papers:
        print("\n[Pipeline] 构建文献矩阵...")
        pipe.step2_matrix(auto_themes=True)

    return papers


def main():
    args = sys.argv[1:]
    filter_sewer = "--all" not in args
    rebuild_matrix = "--rebuild-matrix" in args

    mode = "污水管网相关" if filter_sewer else "全部"
    print(f"=" * 60)
    print(f"Zotero -> 主系统 Pipeline")
    print(f"模式: {mode}文献")
    print(f"=" * 60)

    # 1. 加载文献列表
    print(f"\n[1] 加载文献列表...")
    pdf_paths = load_paper_list(filter_sewer)
    if not pdf_paths:
        print("[错误] 没有可用的 PDF 文件")
        return
    print(f"  找到 {len(pdf_paths)} 个 PDF 文件")

    # 2. 送入系统管道
    print(f"\n[2] 送入系统管道...")
    papers = read_papers_into_system(pdf_paths, rebuild_matrix)

    # 3. 总结
    print(f"\n{'=' * 60}")
    print(f"完成！成功读取 {len(papers)}/{len(pdf_paths)} 篇文献")
    print(f"{'=' * 60}")
    print(f"\n数据已写入:")
    print(f"  - SQLite:     knowledge_store/papers.db")
    print(f"  - 知识库:     knowledge_store/resources.json")
    print(f"  - RAG 索引:   rag_system/data/")
    if rebuild_matrix:
        print(f"  - 文献矩阵:   knowledge_store/literature_matrix.json")
        print(f"  - 论文评估:   knowledge_store/paper_assessments.json")
    print(f"\n后续操作:")
    print(f"  python orchestrator.py status          # 查看系统状态")
    print(f"  python orchestrator.py matrix           # 查看文献矩阵")
    print(f"  python orchestrator.py motivation       # 生成研究动机")


if __name__ == "__main__":
    main()
