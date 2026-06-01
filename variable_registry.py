# -*- coding: utf-8 -*-
"""
变量注册中心 - Variable Registry
全系统唯一的变量分类、关键词映射、衍生变量定义。
其他模块全部从这里读取，不再各自硬编码。
"""

import pandas as pd
import numpy as np

# ============================================================================
# 1. 相态分类关键词（用于自动识别列属于哪一相）
# ============================================================================
PHASE_KEYWORDS = {
    'gas': ['CH4', 'CO2', 'N2O', 'VOCs', 'H2S', 'O2', '甲烷', '氧化亚氮'],
    'liquid': ['TOC', 'IC', 'TC', 'DOC', 'COD', 'DO', '总氮', '总磷',
               '铵态氮', '硝态氮', 'NaCl', 'pH', '液温', '电导率'],
    'solid': ['固总碳', '有机碳', '无机碳', 'DOC(mg/kg)', '全磷',
              '（固）铵态氮', '（固）硝态氮', 'g/kg', 'mg/kg'],
    'env': ['气温', '泥水', '采样时间', '采样时段', '井深', '管径', '本底'],
}

# ============================================================================
# 2. 衍生变量（不应参与统计分析的计算列）
# ============================================================================
DERIVED_VARS = ['气相碳', '液相碳', '固相碳', 'TOC比例', 'IC比例', '气液碳比', 'CH4_TOCT比']

# ============================================================================
# 3. 核心分析变量（按相态分组，用于相关性/PCA/回归等）
# ============================================================================
GAS_VARS = [
    'CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)',
    '甲烷(ppm)', '甲烷PPM', '甲烷（PPM）',
    '氧化亚氮(ppm)', '氧化亚氮（ppm）', '氧化亚氮PPM', '氧化亚氮（PPM）',
    'CO2(ppm)', 'CO2(PPM)', 'CO2(mg/L)',
    'O2(%vol)', 'H2S',
]

LIQUID_VARS = [
    'DO(mg/L)', 'pH', '液温', '液温(℃）', '电导率(uS/cm)', '电导率(us/cm)',
    'TOC（mg/L)', 'TC(mg/L)', 'IC(mg/L)', 'COD（mg/L)', 'COD（锰）（mg/L)',
    '总氮（mg/L)', '总磷（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)',
    'NaCl(mg/L)', 'NaCl(g/L)',
]

SOLID_VARS = [
    '固总碳（g/kg)', '有机碳（g/kg)', '无机碳（g/kg)',
    'DOC(mg/kg)', '全磷（g/kg)',
    '（固）铵态氮（mg/kg）', '（固）硝态氮（mg/kg）',
]

ENV_VARS = [
    '气温/℃', '气温℃', '气温（℃）', '泥水状况', '采样时间', '采样时段',
    '井深(m)', '管径（mm)', 'O2(%vol)', 'O2本底值',
    'CO2本底值', 'VOCs本底值',
]

# 所有核心变量（去重，保持顺序）
ALL_CORE_VARS = list(dict.fromkeys(GAS_VARS + LIQUID_VARS + SOLID_VARS))

# ============================================================================
# 4. 领域回归假设（变量对 + 科研意义）
# ============================================================================
DOMAIN_REGRESSION_PAIRS = [
    ('TOC（mg/L)', 'CH4平均值', '有机碳→甲烷生成'),
    ('TOC（mg/L)', 'CO2', '有机碳→CO₂产生'),
    ('DO(mg/L)', 'CH4平均值', '溶解氧抑制甲烷'),
    ('COD（mg/L)', 'CH4平均值', 'COD→甲烷底物'),
    ('TOC（mg/L)', '总氮（mg/L)', '碳氮耦合'),
    ('铵态氮（mg/L)', 'CH4平均值', '氮转化与甲烷关联'),
    ('TOC（mg/L)', 'IC(mg/L)', '有机碳与无机碳关系'),
    ('pH', 'CH4平均值', 'pH对甲烷的影响'),
    ('液温', 'CH4平均值', '温度效应'),
]

# ============================================================================
# 5. 变量短名映射（用于图表标签缩写）
# ============================================================================
SHORT_NAMES = {
    'CH4平均值': 'CH₄', 'N2O平均值': 'N₂O', 'CO2': 'CO₂',
    'VOCs(ppb)': 'VOCs', 'O2(%vol)': 'O₂',
    'TOC（mg/L)': 'TOC', 'IC(mg/L)': 'IC', 'TC(mg/L)': 'TC',
    'DO(mg/L)': 'DO', 'COD（mg/L)': 'COD',
    '总氮（mg/L)': 'TN', '总磷（mg/L)': 'TP',
    '铵态氮（mg/L)': 'NH₄⁺', '硝态氮（mg/L)': 'NO₃⁻',
    'pH': 'pH', '液温': 'T', '电导率(uS/cm)': 'EC',
    '固总碳（g/kg)': '固TC', '有机碳（g/kg)': '固TOC',
    '无机碳（g/kg)': '固IC', 'DOC(mg/kg)': 'DOC',
    'NaCl(mg/L)': 'NaCl', 'H2S': 'H₂S',
    '气相碳': '气相C', '液相碳': '液相C', '固相碳': '固相C',
    '气液碳比': '气/液C', 'TOC比例': 'TOC/TC', 'IC比例': 'IC/TC',
}

# ============================================================================
# 6. 核心函数
# ============================================================================

def classify_phase(col_name):
    """
    根据列名关键词判断属于哪个相态。

    Returns
    -------
    str: 'gas' / 'liquid' / 'solid' / 'env' / 'unknown'
    """
    col_str = str(col_name)
    col_upper = col_str.upper()

    # 优先匹配精确关键词（避免 'mg/kg' 误匹配液相）
    for phase in ['gas', 'solid', 'env', 'liquid']:
        for kw in PHASE_KEYWORDS[phase]:
            if kw.upper() in col_upper:
                return phase
    return 'unknown'


def get_phase_cols(df, phase, exclude_derived=True):
    """
    从 DataFrame 中获取指定相态的数值列。

    Parameters
    ----------
    df : DataFrame
    phase : str, 'gas'/'liquid'/'solid'/'env'/'all'
    exclude_derived : bool, 是否排除衍生变量

    Returns
    -------
    list of str: 列名列表
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if exclude_derived:
        numeric_cols = [c for c in numeric_cols if c not in DERIVED_VARS]

    if phase == 'all':
        return numeric_cols

    return [c for c in numeric_cols if classify_phase(c) == phase]


def get_analysis_cols(df, exclude_derived=True):
    """
    获取适合做统计分析的数值列（排除衍生变量和ID列）。

    Returns
    -------
    list of str
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if exclude_derived:
        numeric_cols = [c for c in numeric_cols if c not in DERIVED_VARS]
    # 排除只有少量非空值的列
    numeric_cols = [c for c in numeric_cols if df[c].dropna().shape[0] >= 3]
    return numeric_cols


def get_regression_pairs(df):
    """
    从预定义的领域假设中，筛选出数据中实际存在的变量对。

    Returns
    -------
    list of dict: [{'x': str, 'y': str, 'description': str}, ...]
    """
    available = set(df.columns)
    pairs = []
    for x, y, desc in DOMAIN_REGRESSION_PAIRS:
        if x in available and y in available:
            pairs.append({'x': x, 'y': y, 'description': desc})
    return pairs


def get_phase_palette():
    """返回相态配色方案"""
    return {
        'gas': '#4E79A7',
        'liquid': '#F28E2B',
        'solid': '#E15759',
        'env': '#59A14F',
        'unknown': '#999999',
    }


def get_short_name(col_name):
    """获取变量短名，没有则返回原名"""
    return SHORT_NAMES.get(col_name, str(col_name))


def infer_derived_variables(df):
    """
    从原始列推导衍生变量（气相碳、液相碳、固相碳等）。
    就地修改 df，返回 df。
    """
    # 气相碳 = CH4 + CO2
    ch4_col = _find_col(df, ['CH4平均值', '甲烷(ppm)', '甲烷PPM', '甲烷（PPM）'])
    co2_col = _find_col(df, ['CO2', 'CO2(ppm)', 'CO2(PPM)', 'CO2(mg/L)'])
    if ch4_col and co2_col:
        df['气相碳'] = pd.to_numeric(df[ch4_col], errors='coerce') + \
                      pd.to_numeric(df[co2_col], errors='coerce')

    # 液相碳 = TC
    tc_col = _find_col(df, ['TC(mg/L)'])
    if tc_col:
        df['液相碳'] = pd.to_numeric(df[tc_col], errors='coerce')

    # 固相碳 = 固总碳
    solid_col = _find_col(df, ['固总碳（g/kg)'])
    if solid_col:
        df['固相碳'] = pd.to_numeric(df[solid_col], errors='coerce')

    # 气液碳比
    if '气相碳' in df.columns and '液相碳' in df.columns:
        df['气液碳比'] = df['气相碳'] / df['液相碳'].replace(0, np.nan)

    return df


def _find_col(df, candidates):
    """在 df 中找到第一个存在的列名"""
    for c in candidates:
        if c in df.columns:
            return c
    return None
