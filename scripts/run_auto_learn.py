# -*- coding: utf-8 -*-
"""
自动学习：为数据发现的变量对搜索文献并学习机制
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from self_evolving_engine import EvolutionEngine

engine = EvolutionEngine()
engine.initialize()

# 数据发现的关键主题（知识库中缺少机制的变量对）
topics = [
    'sewage pipeline nitrous oxide N2O emissions',
    'wastewater nitrogen ammonium nitrification',
    'sewage CO2 carbon dioxide seasonal variation',
    'dissolved oxygen sewage greenhouse gas methane',
]

total_learned = {'papers': 0, 'patterns': 0, 'mechanisms': 0}

for topic in topics:
    print(f"\n{'='*60}")
    print(f"  学习: {topic}")
    print(f"{'='*60}")

    report = engine.auto_learn(topic, max_papers=5, read_top_n=2)

    total_learned['papers'] += report.get('papers_read', 0)
    total_learned['patterns'] += report.get('patterns_learned', 0)
    total_learned['mechanisms'] += report.get('mechanisms_learned', 0)

    print(f"  结果: {report.get('papers_found', 0)}篇找到, "
          f"{report.get('papers_read', 0)}篇读取, "
          f"{report.get('mechanisms_learned', 0)}条机制, "
          f"{report.get('patterns_learned', 0)}条句式")

    if report.get('error'):
        print(f"  错误: {report['error']}")

print(f"\n{'='*60}")
print(f"  学习完成!")
print(f"  总计: {total_learned['papers']}篇论文, "
      f"{total_learned['mechanisms']}条机制, "
      f"{total_learned['patterns']}条句式")
print(f"{'='*60}")

# 验证知识库更新
from knowledge_memory import KnowledgeMemory
memory = KnowledgeMemory()
stats = memory.get_stats()
print(f"\n知识库状态: {stats['total_entries']}条知识")

# 测试召回
test_queries = [
    'N2O NaCl 相关',
    'TN 铵态氮 氮转化',
    'CO2 季节变化',
    'DO CH4 甲烷',
]
for q in test_queries:
    results = memory.recall(q, top_k=2)
    print(f"\n查询: {q}")
    for r in results:
        val = r['value']
        if isinstance(val, dict):
            print(f"  [{r['category']}] {val.get('pattern', val.get('mechanism', ''))[:80]}")
