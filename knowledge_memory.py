# -*- coding: utf-8 -*-
"""
知识记忆系统 - KnowledgeMemory
统一记忆接口，让其他模块查询学习到的知识。

写作模块调用：memory.get_writing_context("CH4季节差异", "discussion")
分析模块调用：memory.recall("TOC和CH4的关系")
审稿模块调用：memory.recall("常见写作错误", category='review_rules')
"""

import json
import os
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class KnowledgeMemory:
    """
    统一知识记忆接口。

    提供：
    - recall(query, category) — 从记忆中检索相关知识
    - remember(content, category, source) — 存入新知识
    - get_writing_context(topic, section_type) — 为写作模块组装上下文
    - get_stats() — 记忆统计
    """

    def __init__(self, store=None, store_dir=None):
        """
        Parameters
        ----------
        store : KnowledgeStore or None, 已有的知识库实例
        store_dir : str or None, 知识库目录（store 为 None 时使用）
        """
        if store:
            self.store = store
        else:
            from self_evolving_engine import KnowledgeStore
            self.store = KnowledgeStore(store_dir)

    def recall(self, query: str, category: str = None,
               top_k: int = 5) -> List[Dict]:
        """
        从记忆中检索相关知识。

        Parameters
        ----------
        query : str, 查询内容
        category : str or None, 指定分类（None 时搜索全部）
        top_k : int, 返回数量

        Returns
        -------
        list of dict: [{'key': str, 'value': Any, 'category': str, 'confidence': float, 'relevance': float}]
        """
        results = []

        categories = [category] if category else [
            'mechanisms', 'writing_templates', 'domain_terms',
            'methods', 'review_rules', 'resources'
        ]

        query_lower = query.lower()
        query_tokens = set(re.findall(r'[\w一-鿿]+', query_lower))

        for cat in categories:
            entries = self.store.get(cat)
            for key, entry in entries.items():
                val = entry.get('value', entry) if isinstance(entry, dict) else entry
                if not isinstance(val, dict):
                    val = {'raw': val}

                # 计算相关性
                relevance = self._calc_relevance(query_tokens, key, val)
                if relevance > 0.1:
                    results.append({
                        'key': key,
                        'value': val,
                        'category': cat,
                        'confidence': entry.get('confidence', 0.5) if isinstance(entry, dict) else 0.5,
                        'relevance': relevance,
                    })

        # 按 relevance × confidence 排序
        results.sort(key=lambda x: x['relevance'] * x['confidence'], reverse=True)
        return results[:top_k]

    def remember(self, content: dict, category: str, source: str = 'manual',
                 confidence: float = 0.8, key: str = None) -> str:
        """
        存入新知识。

        Parameters
        ----------
        content : dict, 知识内容
        category : str, 知识分类
        source : str, 来源
        confidence : float, 置信度
        key : str or None, 存储键。None 时自动生成。

        Returns
        -------
        str: 存储键
        """
        if key is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            key = f"mem_{timestamp}_{hash(str(content)) % 10000:04d}"

        self.store.set(category, key, content, source=source, confidence=confidence)
        return key

    def get_writing_context(self, topic: str, section_type: str = 'discussion',
                            max_tokens: int = 2000) -> Dict:
        """
        为写作模块组装上下文：相关句式 + 相关机制 + 相关讨论模板。

        Parameters
        ----------
        topic : str, 写作主题（如 "CH4季节差异"）
        section_type : str, 章节类型
        max_tokens : int, 最大 token 数

        Returns
        -------
        dict: {
            'patterns': [{'pattern': str, 'function': str, 'count': int}, ...],
            'mechanisms': [{'pattern': str, 'mechanism': str, 'source': str}, ...],
            'discussion_templates': [{'style': str, 'functions': [str]}, ...],
            'references': [{'title': str, 'year': int, 'citation_count': int}, ...],
        }
        """
        context = {
            'patterns': [],
            'mechanisms': [],
            'discussion_templates': [],
            'references': [],
        }

        # 1. 查找相关句式
        pattern_results = self.recall(topic, category='writing_templates', top_k=10)
        for r in pattern_results:
            val = r['value']
            if isinstance(val, dict) and 'pattern' in val:
                context['patterns'].append({
                    'pattern': val['pattern'],
                    'function': val.get('function', ''),
                    'count': val.get('count', 1),
                    'original': val.get('original', '')[:100],
                })

        # 2. 查找相关机制
        mechanism_results = self.recall(topic, category='mechanisms', top_k=5)
        for r in mechanism_results:
            val = r['value']
            if isinstance(val, dict):
                context['mechanisms'].append({
                    'pattern': val.get('pattern', ''),
                    'mechanism': val.get('mechanism', '')[:300],
                    'source': val.get('source', ''),
                })

        # 3. 查找讨论模板（按 section_type 过滤）
        if section_type == 'discussion':
            disc_results = self.recall('discussion structure', category='writing_templates', top_k=3)
            for r in disc_results:
                val = r['value']
                if isinstance(val, dict) and 'structure_style' in val:
                    context['discussion_templates'].append(val)

        # 4. 查找相关论文引用
        ref_results = self.recall(topic, category='resources', top_k=5)
        for r in ref_results:
            val = r['value']
            if isinstance(val, dict) and val.get('type') == 'academic_paper':
                context['references'].append({
                    'title': val.get('title', ''),
                    'year': val.get('year'),
                    'citation_count': val.get('citation_count', 0),
                    'url': val.get('url', ''),
                })

        return context

    def get_analysis_context(self, var1: str, var2: str) -> Dict:
        """
        为分析模块获取变量关系的解释上下文。

        Parameters
        ----------
        var1, var2 : str, 变量名

        Returns
        -------
        dict: {'mechanisms': [...], 'references': [...]}
        """
        query = f"{var1} {var2}"
        mechanisms = self.recall(query, category='mechanisms', top_k=3)
        refs = self.recall(query, category='resources', top_k=3)

        return {
            'mechanisms': [r['value'] for r in mechanisms if isinstance(r['value'], dict)],
            'references': [r['value'] for r in refs if isinstance(r['value'], dict)
                           and r['value'].get('type') == 'academic_paper'],
        }

    def get_review_context(self) -> Dict:
        """为审稿模块获取已积累的审稿规则"""
        rules = self.store.get('review_rules')
        return {
            'total_rules': len(rules),
            'rules': {k: v.get('value', v) for k, v in rules.items()},
        }

    def get_stats(self) -> Dict:
        """记忆统计"""
        stats = self.store.stats()
        return {
            'categories': {cat: s['count'] for cat, s in stats.items()},
            'total_entries': sum(s['count'] for s in stats.values()),
            'total_versions': sum(s['version'] for s in stats.values()),
        }

    def _calc_relevance(self, query_tokens: set, key: str, value: dict) -> float:
        """计算查询与条目的相关性"""
        # 从 key 和 value 中提取文本
        text_parts = [key.lower()]
        for v in value.values():
            if isinstance(v, str):
                text_parts.append(v.lower())
            elif isinstance(v, list):
                text_parts.extend(str(item).lower() for item in v[:5])

        full_text = ' '.join(text_parts)
        text_tokens = set(re.findall(r'[\w一-鿿]+', full_text))

        # Jaccard 相似度
        if not query_tokens or not text_tokens:
            return 0.0

        intersection = query_tokens & text_tokens
        union = query_tokens | text_tokens

        return len(intersection) / len(union) if union else 0.0


# ============================================================================
# 便捷函数
# ============================================================================

def create_memory(store_dir=None) -> KnowledgeMemory:
    """创建记忆实例"""
    return KnowledgeMemory(store_dir=store_dir)


def recall_knowledge(query: str, store_dir=None, top_k: int = 5) -> List[Dict]:
    """快捷查询"""
    memory = KnowledgeMemory(store_dir=store_dir)
    return memory.recall(query, top_k=top_k)
