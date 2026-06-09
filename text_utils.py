# -*- coding: utf-8 -*-
"""
公共文本工具 - 统一的句子分割、文本相似度、段落处理
消除 motivation_thread / citation_audit / revision_audit 中的重复实现
"""
import re
from difflib import SequenceMatcher


def split_sentences(text: str) -> list:
    """
    中英文混合分句

    Returns
    -------
    list of str: 过滤掉过短(<5字符)的句子
    """
    parts = re.split(r'(?<=[。！？.!?])\s*', text.strip())
    return [s.strip() for s in parts if len(s.strip()) > 5]


def split_paragraphs(text: str) -> list:
    """
    按空行分割段落

    Returns
    -------
    list of str: 过滤掉过短(<10字符)的段落
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if len(p.strip()) > 10]


def canonical(text: str) -> str:
    """
    文本canonical化：去除格式差异，保留核心内容
    """
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[，。、；：！？“”‘’（）\\[\\]{}<>《》,.!?;:()\-"‘’\n\r\t]', '', text)
    text = re.sub(r'\s*(\d+)\s*', r'\1', text)
    return text.strip()


def extract_tokens(text: str, min_len: int = 2) -> set:
    """
    提取中英文词汇tokens

    Parameters
    ----------
    text : str
    min_len : int - 最小token长度（中文默认2，英文默认2）

    Returns
    -------
    set of str
    """
    zh = set(re.findall(f'[一-鿿]{{{min_len},}}', text))
    en = set(re.findall(f'[a-zA-Z]{{{max(min_len, 2)},}}', text.lower()))
    return zh | en


def text_similarity(text1: str, text2: str, method: str = 'hybrid') -> float:
    """
    文本相似度（统一实现）

    Parameters
    ----------
    text1, text2 : str
    method : str
        'jaccard'    - 纯Jaccard（基于共享tokens）
        'sequence'   - 纯SequenceMatcher
        'hybrid'     - Jaccard + SequenceMatcher 混合（默认）
        'ngram'      - 字符3-gram Jaccard + SequenceMatcher

    Returns
    -------
    float: 0.0 ~ 1.0
    """
    if not text1 or not text2:
        return 0.0

    if method == 'jaccard':
        t1 = extract_tokens(text1)
        t2 = extract_tokens(text2)
        if not t1 or not t2:
            return 0.0
        return len(t1 & t2) / len(t1 | t2)

    elif method == 'sequence':
        return SequenceMatcher(None, text1, text2).ratio()

    elif method == 'hybrid':
        t1 = extract_tokens(text1)
        t2 = extract_tokens(text2)
        if not t1 or not t2:
            return 0.0
        jaccard = len(t1 & t2) / len(t1 | t2)
        seq = SequenceMatcher(None, text1, text2).ratio()
        return jaccard * 0.5 + seq * 0.5

    elif method == 'ngram':
        c1 = canonical(text1)
        c2 = canonical(text2)
        if not c1 or not c2:
            return 0.0
        sm_ratio = SequenceMatcher(None, c1, c2).ratio()
        ng1 = set(c1[i:i+3] for i in range(len(c1) - 2))
        ng2 = set(c2[i:i+3] for i in range(len(c2) - 2))
        if not ng1 or not ng2:
            jaccard = 0.0
        else:
            jaccard = len(ng1 & ng2) / len(ng1 | ng2)
        return jaccard * 0.5 + sm_ratio * 0.5

    else:
        raise ValueError(f"Unknown method: {method}")


def title_similarity(text1: str, text2: str) -> float:
    """
    标题相似度（专用于引用标题匹配）
    使用 hybrid 方法
    """
    return text_similarity(text1, text2, method='hybrid')


# ================================================================
# 自测
# ================================================================
if __name__ == '__main__':
    # 分句测试
    sents = split_sentences("这是第一句。这是第二句！Third sentence? Fourth one.")
    assert len(sents) == 4, f"Expected 4, got {len(sents)}"
    print(f"[OK] split_sentences: {len(sents)} sentences")

    # 分段测试
    paras = split_paragraphs("第一段内容，这里有足够长的文本。\n\n第二段内容，也有足够的长度。\n\n第三段内容也有足够长度。")
    assert len(paras) == 3, f"Expected 3, got {len(paras)}"
    print(f"[OK] split_paragraphs: {len(paras)} paragraphs")

    # 相似度测试
    s = text_similarity("污水管网碳污染物", "污水管道碳污染物分析")
    assert s > 0.3, f"Similarity too low: {s}"
    print(f"[OK] text_similarity: {s:.3f}")

    s = text_similarity("完全不同的文本", "Another completely different")
    assert s < 0.2, f"Similarity too high: {s}"
    print(f"[OK] text_similarity (dissimilar): {s:.3f}")

    # canonical测试
    c = canonical("Hello, World! 你好，世界！")
    assert ',' not in c and '!' not in c
    print(f"[OK] canonical: '{c}'")

    # ngram测试
    s = text_similarity("carbon pollutant analysis", "carbon pollution analysis", method='ngram')
    assert s > 0.4, f"Ngram similarity too low: {s}"
    print(f"[OK] ngram similarity: {s:.3f}")

    print("\nAll tests passed!")
