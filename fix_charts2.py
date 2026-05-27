# -*- coding: utf-8 -*-
"""Fix 图1 (CH4 scale) and 图2 (label size)"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.expanduser('~/Desktop/数据分析图表')

df = pd.read_excel(r'C:\Users\Administrator\Desktop\冬春数据.xlsx', sheet_name=None)
winter = df['冬季'].copy()
spring = df['春季'].copy()

w_ch4 = pd.to_numeric(winter.iloc[:, 1], errors='coerce')
w_n2o = pd.to_numeric(winter.iloc[:, 2], errors='coerce')
w_co2 = winter.iloc[:, 3].replace('5000+', 5000).astype(float)
s_ch4 = pd.to_numeric(spring.iloc[:, 1], errors='coerce')
s_n2o = pd.to_numeric(spring.iloc[:, 2], errors='coerce')
s_co2 = pd.to_numeric(spring.iloc[:, 5], errors='coerce')

x = np.arange(20)
width = 0.35


# ====== 图1: 用断轴(broken axis)解决CH4量级差异 ======
fig = plt.figure(figsize=(14, 10))

# 使用GridSpec: CH4占2行(上方), N2O和CO2各占1行
gs = gridspec.GridSpec(4, 1, height_ratios=[1.2, 0.8, 1, 1], hspace=0.3)

# --- CH4 with broken y-axis ---
ax1_top = fig.add_subplot(gs[0])    # 高值区 (spring hotspots)
ax1_bot = fig.add_subplot(gs[1])    # 低值区 (winter + low spring)

# Top: show spring high values
ax1_top.bar(x - width/2, w_ch4.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax1_top.bar(x + width/2, s_ch4.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax1_top.set_ylim(30, 2200)  # show high spring values
ax1_top.set_ylabel('CH4 (ppm)', fontsize=12)
ax1_top.set_xticks(x)
ax1_top.set_xticklabels([])
ax1_top.legend(fontsize=10, loc='upper right')
ax1_top.set_title('CH4 (ppm) — 断轴显示', fontsize=13, fontweight='bold')
ax1_top.grid(axis='y', alpha=0.3)
# Add value labels for high points
for i in range(20):
    sv = s_ch4.values[i]
    if sv > 30:
        ax1_top.text(i + width/2, sv + 30, f'{sv:.0f}', ha='center', fontsize=7, color='#C62828')

# Bottom: show low values (winter visible)
ax1_bot.bar(x - width/2, w_ch4.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax1_bot.bar(x + width/2, s_ch4.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax1_bot.set_ylim(0, 30)  # show low winter values clearly
ax1_bot.set_ylabel('CH4 (ppm)', fontsize=12)
ax1_bot.set_xticks(x)
ax1_bot.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=8)
ax1_bot.set_xlabel('采样点', fontsize=10)
ax1_bot.grid(axis='y', alpha=0.3)

# Add value labels for winter
for i in range(20):
    wv = w_ch4.values[i]
    ax1_bot.text(i - width/2, wv + 0.5, f'{wv:.1f}', ha='center', fontsize=6.5, color='#1565C0')

# Draw broken axis marks
d = 0.012
kwargs = dict(transform=ax1_top.transAxes, color='k', clip_on=False)
ax1_top.plot((-d, +d), (-d, +d), **kwargs)
ax1_top.plot((1 - d, 1 + d), (-d, +d), **kwargs)
kwargs.update(transform=ax1_bot.transAxes)
ax1_bot.plot((-d, +d), (1 - d, 1 + d), **kwargs)
ax1_bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)
ax1_top.spines['bottom'].set_visible(False)
ax1_bot.spines['top'].set_visible(False)

# --- N2O (正常) ---
ax2 = fig.add_subplot(gs[2])
ax2.bar(x - width/2, w_n2o.values[:20], width, label='冬季', color='#1565C0', alpha=0.85)
ax2.bar(x + width/2, s_n2o.values[:20], width, label='春季', color='#C62828', alpha=0.85)
ax2.set_ylabel('N2O (ppm)', fontsize=12)
ax2.set_xticks(x)
ax2.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=8)
ax2.legend(fontsize=10)
ax2.set_title('N2O (ppm)', fontsize=13, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)

# --- CO2 (正常) ---
ax3 = fig.add_subplot(gs[3])
ax3.bar(x - width/2, w_co2.values[:20], width, label='冬季', color='#1565C0', alpha=0.85)
ax3.bar(x + width/2, s_co2.values[:20], width, label='春季', color='#C62828', alpha=0.85)
ax3.set_ylabel('CO2 (ppm)', fontsize=12)
ax3.set_xticks(x)
ax3.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=8)
ax3.set_xlabel('采样点', fontsize=10)
ax3.legend(fontsize=10)
ax3.set_title('CO2 (ppm)', fontsize=13, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

fig.suptitle('冬春季温室气体排放对比', fontsize=16, fontweight='bold', y=0.98)
fig.savefig(os.path.join(OUT, '图1_温室气体季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1 done")


# ====== 图2: 缩小标注，降低突兀感 ======
fig, axes = plt.subplots(1, 2, figsize=(14, 7))

positions = [(i % 4, i // 4) for i in range(20)]

for ax, (data, season) in zip(axes, [(w_ch4, '冬季'), (s_ch4, '春季')]):
    vals = data.values[:20]
    log_vals = np.log10(vals + 1)
    sizes = 200 + log_vals * 500  # 稍微缩小整体尺寸

    for i, (px, py) in enumerate(positions):
        color = plt.cm.YlOrRd(min(0.95, log_vals[i] / (log_vals.max() + 0.01)))
        ax.scatter(px, py, s=sizes[i], c=[color], edgecolors='#666666',
                   linewidth=0.8, zorder=3, alpha=0.8)

        # 标注缩小：字号变小，颜色变淡，不再加粗
        ax.text(px, py + 0.22, f'R{i+1}', ha='center', fontsize=7,
                color='#777777', style='italic')
        ax.text(px, py - 0.06, f'{vals[i]:.1f}', ha='center', fontsize=6,
                color='#999999')

    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.8, 5.5)
    ax.set_aspect('equal')
    ax.set_title(f'{season} CH4 空间分布', fontsize=14, fontweight='bold', pad=10)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.annotate('', xy=(3.5, -0.5), xytext=(-0.3, -0.5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(1.6, -0.7, '水流方向', ha='center', fontsize=10, color='blue')

    if season == '春季':
        for val, label in [(1, '1'), (10, '10'), (100, '100'), (1000, '1000')]:
            lv = np.log10(val + 1)
            sz = 200 + lv * 500
            ax.scatter([], [], s=sz, c='#FFCC80', edgecolors='#666', label=f'{label} ppm')
        ax.legend(title='CH4浓度', loc='upper left', fontsize=7, title_fontsize=8,
                  framealpha=0.9, labelspacing=1.0, handletextpad=0.5)

fig.suptitle('冬春季CH4排放空间分布对比', fontsize=16, fontweight='bold')
plt.subplots_adjust(wspace=0.15, top=0.92, bottom=0.05)
fig.savefig(os.path.join(OUT, '图2_CH4空间分布.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2 done")

print("All fixed!")
