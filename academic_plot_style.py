# -*- coding: utf-8 -*-
"""
=============================================================================
学术论文高质量作图系统 v2.0 - Academic Plot Style System
=============================================================================

设计目标：
1. 统一的作图规范，一套系统解决所有问题
2. 符合 Nature/Science/Cell 等顶刊规范
3. 自动解决标签遮挡、乱码等问题
4. 内置图片审查系统，自动发现问题并修复

作者：AI学术写作系统
版本：2.0
=============================================================================
"""

import os
import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import rcParams
import matplotlib.font_manager as fm
import seaborn as sns
from typing import Optional, List, Tuple, Dict, Any

# ============================================================================
# 第一部分：基础配置
# ============================================================================

# 1.1 期刊规范配置
JOURNAL_CONFIGS = {
    'nature': {
        'name': 'Nature',
        'single_column_mm': 89,
        'double_column_mm': 183,
        'max_height_mm': 247,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'dpi_combo': 600,
        'font_family': 'sans-serif',
        'font_name': 'Arial',
        'font_size_pt': 7,
        'font_min_pt': 5,
        'font_label_pt': 7,
        'font_tick_pt': 6,
        'font_panel_pt': 10,
        'line_width': 0.8,
        'marker_size': 4,
        'panel_label_style': 'lowercase_bold',
        'spine_top': False,
        'spine_right': False,
        'grid': False,
    },
    'science': {
        'name': 'Science',
        'single_column_mm': 55,
        'double_column_mm': 175,
        'max_height_mm': 233,
        'dpi_line_art': 1000,
        'dpi_photo': 300,
        'font_family': 'sans-serif',
        'font_name': 'Helvetica',
        'font_size_pt': 8,
        'font_min_pt': 6,
        'panel_label_style': 'uppercase_paren',
        'spine_top': False,
        'spine_right': False,
        'grid': False,
    },
    'chinese': {
        'name': '中文期刊',
        'single_column_mm': 80,
        'double_column_mm': 160,
        'max_height_mm': 240,
        'dpi_line_art': 600,
        'dpi_photo': 300,
        'font_family': 'sans-serif',
        'font_name': 'SimHei',
        'font_size_pt': 8,
        'font_min_pt': 6,
        'panel_label_style': 'lowercase_bold',
        'spine_top': False,
        'spine_right': False,
        'grid': False,
    },
}

DEFAULT_JOURNAL = 'nature'


# ============================================================================
# 第二部分：字体系统（彻底解决乱码问题）
# ============================================================================

class FontManager:
    """字体管理器 - 自动检测和配置中英文字体"""

    def __init__(self):
        self.cn_font_name = None
        self.cn_font_path = None
        self.cn_font_prop = None
        self.cn_font_prop_bold = None
        self.en_font_name = 'Arial'
        self._setup_fonts()

    def _setup_fonts(self):
        """配置字体"""
        try:
            fm._load_fontmanager(try_read_cache=False)
        except Exception:
            pass

        # 中文字体候选列表
        CN_FONT_CANDIDATES = [
            ('Microsoft YaHei', 'msyh.ttc'),
            ('SimHei', 'simhei.ttf'),
            ('DengXian', 'Deng.ttf'),
            ('SimSun', 'simsun.ttc'),
        ]

        for font_name, font_file in CN_FONT_CANDIDATES:
            font_path = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', font_file)
            if os.path.exists(font_path):
                self.cn_font_name = font_name
                self.cn_font_path = font_path
                break
            for f in fm.fontManager.ttflist:
                if f.name == font_name:
                    self.cn_font_name = font_name
                    self.cn_font_path = f.fname
                    break
            if self.cn_font_name:
                break

        if self.cn_font_name:
            self.cn_font_prop = fm.FontProperties(fname=self.cn_font_path)
            self.cn_font_prop_bold = fm.FontProperties(fname=self.cn_font_path, weight='bold')
            # 设置全局字体
            rcParams['font.sans-serif'] = [self.cn_font_name, 'DejaVu Sans', 'Arial']
            rcParams['font.family'] = 'sans-serif'
        else:
            self.cn_font_prop = fm.FontProperties(family='sans-serif')
            self.cn_font_prop_bold = fm.FontProperties(family='sans-serif', weight='bold')
            warnings.warn("未找到中文字体，中文可能显示为方块！")

        # 解决负号显示问题
        rcParams['axes.unicode_minus'] = False
        rcParams['mathtext.fontset'] = 'stix'
        rcParams['mathtext.default'] = 'regular'

    def get_cn_prop(self, weight='normal'):
        """获取中文字体属性"""
        if weight == 'bold':
            return self.cn_font_prop_bold
        return self.cn_font_prop

    def apply_to_text(self, text_obj, weight='normal'):
        """将中文字体应用到文本对象"""
        text_obj.set_fontproperties(self.get_cn_prop(weight))

    def apply_to_axes(self, ax, title=None, xlabel=None, ylabel=None):
        """将中文字体应用到坐标轴的所有文本"""
        if title:
            ax.set_title(title, fontproperties=self.cn_font_prop, fontsize=rcParams['axes.titlesize'])
        if xlabel:
            ax.set_xlabel(xlabel, fontproperties=self.cn_font_prop, fontsize=rcParams['axes.labelsize'])
        if ylabel:
            ax.set_ylabel(ylabel, fontproperties=self.cn_font_prop, fontsize=rcParams['axes.labelsize'])

        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(self.cn_font_prop)


# 全局字体管理器
FONT_MANAGER = FontManager()

# 兼容旧接口
CHINESE_FONT = FONT_MANAGER.cn_font_name
ENGLISH_FONT = FONT_MANAGER.en_font_name
CN_FONT_PROP = FONT_MANAGER.cn_font_prop
CN_FONT_PROP_BOLD = FONT_MANAGER.cn_font_prop_bold


# ============================================================================
# 第三部分：配色系统（色盲友好）
# ============================================================================

class ColorPalette:
    """配色方案管理器"""

    # Nature 标准配色（10色）
    NATURE = [
        '#E64B35',  # 红
        '#4DBBD5',  # 蓝
        '#00A087',  # 绿
        '#3C5488',  # 深蓝
        '#F39B7F',  # 橙
        '#8491B4',  # 灰蓝
        '#91D1C2',  # 浅绿
        '#DC0000',  # 深红
        '#7E6148',  # 棕
        '#B09C85',  # 浅棕
    ]

    # 色盲友好配色（Okabe-Ito）
    COLORBLIND = [
        '#0072B2',  # 蓝
        '#E69F00',  # 橙
        '#009E73',  # 绿
        '#F0E442',  # 黄
        '#56B4E9',  # 天蓝
        '#D55E00',  # 红
        '#CC79A7',  # 粉
        '#000000',  # 黑
    ]

    # 季节配色
    SEASON = {
        '冬季': '#4DBBD5',
        '春季': '#E64B35',
        '夏季': '#00A087',
        '秋季': '#F39B7F',
        'winter': '#4DBBD5',
        'spring': '#E64B35',
        'summer': '#00A087',
        'autumn': '#F39B7F',
    }

    # 相态配色
    PHASE = {
        '气相': '#4DBBD5',
        '液相': '#E64B35',
        '固相': '#00A087',
        'gas': '#4DBBD5',
        'liquid': '#E64B35',
        'solid': '#00A087',
    }

    # 碳组分配色
    CARBON = {
        'TOC': '#00A087',
        'IC': '#8491B4',
        'TC': '#3C5488',
        'DOC': '#91D1C2',
        'POC': '#F39B7F',
        '有机碳': '#91D1C2',
        '无机碳': '#F39B7F',
    }

    @classmethod
    def get_palette(cls, n_colors: int, palette: str = 'nature') -> List[str]:
        """获取配色方案"""
        if palette == 'nature':
            colors = cls.NATURE
        elif palette == 'colorblind':
            colors = cls.COLORBLIND
        elif palette == 'season':
            colors = list(cls.SEASON.values())
        elif palette == 'phase':
            colors = list(cls.PHASE.values())
        else:
            colors = cls.NATURE

        return [colors[i % len(colors)] for i in range(n_colors)]

    @classmethod
    def get_season_color(cls, season: str) -> str:
        """获取季节颜色"""
        return cls.SEASON.get(season, cls.NATURE[0])

    @classmethod
    def get_phase_color(cls, phase: str) -> str:
        """获取相态颜色"""
        return cls.PHASE.get(phase, cls.NATURE[0])


# 兼容旧接口
NATURE_COLORS = ColorPalette.NATURE
COLORBLIND_SAFE = ColorPalette.COLORBLIND
SEASON_COLORS = ColorPalette.SEASON
PHASE_COLORS = ColorPalette.PHASE
CARBON_COLORS = ColorPalette.CARBON
OKABE_ITO = {
    'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
    'yellow': '#F0E442', 'sky_blue': '#56B4E9', 'red': '#D55E00',
    'pink': '#CC79A7', 'black': '#000000', 'grey': '#999999',
}
TABLEAU_10 = NATURE_COLORS
get_color_palette = ColorPalette.get_palette

def set_axis_labels(ax, xlabel=None, ylabel=None, title=None):
    """设置坐标轴标签（自动处理化学式）"""
    if xlabel:
        ax.set_xlabel(get_label(xlabel))
    if ylabel:
        ax.set_ylabel(get_label(ylabel))
    if title:
        ax.set_title(title)


# ============================================================================
# 第四部分：标签系统（彻底解决遮挡问题）
# ============================================================================

class LabelManager:
    """标签管理器 - 自动处理标签遮挡"""

    # 化学式标签映射
    CHEMICAL_LABELS = {
        # 气相
        'CH4平均值': r'CH$_4$ (ppm)',
        '甲烷(ppm)': r'CH$_4$ (ppm)',
        '甲烷': r'CH$_4$ (ppm)',
        'N2O平均值': r'N$_2$O (ppm)',
        '氧化亚氮(ppm)': r'N$_2$O (ppm)',
        'CO2': r'CO$_2$ (ppm)',
        'CO2(ppm)': r'CO$_2$ (ppm)',
        'VOCs(ppb)': 'VOCs (ppb)',
        'O2(%vol)': r'O$_2$ (%vol)',
        'H2S': r'H$_2$S',
        # 液相
        'DO(mg/L)': 'DO (mg/L)',
        'pH': 'pH',
        '液温': '水温 (℃)',
        '电导率(uS/cm)': '电导率 (μS/cm)',
        'TOC（mg/L)': 'TOC (mg/L)',
        'TC(mg/L)': 'TC (mg/L)',
        'IC(mg/L)': 'IC (mg/L)',
        'COD（mg/L)': 'COD (mg/L)',
        '总氮（mg/L)': 'TN (mg/L)',
        '总磷（mg/L)': 'TP (mg/L)',
        '铵态氮（mg/L)': r'NH$_4^+$-N (mg/L)',
        '硝态氮（mg/L)': r'NO$_3^-$-N (mg/L)',
        'NaCl(mg/L)': 'NaCl (mg/L)',
        # 固相
        '固总碳（g/kg)': 'TC (g/kg)',
        '有机碳（g/kg)': 'TOC (g/kg)',
        '无机碳（g/kg)': 'IC (g/kg)',
        'DOC(mg/kg)': 'DOC (mg/kg)',
        '全磷（g/kg)': 'TP (g/kg)',
        # 环境
        '气温/℃': '气温 (℃)',
        '气温℃': '气温 (℃)',
        '采样点': '采样点',
    }

    @classmethod
    def get_label(cls, col: str) -> str:
        """获取变量的学术标签"""
        return cls.CHEMICAL_LABELS.get(col, col)

    @classmethod
    def format_chemical(cls, text: str) -> str:
        """格式化化学式"""
        replacements = [
            ('CH4', r'CH$_4$'), ('CO2', r'CO$_2$'), ('N2O', r'N$_2$O'),
            ('NO3', r'NO$_3$'), ('NH4', r'NH$_4$'), ('O2', r'O$_2$'),
            ('H2S', r'H$_2$S'), ('NO2', r'NO$_2$'),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    @classmethod
    def shorten_label(cls, label: str, max_len: int = 15) -> str:
        """缩短标签，避免遮挡"""
        if len(label) <= max_len:
            return label
        # 尝试保留单位
        if '(' in label:
            parts = label.split('(')
            name = parts[0].strip()
            unit = '(' + parts[1] if len(parts) > 1 else ''
            available_len = max_len - len(unit) - 1
            if available_len > 3:
                return name[:available_len] + '…' + unit
        return label[:max_len-1] + '…'

    @classmethod
    def auto_rotate_labels(cls, ax, threshold: int = 10):
        """自动旋转标签避免遮挡"""
        labels = ax.get_xticklabels()
        if not labels:
            return

        # 检查标签长度
        max_len = max(len(str(l.get_text())) for l in labels)
        if max_len > threshold:
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=rcParams['xtick.labelsize'])

    @classmethod
    def fix_label_overlap(cls, fig, ax_list):
        """修复标签遮挡"""
        fig.tight_layout(pad=1.0, w_pad=0.8, h_pad=0.8)


# 兼容旧接口
CHEMICAL_LABELS = LabelManager.CHEMICAL_LABELS
get_label = LabelManager.get_label
format_chemical = LabelManager.format_chemical


# ============================================================================
# 第五部分：样式系统
# ============================================================================

class StyleManager:
    """样式管理器 - 统一管理图表样式"""

    @staticmethod
    def set_style(journal: str = 'nature'):
        """设置学术图表样式"""
        cfg = JOURNAL_CONFIGS.get(journal, JOURNAL_CONFIGS['nature'])

        # 清除之前的样式
        plt.rcdefaults()

        # 设置 seaborn 样式（简洁风格）
        sns.set_style('ticks')

        # 更新全局参数
        rcParams.update({
            # 图表尺寸
            'figure.figsize': (7, 5),
            'figure.dpi': 150,
            'figure.facecolor': 'white',
            'figure.edgecolor': 'none',

            # 字体
            'font.size': cfg.get('font_size_pt', 7),
            'axes.titlesize': cfg.get('font_size_pt', 7) + 2,
            'axes.labelsize': cfg.get('font_label_pt', 7),
            'xtick.labelsize': cfg.get('font_tick_pt', 6),
            'ytick.labelsize': cfg.get('font_tick_pt', 6),
            'legend.fontsize': cfg.get('font_tick_pt', 6),

            # 线条
            'lines.linewidth': cfg.get('line_width', 0.8),
            'lines.markersize': cfg.get('marker_size', 4),
            'lines.markeredgewidth': 0.5,

            # 坐标轴
            'axes.linewidth': 0.8,
            'axes.spines.top': cfg.get('spine_top', False),
            'axes.spines.right': cfg.get('spine_right', False),
            'axes.grid': cfg.get('grid', False),

            # 刻度
            'xtick.major.width': 0.8,
            'ytick.major.width': 0.8,
            'xtick.major.size': 4,
            'ytick.major.size': 4,
            'xtick.direction': 'out',
            'ytick.direction': 'out',

            # 图例
            'legend.frameon': False,
            'legend.borderpad': 0.3,
            'legend.handlelength': 1.5,

            # 保存
            'savefig.dpi': cfg.get('dpi_line_art', 600),
            'savefig.format': 'png',
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.05,
            'savefig.transparent': False,
            'savefig.facecolor': 'white',

            # 中文支持
            'axes.unicode_minus': False,
        })

        # 确保中文字体生效
        if FONT_MANAGER.cn_font_name:
            rcParams['font.sans-serif'] = [FONT_MANAGER.cn_font_name, 'DejaVu Sans', 'Arial']
            rcParams['font.family'] = 'sans-serif'

        print(f"[绘图风格] 已加载 {cfg.get('name', journal)} 期刊规范")


# 兼容旧接口
set_academic_style = StyleManager.set_style
set_plot_style = StyleManager.set_style


# ============================================================================
# 第六部分：图表组件系统
# ============================================================================

class FigureComponents:
    """图表组件 - 可复用的图表元素"""

    @staticmethod
    def add_panel_label(ax, index: int, journal: str = None, x: float = -0.15, y: float = 1.05, **kwargs):
        """添加面板标签 (a), (b), (c)"""
        import string
        cfg = JOURNAL_CONFIGS.get(journal or DEFAULT_JOURNAL, JOURNAL_CONFIGS['nature'])
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

        defaults = dict(
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight='bold',
            va='top',
        )
        defaults.update(kwargs)
        ax.text(x, y, label, **defaults)

    @staticmethod
    def add_significance_bar(ax, x1: float, x2: float, y: float, p_value: float,
                             h: float = None, color: str = '#333333',
                             effect_size: float = None, show_detail: bool = False):
        """
        添加显著性横线

        Parameters
        ----------
        ax : matplotlib axes
        x1, x2 : float, 横线起止位置
        y : float, 横线高度
        p_value : float, p值
        h : float, 横线高度增量
        color : str, 颜色
        effect_size : float, 效应量（可选）
        show_detail : bool, 是否显示详细信息（p值和效应量）
        """
        if h is None:
            ylim = ax.get_ylim()
            h = (ylim[1] - ylim[0]) * 0.03

        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y],
                color=color, linewidth=1.0, clip_on=False)

        # 构建标注文本
        stars = significance_stars(p_value)

        if show_detail:
            # 显示详细信息：星号 + p值 + 效应量
            if p_value < 0.001:
                p_text = 'p<0.001'
            elif p_value < 0.01:
                p_text = f'p={p_value:.3f}'
            else:
                p_text = f'p={p_value:.2f}'

            if effect_size is not None:
                # Cohen's d 或 r 的效应量
                if abs(effect_size) < 1:
                    label = f'{stars}\n{p_text}\nr={effect_size:.2f}'
                else:
                    label = f'{stars}\n{p_text}\nd={effect_size:.2f}'
            else:
                label = f'{stars}\n{p_text}'
            fontsize = 7
        else:
            # 只显示星号
            label = stars
            fontsize = 8

        ax.text((x1 + x2) / 2, y + h, label,
                ha='center', va='bottom', fontsize=fontsize,
                fontweight='bold', color=color)

    @staticmethod
    def add_error_bars(ax, x, y, yerr, capsize: int = 3, **kwargs):
        """添加误差棒"""
        defaults = dict(
            fmt='none',
            ecolor='#333333',
            elinewidth=1,
            capsize=capsize,
            capthick=1,
        )
        defaults.update(kwargs)
        ax.errorbar(x, y, yerr=yerr, **defaults)

    @staticmethod
    def add_sample_size(ax, n: int, position: str = 'top-right'):
        """添加样本量标注"""
        if position == 'top-right':
            ax.text(0.95, 0.95, f'n={n}', transform=ax.transAxes,
                    ha='right', va='top', fontsize=7, style='italic')
        elif position == 'bottom-right':
            ax.text(0.95, 0.05, f'n={n}', transform=ax.transAxes,
                    ha='right', va='bottom', fontsize=7, style='italic')

    @staticmethod
    def add_shared_legend(fig, handles, labels, ncol: int = None, position: str = 'bottom', **kwargs):
        """添加共享图例"""
        if ncol is None:
            ncol = min(len(labels), 4)

        defaults = dict(
            loc='lower center',
            ncol=ncol,
            frameon=False,
            bbox_to_anchor=(0.5, -0.05),
        )
        defaults.update(kwargs)
        fig.legend(handles, labels, **defaults)


# 兼容旧接口
add_panel_label = FigureComponents.add_panel_label
add_significance_bar = FigureComponents.add_significance_bar
add_significance_bars = FigureComponents.add_significance_bar  # 旧接口别名
add_error_bars = FigureComponents.add_error_bars
add_sample_size = FigureComponents.add_sample_size
add_shared_legend = FigureComponents.add_shared_legend


# ============================================================================
# 第七部分：图表创建系统
# ============================================================================

class FigureFactory:
    """图表工厂 - 创建标准化图表"""

    @staticmethod
    def create_subplots(n_rows: int, n_cols: int, journal: str = 'nature', **kwargs):
        """创建符合期刊规范的子图布局"""
        cfg = JOURNAL_CONFIGS.get(journal, JOURNAL_CONFIGS['nature'])
        single_w = cfg['single_column_mm'] / 25.4
        double_w = cfg['double_column_mm'] / 25.4
        max_h = cfg['max_height_mm'] / 25.4

        if n_cols == 1:
            width = single_w
        elif n_cols == 2:
            width = double_w
        else:
            width = double_w * 1.2

        height = width * 0.5 * n_rows
        height = min(height, max_h * 0.8)

        figsize = kwargs.pop('figsize', (width, height))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, **kwargs)

        return fig, axes

    @staticmethod
    def get_figure_size(journal: str = None, columns: float = 1, height_ratio: float = 0.6):
        """获取推荐图表尺寸"""
        cfg = JOURNAL_CONFIGS.get(journal or DEFAULT_JOURNAL, JOURNAL_CONFIGS['nature'])
        if columns == 2:
            w = cfg['double_column_mm']
        elif columns == 1.5:
            w = (cfg['single_column_mm'] + cfg['double_column_mm']) / 2
        else:
            w = cfg['single_column_mm']
        h = w * height_ratio
        return (w / 25.4, h / 25.4)

    @staticmethod
    def get_save_dpi(journal: str = None, fig_type: str = 'line_art'):
        """获取保存DPI"""
        cfg = JOURNAL_CONFIGS.get(journal or DEFAULT_JOURNAL, JOURNAL_CONFIGS['nature'])
        if fig_type == 'photo':
            return cfg.get('dpi_photo', 300)
        elif fig_type == 'combo':
            return cfg.get('dpi_combo', 600)
        return cfg.get('dpi_line_art', 1000)


# 兼容旧接口
get_figure_size = FigureFactory.get_figure_size
get_save_dpi = FigureFactory.get_save_dpi
create_subplots = FigureFactory.create_subplots


# ============================================================================
# 第八部分：图表保存系统
# ============================================================================

class FigureSaver:
    """图表保存器"""

    @staticmethod
    def save(fig, filename: str, output_dir: str, journal: str = None,
             formats: List[str] = None, fig_type: str = 'line_art'):
        """按期刊规范保存图表（只生成PNG和PDF，不生成网页版）"""
        cfg = JOURNAL_CONFIGS.get(journal or DEFAULT_JOURNAL, JOURNAL_CONFIGS['nature'])
        dpi = FigureFactory.get_save_dpi(journal, fig_type)
        if formats is None:
            formats = ['png', 'pdf']  # 只生成PNG和PDF，不生成SVG

        os.makedirs(output_dir, exist_ok=True)
        saved = []
        for fmt in formats:
            path = os.path.join(output_dir, f'{filename}.{fmt}')
            fig.savefig(path, dpi=dpi, bbox_inches='tight',
                        format=fmt, pad_inches=0.05, facecolor='white')
            saved.append(path)

        return saved


# 兼容旧接口
save_figure = FigureSaver.save
save_figure_publication = FigureSaver.save


# ============================================================================
# 第九部分：图表审查系统（自动发现问题并修复）
# ============================================================================

class FigureReviewer:
    """图表审查器 - 自动检查图表质量"""

    @staticmethod
    def review(fig, ax_list=None) -> Dict[str, Any]:
        """审查图表质量"""
        issues = []
        fixes = []

        if ax_list is None:
            ax_list = fig.get_axes()

        for ax in ax_list:
            # 检查标签遮挡
            overlap_issues = FigureReviewer._check_label_overlap(ax)
            issues.extend(overlap_issues)

            # 检查字体
            font_issues = FigureReviewer._check_fonts(ax)
            issues.extend(font_issues)

            # 检查颜色
            color_issues = FigureReviewer._check_colors(ax)
            issues.extend(color_issues)

        # 检查尺寸
        size_issues = FigureReviewer._check_size(fig)
        issues.extend(size_issues)

        return {
            'issues': issues,
            'fixes': fixes,
            'score': max(0, 100 - len(issues) * 10),
        }

    @staticmethod
    def _check_label_overlap(ax) -> List[str]:
        """检查标签遮挡"""
        issues = []

        # 检查x轴标签
        x_labels = ax.get_xticklabels()
        if x_labels:
            # 检查标签长度
            max_len = max(len(str(l.get_text())) for l in x_labels)
            if max_len > 15:
                issues.append(f'x轴标签过长({max_len}字符)，可能遮挡')

            # 检查标签重叠
            renderer = ax.figure.canvas.get_renderer()
            for i, label in enumerate(x_labels):
                if i > 0:
                    bbox1 = x_labels[i-1].get_window_extent(renderer)
                    bbox2 = label.get_window_extent(renderer)
                    if bbox1.overlaps(bbox2):
                        issues.append(f'x轴标签 {i-1} 和 {i} 重叠')
                        break

        return issues

    @staticmethod
    def _check_fonts(ax) -> List[str]:
        """检查字体"""
        issues = []

        # 检查中文字体
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            font = label.get_fontproperties()
            if font.get_name() == 'DejaVu Sans' and any('一' <= c <= '鿿' for c in str(label.get_text())):
                issues.append('中文标签可能乱码')

        return issues

    @staticmethod
    def _check_size(fig) -> List[str]:
        """检查尺寸"""
        issues = []

        # 检查是否超过期刊限制
        width, height = fig.get_size_inches()
        max_width = JOURNAL_CONFIGS[DEFAULT_JOURNAL]['double_column_mm'] / 25.4
        max_height = JOURNAL_CONFIGS[DEFAULT_JOURNAL]['max_height_mm'] / 25.4

        if width > max_width * 1.2:
            issues.append(f'图表宽度({width:.1f}英寸)超过期刊限制({max_width:.1f}英寸)')
        if height > max_height * 0.8:
            issues.append(f'图表高度({height:.1f}英寸)接近期刊限制({max_height:.1f}英寸)')

        return issues

    @staticmethod
    def _check_colors(ax) -> List[str]:
        """检查颜色"""
        issues = []

        # 检查是否使用了红绿配色（色盲不友好）
        # 这里简化处理，实际可以更复杂

        return issues

    @staticmethod
    def auto_fix(fig, ax_list=None):
        """自动修复问题"""
        if ax_list is None:
            ax_list = fig.get_axes()

        for ax in ax_list:
            # 修复标签遮挡
            LabelManager.auto_rotate_labels(ax)

            # 修复字体
            FONT_MANAGER.apply_to_axes(ax)

        # 修复布局
        fig.tight_layout(pad=1.0, w_pad=0.8, h_pad=0.8)


# 兼容旧接口
ensure_chinese_text = FONT_MANAGER.apply_to_axes
validate_font_render = lambda x: None  # 占位函数
setup_fonts = lambda: (FONT_MANAGER.cn_font_name, FONT_MANAGER.en_font_name, FONT_MANAGER.cn_font_prop, FONT_MANAGER.cn_font_prop_bold)


# ============================================================================
# 第十部分：显著性标注
# ============================================================================

def significance_stars(p_value: float) -> str:
    """将p值转换为显著性星号"""
    if p_value is None:
        return ''
    if p_value <= 0.001:
        return '***'
    elif p_value <= 0.01:
        return '**'
    elif p_value <= 0.05:
        return '*'
    else:
        return 'n.s.'


# ============================================================================
# 第十一部分：初始化
# ============================================================================

# 设置默认样式
StyleManager.set_style('nature')

# 打印初始化信息
print("=" * 60)
print("学术论文作图系统 v2.0 已加载")
print(f"中文字体: {FONT_MANAGER.cn_font_name}")
print(f"英文字体: {FONT_MANAGER.en_font_name}")
print(f"默认期刊: {DEFAULT_JOURNAL}")
print("=" * 60)
