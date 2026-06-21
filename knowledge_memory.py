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

                # 跳过空内容条目
                if cat == 'mechanisms':
                    mech_text = val.get('mechanism', '')
                    if not mech_text or len(mech_text) < 10:
                        continue

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
        """计算查询与条目的相关性（混合检索：Jaccard + 子串匹配 + 变量名匹配 + TF-IDF余弦相似度）"""
        # 从 key 和 value 中提取文本
        text_parts = [key.lower()]
        for v in value.values():
            if isinstance(v, str):
                text_parts.append(v.lower())
            elif isinstance(v, list):
                text_parts.extend(str(item).lower() for item in v[:5])

        full_text = ' '.join(text_parts)
        text_tokens = set(re.findall(r'[\w一-鿿]+', full_text))

        # 1. Jaccard 相似度
        if not query_tokens or not text_tokens:
            jaccard = 0.0
        else:
            intersection = query_tokens & text_tokens
            union = query_tokens | text_tokens
            jaccard = len(intersection) / len(union) if union else 0.0

        # 2. 子串匹配：查询token是否出现在文本中（部分匹配）
        #    例如 "总氮（mg/L)" 的子串 "总氮" 能匹配 "总氮"
        query_chars = set(re.findall(r'[一-鿿]+', ' '.join(query_tokens)))
        text_chars = set(re.findall(r'[一-鿿]+', full_text))
        if query_chars and text_chars:
            char_overlap = sum(1 for c in query_chars if c in text_chars)
            char_score = char_overlap / len(query_chars)
        else:
            char_score = 0.0

        # 3. 变量名精确匹配：提取变量名核心部分
        #    "总氮（mg/L)" → "总氮", "TOC（mg/L)" → "TOC"
        # 同时处理中英文变量名映射
        VAR_ALIASES = {
            '总氮': 'TN', '铵态氮': 'NH4', '硝态氮': 'NO3', '总磷': 'TP',
            '甲烷': 'CH4', '氧化亚氮': 'N2O', '二氧化碳': 'CO2',
            '溶解氧': 'DO', '化学需氧量': 'COD', '有机碳': 'TOC',
            '无机碳': 'IC', '总碳': 'TC', '电导率': 'EC',
            '挥发性有机物': 'VOCs', '硫化氢': 'H2S',
        }
        # 反向映射
        ALIAS_TO_CN = {v: k for k, v in VAR_ALIASES.items()}

        query_vars = set()
        for t in query_tokens:
            cn = re.findall(r'[一-鿿]+', t)
            query_vars.update(cn)
            en = re.findall(r'[A-Z]{2,}', t.upper())
            query_vars.update(en)
            # 添加别名
            for c in cn:
                if c in VAR_ALIASES:
                    query_vars.add(VAR_ALIASES[c])
            for e in en:
                if e in ALIAS_TO_CN:
                    query_vars.add(ALIAS_TO_CN[e])

        text_vars = set()
        for t in text_tokens:
            cn = re.findall(r'[一-鿿]+', t)
            text_vars.update(cn)
            en = re.findall(r'[A-Z]{2,}', t.upper())
            text_vars.update(en)
            for c in cn:
                if c in VAR_ALIASES:
                    text_vars.add(VAR_ALIASES[c])
            for e in en:
                if e in ALIAS_TO_CN:
                    text_vars.add(ALIAS_TO_CN[e])

        if query_vars and text_vars:
            var_overlap = len(query_vars & text_vars)
            var_score = var_overlap / len(query_vars)
        else:
            var_score = 0.0

        # 4. TF-IDF 余弦相似度（增强语义检索）
        tfidf_score = self._calc_tfidf_similarity(query_tokens, text_tokens)

        # 综合得分：加权平均（TF-IDF权重较高，因为语义能力更强）
        weights = {
            'jaccard': 0.2,
            'char_score': 0.2,
            'var_score': 0.3,
            'tfidf_score': 0.3,
        }
        final_score = (
            jaccard * weights['jaccard'] +
            char_score * weights['char_score'] +
            var_score * weights['var_score'] +
            tfidf_score * weights['tfidf_score']
        )
        return final_score

    def _calc_tfidf_similarity(self, query_tokens: set, text_tokens: set) -> float:
        """
        计算 TF-IDF 余弦相似度

        使用简化的 TF-IDF 计算：
        - TF: 词频（token在查询/文本中出现的比例）
        - IDF: 逆文档频率（使用预设的常见词权重）
        - 余弦相似度: 两个向量的夹角余弦值
        """
        if not query_tokens or not text_tokens:
            return 0.0

        # 构建词汇表
        vocab = query_tokens | text_tokens
        if not vocab:
            return 0.0

        # 预设的 IDF 权重（常见学术词汇权重较低）
        IDF_WEIGHTS = {
            '的': 0.1, '了': 0.1, '在': 0.1, '是': 0.1, '和': 0.1,
            '与': 0.1, '对': 0.1, '等': 0.1, '中': 0.1, '为': 0.1,
            '研究': 0.3, '分析': 0.3, '结果': 0.3, '发现': 0.3,
            '表明': 0.3, '显示': 0.3, '显著': 0.4, '相关': 0.4,
            '差异': 0.4, '影响': 0.4, '因素': 0.4, '机制': 0.5,
            '数据': 0.3, '样本': 0.3, '统计': 0.3, '检验': 0.3,
        }

        # 计算 TF-IDF 向量
        def calc_tfidf_vector(tokens):
            vector = {}
            token_count = len(tokens)
            for token in vocab:
                # TF: 词频
                tf = 1.0 if token in tokens else 0.0
                # IDF: 使用预设权重或默认值
                idf = IDF_WEIGHTS.get(token, 0.5)
                vector[token] = tf * idf
            return vector

        query_vector = calc_tfidf_vector(query_tokens)
        text_vector = calc_tfidf_vector(text_tokens)

        # 计算余弦相似度
        dot_product = sum(query_vector.get(t, 0) * text_vector.get(t, 0) for t in vocab)
        query_norm = sum(v ** 2 for v in query_vector.values()) ** 0.5
        text_norm = sum(v ** 2 for v in text_vector.values()) ** 0.5

        if query_norm == 0 or text_norm == 0:
            return 0.0

        return dot_product / (query_norm * text_norm)


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


# ============================================================================
# FAIR 元数据审计（来自 nature-data skill）
# ============================================================================

# FAIR 原则检查表
FAIR_CHECKLIST = {
    'findable': {
        'persistent_id': '数据集是否有持久标识符（DOI/Accession/Handle/ARK）？',
        'rich_metadata': '是否有丰富的标题/摘要/关键词？',
        'searchable_record': '是否在可搜索的仓库中有记录？',
        'metadata_links_id': '元数据中是否包含数据标识符？',
    },
    'accessible': {
        'standard_protocol': '标识符是否通过标准协议可访问？',
        'explicit_conditions': '访问条件是否明确？',
        'public_metadata': '即使数据受限，元数据是否公开？',
    },
    'interoperable': {
        'community_formats': '文件是否使用社区标准格式？',
        'shared_vocabulary': '元数据是否使用共享词汇/单位/标识符？',
        'qualified_links': '是否有到相关数据/代码/出版物的合格链接？',
    },
    'reusable': {
        'licence_clear': '许可证是否明确？',
        'provenance': '数据来源/方法/版本是否清晰？',
        'quality_notes': '是否有质量控制说明？',
        'community_metadata': '是否有足够的社区标准元数据？',
    },
}

# 数据访问路径分类
DATA_ACCESS_ROUTES = {
    'public_repository': '公共仓库（如 Zenodo, Figshare, Dryad, GBIF）',
    'controlled_access': '受控访问仓库（如 dbGaP, EGA）',
    'within_paper': '论文/补充材料中',
    'reused_public': '复用的公共数据源',
    'third_party_restricted': '第三方受限数据',
    'justified_request': '合理请求获取',
    'not_applicable': '不适用',
}

# 推荐仓库映射
REPOSITORY_MAP = {
    'environmental': ['Zenodo', 'Figshare', 'Dryad', 'PANGAEA'],
    'genomics': ['NCBI SRA', 'ENA', 'DDBJ'],
    'chemical': ['PubChem', 'ChemSpider'],
    'geospatial': ['GBIF', 'OpenStreetMap'],
    'general': ['Zenodo', 'Figshare', 'Harvard Dataverse'],
}


def audit_fair_metadata(datasets: list) -> dict:
    """
    FAIR 元数据审计（来自 nature-data skill）。

    Parameters
    ----------
    datasets : list of dict
        每个数据集的信息：
        [{
            'name': str,
            'description': str,
            'identifier': str (DOI/accession/None),
            'repository': str,
            'access_route': str (DATA_ACCESS_ROUTES 的 key),
            'licence': str,
            'format': str,
            'has_readme': bool,
            'variables_documented': bool,
            'provenance': str,
        }]

    Returns
    -------
    dict: {
        'overall_score': str ('PASS'/'WARN'/'FAIL'),
        'per_dataset': [{'name', 'score', 'issues', 'recommendations'}],
        'blocking_issues': [str],
        'summary': str,
    }
    """
    per_dataset = []
    blocking_issues = []

    for ds in datasets:
        ds_issues = []
        ds_recs = []
        name = ds.get('name', 'unnamed')

        # Findable
        if not ds.get('identifier'):
            ds_issues.append('F: 缺少持久标识符（DOI/Accession）')
            ds_recs.append('为数据集注册 DOI（推荐 Zenodo/Figshare）')

        if not ds.get('description') or len(ds.get('description', '')) < 20:
            ds_issues.append('F: 描述过短或缺失')
            ds_recs.append('补充数据集描述（包含内容、支持的结论）')

        # Accessible
        if ds.get('access_route') in ('third_party_restricted', 'justified_request'):
            if not ds.get('access_procedure'):
                ds_issues.append('A: 受限数据缺少访问流程说明')
                ds_recs.append('说明谁控制访问、如何申请、评估标准')
                blocking_issues.append(f'{name}: 受限数据无访问流程')

        # Interoperable
        bad_formats = ['.xlsx', '.xls', '.doc', '.docx']
        if ds.get('format') and any(ds['format'].endswith(f) for f in bad_formats):
            ds_issues.append('I: 使用了非标准格式，建议转为 CSV/TSV/HDF5')
            ds_recs.append(f'将 {ds["format"]} 转换为开放格式（CSV/TSV）')

        # Reusable
        if not ds.get('licence'):
            ds_issues.append('R: 缺少许可证')
            ds_recs.append('添加 CC0/CC-BY 或适用的许可证')
            blocking_issues.append(f'{name}: 无许可证')

        if not ds.get('has_readme'):
            ds_issues.append('R: 缺少 README 文件')
            ds_recs.append('创建 README（含变量定义、方法、软件版本）')

        if not ds.get('variables_documented'):
            ds_issues.append('R: 变量/单位未文档化')
            ds_recs.append('创建数据字典（列名|定义|单位|允许值）')

        # 评分
        n_issues = len(ds_issues)
        if n_issues == 0:
            score = 'PASS'
        elif n_issues <= 2:
            score = 'WARN'
        else:
            score = 'FAIL'

        per_dataset.append({
            'name': name,
            'score': score,
            'issues': ds_issues,
            'recommendations': ds_recs,
        })

    # 总体评分
    scores = [d['score'] for d in per_dataset]
    if 'FAIL' in scores:
        overall = 'FAIL'
    elif 'WARN' in scores:
        overall = 'WARN'
    else:
        overall = 'PASS'

    return {
        'overall_score': overall,
        'per_dataset': per_dataset,
        'blocking_issues': blocking_issues,
        'summary': f'{scores.count("PASS")}PASS / {scores.count("WARN")}WARN / {scores.count("FAIL")}FAIL',
    }


def generate_data_availability_statement(datasets: list, journal: str = 'nature') -> str:
    """
    生成数据可用性声明（来自 nature-data skill 八步工作流）。

    Parameters
    ----------
    datasets : list of dict
        每个数据集信息（同 audit_fair_metadata）
    journal : str
        目标期刊

    Returns
    -------
    str: 可直接粘贴的数据可用性声明
    """
    lines = ['Data Availability\n']

    for ds in datasets:
        name = ds.get('name', 'the dataset')
        route = ds.get('access_route', 'not_applicable')
        identifier = ds.get('identifier', '')
        repository = ds.get('repository', '')

        if route == 'public_repository':
            if identifier:
                lines.append(
                    f'The {name} data are available at {repository} '
                    f'under accession number {identifier}.'
                )
            else:
                lines.append(
                    f'The {name} data are available at {repository}.'
                )
        elif route == 'controlled_access':
            lines.append(
                f'The {name} data are available from {repository} '
                f'under controlled access. Requests should be directed to '
                f'{ds.get("access_contact", "[contact]")}.'
            )
        elif route == 'within_paper':
            lines.append(
                f'The {name} data are provided in the Supplementary Information.'
            )
        elif route == 'reused_public':
            lines.append(
                f'The {name} data were obtained from {repository} '
                f'(accession number {identifier}).'
            )
        elif route == 'third_party_restricted':
            lines.append(
                f'The {name} data are available from {ds.get("source", "[third party]")} '
                f'under a data-use agreement and are not publicly shared.'
            )
        elif route == 'justified_request':
            lines.append(
                f'The {name} data are available from the corresponding author '
                f'upon reasonable request.'
            )

    return '\n'.join(lines)
