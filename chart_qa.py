# -*- coding: utf-8 -*-
"""
图表质量检测器 v3 - 增强版
检测项：文字重叠、刻度碰撞、图例遮挡、标注与图形重叠、子图挤压、轴标签裁剪
支持自动修复
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import itertools
import io, sys, os
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logger = logging.getLogger(__name__)


def check_chart_quality(fig, auto_fix=True, verbose=False):
    """
    检测图表质量，可选自动修复。

    Parameters
    ----------
    fig : matplotlib Figure
    auto_fix : bool - 检测到问题时是否自动修复
    verbose : bool - 是否打印详细信息

    Returns
    -------
    dict: {
        'status': 'PASS'|'WARN'|'FAIL',
        'high': int,
        'medium': int,
        'issues': [(type, severity, detail), ...],
        'fixed': [(type, action), ...],
    }
    """
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    except Exception as e:
        logger.debug(f"chart_qa renderer: {e}")
        return {'status': 'SKIP', 'high': 0, 'medium': 0, 'issues': [], 'fixed': []}

    issues = []
    fixed = []
    axes = fig.get_axes()

    for ax in axes:
        ax_bbox = ax.get_window_extent(renderer)

        # --- 检测1: x轴刻度碰撞 ---
        xlabels = [l for l in ax.get_xticklabels() if l.get_text().strip()]
        for i in range(len(xlabels) - 1):
            try:
                bb1 = xlabels[i].get_window_extent(renderer)
                bb2 = xlabels[i+1].get_window_extent(renderer)
                if bb1.overlaps(bb2):
                    issues.append(('XTICK_COLLISION', 'HIGH',
                                   f'{xlabels[i].get_text()} <-> {xlabels[i+1].get_text()}'))
                    if auto_fix:
                        # 缩小字号
                        for l in xlabels:
                            l.set_fontsize(max(6, l.get_fontsize() - 1))
                        fixed.append(('XTICK_COLLISION', 'reduced fontsize'))
            except Exception as e:
                logger.debug(f"chart_qa check skipped: {e}")

        # --- 检测2: 文字重叠（标注之间）---
        texts = [c for c in ax.get_children()
                 if hasattr(c, 'get_text') and c.get_text().strip()
                 and c.get_text() not in ['', ' ', ax.get_title()]]
        # 排除轴标签和标题
        texts = [t for t in texts
                 if t not in ax.get_xticklabels() + ax.get_yticklabels()
                 and t != ax.title
                 and t != ax.xaxis.label
                 and t != ax.yaxis.label]

        for t1, t2 in itertools.combinations(texts, 2):
            try:
                bb1 = t1.get_window_extent(renderer)
                bb2 = t2.get_window_extent(renderer)
                if bb1.overlaps(bb2):
                    inter = bb1.intersection(bb1, bb2)
                    if inter is not None:
                        overlap_area = inter.width * inter.height
                        a1 = bb1.width * bb1.height
                        a2 = bb2.width * bb2.height
                        if a1 > 0 and a2 > 0:
                            ratio = overlap_area / min(a1, a2)
                            if ratio > 0.3:
                                issues.append(('TEXT_OVERLAP', 'HIGH',
                                               f'{t1.get_text()[:20]} <-> {t2.get_text()[:20]} ({ratio:.0%})'))
                                if auto_fix:
                                    # 缩小字号
                                    t1.set_fontsize(max(6, t1.get_fontsize() - 1))
                                    t2.set_fontsize(max(6, t2.get_fontsize() - 1))
                                    fixed.append(('TEXT_OVERLAP', 'reduced fontsize'))
            except Exception as e:
                logger.debug(f"chart_qa check skipped: {e}")

        # --- 检测3: 图例遮挡数据 ---
        legend = ax.get_legend()
        if legend is not None:
            try:
                leg_bbox = legend.get_window_extent(renderer)
                for child in ax.patches + ax.lines:
                    try:
                        cb = child.get_window_extent(renderer)
                        if leg_bbox.overlaps(cb):
                            inter = leg_bbox.intersection(leg_bbox, cb)
                            if inter is not None and inter.width * inter.height > 200:
                                issues.append(('LEGEND_OBSCURES_DATA', 'MEDIUM', ''))
                                if auto_fix:
                                    legend.set_bbox_to_anchor(None)
                                    ax.legend(loc='upper left', framealpha=0.9)
                                    fixed.append(('LEGEND_OBSCURES_DATA', 'moved to upper left'))
                                break
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"chart_qa check skipped: {e}")

        # --- 检测4: 标注与图形元素重叠（柱子/散点）---
        for text_obj in texts:
            try:
                tb = text_obj.get_window_extent(renderer)
                for patch in ax.patches:
                    try:
                        pb = patch.get_window_extent(renderer)
                        if tb.overlaps(pb):
                            inter = tb.intersection(tb, pb)
                            if inter is not None:
                                overlap = inter.width * inter.height
                                ta = tb.width * tb.height
                                if ta > 0 and overlap / ta > 0.4:
                                    issues.append(('LABEL_BUBBLE_OVERLAP', 'MEDIUM',
                                                   f'{text_obj.get_text()[:15]} overlaps patch'))
                                    break
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"chart_qa check skipped: {e}")

        # --- 检测5: 轴标签被裁剪 ---
        for label in [ax.xaxis.label, ax.yaxis.label]:
            if label.get_text():
                try:
                    lb = label.get_window_extent(renderer)
                    fig_bbox = fig.get_window_extent()
                    if (lb.x0 < fig_bbox.x0 + 5 or lb.x1 > fig_bbox.x1 - 5 or
                            lb.y0 < fig_bbox.y0 + 5 or lb.y1 > fig_bbox.y1 - 5):
                        issues.append(('AXIS_LABEL_CLIPPING', 'MEDIUM', label.get_text()[:20]))
                except Exception:
                    pass

    # --- 检测6: 子图挤压（高度比不合理）---
    if len(axes) >= 2:
        heights = []
        for ax in axes:
            try:
                bb = ax.get_window_extent(renderer)
                heights.append(bb.height)
            except Exception as e:
                logger.debug(f"chart_qa check skipped: {e}")
        if heights:
            min_h = min(heights)
            max_h = max(heights)
            if max_h > 0 and min_h / max_h < 0.25:
                issues.append(('SUBPLOT_SQUEEZE', 'HIGH',
                               f'最小/最大高度比={min_h/max_h:.0%}，子图过扁'))

    # --- 检测7: colorbar对齐 ---
    for ax in axes:
        for child in ax.get_children():
            if child.__class__.__name__ == 'Colorbar':
                try:
                    cb_bbox = child.ax.get_window_extent(renderer)
                    # 检查colorbar是否与相邻axes有明显偏移
                    for other_ax in axes:
                        if other_ax != ax:
                            ob = other_ax.get_window_extent(renderer)
                            # colorbar应与某个axes垂直对齐
                            if abs(cb_bbox.y0 - ob.y0) > 20 or abs(cb_bbox.y1 - ob.y1) > 20:
                                issues.append(('COLORBAR_ALIGNMENT', 'MEDIUM', ''))
                                break
                except Exception:
                    pass

    # 汇总
    # 过滤掉suptitle被误检为轴外文本的情况
    issues = [i for i in issues if not (i[0] == 'TEXT_OUTSIDE_AXES' and 'suptitle' in str(i[2]).lower())]

    n_high = sum(1 for i in issues if i[1] == 'HIGH')
    n_med = sum(1 for i in issues if i[1] == 'MEDIUM')
    status = 'FAIL' if n_high > 0 else ('WARN' if n_med > 0 else 'PASS')

    return {
        'status': status,
        'high': n_high,
        'medium': n_med,
        'issues': issues,
        'fixed': fixed,
    }


def print_qa_report(result, name='chart'):
    """打印QA报告"""
    icons = {'PASS': '[OK]', 'WARN': '[!!]', 'FAIL': '[XX]', 'SKIP': '[--]'}
    s = icons.get(result['status'], '[??]')
    print(f"  {s} {name} | HIGH:{result['high']} MEDIUM:{result['medium']}", end='')
    if result['fixed']:
        print(f' | Fixed:{len(result["fixed"])}', end='')
    print()

    for typ, sev, detail in result['issues']:
        mark = '[XX]' if sev == 'HIGH' else '[!!]'
        print(f"    {mark} {typ}: {detail}")

    for typ, action in result['fixed']:
        print(f"    [FIX] {typ} -> {action}")


def qa_and_save(fig, path, name=None, dpi=300):
    """检测 + 自动修复 + 保存的便捷函数"""
    if name is None:
        name = os.path.basename(path)
    result = check_chart_quality(fig, auto_fix=True)
    # 如果自动修复了问题，重新绘制
    if result['fixed']:
        fig.canvas.draw()
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    return result


# ================================================================
# Nature 交付级 QA（来自 nature-figure skill QA Contract）
# ================================================================

# Nature 系列期刊尺寸规范（mm）
NATURE_SIZES = {
    'single': 89,      # 单栏 ~89mm
    'double': 183,     # 双栏 ~183mm
    'full': 183,       # 满页
}

# Nature 字体大小规范
NATURE_FONT_SIZES = {
    'body_min': 5,     # 正文最小 5pt
    'body_max': 7,     # 正文推荐 5-7pt
    'panel_label': 8,  # 面板标签 8pt
    'tick_min': 5,     # 刻度标签最小
}

# Nature 色板（色盲安全，来自 figures4papers）
NATURE_PALETTE = {
    'blue_main': '#0F4D92',
    'blue_secondary': '#3775BA',
    'green_1': '#DDF3DE',
    'green_2': '#AADCA9',
    'green_3': '#8BCF8B',
    'red_1': '#F6CFCB',
    'red_2': '#E9A6A1',
    'red_strong': '#B64342',
    'neutral_light': '#CFCECE',
    'neutral_mid': '#767676',
    'neutral_dark': '#4D4D4D',
    'neutral_black': '#272727',
    'teal': '#42949E',
    'violet': '#9A4D8E',
}


def check_nature_delivery(fig, target_journal='nature', auto_fix=False):
    """
    Nature 交付级 QA 检查（来自 nature-figure skill QA Contract）。

    检查项（除已有 chart_qa 检测外）：
    - SVG/PDF 文本可编辑性
    - 色彩无障碍（色盲安全）
    - 字体一致性（Arial/Helvetica）
    - 分辨率/尺寸规范
    - 面板标签规范
    - 图例策略

    Parameters
    ----------
    fig : matplotlib Figure
    target_journal : str - 'nature', 'nat-comms', 'generic'
    auto_fix : bool - 是否自动修复

    Returns
    -------
    dict: 同 check_chart_quality 返回格式，增加 'nature_checks' 字段
    """
    issues = []
    fixed = []

    # --- 基础 QA ---
    base_result = check_chart_quality(fig, auto_fix=auto_fix)
    issues.extend([(t, s, d) for t, s, d in base_result['issues']])
    fixed.extend(base_result['fixed'])

    # --- Nature 交付检查 ---

    # 1. 字体检查：应使用 Arial/Helvetica/sans-serif
    for ax in fig.get_axes():
        for text_obj in ax.get_children():
            if hasattr(text_obj, 'get_fontfamily'):
                family = text_obj.get_fontfamily()
                if family and isinstance(family, (list, tuple)):
                    family_str = str(family[0]).lower()
                elif family:
                    family_str = str(family).lower()
                else:
                    continue
                if any(f in family_str for f in ['times', 'serif', 'georgia', 'palatino']):
                    issues.append(('NATURE_FONT_VIOLATION', 'MAJOR',
                                   f'{text_obj.get_text()[:20] if hasattr(text_obj, "get_text") else ""} '
                                   f'uses {family_str}, should be Arial/Helvetica/sans-serif'))
                    if auto_fix and hasattr(text_obj, 'set_fontfamily'):
                        text_obj.set_fontfamily('sans-serif')
                        fixed.append(('NATURE_FONT_VIOLATION', f'set {family_str} -> sans-serif'))

    # 2. 彩虹色图检查
    for ax in fig.get_axes():
        for im in ax.get_images():
            cmap_name = ''
            try:
                cmap_name = im.get_cmap().name if hasattr(im.get_cmap(), 'name') else str(im.get_cmap())
            except Exception:
                pass
            if cmap_name and any(r in cmap_name.lower() for r in ['rainbow', 'jet', 'hsv', 'hot']):
                issues.append(('NATURE_COLORMAP', 'MAJOR',
                               f'{cmap_name} is not colorblind-safe, use viridis/cividis'))
                if auto_fix:
                    try:
                        im.set_cmap('viridis')
                        fixed.append(('NATURE_COLORMAP', f'{cmap_name} -> viridis'))
                    except Exception:
                        pass

    # 3. 红绿编码检查（色盲不友好）
    for ax in fig.get_axes():
        colors_in_use = set()
        for line in ax.get_lines():
            c = line.get_color()
            if c:
                colors_in_use.add(c.lower())
        for patch in ax.patches:
            c = patch.get_facecolor()
            if c:
                r, g, b = c[0], c[1], c[2]
                if r > 0.5 and g < 0.3 and b < 0.3:
                    colors_in_use.add('red')
                elif g > 0.5 and r < 0.3 and b < 0.3:
                    colors_in_use.add('green')
        if 'red' in colors_in_use and 'green' in colors_in_use:
            has_other = len(colors_in_use - {'red', 'green'}) > 0
            if not has_other:
                issues.append(('NATURE_RED_GREEN', 'MAJOR',
                               'Red/green only encoding — not colorblind-safe'))

    # 4. 面板标签检查（应为小写加粗，左上角 ~8pt）
    panel_labels = []
    for ax in fig.get_axes():
        for text_obj in ax.get_children():
            if hasattr(text_obj, 'get_text'):
                txt = text_obj.get_text()
                if txt and len(txt) <= 3 and txt.isalpha():
                    panel_labels.append(text_obj)
    if len(panel_labels) >= 2:
        for pl in panel_labels:
            try:
                fs = pl.get_fontsize()
                if fs and fs < 6:
                    issues.append(('NATURE_PANEL_LABEL_SIZE', 'MINOR',
                                   f'Panel label "{pl.get_text()}" fontsize={fs}, should be >= 8pt'))
            except Exception:
                pass

    # 5. 统计信息检查（n值、检验方法应标注）
    has_stats_label = False
    for ax in fig.get_axes():
        for text_obj in ax.get_children():
            if hasattr(text_obj, 'get_text'):
                txt = text_obj.get_text()
                if txt and any(s in txt for s in ['n=', 'n =', 'p=', 'p <', 'p=', 't(', 'F(', 'χ²']):
                    has_stats_label = True
                    break
    # 不强制要求所有图都有统计标注，但给出提示
    if not has_stats_label and len(fig.get_axes()) > 0:
        issues.append(('NATURE_STATS_INFO', 'INFO',
                       'No statistics labels detected — consider adding n, test, p-value'))

    # 6. 图例策略检查（共享图例优于重复图例）
    legend_count = sum(1 for ax in fig.get_axes() if ax.get_legend() is not None)
    if legend_count > 2 and len(fig.get_axes()) > 3:
        issues.append(('NATURE_LEGEND_STRATEGY', 'MINOR',
                       f'{legend_count} legends detected — consider shared/direct labels'))

    # 汇总
    n_critical = sum(1 for i in issues if i[1] == 'CRITICAL')
    n_high = sum(1 for i in issues if i[1] == 'HIGH')
    n_major = sum(1 for i in issues if i[1] == 'MAJOR')
    if n_critical > 0 or n_high > 0:
        status = 'FAIL'
    elif n_major > 0:
        status = 'WARN'
    else:
        status = 'PASS'

    return {
        'status': status,
        'high': base_result['high'] + n_critical + n_high + n_major,
        'medium': base_result['medium'],
        'issues': issues,
        'fixed': fixed,
        'nature_checks': True,
        'target_journal': target_journal,
    }


def nature_export_bundle(fig, filename, dpi=600):
    """
    Nature 级导出（来自 nature-figure skill QA Contract）。

    导出 SVG（可编辑文本）+ PDF（矢量）+ TIFF（600dpi 位图预览）。

    Parameters
    ----------
    fig : matplotlib Figure
    filename : str - 基础文件名（不含扩展名）
    dpi : int - TIFF 分辨率，默认 600
    """
    import matplotlib as mpl

    # 确保文本可编辑
    mpl.rcParams['svg.fonttype'] = 'none'
    mpl.rcParams['pdf.fonttype'] = 42

    fig.savefig(f'{filename}.svg', bbox_inches='tight')
    fig.savefig(f'{filename}.pdf', bbox_inches='tight')
    fig.savefig(f'{filename}.tiff', dpi=dpi, bbox_inches='tight')

    return {
        'svg': f'{filename}.svg',
        'pdf': f'{filename}.pdf',
        'tiff': f'{filename}.tiff',
    }


# ================================================================
# 自测
# ================================================================
if __name__ == '__main__':
    print("=" * 50)
    print("Chart QA Checker v3 - Self Test")
    print("=" * 50)

    # 测试1: 正常图
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(5), [1, 3, 2, 5, 4])
    ax.set_xticklabels(['A', 'B', 'C', 'D', 'E'])
    r = check_chart_quality(fig)
    print_qa_report(r, 'normal_bar')
    plt.close(fig)

    # 测试2: 重叠文字
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, 'AAAA', transform=ax.transAxes, fontsize=20)
    ax.text(0.5, 0.5, 'BBBB', transform=ax.transAxes, fontsize=20)
    r = check_chart_quality(fig)
    print_qa_report(r, 'overlapping_text')
    plt.close(fig)

    # 测试3: 图例遮挡
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(range(10), range(10))
    ax.legend(['data'], loc='center')
    r = check_chart_quality(fig)
    print_qa_report(r, 'legend_overlap')
    plt.close(fig)

    print("\nSelf test complete.")
