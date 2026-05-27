# -*- coding: utf-8 -*-
"""Fix 图1 (split + zone labels) and 图2 (readable text)"""
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


def add_zone_background(ax):
    """添加区域背景色和标注"""
    # R1-R12: 教学楼/实验楼 (浅蓝)
    ax.axvspan(-0.5, 11.5, alpha=0.08, color='#1565C0', zorder=0)
    # R13-R20: 食堂/宿舍区 (浅橙)
    ax.axvspan(11.5, 19.5, alpha=0.08, color='#E65100', zorder=0)
    # 分隔线
    ax.axvline(x=11.5, color='gray', linestyle=':', linewidth=1.2, alpha=0.6)
    # 顶部区域标注
    y_top = ax.get_ylim()[1]
    ax.text(5.5, y_top * 0.97, '教学楼/实验楼', ha='center', fontsize=11,
            color='#1565C0', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#1565C0', alpha=0.9))
    ax.text(15.5, y_top * 0.97, '食堂/宿舍区', ha='center', fontsize=11,
            color='#E65100', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#E65100', alpha=0.9))


# ====== CH4：断轴图（独立） ======
fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 7),
                                       gridspec_kw={'height_ratios': [1.2, 0.8], 'hspace': 0.08})

# 上区：春季高值
ax_top.bar(x - width/2, w_ch4.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax_top.bar(x + width/2, s_ch4.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax_top.set_ylim(30, 2200)
ax_top.set_ylabel('CH4 (ppm)', fontsize=13)
ax_top.set_xticks(x)
ax_top.set_xticklabels([])
ax_top.legend(fontsize=11, loc='upper right')
ax_top.grid(axis='y', alpha=0.3)
add_zone_background(ax_top)
for i in range(20):
    sv = s_ch4.values[i]
    if sv > 30:
        ax_top.text(i + width/2, sv + 25, f'{sv:.0f}', ha='center', fontsize=8,
                    color='#C62828', fontweight='bold')

# 下区：冬季低值
ax_bot.bar(x - width/2, w_ch4.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax_bot.bar(x + width/2, s_ch4.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax_bot.set_ylim(0, 10)
ax_bot.set_ylabel('CH4 (ppm)', fontsize=13)
ax_bot.set_xticks(x)
ax_bot.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=10)
ax_bot.set_xlabel('采样点', fontsize=12)
ax_bot.grid(axis='y', alpha=0.3)
add_zone_background(ax_bot)
for i in range(20):
    wv = w_ch4.values[i]
    ax_bot.text(i - width/2, wv + 0.2, f'{wv:.1f}', ha='center', fontsize=7.5, color='#1565C0')

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

fig.suptitle('CH4 排放冬春季对比（断轴显示）', fontsize=16, fontweight='bold')
fig.savefig(os.path.join(OUT, '图1a_CH4季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1a CH4 done")


# ====== N2O：正常图（独立） ======
fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(x - width/2, w_n2o.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax.bar(x + width/2, s_n2o.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax.set_ylabel('N2O (ppm)', fontsize=13)
ax.set_xlabel('采样点', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=10)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)
add_zone_background(ax)
# 标注异常值
for i in range(20):
    sv = s_n2o.values[i]
    if sv > 1:
        ax.text(i + width/2, sv + 0.15, f'{sv:.1f}', ha='center', fontsize=8,
                color='#C62828', fontweight='bold')
ax.set_title('N2O 排放冬春季对比', fontsize=16, fontweight='bold')
fig.savefig(os.path.join(OUT, '图1b_N2O季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1b N2O done")


# ====== CO2：正常图（独立） ======
fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(x - width/2, w_co2.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
ax.bar(x + width/2, s_co2.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
ax.set_ylabel('CO2 (ppm)', fontsize=13)
ax.set_xlabel('采样点', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=10)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)
add_zone_background(ax)
# 标注>2000的值
for i in range(20):
    for vals, label, offset, color in [
        (w_co2.values[:20], 'w', -width/2, '#1565C0'),
        (s_co2.values[:20], 's', width/2, '#C62828'),
    ]:
        if vals[i] > 3000:
            ax.text(i + offset, vals[i] + 100, f'{vals[i]:.0f}', ha='center',
                    fontsize=7.5, color=color, fontweight='bold')
ax.set_title('CO2 排放冬春季对比', fontsize=16, fontweight='bold')
fig.savefig(os.path.join(OUT, '图1c_CO2季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1c CO2 done")


# ====== 图2：缩小图注、加大文字 ======
fig, axes = plt.subplots(1, 2, figsize=(14, 7))

positions = [(i % 4, i // 4) for i in range(20)]

for ax, (data, season) in zip(axes, [(w_ch4, '冬季'), (s_ch4, '春季')]):
    vals = data.values[:20]
    log_vals = np.log10(vals + 1)
    sizes = 250 + log_vals * 450

    for i, (px, py) in enumerate(positions):
        color = plt.cm.YlOrRd(min(0.95, log_vals[i] / (log_vals.max() + 0.01)))
        ax.scatter(px, py, s=sizes[i], c=[color], edgecolors='#555555',
                   linewidth=1.0, zorder=3, alpha=0.85)

        # 加大字号，颜色加深
        ax.text(px, py + 0.25, f'R{i+1}', ha='center', fontsize=9,
                fontweight='bold', color='#333333')
        ax.text(px, py - 0.08, f'{vals[i]:.1f}', ha='center', fontsize=8,
                color='#444444')

    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-1.0, 5.5)
    ax.set_aspect('equal')
    ax.set_title(f'{season} CH4 空间分布', fontsize=15, fontweight='bold', pad=10)
    ax.set_xticks([])
    ax.set_yticks([])

    # 水流方向
    ax.annotate('', xy=(3.5, -0.6), xytext=(-0.3, -0.6),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2.5))
    ax.text(1.6, -0.85, '水流方向', ha='center', fontsize=11, color='blue', fontweight='bold')

    # 图注缩小
    if season == '春季':
        legend_vals = [1, 10, 100, 1000]
        legend_sizes = [250 + np.log10(v + 1) * 450 for v in legend_vals]
        for val, sz in zip(legend_vals, legend_sizes):
            ax.scatter([], [], s=sz, c='#FFCC80', edgecolors='#555', label=f'{val}')
        leg = ax.legend(title='CH4(ppm)', loc='upper left', fontsize=7, title_fontsize=8,
                        framealpha=0.9, labelspacing=0.4, handletextpad=0.3,
                        borderpad=0.5, scatteryoffsets=[0.5])

fig.suptitle('冬春季CH4排放空间分布对比', fontsize=16, fontweight='bold')
plt.subplots_adjust(wspace=0.12, top=0.92, bottom=0.05)
fig.savefig(os.path.join(OUT, '图2_CH4空间分布.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2 done")

print("All fixed!")
