"""
=============================================================================
硕士论文级科研绘图模板 - Academic Plot Style Module
参考 Nature, Water Research, ES&T, STOTEN, Journal of Hydrology 等期刊风格
=============================================================================
"""

import os
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import rcParams
import seaborn as sns
import numpy as np

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
    # 只用文件路径，不设rcParams（rcParams会覆盖fontproperties kwarg）
    font_path = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', 'simhei.ttf')
    if not os.path.exists(font_path):
        for f in fm.fontManager.ttflist:
            if f.name == 'SimHei':
                font_path = f.fname
                break
    if font_path and os.path.exists(font_path):
        CN_FONT_PROP = fm.FontProperties(fname=font_path)
        CN_FONT_PROP_BOLD = fm.FontProperties(fname=font_path, weight='bold')
    else:
        CN_FONT_PROP = fm.FontProperties(family='SimHei')
        CN_FONT_PROP_BOLD = fm.FontProperties(family='SimHei', weight='bold')
    rcParams['axes.unicode_minus'] = False
    rcParams['mathtext.fontset'] = 'stix'
    rcParams['mathtext.default'] = 'regular'
    print(f"[字体配置] SimHei: {font_path}")
    return 'SimHei', 'Times New Roman', CN_FONT_PROP, CN_FONT_PROP_BOLD

CHINESE_FONT, ENGLISH_FONT, CN_FONT_PROP, CN_FONT_PROP_BOLD = setup_fonts()

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
    print("[绘图风格] 学术绘图模板已加载")

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
# 8. 期刊规范（整合自 scientific-visualization skill）
# ============================================================================

JOURNAL_CONFIGS = {
    'nature': {
        'name': 'Nature',
        'single_column_mm': 89,
        'double_column_mm': 183,
        'max_height_mm': 247,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'dpi_combo': 600,
        'font': 'Arial',
        'font_min_pt': 5,
        'font_label_pt': 7,
        'font_tick_pt': 6,
        'font_panel_pt': 10,
        'panel_label_style': 'lowercase_bold',  # a, b, c (Nature)
        'color_space': 'RGB',
        'format_vector': ['pdf', 'eps'],
        'format_raster': ['tiff', 'png'],
    },
    'science': {
        'name': 'Science',
        'single_column_mm': 55,
        'double_column_mm': 175,
        'max_height_mm': 233,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'font': 'Helvetica',
        'font_min_pt': 6,
        'panel_label_style': 'uppercase_paren',  # (A), (B), (C)
    },
    'cell': {
        'name': 'Cell Press',
        'single_column_mm': 85,
        'double_column_mm': 178,
        'max_height_mm': 230,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'font': 'Arial',
        'font_label_pt': 8,
        'font_tick_pt': 6,
        'panel_label_style': 'uppercase_bold',  # A, B, C
    },
    'elsevier': {
        'name': 'Elsevier',
        'single_column_mm': 90,
        'double_column_mm': 190,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'font': 'Arial',
        'panel_label_style': 'uppercase_paren',
    },
}

# 默认期刊
DEFAULT_JOURNAL = 'nature'

def get_journal_config(journal=None):
    """获取期刊配置"""
    return JOURNAL_CONFIGS.get(journal or DEFAULT_JOURNAL, JOURNAL_CONFIGS['nature'])

def mm_to_inches(mm):
    """毫米转英寸"""
    return mm / 25.4

def get_figure_size(journal=None, columns=1):
    """根据期刊获取推荐figsize (inch)"""
    cfg = get_journal_config(journal)
    if columns == 2:
        w = cfg['double_column_mm']
    elif columns == 1.5:
        w = (cfg['single_column_mm'] + cfg['double_column_mm']) / 2
    else:
        w = cfg['single_column_mm']
    h = cfg.get('max_height_mm', 247) * 0.4  # 默认半高
    return (mm_to_inches(w), mm_to_inches(h))

def get_save_dpi(journal=None, fig_type='line_art'):
    """根据期刊获取保存DPI"""
    cfg = get_journal_config(journal)
    if fig_type == 'photo':
        return cfg.get('dpi_photo', 300)
    elif fig_type == 'combo':
        return cfg.get('dpi_combo', 600)
    return cfg.get('dpi_line_art', 1000)

def add_panel_label(ax, index, journal=None, x=-0.12, y=1.08):
    """
    添加子图标注 (a), (b), (c) 等

    Parameters
    ----------
    ax : matplotlib Axes
    index : int, 0=a, 1=b, 2=c...
    journal : str, 期刊名
    x, float, 标注位置 (相对axes坐标)
    """
    import string
    cfg = get_journal_config(journal)
    style = cfg.get('panel_label_style', 'lowercase_bold')
    fontsize = cfg.get('font_panel_pt', 10)

    if style == 'lowercase_bold':
        label = string.ascii_lowercase[index]
    elif style == 'uppercase_bold':
        label = string.ascii_uppercase[index]
    elif style == 'uppercase_paren':
        label = f'({string.ascii_uppercase[index]})'
    elif style == 'lowercase_paren':
        label = f'({string.ascii_lowercase[index]})'
    else:
        label = string.ascii_lowercase[index]

    ax.text(x, y, label, transform=ax.transAxes,
            fontsize=fontsize, fontweight='bold', va='top',
            fontproperties=CN_FONT_PROP)

def save_figure_publication(fig, filename, output_dir, journal=None,
                            formats=None, fig_type='line_art'):
    """
    按期刊规范保存图表

    Parameters
    ----------
    fig : matplotlib Figure
    filename : str, 文件名（不含扩展名）
    output_dir : str, 输出目录
    journal : str, 期刊名 (nature/science/cell/elsevier)
    formats : list, 输出格式 ['pdf','png','svg']
    fig_type : str, line_art/photo/combo
    """
    import os
    cfg = get_journal_config(journal)
    dpi = get_save_dpi(journal, fig_type)
    if formats is None:
        formats = ['png', 'pdf', 'svg']

    os.makedirs(output_dir, exist_ok=True)
    saved = []
    for fmt in formats:
        path = os.path.join(output_dir, f'{filename}.{fmt}')
        fig.savefig(path, dpi=dpi, bbox_inches='tight',
                    format=fmt, pad_inches=0.1, facecolor='white')
        saved.append(path)

    journal_name = cfg.get('name', journal or 'default')
    print(f"  Saved {len(saved)} formats @ {dpi} DPI ({journal_name} spec)")
    return saved

# ============================================================================
# 7. 初始化
# ============================================================================
set_plot_style()

print("=" * 60)
print("学术绘图模板已加载")
print(f"中文字体: {CHINESE_FONT}")
print(f"英文字体: {ENGLISH_FONT}")
print("=" * 60)
