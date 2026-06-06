"""
=============================================================================
硕士论文级科研绘图模板 - Academic Plot Style Module
参考 Nature, Water Research, ES&T, STOTEN, Journal of Hydrology 等期刊风格
=============================================================================
"""

import logging
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import rcParams
import seaborn as sns
import numpy as np

_logger = logging.getLogger(__name__)

# ============================================================================
# 1. 色盲友好配色方案 (Okabe-Ito + Tableau 10)
# ============================================================================
OKABE_ITO = {
    'blue':     '#0072B2',
    'orange':   '#E69F00',
    'green':    '#009E73',
    'yellow':   '#F0E442',
    'sky_blue': '#56B4E9',
    'red':      '#D55E00',
    'pink':     '#CC79A7',
    'black':    '#000000',
    'grey':     '#999999',
}

TABLEAU_10 = [
    '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
    '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC'
]

PHASE_COLORS = {
    '气相': '#4E79A7',
    '液相': '#F28E2B',
    '固相': '#E15759',
}

SEASON_COLORS = {
    '冬季': '#4E79A7',
    '春季': '#F28E2B',
}

CARBON_COLORS = {
    'TOC': '#59A14F',
    'IC':  '#B07AA1',
    'TC':  '#4E79A7',
    'DOC': '#76B7B2',
    'POC': '#EDC948',
    '有机碳': '#76B7B2',
    '无机碳': '#EDC948',
}

# ============================================================================
# 2. 字体配置
# ============================================================================
def setup_fonts():
    import matplotlib.font_manager as fm
    chinese_fonts = [
        'Microsoft YaHei', 'SimHei', 'STHeiti',
        'Noto Sans CJK SC', 'WenQuanYi Micro Hei',
        'PingFang SC', 'Arial Unicode MS',
    ]
    english_font = 'Times New Roman'
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    selected_chinese = 'SimHei'
    for font in chinese_fonts:
        if font in available_fonts:
            selected_chinese = font
            break
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = [selected_chinese, 'DejaVu Sans']
    rcParams['font.serif'] = [english_font, 'DejaVu Serif']
    rcParams['axes.unicode_minus'] = False
    rcParams['mathtext.fontset'] = 'stix'
    rcParams['mathtext.default'] = 'regular'
    _logger.debug(f"[字体配置] 中文: {selected_chinese}, 英文: {english_font}")
    return selected_chinese, english_font

CHINESE_FONT, ENGLISH_FONT = setup_fonts()

# ============================================================================
# 3. 全局绘图参数
# ============================================================================
def set_plot_style():
    sns.set_style('whitegrid', {
        'axes.edgecolor': '#333333',
        'axes.facecolor': 'white',
        'axes.grid': True,
        'grid.color': '#E0E0E0',
        'grid.linestyle': '--',
        'grid.alpha': 0.5,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.spines.left': True,
        'axes.spines.bottom': True,
    })
    rcParams.update({
        'figure.figsize': (8, 6),
        'figure.dpi': 150,
        'figure.facecolor': 'white',
        'figure.edgecolor': '#D9D9D9',
        'font.size': 11,
        'axes.titlesize': 16,
        'axes.labelsize': 13,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'legend.fontsize': 11,
        'lines.linewidth': 2.0,
        'lines.markersize': 8,
        'lines.markeredgewidth': 0.5,
        'xtick.major.width': 1.0,
        'ytick.major.width': 1.0,
        'xtick.minor.width': 0.5,
        'ytick.minor.width': 0.5,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.major.size': 6,
        'ytick.major.size': 6,
        'legend.frameon': True,
        'legend.framealpha': 0.9,
        'legend.edgecolor': '#BBBBBB',
        'legend.facecolor': 'white',
        'legend.fancybox': False,
        'savefig.dpi': 300,
        'savefig.format': 'png',
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,
        'savefig.transparent': False,
    })
    _logger.debug("[绘图风格] 学术绘图模板已加载")

# ============================================================================
# 4. 化学式标签映射
# ============================================================================
CHEMICAL_LABELS = {
    'CH4平均值': r'CH$_4$ (ppm)',
    '甲烷(ppm)': r'CH$_4$ (ppm)',
    '甲烷': r'CH$_4$ (ppm)',
    'N2O平均值': r'N$_2$O (ppm)',
    '氧化亚氮(ppm)': r'N$_2$O (ppm)',
    '氧化亚氮（ppm）': r'N$_2$O (ppm)',
    '氧化亚氮': r'N$_2$O (ppm)',
    'CO2': r'CO$_2$ (ppm)',
    'CO2(ppm)': r'CO$_2$ (ppm)',
    'CO2(PPM)': r'CO$_2$ (ppm)',
    'VOCs(ppb)': 'VOCs (ppb)',
    'O2(%vol)': r'O$_2$ (%vol)',
    'DO(mg/L)': 'DO (mg/L)',
    'pH': 'pH',
    '液温': '水温 (℃)',
    '电导率(uS/cm)': '电导率 (μS/cm)',
    '电导率(us/cm)': '电导率 (μS/cm)',
    'TOC（mg/L)': 'TOC (mg/L)',
    'TC(mg/L)': 'TC (mg/L)',
    'IC(mg/L)': 'IC (mg/L)',
    'COD（mg/L)': 'COD (mg/L)',
    '总氮（mg/L)': 'TN (mg/L)',
    '总磷（mg/L)': 'TP (mg/L)',
    '铵态氮（mg/L)': r'NH$_4^+$ (mg/L)',
    '硝态氮（mg/L)': r'NO$_3^-$ (mg/L)',
    'NaCl(mg/L)': 'NaCl (mg/L)',
    '固总碳（g/kg)': '固相TC (g/kg)',
    '有机碳（g/kg)': '固相TOC (g/kg)',
    '无机碳（g/kg)': '固相IC (g/kg)',
    'DOC(mg/kg)': 'DOC (mg/kg)',
    '全磷（g/kg)': '固相TP (g/kg)',
    '（固）铵态氮（mg/kg）': r'固相NH$_4^+$ (mg/kg)',
    '（固）硝态氮（mg/kg）': r'固相NO$_3^-$ (mg/kg)',
    '气温/℃': '气温 (℃)',
    '气温℃': '气温 (℃)',
    'H2S': r'H$_2$S',
    '泥水状况': '泥水状况',
    '采样时间': '采样时间',
    '采样时段': '采样时段',
    '气相碳': '气相碳 (ppm)',
    '液相碳': '液相碳 (mg/L)',
    '固相碳': '固相碳 (g/kg)',
    'TOC比例': 'TOC/TC',
    'IC比例': 'IC/TC',
    '气液碳比': '气/液碳比',
    'CH4_TOCT比': r'CH$_4$/TOC',
}

def get_label(col):
    return CHEMICAL_LABELS.get(col, col)

def format_chemical(text):
    replacements = [
        ('CH4', r'CH$_4$'), ('CO2', r'CO$_2$'), ('N2O', r'N$_2$O'),
        ('NO3', r'NO$_3$'), ('NH4', r'NH$_4$'), ('O2', r'O$_2$'),
        ('H2S', r'H$_2$S'), ('NO2', r'NO$_2$'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text

# ============================================================================
# 5. 显著性标注
# ============================================================================
def significance_stars(p_value):
    if p_value <= 0.001:
        return '***'
    elif p_value <= 0.01:
        return '**'
    elif p_value <= 0.05:
        return '*'
    else:
        return 'n.s.'

def add_significance_bars(ax, x1, x2, y, h=0.02, p_value=0.05, text_offset=0.01):
    from matplotlib import lines as mlines
    line = mlines.Line2D([x1, x1, x2, x2],
                         [y, y + h, y + h, y],
                         color='#333333', lw=1.2)
    ax.add_line(line)
    stars = significance_stars(p_value)
    ax.text((x1 + x2) / 2, y + h + text_offset, stars,
            ha='center', va='bottom',
            fontsize=12, fontweight='bold', color='#333333')

# ============================================================================
# 6. 保存函数
# ============================================================================
def save_figure(fig, filename, output_dir, formats=None):
    import os
    if formats is None:
        formats = ['png', 'pdf', 'svg']
    saved_files = []
    for fmt in formats:
        filepath = os.path.join(output_dir, f"{filename}.{fmt}")
        fig.savefig(filepath, dpi=300, bbox_inches='tight',
                    format=fmt, pad_inches=0.1)
        saved_files.append(filepath)
    return saved_files

# ============================================================================
# 7. 初始化（仅首次import时执行，使用logging代替print）
# ============================================================================
_initialized = False
if not _initialized:
    set_plot_style()
    _initialized = True
