# -*- coding: utf-8 -*-
"""Fix 图2: legend + text readability"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
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
s_ch4 = pd.to_numeric(spring.iloc[:, 1], errors='coerce')

fig, axes = plt.subplots(1, 2, figsize=(14, 8))

positions = [(i % 4, i // 4) for i in range(20)]

for ax, (data, season) in zip(axes, [(w_ch4, '冬季'), (s_ch4, '春季')]):
    vals = data.values[:20]
    log_vals = np.log10(vals + 1)
    sizes = 200 + log_vals * 400

    for i, (px, py) in enumerate(positions):
        color = plt.cm.YlOrRd(min(0.95, log_vals[i] / (log_vals.max() + 0.01)))
        ax.scatter(px, py, s=sizes[i], c=[color], edgecolors='#444444',
                   linewidth=0.8, zorder=3, alpha=0.8)

        # 文字放在气泡右侧，白底衬托确保可读
        ax.text(px + 0.28, py + 0.08, f'R{i+1}', ha='left', fontsize=8.5,
                fontweight='bold', color='#222222', zorder=5)
        ax.text(px + 0.28, py - 0.15, f'{vals[i]:.1f}', ha='left', fontsize=7.5,
                color='#C62828' if season == '春季' else '#1565C0', zorder=5)

    ax.set_xlim(-0.8, 4.0)
    ax.set_ylim(-1.2, 5.5)
    ax.set_aspect('equal')
    ax.set_title(f'{season} CH4 空间分布', fontsize=15, fontweight='bold', pad=10)
    ax.set_xticks([])
    ax.set_yticks([])

    # 水流方向
    ax.annotate('', xy=(3.8, -0.8), xytext=(-0.4, -0.8),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2.5))
    ax.text(1.7, -1.05, '水流方向', ha='center', fontsize=11, color='blue', fontweight='bold')

# 底部水平图注（共享）
legend_vals = [1, 5, 50, 500]
legend_sizes = [200 + np.log10(v + 1) * 400 for v in legend_vals]
handles = []
for val, sz in zip(legend_vals, legend_sizes):
    h = mlines.Line2D([], [], color='#FFCC80', marker='o', linestyle='None',
                       markersize=np.sqrt(sz) / 2.5, markeredgecolor='#555',
                       label=f'{val} ppm')
    handles.append(h)

fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=10,
           title='CH4浓度', title_fontsize=11, framealpha=0.95,
           columnspacing=1.5, handletextpad=0.8,
           bbox_to_anchor=(0.5, 0.01))

fig.suptitle('冬春季CH4排放空间分布对比', fontsize=16, fontweight='bold')
plt.subplots_adjust(wspace=0.1, top=0.92, bottom=0.12)
fig.savefig(os.path.join(OUT, '图2_CH4空间分布.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2 done")
