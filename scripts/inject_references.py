# -*- coding: utf-8 -*-
"""
从papers.db中提取已有论文，注入到知识库resources中
"""
import sys, io, sqlite3, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from self_evolving_engine import KnowledgeStore
store = KnowledgeStore()

# 从papers.db读取论文
conn = sqlite3.connect('knowledge_store/papers.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 获取论文基本信息
cursor.execute('''
    SELECT p.paper_id, p.title, p.authors, p.year, p.abstract,
           p.venue, p.doi, p.citation_count
    FROM papers p
    WHERE p.title IS NOT NULL AND p.title != ''
''')
papers = cursor.fetchall()

# 获取章节文本（用于提取abstract如果缺失）
cursor.execute('''
    SELECT paper_id, section_type, text
    FROM sections
    WHERE section_type IN ('abstract', 'introduction')
    LIMIT 100
''')
sections = {}
for row in cursor.fetchall():
    pid = row['paper_id']
    if pid not in sections:
        sections[pid] = {}
    sections[pid][row['section_type']] = row['text'][:500] if row['text'] else ''

conn.close()

# 注入到resources
count = 0
for paper in papers:
    pid = paper['paper_id']
    title = paper['title']
    if not title or len(title) < 5:
        continue

    # 获取abstract
    abstract = paper['abstract'] or ''
    if not abstract and pid in sections:
        abstract = sections[pid].get('abstract', '') or sections[pid].get('introduction', '')[:300]

    # 解析authors
    authors = paper['authors'] or ''
    if isinstance(authors, str):
        # 尝试解析为列表
        if ',' in authors:
            authors = [a.strip() for a in authors.split(',')][:5]
        else:
            authors = [authors]

    key = f'paper_{pid[:30].replace(" ", "_").replace("/", "_")}'

    resource = {
        'type': 'academic_paper',
        'title': title,
        'authors': authors,
        'year': paper['year'] or 2020,
        'venue': paper['venue'] or '',
        'doi': paper['doi'] or '',
        'citation_count': paper['citation_count'] or 0,
        'abstract': abstract,
        'source': 'papers.db',
    }

    store.set('resources', key, resource, source='papers.db', confidence=0.8)
    count += 1
    print(f'  + [{paper["year"]}] {title[:50]}')

print(f'\n注入完成: {count}篇论文')

# 验证
from knowledge_memory import KnowledgeMemory
memory = KnowledgeMemory()
stats = memory.get_stats()
print(f'知识库resources: {stats["categories"].get("resources", 0)}条')

# 测试召回
test_queries = [
    'sewage methane CH4 emission',
    'sewer CO2 greenhouse gas',
    'carbon phase distribution wastewater',
    '污水管网 温室气体',
]
for q in test_queries:
    results = memory.recall(q, category='resources', top_k=2)
    print(f'\n查询: {q}')
    for r in results:
        val = r['value']
        if isinstance(val, dict):
            print(f'  [{val.get("year")}] {val.get("title", "")[:50]}')
