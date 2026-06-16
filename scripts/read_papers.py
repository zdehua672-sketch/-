# -*- coding: utf-8 -*-
"""
独立文献搜索命令 — 不在主管线中运行

用法：
  python scripts/read_papers.py                        # 在线搜索+本地读取
  python scripts/read_papers.py --local papers/        # 只读本地目录
  python scripts/read_papers.py --query "sewer CH4"    # 自定义搜索词
  python scripts/read_papers.py --skip-search          # 跳过在线搜索

结果保存到 knowledge_store/papers_read.json，主管线自动加载。
"""
import sys, os, json, glob, time, logging, argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format='%(name)s %(message)s')
logger = logging.getLogger('read_papers')

STORE_DIR = 'knowledge_store'
OUTPUT_FILE = os.path.join(STORE_DIR, 'papers_read.json')
PATTERNS_FILE = os.path.join(STORE_DIR, 'learned_patterns.json')


# ============================================================
# 1. 在线搜索文献
# ============================================================

def search_online(queries: list, max_per_query: int = 8) -> list:
    """使用 AutoPaperFinder 在线搜索文献"""
    from auto_paper_finder import AutoPaperFinder
    from self_evolving_engine import KnowledgeStore

    store = KnowledgeStore(STORE_DIR)
    finder = AutoPaperFinder(store=store)

    all_papers = []
    for q in queries:
        try:
            logger.info(f"搜索: {q}")
            papers = finder.find_papers(q, max_results=max_per_query)
            logger.info(f"  -> {len(papers)} 篇")
            all_papers.extend(papers)
            time.sleep(3)  # 避免限速
        except Exception as e:
            logger.warning(f"  搜索失败: {e}")

    # 去重
    seen = set()
    unique = []
    for p in all_papers:
        key = p.get('paper_id', p.get('title', '')).strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


# ============================================================
# 2. 本地文献读取
# ============================================================

def read_local(papers_dir: str) -> list:
    """读取本地 PDF/TXT/MD 文献"""
    from paper_reader import PaperReader
    reader = PaperReader()

    papers = []
    for ext in ['*.pdf', '*.txt', '*.md']:
        for filepath in glob.glob(os.path.join(papers_dir, ext)):
            try:
                content = reader.read(filepath, fetch_metadata=False)
                if content and content.metadata:
                    papers.append({
                        'path': filepath,
                        'title': content.metadata.title,
                        'authors': content.metadata.authors,
                        'abstract': content.metadata.abstract,
                        'sections': len(content.sections),
                        'references': len(content.references),
                        'source': 'local',
                    })
                    logger.info(f"  读取: {content.metadata.title[:50]}")
            except Exception as e:
                logger.warning(f"  读取失败 {filepath}: {e}")

    return papers


# ============================================================
# 3. 写作模式学习
# ============================================================

def learn_patterns(papers: list) -> dict:
    """从已读论文中提取写作模式"""
    if not papers:
        logger.info("无论文，跳过模式学习")
        return {}

    from pattern_learner import SentencePatternLearner, DiscussionLearner, MechanismLearner

    sentence_learner = SentencePatternLearner()
    discussion_learner = DiscussionLearner()
    mechanism_learner = MechanismLearner()

    all_patterns = []
    all_structures = []
    all_mechanisms = []

    for p in papers:
        abstract = p.get('abstract', '')
        if abstract and len(abstract) > 50:
            patterns = sentence_learner.extract_patterns(abstract)
            all_patterns.extend(patterns)

    result = {
        'sentence_patterns': all_patterns[:50],
        'discussion_structures': all_structures,
        'mechanisms': all_mechanisms,
        'paper_count': len(papers),
        'learned_at': datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"模式学习: {len(all_patterns)} 个句式模式")
    return result


# ============================================================
# 4. 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='独立文献搜索命令')
    parser.add_argument('--local', type=str, help='本地文献目录路径')
    parser.add_argument('--query', type=str, nargs='+', help='自定义搜索关键词')
    parser.add_argument('--skip-search', action='store_true', help='跳过在线搜索')
    parser.add_argument('--max-per-query', type=int, default=8, help='每个查询最大结果数')
    args = parser.parse_args()

    print("=" * 60)
    print("  独立文献搜索命令")
    print("=" * 60)

    all_papers = []

    # 1. 本地读取
    if args.local:
        print(f"\n[1] 读取本地文献: {args.local}")
        local_papers = read_local(args.local)
        all_papers.extend(local_papers)
        print(f"    本地读取: {len(local_papers)} 篇")

    # 2. 在线搜索
    if not args.skip_search:
        print(f"\n[2] 在线搜索文献...")
        if args.query:
            queries = args.query
        else:
            # 默认搜索词（污水管网碳排放领域）
            queries = [
                'sewer greenhouse gas methane emission',
                'wastewater dissolved organic carbon biodegradation',
                'sewage network N2O nitrous oxide production',
                'sewer biofilm carbon transformation microbial',
                'wastewater collection system carbon footprint',
            ]

        online_papers = search_online(queries, args.max_per_query)
        all_papers.extend(online_papers)
        print(f"    在线搜索: {len(online_papers)} 篇")

    # 3. 去重合并
    seen = set()
    unique = []
    for p in all_papers:
        key = p.get('title', '').strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)

    print(f"\n[3] 合并去重: {len(unique)} 篇")

    # 4. 写作模式学习
    print(f"\n[4] 写作模式学习...")
    patterns = learn_patterns(unique)

    # 5. 保存结果
    os.makedirs(STORE_DIR, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[5] 文献数据已保存: {OUTPUT_FILE}")

    if patterns:
        with open(PATTERNS_FILE, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2, default=str)
        print(f"    写作模式已保存: {PATTERNS_FILE}")

    # 6. 汇总
    print(f"\n{'=' * 60}")
    print(f"  完成！")
    print(f"  文献: {len(unique)} 篇")
    print(f"  句式: {len(patterns.get('sentence_patterns', []))} 个")
    print(f"  文件: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
