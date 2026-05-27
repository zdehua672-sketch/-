# -*- coding: utf-8 -*-
"""Final charts: separated by gas, correct pipeline order, extensible for 4 seasons"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.expanduser('~/Desktop/数据分析图表')
os.makedirs(OUT, exist_ok=True)

df = pd.read_excel(r'C:\Users\Administrator\Desktop\冬春数据.xlsx', sheet_name=None)
winter = df['冬季'].copy()
spring = df['春季'].copy()

# 提取数据
w_ch4 = pd.to_numeric(winter.iloc[:, 1], errors='coerce')
w_n2o = pd.to_numeric(winter.iloc[:, 2], errors='coerce')
w_co2 = winter.iloc[:, 3].replace('5000+', 5000).astype(float)
s_ch4 = pd.to_numeric(spring.iloc[:, 1], errors='coerce')
s_n2o = pd.to_numeric(spring.iloc[:, 2], errors='coerce')
s_co2 = pd.to_numeric(spring.iloc[:, 5], errors='coerce')

# R1-R12 重新排序: R12→R1（上游到下游）
pipe1_order = list(range(11, -1, -1))  # indices 11,10,...,0 对应 R12,R11,...,R1
# R13-R20 保持顺序
pipe2_order = list(range(12, 20))       # indices 12,...,19 对应 R13,...,R20

# 颜色方案
C_WINTER = '#1565C0'
C_SPRING = '#C62828'
C_PIPE1_BG = '#E3F2FD'
C_PIPE2_BG = '#FFF3E0'


def get_ordered(vals, order):
    """按管道顺序取值"""
    return [vals.iloc[i] if i < len(vals) else 0 for i in order]


def add_pipe_zones(ax, n1=12, n2=8):
    """添加两根管道的背景分区"""
    ax.axvspan(-0.5, n1 - 0.5, alpha=0.06, color=C_PIPE1_BG, zorder=0)
    ax.axvspan(n1 - 0.5, n1 + n2 - 0.5, alpha=0.06, color=C_PIPE2_BG, zorder=0)
    ax.axvline(x=n1 - 0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
    # 区域标签
    y_top = ax.get_ylim()[1]
    ax.text((n1 - 1) / 2, y_top * 0.95, '管道1: R12(源头) → R1(出口)', ha='center',
            fontsize=11, color='#1565C0', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#1565C0', alpha=0.9))
    ax.text(n1 + (n2 - 1) / 2, y_top * 0.95, '管道2: R13 → R20', ha='center',
            fontsize=11, color='#E65100', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#E65100', alpha=0.9))


def draw_seasonal_bars(ax, all_seasons, order, width=0.2):
    """绘制多季节柱状图（预留4季）"""
    n = len(order)
    x = np.arange(n)
    n_seasons = len(all_seasons)
    offsets = np.arange(n_seasons) * width - (n_seasons - 1) * width / 2
    colors = [C_WINTER, C_SPRING, '#2E7D32', '#7B1FA2']
    season_names = ['冬季(1月)', '春季(4月)', '夏季(7月)', '秋季(10月)']

    for j, (vals, color, name) in enumerate(zip(all_seasons, colors[:n_seasons], season_names[:n_seasons])):
        ordered = get_ordered(vals, order)
        bars = ax.bar(x + offsets[j], ordered, width * 0.9, label=name, color=color, alpha=0.85)
    return x, n


# ================================================================
# 图1a: CH4 四季对比（管道1，断轴）
# ================================================================
fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 8),
                                       gridspec_kw={'height_ratios': [1.3, 0.7], 'hspace': 0.06})

seasons_ch4 = [w_ch4, s_ch4]
x, n = draw_seasonal_bars(ax_top, seasons_ch4, pipe1_order)
draw_seasonal_bars(ax_bot, seasons_ch4, pipe1_order)

# X轴标签: R12→R1
labels_p1 = [f'R{i+1}' for i in pipe1_order]
for ax in [ax_top, ax_bot]:
    ax.set_xticks(x)
    ax.set_xticklabels(labels_p1, fontsize=10)
    add_pipe_zones(ax)

ax_top.set_ylim(10, 20)
ax_top.set_ylabel('CH4 (ppm)', fontsize=12)
ax_top.legend(fontsize=10, loc='upper right')
ax_top.set_title('CH4 管道1（R12→R1）', fontsize=13, fontweight='bold')
ax_top.grid(axis='y', alpha=0.3)

ax_bot.set_ylim(0, 5)
ax_bot.set_ylabel('CH4 (ppm)', fontsize=12)
ax_bot.set_xlabel('采样点（上游→下游）', fontsize=11)
ax_bot.grid(axis='y', alpha=0.3)

# 断轴标记
d = 0.012
for ax in [ax_top, ax_bot]:
    ax.spines['bottom' if ax == ax_top else 'top'].set_visible(False)
kwargs = dict(transform=ax_top.transAxes, color='k', clip_on=False)
ax_top.plot((-d, +d), (-d, +d), **kwargs)
ax_top.plot((1 - d, 1 + d), (-d, +d), **kwargs)
kwargs = dict(transform=ax_bot.transAxes, color='k', clip_on=False)
ax_bot.plot((-d, +d), (1 - d, 1 + d), **kwargs)
ax_bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)

fig.suptitle('CH4 排放季节对比 — 管道1（断轴）', fontsize=16, fontweight='bold')
fig.savefig(os.path.join(OUT, '图1a_CH4_管道1.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1a done")

# ================================================================
# 图1b: CH4 管道2
# ================================================================
fig, ax = plt.subplots(figsize=(10, 5))
x, n = draw_seasonal_bars(ax, seasons_ch4, pipe2_order)
labels_p2 = [f'R{i+1}' for i in pipe2_order]
ax.set_xticks(x)
ax.set_xticklabels(labels_p2, fontsize=11)
ax.set_ylabel('CH4 (ppm)', fontsize=12)
ax.set_xlabel('采样点', fontsize=11)
ax.legend(fontsize=10)
ax.set_title('CH4 排放季节对比 — 管道2（R13-R20）', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# 标注高值
ordered_w = get_ordered(w_ch4, pipe2_order)
ordered_s = get_ordered(s_ch4, pipe2_order)
for i in range(n):
    for j, (vals, offset, color) in enumerate([
        (ordered_w, -0.15, C_WINTER), (ordered_s, 0.15, C_SPRING)
    ]):
        if vals[i] > 50:
            ax.text(i + offset, vals[i] + 5, f'{vals[i]:.0f}', ha='center',
                    fontsize=8, color=color, fontweight='bold')

fig.savefig(os.path.join(OUT, '图1b_CH4_管道2.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1b done")

# ================================================================
# 图2a: N2O 管道1
# ================================================================
fig, ax = plt.subplots(figsize=(14, 5))
seasons_n2o = [w_n2o, s_n2o]
x, n = draw_seasonal_bars(ax, seasons_n2o, pipe1_order)
labels_p1 = [f'R{i+1}' for i in pipe1_order]
ax.set_xticks(x)
ax.set_xticklabels(labels_p1, fontsize=10)
add_pipe_zones(ax)
ax.set_ylabel('N2O (ppm)', fontsize=12)
ax.set_xlabel('采样点（上游→下游）', fontsize=11)
ax.legend(fontsize=10)
ax.set_title('N2O 排放季节对比 — 管道1（R12→R1）', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
fig.savefig(os.path.join(OUT, '图2a_N2O_管道1.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2a done")

# ================================================================
# 图2b: N2O 管道2
# ================================================================
fig, ax = plt.subplots(figsize=(10, 5))
x, n = draw_seasonal_bars(ax, seasons_n2o, pipe2_order)
labels_p2 = [f'R{i+1}' for i in pipe2_order]
ax.set_xticks(x)
ax.set_xticklabels(labels_p2, fontsize=11)
ax.set_ylabel('N2O (ppm)', fontsize=12)
ax.set_xlabel('采样点', fontsize=11)
ax.legend(fontsize=10)
ax.set_title('N2O 排放季节对比 — 管道2（R13-R20）', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# 标注异常值
ordered_s = get_ordered(s_n2o, pipe2_order)
for i in range(n):
    if ordered_s[i] > 1:
        ax.text(i + 0.15, ordered_s[i] + 0.1, f'{ordered_s[i]:.1f}',
                ha='center', fontsize=8, color=C_SPRING, fontweight='bold')

fig.savefig(os.path.join(OUT, '图2b_N2O_管道2.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2b done")

# ================================================================
# 图3a: CO2 管道1
# ================================================================
fig, ax = plt.subplots(figsize=(14, 5))
seasons_co2 = [w_co2, s_co2]
x, n = draw_seasonal_bars(ax, seasons_co2, pipe1_order)
labels_p1 = [f'R{i+1}' for i in pipe1_order]
ax.set_xticks(x)
ax.set_xticklabels(labels_p1, fontsize=10)
add_pipe_zones(ax)
ax.set_ylabel('CO2 (ppm)', fontsize=12)
ax.set_xlabel('采样点（上游→下游）', fontsize=11)
ax.legend(fontsize=10)
ax.set_title('CO2 排放季节对比 — 管道1（R12→R1）', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
fig.savefig(os.path.join(OUT, '图3a_CO2_管道1.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图3a done")

# ================================================================
# 图3b: CO2 管道2
# ================================================================
fig, ax = plt.subplots(figsize=(10, 5))
x, n = draw_seasonal_bars(ax, seasons_co2, pipe2_order)
labels_p2 = [f'R{i+1}' for i in pipe2_order]
ax.set_xticks(x)
ax.set_xticklabels(labels_p2, fontsize=11)
ax.set_ylabel('CO2 (ppm)', fontsize=12)
ax.set_xlabel('采样点', fontsize=11)
ax.legend(fontsize=10)
ax.set_title('CO2 排放季节对比 — 管道2（R13-R20）', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# 标注高值
ordered_s = get_ordered(s_co2, pipe2_order)
for i in range(n):
    if ordered_s[i] > 3000:
        ax.text(i + 0.15, ordered_s[i] + 100, f'{ordered_s[i]:.0f}',
                ha='center', fontsize=7.5, color=C_SPRING, fontweight='bold')

fig.savefig(os.path.join(OUT, '图3b_CO2_管道2.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图3b done")


# ================================================================
# 图4: CH4 空间管道示意图
# ================================================================
fig, axes = plt.subplots(2, 1, figsize=(16, 10))

for ax, (data, season, ax_idx) in zip(axes, [
    (w_ch4, '冬季', 0), (s_ch4, '春季', 1)
]):
    ax.set_xlim(-1, 22)
    ax.set_ylim(-2, 6)
    ax.set_aspect('equal')
    ax.axis('off')

    vals = data.values[:20]

    # --- 管道1: R12→R1 (横向) ---
    ax.text(5.5, 5.2, '管道1: 教学楼/实验楼', fontsize=13, fontweight='bold',
            ha='center', color='#1565C0')
    # 管道线条
    ax.plot([0.5, 11.5], [4, 4], color='#90A4AE', linewidth=8, solid_capstyle='round', zorder=1)
    ax.annotate('', xy=(11.5, 4), xytext=(0.5, 4),
                arrowprops=dict(arrowstyle='->', color='#607D8B', lw=2))
    ax.text(6, 3.2, '水流方向 R12→R1', ha='center', fontsize=10, color='#607D8B')

    # R12到R1的节点
    log_max = np.log10(max(vals.max(), 1) + 1)
    for i in range(12):
        r_idx = pipe1_order[i]  # 11,10,...,0
        x_pos = 0.5 + i
        val = vals[r_idx]
        sz = 80 + np.log10(val + 1) / log_max * 300
        color = plt.cm.YlOrRd(min(0.9, np.log10(val + 1) / (log_max + 0.01)))

        ax.scatter(x_pos, 4, s=sz, c=[color], edgecolors='#444', linewidth=0.8, zorder=3)
        ax.text(x_pos, 4.55, f'R{r_idx+1}', ha='center', fontsize=9, fontweight='bold', color='#333')
        ax.text(x_pos, 3.45, f'{val:.1f}', ha='center', fontsize=8, color='#555')

    # --- 管道2: R13→R20 (横向) ---
    ax.text(16, 5.2, '管道2: 食堂/宿舍区', fontsize=13, fontweight='bold',
            ha='center', color='#E65100')
    ax.plot([12.5, 19.5], [4, 4], color='#90A4AE', linewidth=8, solid_capstyle='round', zorder=1)
    ax.annotate('', xy=(19.5, 4), xytext=(12.5, 4),
                arrowprops=dict(arrowstyle='->', color='#607D8B', lw=2))

    for i in range(8):
        r_idx = pipe2_order[i]
        x_pos = 12.5 + i
        val = vals[r_idx]
        sz = 80 + np.log10(val + 1) / log_max * 300
        color = plt.cm.YlOrRd(min(0.9, np.log10(val + 1) / (log_max + 0.01)))

        ax.scatter(x_pos, 4, s=sz, c=[color], edgecolors='#444', linewidth=0.8, zorder=3)
        ax.text(x_pos, 4.55, f'R{r_idx+1}', ha='center', fontsize=9, fontweight='bold', color='#333')
        ax.text(x_pos, 3.45, f'{val:.1f}', ha='center', fontsize=8, color='#555')

    ax.text(0, 1.5, f'{season}', fontsize=16, fontweight='bold',
            color=C_WINTER if season == '冬季' else C_SPRING,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

# 图注
legend_vals = [1, 10, 100, 1000]
for val in legend_vals:
    sz = 80 + np.log10(val + 1) / (np.log10(2100) + 0.01) * 300
    axes[1].scatter([], [], s=sz, c='#FFCC80', edgecolors='#444', label=f'{val} ppm')
axes[1].legend(title='CH4浓度', loc='lower center', ncol=4, fontsize=9, title_fontsize=10,
               framealpha=0.9, bbox_to_anchor=(0.5, -0.15))

fig.suptitle('CH4 排放管道示意图', fontsize=17, fontweight='bold')
plt.subplots_adjust(hspace=0.05, top=0.92, bottom=0.08)
fig.savefig(os.path.join(OUT, '图4_CH4管道示意图.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图4 done")

print('\nAll charts done!')
