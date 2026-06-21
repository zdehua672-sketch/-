# -*- coding: utf-8 -*-
"""
气体污染物空间分布图生成模块

按季节和功能区分组，生成高质量学术期刊图表

作者：AI学术写作系统
版本：1.0
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
import seaborn as sns
from scipy import stats

# 导入学术图表规范
from academic_plot_style import (
    set_academic_style, get_figure_size, get_label, get_color_palette,
    save_figure_publication, add_panel_label, add_significance_bar,
    SEASON_COLORS, NATURE_COLORS, FONT_MANAGER
)


def create_gas_distribution_figures(df: pd.DataFrame, output_dir: str) -> list:
    """
    创建气体污染物空间分布图

    Parameters
    ----------
    df : pd.DataFrame, 数据
    output_dir : str, 输出目录

    Returns
    -------
    list : 生成的图片文件路径
    """
    # 设置学术风格
    set_academic_style('nature')

    # 定义气体变量（支持多种命名格式）
    gas_vars = ['甲烷(ppm)', 'CH4平均值', 'CO2(ppm)', 'CO2', '氧化亚氮(ppm)', 'N2O平均值', 'VOCs(ppb)']
    # 去重并保持顺序
    seen = set()
    available_vars = []
    for v in gas_vars:
        if v in df.columns and v not in seen:
            available_vars.append(v)
            seen.add(v)

    if not available_vars:
        print("没有找到气体变量数据")
        return []

    # 定义功能区
    def get_area(point):
        """根据采样点判断功能区"""
        if point.startswith('R'):
            num = int(point[1:]) if point[1:].isdigit() else 0
            if 1 <= num <= 12:
                return '教学楼/实验楼'
            elif 13 <= num <= 20:
                return '食堂/宿舍楼'
        return '其他'

    # 添加功能区列
    df = df.copy()
    df['功能区'] = df['采样点'].apply(get_area)

    # 获取季节列表
    seasons = sorted(df['季节'].unique())

    # 定义功能区颜色
    area_colors = {
        '教学楼/实验楼': '#4DBBD5',  # 蓝色
        '食堂/宿舍楼': '#E64B35',    # 红色
        '其他': '#8491B4',           # 灰色
    }

    generated_figures = []

    # 为每个气体变量生成图表
    for var in available_vars:
        fig_path = _create_single_gas_figure(
            df, var, seasons, area_colors, output_dir
        )
        if fig_path:
            generated_figures.append(fig_path)

    return generated_figures


def _create_single_gas_figure(df: pd.DataFrame, var: str, seasons: list,
                               area_colors: dict, output_dir: str) -> str:
    """
    为单个气体变量创建空间分布柱状图

    Parameters
    ----------
    df : pd.DataFrame, 数据
    var : str, 变量名
    seasons : list, 季节列表
    area_colors : dict, 功能区颜色
    output_dir : str, 输出目录

    Returns
    -------
    str : 图片文件路径
    """
    # 获取变量标签
    var_label = get_label(var)

    # 创建图表
    n_seasons = len(seasons)
    fig, axes = plt.subplots(1, n_seasons,
                            figsize=get_figure_size('nature', columns=2, height_ratio=0.6))

    if n_seasons == 1:
        axes = [axes]

    # 为每个季节创建子图
    for idx, season in enumerate(seasons):
        ax = axes[idx]
        season_data = df[df['季节'] == season].copy()

        if len(season_data) == 0:
            ax.set_visible(False)
            continue

        # 按采样点排序（R1, R2, ..., R20）
        def sort_key(point):
            # 提取数字部分进行排序
            import re
            match = re.search(r'R(\d+)', str(point))
            if match:
                return int(match.group(1))
            return 999

        season_data = season_data.copy()
        season_data['_sort_key'] = season_data['采样点'].apply(sort_key)
        season_data = season_data.sort_values('_sort_key')

        # 获取采样点和值
        points = season_data['采样点'].values
        values = pd.to_numeric(season_data[var], errors='coerce').values

        # 根据功能区设置颜色
        def get_area_color(point):
            """根据采样点获取功能区颜色"""
            if point.startswith('R'):
                try:
                    num = int(point[1:])
                    if 1 <= num <= 12:
                        return area_colors.get('教学楼/实验楼', '#4DBBD5')
                    elif 13 <= num <= 20:
                        return area_colors.get('食堂/宿舍楼', '#E64B35')
                except ValueError:
                    pass
            return '#8491B4'  # 默认灰色

        colors = [get_area_color(p) for p in points]

        # 绘制柱状图
        x_pos = np.arange(len(points))
        bars = ax.bar(x_pos, values,
                     color=colors, alpha=0.8,
                     edgecolor='white', linewidth=0.5)

        # 设置x轴标签（避免遮挡）
        ax.set_xticks(x_pos)
        ax.set_xticklabels(points, rotation=90, ha='center', fontsize=7)

        # 设置y轴标签
        ax.set_ylabel(var_label, fontsize=8)

        # 设置标题
        ax.set_title(f'{season}', fontsize=9, pad=10)

        # 添加网格线
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)

        # 添加样本量标注
        ax.text(0.95, 0.95, f'n={len(season_data)}',
                transform=ax.transAxes, ha='right', va='top',
                fontsize=7, style='italic')

        # 添加功能区图例
        handles = [mpatches.Patch(color=color, label=name)
                  for name, color in area_colors.items()]
        ax.legend(handles=handles, fontsize=6, loc='upper left',
                 framealpha=0.8, edgecolor='#CCCCCC')

    # 添加面板标签
    for idx in range(n_seasons):
        add_panel_label(axes[idx], idx)

    # 调整布局
    plt.tight_layout(pad=1.0, w_pad=0.5, h_pad=0.5)

    # 保存图表
    var_name = var.replace('(', '').replace(')', '').replace('/', '_')
    filename = f'gas_distribution_{var_name}'
    fig_path = save_figure_publication(fig, filename, output_dir, journal='nature')

    plt.close(fig)

    return fig_path[0] if fig_path else None


def create_area_comparison_figure(df: pd.DataFrame, output_dir: str) -> str:
    """
    创建功能区对比图

    Parameters
    ----------
    df : pd.DataFrame, 数据
    output_dir : str, 输出目录

    Returns
    -------
    str : 图片文件路径
    """
    # 设置学术风格
    set_academic_style('nature')

    # 定义气体变量（支持多种命名格式）
    gas_vars = ['甲烷(ppm)', 'CH4平均值', 'CO2(ppm)', 'CO2', '氧化亚氮(ppm)', 'N2O平均值', 'VOCs(ppb)']
    # 去重并保持顺序
    seen = set()
    available_vars = []
    for v in gas_vars:
        if v in df.columns and v not in seen:
            available_vars.append(v)
            seen.add(v)

    if not available_vars:
        return None

    # 定义功能区
    def get_area(point):
        if point.startswith('R'):
            num = int(point[1:]) if point[1:].isdigit() else 0
            if 1 <= num <= 12:
                return '教学楼/实验楼'
            elif 13 <= num <= 20:
                return '食堂/宿舍楼'
        return '其他'

    df = df.copy()
    df['功能区'] = df['采样点'].apply(get_area)

    # 创建图表
    n_vars = len(available_vars)
    fig, axes = plt.subplots(2, 2, figsize=get_figure_size('nature', columns=2, height_ratio=0.8))

    # 功能区颜色
    area_colors = {
        '教学楼/实验楼': '#4DBBD5',
        '食堂/宿舍楼': '#E64B35',
    }

    # 为每个变量创建子图
    for idx, var in enumerate(available_vars[:4]):
        ax = axes[idx // 2][idx % 2]
        var_label = get_label(var)

        # 按功能区和季节分组
        for area_name, color in area_colors.items():
            area_data = df[df['功能区'] == area_name]
            if len(area_data) == 0:
                continue

            # 按季节分组
            seasons = sorted(area_data['季节'].unique())
            for season in seasons:
                season_data = area_data[area_data['季节'] == season]
                values = season_data[var].dropna()

                if len(values) > 0:
                    # 绘制箱线图
                    bp = ax.boxplot([values], positions=[seasons.index(season)],
                                   widths=0.3, patch_artist=True)

                    # 设置颜色
                    for box in bp['boxes']:
                        box.set_facecolor(color)
                        box.set_alpha(0.7)

                    # 添加散点
                    jitter = np.random.normal(0, 0.05, len(values))
                    ax.scatter([seasons.index(season) + j for j in jitter],
                              values, color=color, s=20, alpha=0.6,
                              edgecolors='white', linewidth=0.3)

        # 设置标签
        ax.set_xticks(range(len(seasons)))
        ax.set_xticklabels(seasons, fontsize=7)
        ax.set_ylabel(var_label, fontsize=8)
        ax.set_title(var_label, fontsize=9, pad=10)

        # 添加网格线
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)

    # 添加面板标签
    for idx in range(4):
        add_panel_label(axes[idx // 2][idx % 2], idx)

    # 添加共享图例
    handles = [mpatches.Patch(color=color, label=name)
              for name, color in area_colors.items()]
    fig.legend(handles=labels, loc='lower center', ncol=2,
              fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.02))

    # 调整布局
    plt.tight_layout(pad=1.0, w_pad=0.5, h_pad=0.5)

    # 保存图表
    fig_path = save_figure_publication(fig, 'gas_area_comparison', output_dir, journal='nature')

    plt.close(fig)

    return fig_path[0] if fig_path else None


def load_gas_data():
    """加载气体数据（使用冬春数据.xlsx）"""
    import pandas as pd
    import os

    # 优先使用桌面上的冬春数据.xlsx
    desktop_file = os.path.join(os.path.expanduser('~'), 'OneDrive', '桌面', '冬春数据.xlsx')
    local_file = 'data/sample_data.xlsx'

    # 选择数据文件
    if os.path.exists(desktop_file):
        data_file = desktop_file
        print(f"使用桌面数据: {data_file}")
    elif os.path.exists(local_file):
        data_file = local_file
        print(f"使用本地数据: {data_file}")
    else:
        print("未找到数据文件")
        return None

    try:
        # 读取两个sheet
        winter_df = pd.read_excel(data_file, sheet_name='冬季')
        spring_df = pd.read_excel(data_file, sheet_name='春季')

        # 添加季节列
        winter_df['季节'] = '冬季'
        spring_df['季节'] = '春季'

        # 统一列名（春季数据列名可能不同）
        if '检查井编号' in spring_df.columns:
            spring_df = spring_df.rename(columns={'检查井编号': '采样点'})

        # 合并数据
        df = pd.concat([winter_df, spring_df], ignore_index=True)

        # 确保有采样点列
        if '采样点' not in df.columns:
            print("❌ 数据中没有'采样点'列")
            return None

        print(f"数据加载成功: {len(df)} 行, {len(df['采样点'].unique())} 个采样点")
        return df

    except Exception as e:
        print(f"加载数据失败: {e}")
        return None


if __name__ == '__main__':
    # 加载数据
    df = load_gas_data()

    if df is not None:
        output_dir = 'paper_output/figures'
        os.makedirs(output_dir, exist_ok=True)

        print("=== 生成气体分布图 ===")
        figures = create_gas_distribution_figures(df, output_dir)
        print(f"生成 {len(figures)} 张图片")
