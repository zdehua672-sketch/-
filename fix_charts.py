# -*- coding: utf-8 -*-
"""Fix and regenerate charts - one per figure for better quality"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
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

w_ch4 = pd.to_numeric(winter.iloc[:, 1], errors='coerce')
w_n2o = pd.to_numeric(winter.iloc[:, 2], errors='coerce')
w_co2 = winter.iloc[:, 3].replace('5000+', 5000).astype(float)
s_ch4 = pd.to_numeric(spring.iloc[:, 1], errors='coerce')
s_n2o = pd.to_numeric(spring.iloc[:, 2], errors='coerce')
s_co2 = pd.to_numeric(spring.iloc[:, 5], errors='coerce')


# ====== 图1: 温室气体季节对比（3个独立子图，加大间距） ======
fig, axes = plt.subplots(3, 1, figsize=(14, 12))
x = np.arange(20)
width = 0.35

for ax, (title, w, s, unit) in zip(axes, [
    ('CH4 (ppm)', w_ch4, s_ch4, 'ppm'),
    ('N2O (ppm)', w_n2o, s_n2o, 'ppm'),
    ('CO2 (ppm)', w_co2, s_co2, 'ppm'),
]):
    ax.bar(x - width/2, w.values[:20], width, label='冬季(1月)', color='#1565C0', alpha=0.85)
    ax.bar(x + width/2, s.values[:20], width, label='春季(4月)', color='#C62828', alpha=0.85)
    ax.set_ylabel(f'{title}', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=9)
    ax.legend(fontsize=11, loc='upper right')
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

axes[2].set_xlabel('采样点', fontsize=12)
fig.suptitle('冬春季温室气体排放对比', fontsize=16, fontweight='bold')
plt.subplots_adjust(hspace=0.35, top=0.94, bottom=0.06)
fig.savefig(os.path.join(OUT, '图1_温室气体季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1 done")


# ====== 图2: CH4空间分布（修复气泡大小，用对数尺度） ======
fig, axes = plt.subplots(1, 2, figsize=(14, 7))

positions = [(i % 4, i // 4) for i in range(20)]

for ax, (data, season) in zip(axes, [(w_ch4, '冬季'), (s_ch4, '春季')]):
    vals = data.values[:20]
    # Use log scale for bubble size to avoid overflow
    log_vals = np.log10(vals + 1)  # +1 to avoid log(0)
    sizes = 300 + log_vals * 600  # controlled range

    for i, (px, py) in enumerate(positions):
        color = plt.cm.YlOrRd(min(0.95, log_vals[i] / (log_vals.max() + 0.01)))
        ax.scatter(px, py, s=sizes[i], c=[color], edgecolors='#333333',
                   linewidth=1.2, zorder=3, alpha=0.85)
        # Label with offset to avoid overlap
        ax.text(px, py + 0.28, f'R{i+1}', ha='center', fontsize=8,
                fontweight='bold', color='#333333')
        ax.text(px, py - 0.08, f'{vals[i]:.1f}', ha='center', fontsize=7,
                color='#555555')

    ax.set_xlim(-0.7, 3.7)
    ax.set_ylim(-0.8, 5.5)
    ax.set_aspect('equal')
    ax.set_title(f'{season} CH4 空间分布', fontsize=14, fontweight='bold', pad=10)
    ax.set_xticks([])
    ax.set_yticks([])

    # Flow direction arrow at bottom
    ax.annotate('', xy=(3.5, -0.5), xytext=(-0.3, -0.5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2.5))
    ax.text(1.6, -0.7, '水流方向', ha='center', fontsize=11, color='blue', fontweight='bold')

    # Add size legend
    if season == '春季':
        for val, label in [(1, '1 ppm'), (10, '10'), (100, '100'), (1000, '1000')]:
            lv = np.log10(val + 1)
            sz = 300 + lv * 600
            ax.scatter([], [], s=sz, c='#FFCC80', edgecolors='#333', label=label)
        ax.legend(title='CH4浓度', loc='upper left', fontsize=8, title_fontsize=9,
                  framealpha=0.9, labelspacing=1.2)

fig.suptitle('冬春季CH4排放空间分布对比', fontsize=16, fontweight='bold')
plt.subplots_adjust(wspace=0.15, top=0.92, bottom=0.05)
fig.savefig(os.path.join(OUT, '图2_CH4空间分布.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2 done")


# ====== 图3: 水质参数雷达图（分开输出） ======
max_vals = {'DO': 15, 'pH': 10, 'TOC': 150, 'COD': 2000, 'TN': 150, 'NH4-N': 120}

for season_data, season_name, col_map in [
    (winter, '冬季', {11:'DO', 15:'pH', 17:'TOC', 24:'COD', 20:'TN', 22:'NH4-N'}),
    (spring, '春季', {12:'DO', 15:'pH', 16:'TOC', 23:'COD', 19:'TN', 21:'NH4-N'}),
]:
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

    labels = list(col_map.values())
    means = []
    for col_idx in col_map.keys():
        vals = pd.to_numeric(season_data.iloc[:, col_idx], errors='coerce').dropna()
        means.append(vals.mean() if len(vals) > 0 else 0)

    normed = [min(1.0, m / max_vals[l]) for m, l in zip(means, labels)]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    normed += normed[:1]
    angles += angles[:1]

    ax.plot(angles, normed, 'o-', linewidth=2.5, color='#C62828', markersize=8)
    ax.fill(angles, normed, alpha=0.2, color='#C62828')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=13, fontweight='bold')
    ax.set_title(f'{season_name}水质参数雷达图', fontsize=16, fontweight='bold', pad=25)

    # Add actual values
    for angle, label, val, n in zip(angles[:-1], labels, means, normed[:-1]):
        ax.text(angle, n + 0.13, f'{val:.1f}', ha='center', fontsize=10,
                fontweight='bold', color='#B71C1C')

    fig.savefig(os.path.join(OUT, f'图3_水质雷达图_{season_name}.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"图3 {season_name} done")


# ====== 图4: 相关性热力图（分开输出，colorbar独立） ======
for season_data, season_name, col_map in [
    (winter, '冬季', {1:'CH4', 2:'N2O', 3:'CO2', 5:'O2', 11:'DO', 15:'pH', 17:'TOC', 20:'TN', 22:'NH4', 24:'COD'}),
    (spring, '春季', {1:'CH4', 2:'N2O', 5:'CO2', 7:'O2', 12:'DO', 15:'pH', 16:'TOC', 19:'TN', 21:'NH4', 23:'COD'}),
]:
    fig, ax = plt.subplots(figsize=(9, 8))

    corr_data = {}
    for col_idx, label in col_map.items():
        vals = pd.to_numeric(season_data.iloc[:, col_idx], errors='coerce')
        if vals.dropna().shape[0] > 2:
            corr_data[label] = vals
    corr_df = pd.DataFrame(corr_data)
    corr_matrix = corr_df.corr()

    im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_yticks(range(len(corr_matrix.columns)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right', fontsize=11)
    ax.set_yticklabels(corr_matrix.columns, fontsize=11)

    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            val = corr_matrix.iloc[i, j]
            color = 'white' if abs(val) > 0.6 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=9,
                    fontweight='bold', color=color)

    # Separate colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.08)
    cbar.set_label('Pearson 相关系数 r', fontsize=12)

    ax.set_title(f'{season_name}水质参数相关性热力图', fontsize=16, fontweight='bold', pad=15)
    fig.savefig(os.path.join(OUT, f'图4_相关性热力图_{season_name}.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"图4 {season_name} done")


# ====== 图5: 季节变化倍数（单独输出） ======
fig, ax = plt.subplots(figsize=(14, 6))

ratio_ch4 = s_ch4.values[:20] / w_ch4.values[:20]
ratio_n2o = s_n2o.values[:20] / w_n2o.values[:20]

x = np.arange(20)
bars1 = ax.bar(x - 0.18, ratio_ch4, 0.35, label='CH4 春/冬比', color='#C62828', alpha=0.85)
bars2 = ax.bar(x + 0.18, ratio_n2o, 0.35, label='N2O 春/冬比', color='#1565C0', alpha=0.85)

ax.axhline(y=1, color='gray', linestyle='--', linewidth=1.5, label='比值=1（无变化）')
ax.set_xlabel('采样点', fontsize=12)
ax.set_ylabel('春季/冬季比值（对数尺度）', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels([f'R{i+1}' for i in range(20)], fontsize=10)
ax.legend(fontsize=11)
ax.set_title('各采样点温室气体春季/冬季变化倍数', fontsize=15, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
ax.set_yscale('log')

# Add value labels on CH4 bars
for bar, val in zip(bars1, ratio_ch4):
    if val > 5:
        ax.text(bar.get_x() + bar.get_width()/2, val * 1.15, f'{val:.0f}x',
                ha='center', fontsize=8, fontweight='bold', color='#C62828')

fig.savefig(os.path.join(OUT, '图5_季节变化倍数.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图5 done")


# ====== 图6: 泥水状况影响（分开输出） ======
for season_data, season_name in [(winter, '冬季'), (spring, '春季')]:
    fig, ax = plt.subplots(figsize=(9, 6))

    conditions = season_data.iloc[:, 10].values[:20]
    ch4 = pd.to_numeric(season_data.iloc[:, 1], errors='coerce').values[:20]

    cond_types = ['无水无泥', '有水无泥', '有水泥少', '无水有泥']
    cond_colors = ['#FFCC80', '#81C784', '#64B5F6', '#CE93D8']
    cond_data = {c: [] for c in cond_types}

    for i in range(20):
        if conditions[i] in cond_data:
            cond_data[conditions[i]].append(ch4[i])

    positions = []
    labels = []
    box_data = []
    box_colors = []
    for c, col in zip(cond_types, cond_colors):
        if cond_data[c]:
            positions.append(len(box_data) + 1)
            labels.append(c)
            box_data.append(cond_data[c])
            box_colors.append(col)

    bp = ax.boxplot(box_data, positions=positions, patch_artist=True, widths=0.5)
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)

    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel('CH4 浓度 (ppm)', fontsize=12)
    ax.set_title(f'{season_name}泥水状况与CH4排放的关系', fontsize=15, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    for i, (pos, d) in enumerate(zip(positions, box_data)):
        ax.scatter([pos] * len(d), d, color='black', s=30, zorder=5, alpha=0.7)

    # Add count labels
    for pos, d, label in zip(positions, box_data, labels):
        ax.text(pos, ax.get_ylim()[1] * 0.95, f'n={len(d)}', ha='center',
                fontsize=10, color='#555555')

    fig.savefig(os.path.join(OUT, f'图6_泥水状况影响_{season_name}.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"图6 {season_name} done")


print(f'\nAll fixed charts saved to: {OUT}')
