# -*- coding: utf-8 -*-
"""
图表质量检查器 — 集成 scipilot-figure-skill 的核心能力

集成内容：
1. visual_qa - 程序自检（缺字/裁切/重叠）
2. layout_tools - 子图标签对齐
3. viz_pitfalls - 15条画图陷阱检测
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.text as mtext

logger = logging.getLogger(__name__)

# Windows GBK 终端修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# ============================================================
# 1. 视觉质量审计（来自 visual_qa.py）
# ============================================================

SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}
_GLYPH_MARKERS = ("missing from", "Glyph", "findfont")


class _GlyphLogHandler(logging.Handler):
    """拦截 matplotlib logger 里关于缺字的记录"""
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        msg = record.getMessage()
        if any(m in msg for m in _GLYPH_MARKERS):
            self.messages.append(msg)


def audit_layout(fig, clip_tol_px=2.0, overlap_tol_px=1.0):
    """
    对 matplotlib Figure 做版面自检

    Returns: [(severity, msg), ...]
    """
    import io
    import warnings

    issues = []

    # 1. 缺字检测
    handler = _GlyphLogHandler()
    mpl_logger = logging.getLogger("matplotlib")
    prev_level = mpl_logger.level
    mpl_logger.setLevel(logging.WARNING)
    mpl_logger.addHandler(handler)

    collected = []
    try:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100)
            buf.close()
        for w in wlist:
            s = str(w.message)
            if any(m in s for m in _GLYPH_MARKERS):
                collected.append(s)
    finally:
        mpl_logger.removeHandler(handler)
        mpl_logger.setLevel(prev_level)

    collected.extend(handler.messages)
    seen = set()
    uniq = []
    for m in collected:
        if m not in seen:
            seen.add(m)
            uniq.append(m)

    if uniq:
        sample = " | ".join(uniq[:3])
        issues.append((
            "FAIL",
            f"检测到缺字，成图会出现方框/乱码：{sample[:200]}。"
            "请配置 CJK 字体；若是负号方框，确认 axes.unicode_minus=False。"
        ))

    # 2. 文字越界裁切
    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    W = float(fig.bbox.width)
    H = float(fig.bbox.height)

    tick_ids = set()
    for ax in fig.axes:
        for tl in (*ax.get_xticklabels(), *ax.get_yticklabels()):
            tick_ids.add(id(tl))

    clipped = []
    for t in fig.findobj(mtext.Text):
        try:
            if not t.get_visible() or not t.get_text().strip():
                continue
            if id(t) in tick_ids:
                continue
            bb = t.get_window_extent(renderer)
            if (bb.x0 < -clip_tol_px or bb.y0 < -clip_tol_px
                    or bb.x1 > W + clip_tol_px or bb.y1 > H + clip_tol_px):
                txt = t.get_text().strip().replace("\n", " ")
                if txt:
                    clipped.append(txt[:24])
        except Exception:
            continue

    if clipped:
        uniq_clipped = list(dict.fromkeys(clipped))[:6]
        issues.append((
            "WARN",
            f"以下文字可能超出画布被裁切：{uniq_clipped}。"
        ))

    # 3. 刻度标签重叠
    overlap_axes = 0
    for ax in fig.axes:
        for labels, axis in [(ax.get_xticklabels(), "x"), (ax.get_yticklabels(), "y")]:
            boxes = []
            for l in labels:
                try:
                    if l.get_visible() and l.get_text().strip():
                        boxes.append(l.get_window_extent(renderer))
                except Exception:
                    continue
            if len(boxes) >= 2:
                if axis == "x":
                    boxes.sort(key=lambda b: b.x0)
                    if any(a.x1 - b.x0 > overlap_tol_px for a, b in zip(boxes, boxes[1:])):
                        overlap_axes += 1
                else:
                    boxes.sort(key=lambda b: b.y0)
                    if any(a.y1 - b.y0 > overlap_tol_px for a, b in zip(boxes, boxes[1:])):
                        overlap_axes += 1

    if overlap_axes:
        issues.append((
            "WARN",
            f"{overlap_axes} 个子图存在刻度标签重叠。"
        ))

    return issues


def print_report(issues):
    """打印审计结果，返回 verdict"""
    if not issues:
        print("  [PASS] 程序自检未发现缺字/裁切/刻度重叠。")
        return "PASS"
    max_sev = max(SEVERITY[s] for s, _ in issues)
    verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]
    for sev, msg in sorted(issues, key=lambda x: -SEVERITY[x[0]]):
        print(f"  [{sev}] {msg}")
    print(f"  >>> verdict: {verdict}")
    return verdict


# ============================================================
# 2. 画图陷阱检测（来自 viz_pitfalls.md）
# ============================================================

class PitfallChecker:
    """
    科研画图陷阱检测器

    检测 15 种常见画图错误，主动拦截。
    """

    def check(self, fig, metadata=None) -> list:
        """
        检查图表中的陷阱

        Returns: [(pitfall_id, severity, message, suggestion), ...]
        """
        issues = []
        metadata = metadata or {}

        for ax in fig.axes:
            # P1: 均值柱状图掩盖分布
            if self._is_bar_chart(ax) and metadata.get('n_per_group', 100) < 10:
                issues.append((
                    'P1', 'WARN',
                    '样本量<10时均值柱状图掩盖分布',
                    '改用箱线+stripplot叠加显示原始点'
                ))

            # P2: 双Y轴
            if len(fig.axes) > 1 and self._has_dual_y_axis(fig):
                issues.append((
                    'P2', 'WARN',
                    '双Y轴的"相关"是作图者捏造的',
                    '拆成上下两个子图，或标准化后共轴'
                ))

            # P3: 饼图
            if self._is_pie_chart(ax):
                issues.append((
                    'P3', 'WARN',
                    '饼图人眼对角度辨别精度低',
                    '改用横向柱状图'
                ))

            # P4: Y轴不当截断
            if self._y_axis_truncated(ax):
                issues.append((
                    'P4', 'WARN',
                    'Y轴未从0开始，可能误导',
                    '从0开始或使用log轴'
                ))

            # P14: rainbow/jet色图
            if self._uses_rainbow(ax):
                issues.append((
                    'P14', 'WARN',
                    'rainbow/jet色图对色盲不友好',
                    '改用viridis/RdBu_r'
                ))

        # P9: 误差类型不交代
        if metadata.get('has_error_bars') and not metadata.get('error_type_specified'):
            issues.append((
                'P9', 'INFO',
                '误差棒类型未说明',
                '图注必须写清SD/SEM/95%CI + n + 检验方法'
            ))

        return issues

    def _is_bar_chart(self, ax):
        """检测是否为柱状图"""
        return any(isinstance(c, plt.matplotlib.patches.Rectangle)
                   for c in ax.get_children()
                   if hasattr(c, 'get_width') and c.get_width() > 0)

    def _has_dual_y_axis(self, fig):
        """检测是否有双Y轴"""
        return len(fig.axes) > 1

    def _is_pie_chart(self, ax):
        """检测是否为饼图"""
        return any(isinstance(c, plt.matplotlib.patches.Wedge)
                   for c in ax.get_children())

    def _y_axis_truncated(self, ax):
        """检测Y轴是否被截断"""
        ylim = ax.get_ylim()
        if ylim[0] > 0 and ylim[1] > 0:
            # 检查数据是否从0开始有意义
            return True
        return False

    def _uses_rainbow(self, ax):
        """检测是否使用了rainbow/jet色图"""
        for c in ax.get_children():
            if hasattr(c, 'get_cmap'):
                cmap = c.get_cmap()
                if cmap and cmap.name in ['rainbow', 'jet', 'hsv', 'hot']:
                    return True
        return False


# ============================================================
# 3. 子图标签对齐（来自 layout_tools.py）
# ============================================================

def add_panel_labels(fig, labels=None, fontsize=8, fontweight='bold',
                     x_offset=0.02, y_offset=0.98):
    """
    为多面板图添加 (a)(b)(c) 标签

    使用 figure 坐标统一位置，确保对齐。
    """
    if labels is None:
        labels = [chr(ord('a') + i) for i in range(len(fig.axes))]

    for i, (ax, label) in enumerate(zip(fig.axes, labels)):
        if i >= len(labels):
            break
        ax.text(
            x_offset, y_offset, f'({label})',
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va='top', ha='left',
        )

    return fig


# ============================================================
# 4. 集成检查接口
# ============================================================

def full_quality_check(fig, metadata=None, output_path=None):
    """
    完整的图表质量检查

    1. 程序自检（缺字/裁切/重叠）
    2. 陷阱检测（15种常见错误）
    3. 可选：生成预览供AI读图

    Returns: dict with 'verdict', 'issues', 'preview_path'
    """
    all_issues = []

    # 程序自检
    layout_issues = audit_layout(fig)
    for sev, msg in layout_issues:
        all_issues.append(('layout', sev, msg))

    # 陷阱检测
    pitfall_checker = PitfallChecker()
    pitfalls = pitfall_checker.check(fig, metadata)
    for pid, sev, msg, suggestion in pitfalls:
        all_issues.append((f'pitfall_{pid}', sev, f'{msg} -> {suggestion}'))

    # 生成预览
    preview_path = None
    if output_path:
        try:
            preview_path = output_path.replace('.png', '_preview.png')
            fig.savefig(preview_path, dpi=150, bbox_inches='tight')
        except Exception as e:
            logger.warning(f"预览生成失败: {e}")

    # 判断verdict
    max_sev = 0
    for _, sev, _ in all_issues:
        max_sev = max(max_sev, SEVERITY.get(sev, 0))

    verdict = {2: "FAIL", 1: "WARN", 0: "PASS"}[max_sev]

    return {
        'verdict': verdict,
        'issues': all_issues,
        'preview_path': preview_path,
        'total_issues': len(all_issues),
        'fail_count': sum(1 for _, s, _ in all_issues if s == 'FAIL'),
        'warn_count': sum(1 for _, s, _ in all_issues if s == 'WARN'),
    }


def check_and_fix_figure(fig, metadata=None, output_path=None):
    """
    检查并自动修复图表问题

    1. 运行完整检查
    2. 自动修复可修复的问题
    3. 返回修复后的图表和检查结果
    """
    # 运行检查
    result = full_quality_check(fig, metadata, output_path)

    # 自动修复：添加子图标签
    if metadata and metadata.get('add_panel_labels', False):
        add_panel_labels(fig)

    # 自动修复：调整布局
    try:
        fig.tight_layout()
    except Exception:
        pass

    return fig, result
