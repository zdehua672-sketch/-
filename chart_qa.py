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
