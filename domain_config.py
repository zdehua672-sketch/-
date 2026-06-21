# -*- coding: utf-8 -*-
"""
领域配置系统
============
将域名、标准、模板等参数化，支持任意研究领域。
不再硬编码"污水管网碳排放"。

用法:
    from domain_config import DomainConfig, get_config

    config = get_config('sewer_carbon')  # 或 'water_quality', 'soil_pollution', 'custom'
    print(config.domain_name)  # '污水管网碳排放'
    print(config.standards)    # {'TOC': 'HJ 501-2009', ...}
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class WritingQualityConfig:
    """写作质量控制配置"""
    # 文本长度限制
    min_text_length: int = 100          # 最小有效文本长度
    max_conclusion_length: int = 1000   # 结论最大长度

    # 质量评分阈值
    min_quality_score: int = 30         # 最低质量分数（0-100）
    min_academic_features: int = 3      # 最少学术特征词数量
    min_references: int = 1             # 最少引用数量

    # 重试配置
    max_retries: int = 3                # 最大重试次数
    retry_delay: float = 1.0            # 重试延迟（秒）

    # 候选生成配置
    num_candidates: int = 1             # 候选草稿数量（1 = 不生成候选）


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    # 检索配置
    max_recall_results: int = 10        # 最大召回数量
    similarity_threshold: float = 0.1   # 相似度阈值
    jaccard_threshold: float = 0.05     # Jaccard 相似度阈值

    # 置信度配置
    initial_confidence: float = 0.5     # 初始置信度
    confidence_decay: float = 0.95      # 置信度衰减因子
    min_confidence: float = 0.1         # 最低置信度

    # 去重配置
    dedup_similarity: float = 0.8       # 去重相似度阈值


@dataclass
class DomainConfig:
    """研究领域配置"""
    # 基本信息
    domain_name: str = "环境科学"
    domain_name_en: str = "Environmental Science"
    research_object: str = ""
    research_object_en: str = ""

    # 分析标准
    standards: Dict[str, str] = field(default_factory=dict)

    # 核心变量
    key_variables: List[str] = field(default_factory=list)

    # 写作参数
    introduction_background: str = ""
    introduction_gap: str = ""
    conclusion_implications: str = ""

    # 图表参数
    figure_style: str = "chinese"  # chinese / sci / nature
    color_palette: str = "phase"   # phase / season / default

    # 限制条件
    typical_limitations: List[str] = field(default_factory=list)

    # 子配置
    writing_quality: WritingQualityConfig = field(default_factory=WritingQualityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)


# ============================================================
# 预定义领域配置
# ============================================================

DOMAINS = {
    'sewer_carbon': DomainConfig(
        domain_name='污水管网碳排放',
        domain_name_en='Carbon Emissions from Sewer Systems',
        research_object='校园污水管网',
        research_object_en='Campus sewer network',
        standards={
            'TOC': 'HJ 501-2009',
            'COD': 'GB 11914-89',
            'TN': 'HJ 636-2012',
            'TP': 'GB 11893-89',
            'NH4+': 'HJ 535-2009',
            'NO3-': 'HJ/T 346-2007',
            'DO': 'HJ 506-2009',
            'pH': 'GB 6920-86',
        },
        key_variables=['CH4平均值', 'CO2', 'N2O', 'TOC（mg/L)', 'DO(mg/L)', 'COD（mg/L)', 'pH', '液温'],
        introduction_background='污水管网是城市基础设施的重要组成部分，在输送过程中产生的温室气体排放不容忽视。',
        introduction_gap='现有研究多关注污水处理厂的碳排放，对管网系统中碳污染物的多相态转化机制研究不足。',
        conclusion_implications='为校园污水管网碳排放核算和碳管理策略制定提供了数据支撑和科学依据。',
        figure_style='chinese',
        color_palette='phase',
        typical_limitations=[
            '采样点数量有限(n=18)，统计检验力可能不足',
            '仅覆盖冬春两季，缺少夏秋数据',
            '未考虑管龄、管材对碳排放的影响',
            '缺少连续监测数据，无法反映日变化规律',
        ],
    ),

    'water_quality': DomainConfig(
        domain_name='水质分析',
        domain_name_en='Water Quality Analysis',
        research_object='水体',
        research_object_en='Water body',
        standards={
            'TOC': 'HJ 501-2009',
            'COD': 'GB 11914-89',
            'BOD5': 'HJ 505-2009',
            'TN': 'HJ 636-2012',
            'TP': 'GB 11893-89',
            'NH3-N': 'HJ 535-2009',
            'DO': 'HJ 506-2009',
            'SS': 'GB 11901-89',
            'pH': 'GB 6920-86',
        },
        key_variables=['pH', 'DO', 'COD', 'BOD5', 'TN', 'TP', 'NH3-N', 'SS'],
        introduction_background='水环境质量是生态环境保护的重要指标。',
        introduction_gap='现有水质评价方法多采用单因子评价，缺乏多维度综合分析。',
        conclusion_implications='为水环境质量评价和污染治理提供了科学依据。',
        typical_limitations=[
            '采样频次有限',
            '未考虑季节性变化',
        ],
    ),

    'soil_pollution': DomainConfig(
        domain_name='土壤污染分析',
        domain_name_en='Soil Pollution Analysis',
        research_object='土壤',
        research_object_en='Soil',
        standards={
            'pH': 'NY/T 1377-2007',
            '有机质': 'NY/T 1121.6-2006',
            '全氮': 'NY/T 53-1987',
            '有效磷': 'NY/T 1121.7-2006',
            '速效钾': 'NY/T 889-2004',
            '重金属': 'HJ 491-2019',
        },
        key_variables=['pH', '有机质', '全氮', '有效磷', '速效钾'],
        introduction_background='土壤是农业生产的基础，土壤污染直接影响粮食安全。',
        introduction_gap='现有研究多关注单一污染物，缺乏多元素协同分析。',
        conclusion_implications='为土壤污染治理和安全利用提供了数据支撑。',
        typical_limitations=[
            '采样深度有限',
            '未考虑空间自相关',
        ],
    ),

    'air_quality': DomainConfig(
        domain_name='大气环境分析',
        domain_name_en='Air Quality Analysis',
        research_object='大气',
        research_object_en='Atmosphere',
        standards={
            'PM2.5': 'GB 3095-2012',
            'PM10': 'GB 3095-2012',
            'SO2': 'GB 3095-2012',
            'NO2': 'GB 3095-2012',
            'CO': 'GB 3095-2012',
            'O3': 'GB 3095-2012',
        },
        key_variables=['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3'],
        introduction_background='大气污染是影响公众健康的重要环境问题。',
        introduction_gap='现有研究多关注单一污染物的健康效应，缺乏多污染物交互作用研究。',
        conclusion_implications='为大气污染防治和环境管理提供了科学依据。',
        typical_limitations=[
            '监测站点分布不均',
            '未考虑气象条件影响',
        ],
    ),
}


def get_config(domain: str = None) -> DomainConfig:
    """
    获取领域配置。

    Parameters
    ----------
    domain : str
        领域名称，如 'sewer_carbon', 'water_quality', 'soil_pollution', 'air_quality'
        None 时返回默认配置

    Returns
    -------
    DomainConfig
    """
    if domain and domain in DOMAINS:
        return DOMAINS[domain]
    return DomainConfig()  # 返回默认配置


def list_domains() -> List[str]:
    """列出所有可用的领域"""
    return list(DOMAINS.keys())


def register_domain(name: str, config: DomainConfig):
    """注册新的领域配置"""
    DOMAINS[name] = config
