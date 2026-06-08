"""双语查询扩展"""
import re


# 中英文术语对照表（环境科学/碳污染物领域）
TERM_MAP = {
    '甲烷': 'methane CH4',
    '二氧化碳': 'carbon dioxide CO2',
    '溶解氧': 'dissolved oxygen DO',
    '总有机碳': 'total organic carbon TOC',
    '化学需氧量': 'chemical oxygen demand COD',
    '污水管网': 'sewage network pipeline',
    '产甲烷': 'methanogenesis',
    '厌氧': 'anaerobic',
    '好氧': 'aerobic',
    '碳平衡': 'carbon balance',
    '有机碳': 'organic carbon',
    '沉积物': 'sediment',
    '生物膜': 'biofilm',
    '温室气体': 'greenhouse gas',
    'methane': '甲烷 CH4',
    'carbon dioxide': '二氧化碳 CO2',
    'dissolved oxygen': '溶解氧 DO',
    'total organic carbon': '总有机碳 TOC',
    'sewage': '污水管网',
    'methanogenesis': '产甲烷',
    'anaerobic': '厌氧',
    'carbon balance': '碳平衡',
    'biofilm': '生物膜',
}


def detect_language(text: str) -> str:
    """检测文本主要语言"""
    zh_count = sum(1 for c in text if '一' <= c <= '鿿')
    en_count = sum(1 for c in text if c.isascii() and c.isalpha())
    return 'zh' if zh_count > en_count else 'en'


def expand_query(query: str, max_expansions: int = 5) -> list:
    """
    扩展查询，返回多个查询变体

    Returns
    -------
    list of str，包含原始查询和扩展查询
    """
    queries = [query]
    query_lower = query.lower()
    lang = detect_language(query)

    expansions = []
    for term, translation in TERM_MAP.items():
        if term.lower() in query_lower:
            # 找到对照术语
            expansions.append(translation)
        elif lang == 'zh' and '一' <= term[0] <= '鿿' and term in query:
            expansions.append(translation)
        elif lang == 'en' and term[0].isascii() and term.lower() in query_lower:
            expansions.append(translation)

    # 去重并限制数量
    seen = {query_lower}
    for exp in expansions:
        exp_lower = exp.lower()
        if exp_lower not in seen and len(queries) < max_expansions + 1:
            seen.add(exp_lower)
            queries.append(exp)

    return queries
