# -*- coding: utf-8 -*-
"""Analyze winter-spring campus sewage data"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from scipy import stats

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.expanduser('~/Desktop/数据分析图表')
os.makedirs(OUT, exist_ok=True)

# Load data
df = pd.read_excel(r'C:\Users\Administrator\Desktop\冬春数据.xlsx', sheet_name=None)
winter = df['冬季'].copy()
spring = df['春季'].copy()

# ============================================================
# Statistical analysis
# ============================================================
print('='*60)
print('【统计分析报告】冬春校园排污井数据')
print('='*60)

# Fix column names
w_ch4 = pd.to_numeric(winter.iloc[:, 1], errors='coerce')  # 甲烷
w_n2o = pd.to_numeric(winter.iloc[:, 2], errors='coerce')  # 氧化亚氮
w_co2 = winter.iloc[:, 3].replace('5000+', 5000).astype(float)  # CO2
w_co2_bg = winter.iloc[:, 4].astype(float)  # CO2本底
w_o2 = pd.to_numeric(winter.iloc[:, 5], errors='coerce')  # O2
w_vocs = pd.to_numeric(winter.iloc[:, 7], errors='coerce')  # VOCs

s_ch4 = pd.to_numeric(spring.iloc[:, 1], errors='coerce')
s_n2o = pd.to_numeric(spring.iloc[:, 2], errors='coerce')
s_vocs = pd.to_numeric(spring.iloc[:, 3], errors='coerce')
s_co2 = pd.to_numeric(spring.iloc[:, 5], errors='coerce')
s_co2_bg = pd.to_numeric(spring.iloc[:, 6], errors='coerce')
s_o2 = pd.to_numeric(spring.iloc[:, 7], errors='coerce')

# 1. Greenhouse gases
print('\n1. 温室气体季节对比')
print('-'*40)
for name, w, s in [('CH4(ppm)', w_ch4, s_ch4), ('N2O(ppm)', w_n2o, s_n2o), ('CO2(ppm)', w_co2, s_co2)]:
    print(f'\n{name}:')
    print(f'  冬季: mean={w.mean():.2f}, median={w.median():.2f}, range=[{w.min():.1f}, {w.max():.1f}]')
    print(f'  春季: mean={s.mean():.2f}, median={s.median():.2f}, range=[{s.min():.1f}, {s.max():.1f}]')
    print(f'  春/冬比: {s.mean()/w.mean():.1f}x')

# Net emissions
w_co2_net = w_co2 - w_co2_bg
s_co2_net = s_co2 - s_co2_bg
print(f'\n净CO2排放(扣除本底):')
print(f'  冬季: mean={w_co2_net.mean():.0f} ppm')
print(f'  春季: mean={s_co2_net.mean():.0f} ppm')

# 2. Water quality (only points with water)
print('\n2. 水质参数对比')
print('-'*40)
# Winter water quality columns: DO=11, NaCl=12, conductivity=13, temp=14, pH=15, H2S=16, TOC=17, TC=18, IC=19, TN=20, TP=21, NH4=22, NO3=23, COD=24
# Spring water quality columns: temp=11, DO=12, NaCl=13, conductivity=14, pH=15, TOC=16, TC=17, IC=18, TN=19, TP=20, NH4=21, NO3=22, COD=23
wq_params = [
    ('DO(mg/L)', 11, 12), ('pH', 15, 15), ('TOC(mg/L)', 17, 16),
    ('COD(mg/L)', 24, 23), ('TN(mg/L)', 20, 19), ('NH4-N(mg/L)', 22, 21),
    ('TP(mg/L)', 21, 20), ('电导率(uS/cm)', 13, 14),
]
for name, wi, si in wq_params:
    w = pd.to_numeric(winter.iloc[:, wi], errors='coerce').dropna()
    s = pd.to_numeric(spring.iloc[:, si], errors='coerce').dropna()
    print(f'\n{name} (冬季n={len(w)}, 春季n={len(s)}):')
    if len(w) > 0:
        print(f'  冬季: mean={w.mean():.2f}, range=[{w.min():.2f}, {w.max():.2f}]')
    if len(s) > 0:
        print(f'  春季: mean={s.mean():.2f}, range=[{s.min():.2f}, {s.max():.2f}]')

# 3. Hotspots
print('\n3. 高排放热点')
print('-'*40)
print('\n春季 CH4 前5:')
for idx in s_ch4.nlargest(5).index:
    print(f'  {spring.iloc[idx, 0]}: {s_ch4[idx]:.1f} ppm')
print('\n春季 N2O 前5:')
for idx in s_n2o.nlargest(5).index:
    print(f'  {spring.iloc[idx, 0]}: {s_n2o[idx]:.2f} ppm')
print('\n春季 CO2 前5:')
for idx in s_co2.nlargest(5).index:
    print(f'  {spring.iloc[idx, 0]}: {s_co2[idx]:.0f} ppm')

# 4. Water condition
print('\n4. 泥水状况分布')
print('-'*40)
print('冬季:', dict(winter.iloc[:, 10].value_counts()))
print('春季:', dict(spring.iloc[:, 10].value_counts()))

# ============================================================
# Visualization
# ============================================================
print('\n\nGenerating charts...')

# --- Chart 1: Greenhouse gas bar comparison ---
fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))

gas_data = [
    ('CH4 (ppm)', w_ch4, s_ch4),
    ('N2O (ppm)', w_n2o, s_n2o),
    ('CO2 (ppm)', w_co2, s_co2),
]

for ax, (title, w, s) in zip(axes, gas_data):
    x = np.arange(20)
    width = 0.35
    ax.bar(x - width/2, w.values[:20], width, label='冬季', color='#1565C0', alpha=0.8)
    ax.bar(x + width/2, s.values[:20], width, label='春季', color='#C62828', alpha=0.8)
    ax.set_xlabel('采样点')
    ax.set_ylabel(title)
    ax.set_xticks(x)
    ax.set_xticklabels([f'R{i+1}' for i in range(20)], rotation=45, fontsize=7)
    ax.legend()
    ax.set_title(title, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

fig.suptitle('图1 冬季vs春季温室气体排放对比', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUT, '图1_温室气体季节对比.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图1 done")

# --- Chart 2: CH4 spatial distribution (bubble map) ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, (data, season) in zip(axes, [(w_ch4, '冬季'), (s_ch4, '春季')]):
    vals = data.values[:20]
    # Arrange in a rough spatial grid (4x5)
    positions = [(i%4, i//4) for i in range(20)]
    for i, (px, py) in enumerate(positions):
        size = max(200, min(2000, vals[i] * 50)) if season == '春季' else max(200, vals[i] * 200)
        color = plt.cm.Reds(min(1.0, vals[i] / (vals.max() + 0.01)))
        ax.scatter(px, py, s=size, c=[color], edgecolors='black', linewidth=1, zorder=3)
        ax.text(px, py+0.15, f'R{i+1}\n{vals[i]:.1f}', ha='center', fontsize=7, fontweight='bold')
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect('equal')
    ax.set_title(f'{season} CH4空间分布', fontsize=13, fontweight='bold')
    ax.set_xticks([])
    ax.set_yticks([])
    # Add arrow for flow direction
    ax.annotate('', xy=(3.5, 2.5), xytext=(-0.3, 2.5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    ax.text(1.5, -0.3, '水流方向 →', ha='center', fontsize=10, color='blue')

fig.suptitle('图2 冬春季CH4排放空间分布对比', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUT, '图2_CH4空间分布.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图2 done")

# --- Chart 3: Water quality radar chart ---
fig, axes = plt.subplots(1, 2, figsize=(12, 5), subplot_kw=dict(projection='polar'))

for ax, (season_data, season_name, col_map) in zip(axes, [
    (winter, '冬季', {11:'DO', 15:'pH', 17:'TOC', 24:'COD', 20:'TN', 22:'NH4-N'}),
    (spring, '春季', {12:'DO', 15:'pH', 16:'TOC', 23:'COD', 19:'TN', 21:'NH4-N'}),
]):
    # Get means of water quality points (normalized)
    labels = list(col_map.values())
    means = []
    for col_idx in col_map.keys():
        vals = pd.to_numeric(season_data.iloc[:, col_idx], errors='coerce').dropna()
        means.append(vals.mean() if len(vals) > 0 else 0)

    # Normalize to 0-1
    max_vals = {'DO': 15, 'pH': 10, 'TOC': 150, 'COD': 2000, 'TN': 150, 'NH4-N': 120}
    normed = [min(1.0, m / max_vals[l]) for m, l in zip(means, labels)]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    normed += normed[:1]
    angles += angles[:1]

    ax.plot(angles, normed, 'o-', linewidth=2, color='#C62828')
    ax.fill(angles, normed, alpha=0.25, color='#C62828')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(f'{season_name}水质参数', fontsize=13, fontweight='bold', pad=15)

    # Add actual values as text
    for angle, label, val in zip(angles[:-1], labels, means):
        ax.text(angle, min(1.0, val/max_vals[label])+0.12, f'{val:.1f}',
                ha='center', fontsize=8, fontweight='bold')

fig.suptitle('图3 冬春季水质参数雷达图', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUT, '图3_水质参数雷达图.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图3 done")

# --- Chart 4: Correlation heatmap ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for ax, (data, season_name, col_indices) in zip(axes, [
    (winter, '冬季', {1:'CH4', 2:'N2O', 3:'CO2', 5:'O2', 11:'DO', 15:'pH', 17:'TOC', 20:'TN', 22:'NH4', 24:'COD'}),
    (spring, '春季', {1:'CH4', 2:'N2O', 5:'CO2', 7:'O2', 12:'DO', 15:'pH', 16:'TOC', 19:'TN', 21:'NH4', 23:'COD'}),
]):
    # Build numeric dataframe
    corr_data = {}
    for col_idx, label in col_indices.items():
        vals = pd.to_numeric(data.iloc[:, col_idx], errors='coerce')
        if vals.replace('', np.nan).dropna().shape[0] > 2:
            corr_data[label] = vals
    corr_df = pd.DataFrame(corr_data)
    corr_matrix = corr_df.corr()

    im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_yticks(range(len(corr_matrix.columns)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, fontsize=8)
    ax.set_yticklabels(corr_matrix.columns, fontsize=8)

    # Add correlation values
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            val = corr_matrix.iloc[i, j]
            color = 'white' if abs(val) > 0.6 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=7, color=color)

    ax.set_title(f'{season_name}参数相关性', fontsize=13, fontweight='bold')

fig.colorbar(im, ax=axes, shrink=0.8, label='Pearson r')
fig.suptitle('图4 冬春季水质参数相关性热力图', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUT, '图4_相关性热力图.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图4 done")

# --- Chart 5: Seasonal change ratio ---
fig, ax = plt.subplots(figsize=(12, 6))

# Calculate spring/winter ratio for each point
for gas_name, w_vals, s_vals, color in [
    ('CH4', w_ch4.values[:20], s_ch4.values[:20], '#C62828'),
    ('N2O', w_n2o.values[:20], s_n2o.values[:20], '#1565C0'),
]:
    ratio = s_vals / w_vals
    ax.bar(np.arange(20) + (0.4 if gas_name == 'N2O' else 0), ratio,
           0.35, label=f'{gas_name} 春/冬比', color=color, alpha=0.8)

ax.axhline(y=1, color='gray', linestyle='--', linewidth=1.5, label='比值=1（无变化）')
ax.set_xlabel('采样点')
ax.set_ylabel('春季/冬季比值')
ax.set_xticks(np.arange(20) + 0.2)
ax.set_xticklabels([f'R{i+1}' for i in range(20)], rotation=45)
ax.legend()
ax.set_title('图5 各采样点温室气体春季/冬季变化倍数', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
ax.set_yscale('log')

plt.tight_layout()
fig.savefig(os.path.join(OUT, '图5_季节变化倍数.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图5 done")

# --- Chart 6: Water condition impact on emissions ---
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for ax, (data, ch4_col, season) in zip(axes, [
    (winter, 1, '冬季'), (spring, 1, '春季')
]):
    conditions = data.iloc[:, 10].values  # 泥水状况
    ch4 = pd.to_numeric(data.iloc[:, ch4_col], errors='coerce').values[:20]

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

    bp = ax.boxplot(box_data, positions=positions, patch_artist=True, widths=0.6)
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('CH4 (ppm)')
    ax.set_title(f'{season}泥水状况与CH4排放', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Add individual points
    for i, (pos, d) in enumerate(zip(positions, box_data)):
        ax.scatter([pos]*len(d), d, color='black', s=20, zorder=5, alpha=0.7)

fig.suptitle('图6 泥水状况对CH4排放的影响', fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(OUT, '图6_泥水状况影响.png'), dpi=300, bbox_inches='tight')
plt.close(fig)
print("图6 done")

print(f'\nAll charts saved to: {OUT}')
