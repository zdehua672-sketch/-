# -*- coding: utf-8 -*-
"""
写作模式学习器 - PatternLearner
从已读论文中提取句式模式、讨论结构、机制知识。

三个核心类:
  SentencePatternLearner - 句式骨架提取
  DiscussionLearner      - 讨论结构学习
  MechanismLearner       - 机制知识提取
"""

import re
import json
import os
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 1. SentencePatternLearner - 句式提取
# ============================================================================

class SentencePatternLearner:
    """
    从论文正文中提取句式模式。

    方法：
    1. 按句号/分号分句
    2. 识别句式骨架：去除变量名、数值、引用，保留结构
    3. 按功能分类：背景句、方法句、结果句、讨论句、过渡句
    """

    # 变量/数值替换模式
    VARIABLE_PATTERNS = [
        # 化学式
        (r'\bCH[_₄]4?\b', '[CHEMICAL]'),
        (r'\bCO[_₂]2?\b', '[CHEMICAL]'),
        (r'\bN[_₂]2?O\b', '[CHEMICAL]'),
        (r'\bNH[_₄]4?\+?\b', '[CHEMICAL]'),
        (r'\bNO[_₃]3?\-?\b', '[CHEMICAL]'),
        (r'\bH[_₂]2?S\b', '[CHEMICAL]'),
        (r'\bO[_₂]2?\b', '[CHEMICAL]'),
        # 数值+单位
        (r'\d+\.?\d*\s*(mg/L|mg/kg|ppm|ppb|℃|%|μS/cm|g/kg)', '[VALUE_UNIT]'),
        (r'\d+\.?\d*', '[NUM]'),
        # p值
        (r'p\s*[<>=≤≥]\s*\d+\.?\d*', 'p [SIGN] [NUM]'),
        (r'[pP]\s*=\s*\d+\.?\d*', 'p = [NUM]'),
        # R²
        (r'R[²2]\s*=\s*\d+\.?\d*', 'R² = [NUM]'),
        # 统计检验
        (r'F\s*\(\d+\s*,\s*\d+\)\s*=\s*\d+\.?\d*', 'F([DF], [DF]) = [NUM]'),
        (r't\s*=\s*-?\d+\.?\d*', 't = [NUM]'),
        (r'U\s*=\s*\d+', 'U = [NUM]'),
        # 百分比
        (r'\d+\.?\d*%', '[PCT]%'),
        # 引用标记
        (r'\([^)]*\d{4}[^)]*\)', '[REF]'),
        (r'\[\d+(?:[,\s]*\d+)*\]', '[REF]'),
        # 变量名（中文+英文混合）
        (r'(?:TOC|COD|DO|TN|TP|IC|TC|DOC|pH)\s*(?:\([^)]*\))?', '[VAR]'),
    ]

    # 句式功能分类关键词
    SECTION_SIGNALS = {
        'background': ['however', 'although', 'remains', 'remains unclear',
                       '然而', '但是', '目前', '尚不', '仍需', '引起了', '关注'],
        'method': ['measured', 'analyzed', 'calculated', 'using', 'collected',
                   '测定', '分析', '计算', '采用', '采集', '方法', '通过'],
        'result': ['significantly', 'higher', 'lower', 'correlation', 'showed',
                   'revealed', 'found',
                   '显著', '高于', '低于', '相关', '表明', '显示', '发现', '结果'],
        'discussion': ['suggest', 'indicate', 'attributed', 'mechanism', 'explain',
                       'consistent with', 'compared to',
                       '表明', '归因于', '机制', '解释', '一致', '相比', '可能'],
        'transition': ['furthermore', 'moreover', 'in addition', 'however',
                       '此外', '另外', '同时', '然而', '因此'],
    }

    def __init__(self):
        self.patterns = defaultdict(list)  # {section_type: [pattern_str, ...]}

    def learn_from_text(self, text: str, section_type: str = 'unknown') -> List[Dict]:
        """
        从文本中提取句式模式。

        Parameters
        ----------
        text : str, 论文正文
        section_type : str, 章节类型 ('introduction'/'methods'/'results'/'discussion')

        Returns
        -------
        list of dict: [{'pattern': str, 'original': str, 'function': str, 'count': int}]
        """
        sentences = self._split_sentences(text)
        extracted = []

        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 15:  # 太短的句子跳过
                continue

            # 提取句式骨架
            pattern = self._extract_pattern(sent)
            if not pattern or len(pattern) < 10:
                continue

            # 判断句式功能
            function = self._classify_function(sent, section_type)

            extracted.append({
                'pattern': pattern,
                'original': sent[:200],
                'function': function,
                'section_type': section_type,
            })

        # 聚合相同句式
        aggregated = self._aggregate_patterns(extracted)
        self.patterns[section_type].extend(aggregated)

        return aggregated

    def get_patterns(self, section_type: str = None, function: str = None,
                     top_n: int = 10) -> List[Dict]:
        """获取最常用的句式模式"""
        all_patterns = []
        if section_type:
            all_patterns = self.patterns.get(section_type, [])
        else:
            for patterns in self.patterns.values():
                all_patterns.extend(patterns)

        if function:
            all_patterns = [p for p in all_patterns if p.get('function') == function]

        # 按出现次数排序
        all_patterns.sort(key=lambda x: x.get('count', 1), reverse=True)
        return all_patterns[:top_n]

    def _split_sentences(self, text: str) -> List[str]:
        """中英文分句"""
        # 英文按句号分，但排除缩写
        text = re.sub(r'\b(e\.g|i\.e|et al|vs|Fig|Eq|Ref)\.\s*', r'\1<PERIOD> ', text)
        # 中文按句号/问号/感叹号分
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.replace('<PERIOD>', '.').strip() for s in sentences if s.strip()]

    def _extract_pattern(self, sentence: str) -> str:
        """提取句式骨架：替换变量、数值、引用为占位符"""
        pattern = sentence

        # 按优先级替换
        for regex, replacement in self.VARIABLE_PATTERNS:
            pattern = re.sub(regex, replacement, pattern, flags=re.IGNORECASE)

        # 清理连续的占位符
        pattern = re.sub(r'(?:\[NUM\]\s*){2,}', '[NUM] ', pattern)
        pattern = re.sub(r'\s+', ' ', pattern).strip()

        return pattern

    def _classify_function(self, sentence: str, section_type: str) -> str:
        """判断句式功能"""
        sent_lower = sentence.lower()

        scores = {}
        for func, keywords in self.SECTION_SIGNALS.items():
            scores[func] = sum(1 for kw in keywords if kw.lower() in sent_lower)

        if max(scores.values()) == 0:
            return section_type if section_type != 'unknown' else 'other'

        return max(scores, key=scores.get)

    def _aggregate_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """聚合同一句式"""
        counter = Counter()
        examples = {}

        for p in patterns:
            key = p['pattern']
            counter[key] += 1
            if key not in examples:
                examples[key] = p

        aggregated = []
        for pattern, count in counter.most_common(50):
            entry = examples[pattern].copy()
            entry['count'] = count
            aggregated.append(entry)

        return aggregated


# ============================================================================
# 2. DiscussionLearner - 讨论结构学习
# ============================================================================

class DiscussionLearner:
    """
    学习讨论部分的组织结构。

    识别模式：
    - 开头方式：总结发现 / 对比文献 / 提出问题
    - 论证方式：PARCM / 漏斗 / 对比
    - 机制解释模式
    - 局限性陈述模式
    - 结论收束模式
    """

    # 讨论结构信号词
    OPENING_SIGNALS = {
        'summary': ['this study', 'our results', 'the present study', 'findings',
                     '本研究', '本研究发现', '结果表明', '研究发现'],
        'comparison': ['consistent with', 'in agreement', 'similar to', 'compared',
                       '与...', '一致', '相似', '相比', '对比'],
        'question': ['remains unclear', 'however', 'little is known',
                     '尚不', '仍需', '目前关于'],
    }

    MECHANISM_SIGNALS = [
        'mechanism', 'pathway', 'process', 'responsible for', 'attributed to',
        'due to', 'caused by', 'leads to', 'results in',
        '机制', '途径', '过程', '归因于', '由于', '导致', '引起',
    ]

    LIMITATION_SIGNALS = [
        'limitation', 'caveat', 'however', 'should be noted', 'further research',
        '局限', '不足', '需要注意', '有待进一步', '未来研究',
    ]

    CONCLUSION_SIGNALS = [
        'in conclusion', 'overall', 'our findings suggest', 'taken together',
        '总之', '综上', '本研究表明', '总结',
    ]

    def __init__(self):
        self.structures = []

    def learn_structure(self, discussion_text: str) -> Dict:
        """
        分析讨论部分的组织方式。

        Returns
        -------
        dict: {
            'opening_type': str,
            'has_mechanism': bool,
            'has_limitation': bool,
            'has_conclusion': bool,
            'paragraph_functions': [str, ...],
            'structure_style': str,
        }
        """
        paragraphs = [p.strip() for p in discussion_text.split('\n') if p.strip() and len(p.strip()) > 30]

        result = {
            'opening_type': self._detect_opening(paragraphs[0] if paragraphs else ''),
            'has_mechanism': False,
            'has_limitation': False,
            'has_conclusion': False,
            'paragraph_functions': [],
            'structure_style': 'unknown',
        }

        for i, para in enumerate(paragraphs):
            para_lower = para.lower()

            # 检测各段落功能
            if i == 0:
                result['paragraph_functions'].append(f'opening:{result["opening_type"]}')
            elif any(kw in para_lower for kw in self.CONCLUSION_SIGNALS):
                result['paragraph_functions'].append('conclusion')
                result['has_conclusion'] = True
            elif any(kw in para_lower for kw in self.LIMITATION_SIGNALS):
                result['paragraph_functions'].append('limitation')
                result['has_limitation'] = True
            elif any(kw in para_lower for kw in self.MECHANISM_SIGNALS):
                result['paragraph_functions'].append('mechanism_explanation')
                result['has_mechanism'] = True
            elif any(kw in para_lower for kw in self.COMPARISON_SIGNALS if hasattr(self, 'COMPARISON_SIGNALS')):
                result['paragraph_functions'].append('comparison_with_literature')
            else:
                result['paragraph_functions'].append('finding_discussion')

        # 判断整体结构风格
        funcs = result['paragraph_functions']
        if funcs and funcs[0].startswith('opening:summary') and result['has_mechanism']:
            result['structure_style'] = 'parcm'
        elif funcs and funcs[0].startswith('opening:comparison'):
            result['structure_style'] = 'comparison_first'
        elif result['has_limitation'] and result['has_conclusion']:
            result['structure_style'] = 'standard'
        else:
            result['structure_style'] = 'free_form'

        self.structures.append(result)
        return result

    def get_structure_template(self, style: str = 'parcm') -> Dict:
        """返回学习到的结构模板"""
        matching = [s for s in self.structures if s.get('structure_style') == style]
        if not matching:
            # 返回默认模板
            return self._default_template(style)

        # 统计最常见的段落功能序列
        func_sequences = [s['paragraph_functions'] for s in matching]
        avg_length = sum(len(f) for f in func_sequences) / len(func_sequences)

        return {
            'style': style,
            'avg_paragraphs': round(avg_length),
            'common_functions': self._most_common_functions(func_sequences),
            'has_mechanism': sum(1 for s in matching if s['has_mechanism']) / len(matching) > 0.5,
            'has_limitation': sum(1 for s in matching if s['has_limitation']) / len(matching) > 0.5,
            'has_conclusion': sum(1 for s in matching if s['has_conclusion']) / len(matching) > 0.5,
        }

    def _detect_opening(self, text: str) -> str:
        """检测讨论开头方式"""
        text_lower = text.lower()
        for style, keywords in self.OPENING_SIGNALS.items():
            if any(kw in text_lower for kw in keywords):
                return style
        return 'other'

    def _default_template(self, style: str) -> Dict:
        """默认结构模板"""
        templates = {
            'parcm': {
                'style': 'parcm',
                'avg_paragraphs': 5,
                'common_functions': [
                    'opening:summary', 'finding_discussion', 'mechanism_explanation',
                    'comparison_with_literature', 'conclusion'
                ],
                'has_mechanism': True,
                'has_limitation': True,
                'has_conclusion': True,
            },
            'comparison_first': {
                'style': 'comparison_first',
                'avg_paragraphs': 5,
                'common_functions': [
                    'opening:comparison', 'finding_discussion', 'mechanism_explanation',
                    'limitation', 'conclusion'
                ],
                'has_mechanism': True,
                'has_limitation': True,
                'has_conclusion': True,
            },
            'standard': {
                'style': 'standard',
                'avg_paragraphs': 4,
                'common_functions': [
                    'opening:summary', 'finding_discussion', 'limitation', 'conclusion'
                ],
                'has_mechanism': False,
                'has_limitation': True,
                'has_conclusion': True,
            },
        }
        return templates.get(style, templates['standard'])

    def _most_common_functions(self, sequences: List[List[str]]) -> List[str]:
        """统计最常见的段落功能序列"""
        if not sequences:
            return []
        # 取最长序列作为基准
        max_len = max(len(s) for s in sequences)
        # 按位置统计
        position_counts = defaultdict(Counter)
        for seq in sequences:
            for i, func in enumerate(seq):
                position_counts[i][func] += 1

        result = []
        for i in range(max_len):
            if position_counts[i]:
                result.append(position_counts[i].most_common(1)[0][0])
        return result


# ============================================================================
# 3. MechanismLearner - 机制知识提取
# ============================================================================

class MechanismLearner:
    """
    从论文摘要中自动提取变量间关系（机制知识）。

    方法：识别 "X positively/negatively correlates with Y"、
    "X promotes/inhibits Y" 等模式。
    """

    # 英文关系模式
    EN_RELATION_PATTERNS = [
        # X positively correlates with Y
        (r'([A-Za-z_][\w\s]*?)\s+(?:positively|significantly)\s+(?:correlat|associat|relat)\w*\s+(?:with|to)\s+([\w\s]+?)(?:\s*[\(;,\.])',
         'positive_correlation'),
        # X negatively correlates with Y
        (r'([A-Za-z_][\w\s]*?)\s+(?:negatively|inversely)\s+(?:correlat|associat|relat)\w*\s+(?:with|to)\s+([\w\s]+?)(?:\s*[\(;,\.])',
         'negative_correlation'),
        # X promotes/enhances/increases Y
        (r'([A-Za-z_][\w\s]*?)\s+(?:promot|enhanc|increas|stimulat|facilitat)\w*\s+([\w\s]+?)(?:\s*[\.;,])',
         'positive_effect'),
        # X inhibits/reduces/suppresses/decreases Y
        (r'([A-Za-z_][\w\s]*?)\s+(?:inhibit|reduc|suppress|decreas|limit|impair)\w*\s+([\w\s]+?)(?:\s*[\.;,])',
         'negative_effect'),
        # X is controlled/regulated by Y
        (r'([A-Za-z_][\w\s]*?)\s+(?:is|are)\s+(?:control|regulat|govern|determin)\w*\s+by\s+([\w\s]+?)(?:\s*[\.;,])',
         'regulated_by'),
    ]

    # 中文关系模式
    ZH_RELATION_PATTERNS = [
        (r'([一-鿿\w]+)\s*(?:与|和)\s*([一-鿿\w]+)\s*(?:呈|存在|具有)\s*(?:显著)?\s*正相关',
         'positive_correlation'),
        (r'([一-鿿\w]+)\s*(?:与|和)\s*([一-鿿\w]+)\s*(?:呈|存在|具有)\s*(?:显著)?\s*负相关',
         'negative_correlation'),
        (r'([一-鿿\w]+)\s*(?:促进|增强|提高|增加)\s*(?:了)?\s*([一-鿿\w]+)',
         'positive_effect'),
        (r'([一-鿿\w]+)\s*(?:抑制|降低|减少|削弱)\s*(?:了)?\s*([一-鿿\w]+)',
         'negative_effect'),
    ]

    def __init__(self):
        self.mechanisms = []

    def learn_from_text(self, text: str, source: str = '') -> List[Dict]:
        """
        从文本中提取机制知识。

        Parameters
        ----------
        text : str, 论文摘要或正文
        source : str, 来源标识

        Returns
        -------
        list of dict: [{'var1': str, 'var2': str, 'relation': str, 'evidence': str, 'source': str}]
        """
        extracted = []

        # 英文模式
        for pattern, relation_type in self.EN_RELATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                var1 = match.group(1).strip()
                var2 = match.group(2).strip()
                if self._is_valid_variable(var1) and self._is_valid_variable(var2):
                    extracted.append({
                        'var1': var1,
                        'var2': var2,
                        'relation': relation_type,
                        'evidence': match.group(0).strip(),
                        'source': source,
                        'language': 'en',
                    })

        # 中文模式
        for pattern, relation_type in self.ZH_RELATION_PATTERNS:
            for match in re.finditer(pattern, text):
                var1 = match.group(1).strip()
                var2 = match.group(2).strip()
                if self._is_valid_variable(var1) and self._is_valid_variable(var2):
                    extracted.append({
                        'var1': var1,
                        'var2': var2,
                        'relation': relation_type,
                        'evidence': match.group(0).strip(),
                        'source': source,
                        'language': 'zh',
                    })

        self.mechanisms.extend(extracted)
        return extracted

    def learn_from_paper(self, title: str, abstract: str,
                         sections: list = None) -> List[Dict]:
        """
        从完整论文中提取机制知识。

        Parameters
        ----------
        title : str, 论文标题
        abstract : str, 摘要
        sections : list of dict, 章节列表 [{'text': str, 'section_type': str}]

        Returns
        -------
        list of dict
        """
        all_extracted = []

        # 从摘要提取（摘要通常包含核心发现）
        if abstract:
            mechs = self.learn_from_text(abstract, source=f'abstract:{title[:50]}')
            all_extracted.extend(mechs)

        # 从结果和讨论部分提取
        if sections:
            for sec in sections:
                if sec.get('section_type') in ('results', 'discussion'):
                    mechs = self.learn_from_text(
                        sec.get('text', '')[:2000],
                        source=f'{sec["section_type"]}:{title[:50]}'
                    )
                    all_extracted.extend(mechs)

        return all_extracted

    def get_mechanisms(self, var1: str = None, var2: str = None,
                       relation: str = None) -> List[Dict]:
        """查询已学习的机制知识"""
        results = self.mechanisms
        if var1:
            results = [m for m in results if var1.lower() in m['var1'].lower()]
        if var2:
            results = [m for m in results if var2.lower() in m['var2'].lower()]
        if relation:
            results = [m for m in results if m['relation'] == relation]
        return results

    def to_knowledge_store_format(self) -> Dict:
        """转换为知识库存储格式"""
        entries = {}
        for i, mech in enumerate(self.mechanisms):
            key = f"learned_{mech['var1'][:15]}_{mech['relation']}_{mech['var2'][:15]}_{i}"
            key = re.sub(r'[^\w]', '_', key).lower()
            entries[key] = {
                'pattern': f"{mech['var1']} {mech['relation']} {mech['var2']}",
                'mechanism': mech['evidence'],
                'var1': mech['var1'],
                'var2': mech['var2'],
                'relation_type': mech['relation'],
                'source': mech['source'],
                'learned_at': datetime.now(timezone.utc).isoformat(),
            }
        return entries

    def _is_valid_variable(self, text: str) -> bool:
        """检查是否是有效的变量名"""
        if len(text) < 2 or len(text) > 50:
            return False
        # 排除常见非变量词
        stopwords = {'the', 'this', 'that', 'these', 'those', 'which', 'with',
                     'from', 'been', 'have', 'has', 'had', 'were', 'was', 'are',
                     'is', 'be', 'do', 'did', 'does', 'can', 'could', 'may',
                     'might', 'shall', 'should', 'will', 'would', 'not',
                     '的', '了', '在', '是', '和', '与', '对', '中', '为'}
        words = text.lower().split()
        if all(w in stopwords for w in words):
            return False
        return True


# ============================================================================
# 4. MethodologyLearner - 方法论学习器
# ============================================================================

class MethodologyLearner:
    """
    从论文的 Methods 部分提取方法论模式。

    功能：
    1. 提取实验方法描述
    2. 识别统计方法
    3. 学习采样方法
    4. 提取仪器/设备信息
    """

    # 方法论关键词分类
    METHOD_CATEGORIES = {
        'sampling': ['采样', '采集', '样品', 'sampling', 'collection', 'grab', 'composite'],
        'analysis': ['测定', '分析', '检测', 'measurement', 'analysis', 'detection', 'determination'],
        'statistical': ['统计', '检验', '回归', '相关', 'ANOVA', 't-test', 'Mann-Whitney',
                       'Kruskal', 'Shapiro', 'Pearson', 'Spearman', 'p值', 'p-value'],
        'instrument': ['仪器', '设备', '型号', 'analyzer', 'spectrometer', 'chromatograph',
                      'sensor', 'meter', 'detector'],
        'preprocessing': ['预处理', '前处理', '消解', '过滤', '稀释', '萃取', 'digestion',
                         'filtration', 'dilution', 'extraction'],
    }

    # 中文方法论模式
    ZH_METHOD_PATTERNS = [
        # 采用XX方法测定...
        (r'采[用取]([\w\s\+\/\(\)]+)(?:方法|法|技术|手段)(?:测定|分析|检测)([\w\s]+)',
         'method_used'),
        # 使用XX仪器
        (r'使[用到]([\w\s\-\(\)]+)(?:仪器|设备|装置|分析仪)(?:测定|检测|分析)?([\w\s]*)',
         'instrument_used'),
        # 样品采集方法
        (r'(?:采集|收集|取)(?:了)?([\w\s]+)(?:样品|样本|水样|气样)',
         'sampling_method'),
        # 统计方法
        (r'([A-Za-z\-\s]+(?:检验|分析|相关|回归))(?:\s*\(([A-Za-z\-\s]+)\))?',
         'statistical_method'),
    ]

    # 英文方法论模式
    EN_METHOD_PATTERNS = [
        # was/were measured/analyzed/determined using...
        (r'(?:was|were)\s+(?:measured|analyzed|determined|detected|quantified)\s+(?:using|by|with)\s+([\w\s\-\(\)]+?)(?:\.|,|\()',
         'measurement_method'),
        # Samples were collected/collected from...
        (r'[Ss]amples?\s+(?:were|was)\s+(?:collected|gathered|obtained|taken)\s+(?:from|at)\s+([\w\s]+?)(?:\.|,)',
         'sampling_method'),
        # Statistical analysis was performed using...
        (r'[Ss]tatistical\s+(?:analysis|tests?)\s+(?:were|was)\s+(?:performed|conducted|carried out)\s+(?:using|with)\s+([\w\s\-\(\)]+?)(?:\.|,)',
         'statistical_method'),
    ]

    def __init__(self):
        self.methods = []

    def extract_methods(self, paper_text: str, source: str = '') -> List[Dict]:
        """
        从论文 Methods 部分提取方法论信息。

        Parameters
        ----------
        paper_text : str, 论文 Methods 部分文本
        source : str, 来源标识

        Returns
        -------
        list of dict: [{'category': str, 'method': str, 'detail': str, 'source': str}]
        """
        extracted = []

        # 中文模式匹配
        for pattern, method_type in self.ZH_METHOD_PATTERNS:
            for match in re.finditer(pattern, paper_text):
                method_text = match.group(0).strip()
                category = self._classify_method(method_text)

                extracted.append({
                    'category': category,
                    'type': method_type,
                    'method': match.group(1).strip() if match.lastindex >= 1 else method_text,
                    'detail': match.group(2).strip() if match.lastindex >= 2 else '',
                    'evidence': method_text,
                    'source': source,
                    'language': 'zh',
                })

        # 英文模式匹配
        for pattern, method_type in self.EN_METHOD_PATTERNS:
            for match in re.finditer(pattern, paper_text, re.IGNORECASE):
                method_text = match.group(0).strip()
                category = self._classify_method(method_text)

                extracted.append({
                    'category': category,
                    'type': method_type,
                    'method': match.group(1).strip() if match.lastindex >= 1 else method_text,
                    'detail': '',
                    'evidence': method_text,
                    'source': source,
                    'language': 'en',
                })

        self.methods.extend(extracted)
        return extracted

    def learn_from_paper(self, title: str, abstract: str,
                         sections: list = None) -> List[Dict]:
        """
        从完整论文中学习方法论。

        Parameters
        ----------
        title : str, 论文标题
        abstract : str, 摘要
        sections : list of dict, 章节列表 [{'text': str, 'section_type': str}]

        Returns
        -------
        list of dict
        """
        all_extracted = []

        # 从 Methods 部分提取
        if sections:
            for sec in sections:
                sec_type = sec.get('section_type', '') if isinstance(sec, dict) else getattr(sec, 'section_type', '')
                if sec_type in ('methods', 'methodology', 'materials_and_methods'):
                    text = sec.get('text', '') if isinstance(sec, dict) else getattr(sec, 'text', '')
                    if text:
                        methods = self.extract_methods(text[:5000], source=f'methods:{title[:50]}')
                        all_extracted.extend(methods)

        # 从摘要中提取方法关键词
        if abstract:
            method_keywords = self._extract_method_keywords(abstract)
            for kw in method_keywords:
                all_extracted.append({
                    'category': self._classify_method(kw),
                    'type': 'keyword',
                    'method': kw,
                    'detail': '',
                    'evidence': kw,
                    'source': f'abstract:{title[:50]}',
                    'language': 'zh' if any('一' <= c <= '鿿' for c in kw) else 'en',
                })

        self.methods.extend(all_extracted)
        return all_extracted

    def get_methods(self, category: str = None) -> List[Dict]:
        """查询已学习的方法论"""
        results = self.methods
        if category:
            results = [m for m in results if m['category'] == category]
        return results

    def get_method_summary(self) -> Dict:
        """获取方法论摘要"""
        summary = {}
        for m in self.methods:
            cat = m['category']
            if cat not in summary:
                summary[cat] = []
            if m['method'] not in [x['method'] for x in summary[cat]]:
                summary[cat].append({
                    'method': m['method'],
                    'count': sum(1 for x in self.methods if x['method'] == m['method']),
                })
        return summary

    def _classify_method(self, text: str) -> str:
        """分类方法论类型"""
        text_lower = text.lower()
        for category, keywords in self.METHOD_CATEGORIES.items():
            if any(kw.lower() in text_lower for kw in keywords):
                return category
        return 'other'

    def _extract_method_keywords(self, text: str) -> List[str]:
        """从文本中提取方法关键词"""
        keywords = []
        # 提取括号中的方法名
        bracket_matches = re.findall(r'[（(]([\w\s\-\+\/]+)[）)]', text)
        keywords.extend([m.strip() for m in bracket_matches if len(m.strip()) > 3])

        # 提取常见方法名词
        method_nouns = ['GC-MS', 'HPLC', 'ICP', 'UV-Vis', 'PCR', 'SEM', 'XRD', 'FTIR',
                       'TOC分析', 'COD测定', 'BOD测定', '气相色谱', '液相色谱',
                       '离子色谱', '原子吸收', '质谱分析']
        for noun in method_nouns:
            if noun.lower() in text.lower():
                keywords.append(noun)

        return keywords


# ============================================================================
# 5. 便捷函数
# ============================================================================

def learn_patterns_from_paper(paper_content, store=None) -> Dict:
    """
    从一篇论文中学习所有模式。

    Parameters
    ----------
    paper_content : PaperContent (from paper_reader.py)
    store : KnowledgeStore or None

    Returns
    -------
    dict: {'patterns': [...], 'structure': {...}, 'mechanisms': [...]}
    """
    result = {'patterns': [], 'structure': {}, 'mechanisms': []}

    if not paper_content:
        return result

    # 1. 句式学习
    spl = SentencePatternLearner()
    for sec in getattr(paper_content, 'sections', []):
        text = sec.text if hasattr(sec, 'text') else sec.get('text', '')
        section_type = sec.section_type if hasattr(sec, 'section_type') else sec.get('section_type', 'unknown')
        if text:
            patterns = spl.learn_from_text(text[:3000], section_type)
            result['patterns'].extend(patterns)

    # 2. 讨论结构学习
    dl = DiscussionLearner()
    for sec in getattr(paper_content, 'sections', []):
        text = sec.text if hasattr(sec, 'text') else sec.get('text', '')
        section_type = sec.section_type if hasattr(sec, 'section_type') else sec.get('section_type', '')
        if section_type == 'discussion' and text:
            result['structure'] = dl.learn_structure(text[:3000])

    # 3. 机制知识提取
    ml = MechanismLearner()
    title = ''
    abstract = ''
    if hasattr(paper_content, 'metadata'):
        title = getattr(paper_content.metadata, 'title', '')
        abstract = getattr(paper_content.metadata, 'abstract', '')
    sections_data = []
    for sec in getattr(paper_content, 'sections', []):
        sections_data.append({
            'text': (sec.text if hasattr(sec, 'text') else sec.get('text', ''))[:2000],
            'section_type': sec.section_type if hasattr(sec, 'section_type') else sec.get('section_type', ''),
        })
    mechanisms = ml.learn_from_paper(title, abstract, sections_data)
    result['mechanisms'] = mechanisms

    # 4. 存入知识库
    if store:
        # 句式模板
        for p in result['patterns'][:20]:
            key = f"learned_{p['function']}_{hash(p['pattern']) % 10000:04d}"
            store.set("writing_templates", key, {
                'pattern': p['pattern'],
                'original': p.get('original', ''),
                'function': p['function'],
                'section_type': p.get('section_type', ''),
                'count': p.get('count', 1),
                'source': f'learned:{title[:50]}',
            }, source='pattern_learner', confidence=0.7)

        # 机制知识
        for key, entry in ml.to_knowledge_store_format().items():
            store.set("mechanisms", key, entry,
                      source='mechanism_learner', confidence=0.6)

    return result
