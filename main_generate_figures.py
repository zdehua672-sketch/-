# -*- coding: utf-8 -*-
"""
硕士论文级科研绘图与统计分析系统 v5.0
基于"冬春数据.xlsx"
校园污水管网固-液-气多相态碳污染物赋存特征及碳平衡分析
"""

import os, sys, warnings
warnings.filterwarnings('ignore')
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram

# ============================================================================
# 全局设置
# ============================================================================
plt.rcParams.update({
    'font.family': 'Microsoft YaHei',
    'font.sans-serif': ['Microsoft YaHei'],
    'axes.unicode_minus': False,
    'mathtext.fontset': 'stix',
})

SEASON_COLORS = {'冬季': '#0072B2', '春季': '#E69F00'}
PHASE_COLORS = {'气相': '#56B4E9', '液相': '#009E73', '固相': '#D55E00'}
ZONE_COLORS = {'教学实验区': '#0072B2', '生活区': '#E69F00'}

BASE_DIR = r'C:\Users\Administrator\Desktop\硕士毕业论文'
OUTPUT_DIR = os.path.join(BASE_DIR, '论文图件_优化版')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_fig(fig, name):
    for ext in ['.png', '.pdf']:
        fp = os.path.join(OUTPUT_DIR, f'{name}{ext}')
        fig.savefig(fp, dpi=300 if ext=='.png' else 150, bbox_inches='tight', facecolor='white')
    print(f'  OK: {name}')


def sig_stars(p):
    if p <= 0.001: return '***'
    if p <= 0.01: return '**'
    if p <= 0.05: return '*'
    return 'n.s.'


def label_map(col):
    m = {
        '甲烷(ppm)': 'CH$_4$ (ppm)',
        '氧化亚氮(ppm)': 'N$_2$O (ppm)',
        'NO2（ppm）': 'NO$_2$ (ppm)',
        'CO2(ppm)': 'CO$_2$ (ppm)',
        'CO2(PPM)': 'CO$_2$ (ppm)',
        'VOCs(ppb)': 'VOCs (ppb)',
        'O2(%vol)': 'O$_2$ (%vol)',
        'TOC(mg/L)': 'TOC (mg/L)',
        'TC(mg/L)': 'TC (mg/L)',
        'IC(mg/L)': 'IC (mg/L)',
        '总氮(mg/L)': 'TN (mg/L)',
        '总磷(mg/L)': 'TP (mg/L)',
        '铵态氮(mg/L)': 'NH$_4^+$-N (mg/L)',
        '硝态氮(mg/L)': 'NO$_3^-$-N (mg/L)',
        'COD(mg/L)': 'COD (mg/L)',
        'DO(mg/L)': 'DO (mg/L)',
        'pH': 'pH',
        '液温': '水温 (℃)',
        '电导率(uS/cm)': '电导率 (μS/cm)',
        '电导率(us/cm)': '电导率 (μS/cm)',
        '气温℃': '气温 (℃)',
        'NaCl(mg/L)': 'NaCl (mg/L)',
        'H2S': 'H$_2$S (ppm)',
        '有机碳(g/kg)': '有机碳 (g/kg)',
        'DOC(mg/kg)': 'DOC (mg/kg)',
        '全磷(g/kg)': '全磷 (g/kg)',
        '无机碳(g/kg)': '无机碳 (g/kg)',
        '固总碳(g/kg)': '固总碳 (g/kg)',
    }
    return m.get(col, col)


# ============================================================================
# 数据加载
# ============================================================================
def load_data():
    print('='*60)
    print('加载冬春数据.xlsx...')
    print('='*60)
    
    fp = os.path.join(BASE_DIR, '冬春数据.xlsx')
    
    # 冬季
    w = pd.read_excel(fp, sheet_name='冬季')
    w = w.dropna(subset=[w.columns[0]])
    w = w[w.iloc[:,0] != w.columns[0]]
    w = w.rename(columns={w.columns[0]: '采样点'})
    w['季节'] = '冬季'
    
    # 春季
    s = pd.read_excel(fp, sheet_name='春季')
    s = s.dropna(subset=[s.columns[0]])
    s = s[s.iloc[:,0] != s.columns[0]]
    s = s.rename(columns={s.columns[0]: '采样点'})
    s['季节'] = '春季'
    
    # 统一列名映射
    rename_dict = {
        '甲烷(ppm)': '甲烷(ppm)',
        '氧化亚氮(ppm)': '氧化亚氮(ppm)',
        'NO2（ppm）': 'NO2（ppm）',
        'CO2(ppm)': 'CO2(ppm)',
        'CO2(PPM)': 'CO2(ppm)',
        'VOCs(ppb)': 'VOCs(ppb)',
        'O2(%vol)': 'O2(%vol)',
        '气温/℃': '气温℃',
        '气温℃': '气温℃',
        '电导率(uS/cm)': '电导率(uS/cm)',
        '电导率(us/cm)': '电导率(uS/cm)',
        'TOC（mg/L)': 'TOC(mg/L)',
        'TOC(mg/L)': 'TOC(mg/L)',
        'TC(mg/L)': 'TC(mg/L)',
        'IC(mg/L)': 'IC(mg/L)',
        '总氮（mg/L)': '总氮(mg/L)',
        '总氮(mg/L)': '总氮(mg/L)',
        '总磷（mg/L)': '总磷(mg/L)',
        '总磷(mg/L)': '总磷(mg/L)',
        '铵态氮（mg/L)': '铵态氮(mg/L)',
        '铵态氮(mg/L)': '铵态氮(mg/L)',
        '硝态氮（mg/L)': '硝态氮(mg/L)',
        '硝态氮(mg/L)': '硝态氮(mg/L)',
        'COD（mg/L)': 'COD(mg/L)',
        'COD(mg/L)': 'COD(mg/L)',
        'NaCl(mg/L)': 'NaCl(mg/L)',
        'DO(mg/L)': 'DO(mg/L)',
        '液温': '液温',
        'pH': 'pH',
        'H2S': 'H2S',
        '泥水状况': '泥水状况',
        '采样时间': '采样时间',
        '采样时段': '采样时段',
        '有机碳（g/kg)': '有机碳(g/kg)',
        '有机碳(g/kg)': '有机碳(g/kg)',
        'DOC(mg/kg)': 'DOC(mg/kg)',
        '全磷（g/kg)': '全磷(g/kg)',
        '全磷(g/kg)': '全磷(g/kg)',
        '无机碳（g/kg)': '无机碳(g/kg)',
        '无机碳(g/kg)': '无机碳(g/kg)',
        '固总碳（g/kg)': '固总碳(g/kg)',
        '固总碳(g/kg)': '固总碳(g/kg)',
        '氨氮（铵态氮mg/kg）': '固相铵态氮(mg/kg)',
        '硝氮（硝态氮mg/kg）': '固相硝态氮(mg/kg)',
        '（固）铵态氮（mg/kg）': '固相铵态氮(mg/kg)',
        '（固）硝态氮（mg/kg）': '固相硝态氮(mg/kg)',
    }
    
    for df in [w, s]:
        df.columns = [str(c).strip() for c in df.columns]
        rename = {k: v for k, v in rename_dict.items() if k in df.columns}
        df.rename(columns=rename, inplace=True)
    
    # 转数值
    for df in [w, s]:
        for c in df.columns:
            if c not in ['采样点', '季节', '泥水状况', '采样时间', '采样时段']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
    
    # 合并
    df_all = pd.concat([w, s], ignore_index=True)
    
    # 功能区划分：R1-R12教学实验区，R13-R20生活区
    def get_zone(x):
        x = str(x).upper().strip()
        # 提取数字部分（处理"R14(生活)"等格式）
        import re
        nums = re.findall(r'\d+', x)
        if nums:
            n = int(nums[0])
            return '教学实验区' if n <= 12 else '生活区'
        return '生活区'
    
    df_all['功能区'] = df_all['采样点'].apply(get_zone)
    
    # 计算气相碳
    if '甲烷(ppm)' in df_all.columns and 'CO2(ppm)' in df_all.columns:
        df_all['气相碳'] = df_all['甲烷(ppm)'].fillna(0) + df_all['CO2(ppm)'].fillna(0)
    if 'TOC(mg/L)' in df_all.columns:
        df_all['液相碳'] = df_all['TOC(mg/L)']
    
    print(f'  冬季: {len(w)} 行, 春季: {len(s)} 行')
    print(f'  合并: {len(df_all)} 行 x {len(df_all.columns)} 列')
    print(f'  列: {list(df_all.columns)}')
    
    return df_all


# ============================================================================
# 图1: 三相碳组成饼图（修复数值重叠）
# ============================================================================
def fig1_pie(df):
    print('\n[图1] 三相碳组成饼图...')
    has_gas = '气相碳' in df.columns and df['气相碳'].notna().sum() > 0
    has_liq = '液相碳' in df.columns and df['液相碳'].notna().sum() > 0
    has_solid = '有机碳(g/kg)' in df.columns and df['有机碳(g/kg)'].notna().sum() > 0
    
    if not (has_gas or has_liq or has_solid):
        print('  SKIP: 数据不足')
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
    
    for idx, season in enumerate(['冬季', '春季']):
        ax = axes[idx]
        sd = df[df['季节'] == season]
        
        vals = {}
        if has_gas:
            v = sd['气相碳'].mean()
            if not np.isnan(v): vals['气相'] = v
        if has_liq:
            v = sd['液相碳'].mean()
            if not np.isnan(v): vals['液相'] = v
        if has_solid:
            v = sd['有机碳(g/kg)'].mean()
            if not np.isnan(v): vals['固相'] = v
        
        if len(vals) < 2:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center', fontsize=14)
            ax.set_title(season, fontsize=14, fontweight='bold')
            continue
        
        labels = list(vals.keys())
        sizes = list(vals.values())
        colors = [PHASE_COLORS.get(l, '#999') for l in labels]
        
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors,
            autopct='%1.1f%%', pctdistance=0.6,
            startangle=90, explode=[0.03]*len(labels),
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'fontsize': 12})
        for t in texts:
            t.set_fontsize(13); t.set_fontweight('bold')
        for t in autotexts:
            t.set_fontsize(12); t.set_fontweight('bold'); t.set_color('white')
        
        ax.set_title(season, fontsize=16, fontweight='bold', pad=15)
        ax.axis('equal')
        
        leg_labels = [f'{l}: {v:.2f}' for l, v in zip(labels, sizes)]
        ax.legend(wedges, leg_labels, title='相态(均值)',
                 loc='center left', bbox_to_anchor=(1.05, 0.5),
                 frameon=True, edgecolor='#CCC', fontsize=11)
    
    fig.suptitle('固-液-气三相碳组成', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图1_三相碳组成饼图')
    plt.close()


# ============================================================================
# 图2: 气体浓度箱线图（修复春季氧化亚氮→NO2）
# ============================================================================
def fig2_gas_box(df):
    print('\n[图2] 气体浓度箱线图...')
    # 冬季气体
    w = df[df['季节']=='冬季']
    s = df[df['季节']=='春季']
    
    # 分别处理两季不同的气体指标
    fig, axes = plt.subplots(1, 4, figsize=(22, 5.5), facecolor='white')
    
    # CH4 - 两季都有
    ax = axes[0]
    for season, color in [('冬季', SEASON_COLORS['冬季']), ('春季', SEASON_COLORS['春季'])]:
        d = df[df['季节']==season]['甲烷(ppm)'].dropna()
        if len(d) > 0:
            bp = ax.boxplot([d], positions=[1 if season=='冬季' else 2],
                          patch_artist=True, widths=0.45,
                          medianprops={'color':'black','linewidth':1.5},
                          boxprops={'facecolor':color,'alpha':0.7,'linewidth':1.2},
                          flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
            jit = np.random.normal(1 if season=='冬季' else 2, 0.05, len(d))
            ax.scatter(jit, d, alpha=0.6, s=35, color=color, edgecolors='white', linewidth=0.5, zorder=5)
    ax.set_xticks([1, 2]); ax.set_xticklabels(['冬季', '春季'], fontsize=12)
    ax.set_ylabel('CH$_4$ (ppm)', fontsize=12)
    ax.set_title('CH$_4$', fontsize=14, fontweight='bold')
    wd = df[df['季节']=='冬季']['甲烷(ppm)'].dropna()
    sd = df[df['季节']=='春季']['甲烷(ppm)'].dropna()
    if len(wd)>1 and len(sd)>1:
        _, p = stats.mannwhitneyu(wd, sd, alternative='two-sided')
        ymax = max(max(wd), max(sd)); ymin = min(min(wd), min(sd))
        yr = ymax - ymin if ymax != ymin else ymax*0.2
        yp = ymax + yr*0.1
        ax.plot([1,1,2,2], [yp, yp+yr*0.04, yp+yr*0.04, yp], color='black', lw=1.2)
        ax.text(1.5, yp+yr*0.06, sig_stars(p), ha='center', va='bottom', fontsize=13, fontweight='bold')
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
    
    # N2O (冬季) vs NO2 (春季)
    ax = axes[1]
    w_n2o = df[df['季节']=='冬季']['氧化亚氮(ppm)'].dropna() if '氧化亚氮(ppm)' in df.columns else pd.Series()
    s_no2 = df[df['季节']=='春季']['NO2（ppm）'].dropna() if 'NO2（ppm）' in df.columns else pd.Series()
    
    if len(w_n2o) > 0:
        bp = ax.boxplot([w_n2o], positions=[1], patch_artist=True, widths=0.45,
                       medianprops={'color':'black','linewidth':1.5},
                       boxprops={'facecolor':SEASON_COLORS['冬季'],'alpha':0.7,'linewidth':1.2},
                       flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
        jit = np.random.normal(1, 0.05, len(w_n2o))
        ax.scatter(jit, w_n2o, alpha=0.6, s=35, color=SEASON_COLORS['冬季'], edgecolors='white', linewidth=0.5, zorder=5)
    if len(s_no2) > 0:
        bp = ax.boxplot([s_no2], positions=[2], patch_artist=True, widths=0.45,
                       medianprops={'color':'black','linewidth':1.5},
                       boxprops={'facecolor':SEASON_COLORS['春季'],'alpha':0.7,'linewidth':1.2},
                       flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
        jit = np.random.normal(2, 0.05, len(s_no2))
        ax.scatter(jit, s_no2, alpha=0.6, s=35, color=SEASON_COLORS['春季'], edgecolors='white', linewidth=0.5, zorder=5)
    ax.set_xticks([1, 2]); ax.set_xticklabels(['冬季(N$_2$O)', '春季(NO$_2$)'], fontsize=11)
    ax.set_ylabel('浓度 (ppm)', fontsize=12)
    ax.set_title('N$_2$O / NO$_2$', fontsize=14, fontweight='bold')
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
    
    # CO2 - 两季都有
    ax = axes[2]
    for season, color in [('冬季', SEASON_COLORS['冬季']), ('春季', SEASON_COLORS['春季'])]:
        d = df[df['季节']==season]['CO2(ppm)'].dropna()
        if len(d) > 0:
            bp = ax.boxplot([d], positions=[1 if season=='冬季' else 2],
                          patch_artist=True, widths=0.45,
                          medianprops={'color':'black','linewidth':1.5},
                          boxprops={'facecolor':color,'alpha':0.7,'linewidth':1.2},
                          flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
            jit = np.random.normal(1 if season=='冬季' else 2, 0.05, len(d))
            ax.scatter(jit, d, alpha=0.6, s=35, color=color, edgecolors='white', linewidth=0.5, zorder=5)
    ax.set_xticks([1, 2]); ax.set_xticklabels(['冬季', '春季'], fontsize=12)
    ax.set_ylabel('CO$_2$ (ppm)', fontsize=12)
    ax.set_title('CO$_2$', fontsize=14, fontweight='bold')
    wd = df[df['季节']=='冬季']['CO2(ppm)'].dropna()
    sd = df[df['季节']=='春季']['CO2(ppm)'].dropna()
    if len(wd)>1 and len(sd)>1:
        _, p = stats.mannwhitneyu(wd, sd, alternative='two-sided')
        ymax = max(max(wd), max(sd)); ymin = min(min(wd), min(sd))
        yr = ymax - ymin if ymax != ymin else ymax*0.2
        yp = ymax + yr*0.1
        ax.plot([1,1,2,2], [yp, yp+yr*0.04, yp+yr*0.04, yp], color='black', lw=1.2)
        ax.text(1.5, yp+yr*0.06, sig_stars(p), ha='center', va='bottom', fontsize=13, fontweight='bold')
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
    
    # VOCs - 两季都有
    ax = axes[3]
    for season, color in [('冬季', SEASON_COLORS['冬季']), ('春季', SEASON_COLORS['春季'])]:
        d = df[df['季节']==season]['VOCs(ppb)'].dropna()
        if len(d) > 0:
            bp = ax.boxplot([d], positions=[1 if season=='冬季' else 2],
                          patch_artist=True, widths=0.45,
                          medianprops={'color':'black','linewidth':1.5},
                          boxprops={'facecolor':color,'alpha':0.7,'linewidth':1.2},
                          flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
            jit = np.random.normal(1 if season=='冬季' else 2, 0.05, len(d))
            ax.scatter(jit, d, alpha=0.6, s=35, color=color, edgecolors='white', linewidth=0.5, zorder=5)
    ax.set_xticks([1, 2]); ax.set_xticklabels(['冬季', '春季'], fontsize=12)
    ax.set_ylabel('VOCs (ppb)', fontsize=12)
    ax.set_title('VOCs', fontsize=14, fontweight='bold')
    wd = df[df['季节']=='冬季']['VOCs(ppb)'].dropna()
    sd = df[df['季节']=='春季']['VOCs(ppb)'].dropna()
    if len(wd)>1 and len(sd)>1:
        _, p = stats.mannwhitneyu(wd, sd, alternative='two-sided')
        ymax = max(max(wd), max(sd)); ymin = min(min(wd), min(sd))
        yr = ymax - ymin if ymax != ymin else ymax*0.2
        yp = ymax + yr*0.1
        ax.plot([1,1,2,2], [yp, yp+yr*0.04, yp+yr*0.04, yp], color='black', lw=1.2)
        ax.text(1.5, yp+yr*0.06, sig_stars(p), ha='center', va='bottom', fontsize=13, fontweight='bold')
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
    
    fig.suptitle('冬春季气体浓度对比', fontsize=18, fontweight='bold', y=1.03)
    plt.tight_layout()
    save_fig(fig, '图2_气体浓度箱线图')
    plt.close()


# ============================================================================
# 图2b: 气体浓度分组柱状图（教学实验区 vs 生活区）
# ============================================================================
def fig2b_gas_bar(df):
    print('\n[图2b] 气体浓度分组柱状图（功能区对比）...')
    gases = ['甲烷(ppm)', 'CO2(ppm)', 'VOCs(ppb)']
    gases = [c for c in gases if c in df.columns]
    if not gases: print('  SKIP'); return
    
    n = len(gases)
    fig, axes = plt.subplots(1, n, figsize=(7*n, 5.5), facecolor='white')
    if n == 1: axes = [axes]
    
    for i, gas in enumerate(gases):
        ax = axes[i]
        x = np.arange(4)
        width = 0.35
        
        means, errs, lbls = [], [], []
        for season in ['冬季', '春季']:
            for zone in ['教学实验区', '生活区']:
                d = df[(df['季节']==season) & (df['功能区']==zone)][gas].dropna()
                if len(d) > 0:
                    means.append(d.mean())
                    errs.append(d.std()/np.sqrt(len(d)))
                    lbls.append(f'{season}\n{zone}')
                else:
                    means.append(0); errs.append(0); lbls.append(f'{season}\n{zone}')
        
        colors = ['#0072B2', '#0072B2', '#E69F00', '#E69F00']
        alphas = [0.5, 1.0, 0.5, 1.0]
        for j, (m, e, c, a) in enumerate(zip(means, errs, colors, alphas)):
            ax.bar(j, m, width, yerr=e, color=c, alpha=a, capsize=4,
                  edgecolor='white', linewidth=0.5, error_kw={'linewidth':1.2})
        
        ax.set_xticks(range(4))
        ax.set_xticklabels(['冬季\n教学实验区', '冬季\n生活区', '春季\n教学实验区', '春季\n生活区'], fontsize=10)
        ax.set_ylabel(label_map(gas), fontsize=12)
        ax.set_title(label_map(gas), fontsize=14, fontweight='bold')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
        
        # 显著性标注
        for season in ['冬季', '春季']:
            idx1 = 0 if season == '冬季' else 2
            idx2 = 1 if season == '冬季' else 3
            if means[idx1] > 0 and means[idx2] > 0:
                d1 = df[(df['季节']==season) & (df['功能区']=='教学实验区')][gas].dropna()
                d2 = df[(df['季节']==season) & (df['功能区']=='生活区')][gas].dropna()
                if len(d1)>1 and len(d2)>1:
                    _, p = stats.mannwhitneyu(d1, d2, alternative='two-sided')
                    ymax = max(means[idx1]+errs[idx1], means[idx2]+errs[idx2])
                    yr = ymax*0.1 if ymax > 0 else 1
                    yp = ymax + yr
                    ax.plot([idx1, idx1, idx2, idx2], [yp, yp+yr*0.3, yp+yr*0.3, yp], color='black', lw=1.2)
                    ax.text((idx1+idx2)/2, yp+yr*0.4, sig_stars(p), ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    fig.suptitle('不同功能区气体浓度对比', fontsize=18, fontweight='bold', y=1.03)
    plt.tight_layout()
    save_fig(fig, '图2b_气体浓度功能区柱状图')
    plt.close()


# ============================================================================
# 图3: 液相箱线图
# ============================================================================
def fig3_liquid_box(df):
    print('\n[图3] 液相指标箱线图...')
    vars = ['TOC(mg/L)', '总氮(mg/L)', '总磷(mg/L)', '铵态氮(mg/L)', '硝态氮(mg/L)',
            'COD(mg/L)', 'DO(mg/L)', 'pH', '液温', '电导率(uS/cm)']
    vars = [c for c in vars if c in df.columns]
    if not vars: print('  SKIP'); return
    
    n = len(vars); nc = min(4, n); nr = (n + nc - 1)//nc
    fig, axes = plt.subplots(nr, nc, figsize=(5*nc, 4.5*nr), facecolor='white')
    axes = axes.flatten()
    
    for i, var in enumerate(vars):
        ax = axes[i]
        d = pd.to_numeric(df[var], errors='coerce')
        wd = d[df['季节']=='冬季'].dropna()
        sd = d[df['季节']=='春季'].dropna()
        
        dl, lbls, cols = [], [], []
        for dd, ss, cc in [(wd,'冬季',SEASON_COLORS['冬季']),(sd,'春季',SEASON_COLORS['春季'])]:
            if len(dd) > 0: dl.append(dd); lbls.append(ss); cols.append(cc)
        
        if dl:
            bp = ax.boxplot(dl, patch_artist=True, widths=0.45,
                           medianprops={'color':'black','linewidth':1.5},
                           flierprops={'marker':'o','markerfacecolor':'#666','markersize':4,'alpha':0.4},
                           boxprops={'linewidth':1.2}, whiskerprops={'linewidth':1.2}, capprops={'linewidth':1.2})
            for p, c in zip(bp['boxes'], cols): p.set_facecolor(c); p.set_alpha(0.7)
            for j, (dd_, c) in enumerate(zip(dl, cols)):
                if len(dd_) > 0:
                    jit = np.random.normal(j+1, 0.05, len(dd_))
                    ax.scatter(jit, dd_, alpha=0.5, s=25, color=c, edgecolors='white', linewidth=0.5, zorder=5)
            ax.set_xticklabels(lbls, fontsize=11)
            
            if len(dl)==2 and len(dl[0])>1 and len(dl[1])>1:
                _, p = stats.mannwhitneyu(dl[0], dl[1], alternative='two-sided')
                ymax = max(max(d) for d in dl); ymin = min(min(d) for d in dl)
                yr = ymax - ymin if ymax != ymin else ymax*0.2
                yp = ymax + yr*0.1
                ax.plot([1,1,2,2], [yp, yp+yr*0.04, yp+yr*0.04, yp], color='black', lw=1.2)
                ax.text(1.5, yp+yr*0.06, sig_stars(p), ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        ax.set_ylabel(label_map(var), fontsize=11)
        ax.set_title(label_map(var), fontsize=12, fontweight='bold')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(axis='y', alpha=0.25, linestyle='--'); ax.set_axisbelow(True)
    
    for i in range(n, len(axes)): axes[i].set_visible(False)
    fig.suptitle('冬春季液相指标对比', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图3_液相指标箱线图')
    plt.close()


# ============================================================================
# 图4: 相关性热图
# ============================================================================
def fig4_corr(df):
    print('\n[图4] 相关性热图...')
    cols = ['甲烷(ppm)', '氧化亚氮(ppm)', 'CO2(ppm)', 'VOCs(ppb)',
            'TOC(mg/L)', 'DO(mg/L)', 'pH', '液温', '电导率(uS/cm)',
            '总氮(mg/L)', '铵态氮(mg/L)', '硝态氮(mg/L)']
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 4: print('  SKIP'); return
    
    corr = df[cols].apply(pd.to_numeric, errors='coerce').corr(method='spearman')
    lbls = [label_map(c) for c in corr.columns]
    
    fig, ax = plt.subplots(figsize=(11, 9), facecolor='white')
    im = ax.imshow(corr.values, cmap=plt.cm.RdBu_r, vmin=-1, vmax=1, aspect='auto')
    
    for i in range(len(corr)):
        for j in range(len(corr)):
            if i >= j:
                v = corr.values[i,j]
                ax.text(j, i, f'{v:.2f}', ha='center', va='center',
                       fontsize=8, color='white' if abs(v)>0.5 else 'black', fontweight='bold')
    
    ax.set_xticks(range(len(lbls))); ax.set_yticks(range(len(lbls)))
    ax.set_xticklabels(lbls, rotation=45, ha='right', fontsize=9)
    ax.set_yticklabels(lbls, fontsize=9)
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label('Spearman r', fontsize=11)
    ax.set_title('多参数相关性热图', fontsize=18, fontweight='bold', pad=15)
    plt.tight_layout()
    save_fig(fig, '图4_相关性热图')
    plt.close()


# ============================================================================
# 图5: PCA
# ============================================================================
def fig5_pca(df):
    print('\n[图5] PCA双标图...')
    cols = ['甲烷(ppm)', '氧化亚氮(ppm)', 'CO2(ppm)', 'VOCs(ppb)',
            'DO(mg/L)', 'pH', '液温', '电导率(uS/cm)']
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 4: print('  SKIP'); return
    
    pdf = df[cols].dropna()
    if len(pdf) < 5: print('  SKIP: 样本不足'); return
    
    X = pdf.values
    Xc = X - X.mean(axis=0)
    cov = np.cov(Xc.T)
    ev, evec = np.linalg.eigh(cov)
    idx = np.argsort(ev)[::-1]
    ev, evec = ev[idx], evec[:, idx]
    
    comp = evec[:, :2]
    expl = ev[:2] / ev.sum()
    scores = Xc @ comp
    load = comp * np.sqrt(ev[:2])
    
    fig, ax = plt.subplots(figsize=(9, 8), facecolor='white')
    seasons = df.loc[pdf.index, '季节'].values
    for s in ['冬季', '春季']:
        m = seasons == s
        if m.sum() > 0:
            ax.scatter(scores[m,0], scores[m,1], c=[SEASON_COLORS[s]], label=s,
                      s=90, alpha=0.7, edgecolors='#333', linewidth=0.5, zorder=5)
    
    for i, col in enumerate(cols):
        sc = 3
        ax.arrow(0, 0, load[i,0]*sc, load[i,1]*sc, head_width=0.08, head_length=0.08,
                fc='#D55E00', ec='#D55E00', alpha=0.7)
        ax.text(load[i,0]*sc*1.15, load[i,1]*sc*1.15, label_map(col),
               fontsize=9, ha='center', va='center', color='#D55E00', fontweight='bold')
    
    ax.add_patch(plt.Circle((0,0), 3, fill=False, color='#999', linestyle='--', lw=0.8, alpha=0.4))
    ax.axhline(0, color='#999', lw=0.5, alpha=0.3)
    ax.axvline(0, color='#999', lw=0.5, alpha=0.3)
    ax.set_xlabel(f'PC1 ({expl[0]*100:.1f}%)', fontsize=13)
    ax.set_ylabel(f'PC2 ({expl[1]*100:.1f}%)', fontsize=13)
    ax.set_title('PCA双标图', fontsize=18, fontweight='bold', pad=15)
    ax.legend(fontsize=12, frameon=True, edgecolor='#CCC')
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(alpha=0.25, linestyle='--')
    ax.set_axisbelow(True)
    plt.tight_layout()
    save_fig(fig, '图5_PCA双标图')
    plt.close()


# ============================================================================
# 图6: HCA
# ============================================================================
def fig6_hca(df):
    print('\n[图6] 层次聚类树状图...')
    cols = ['甲烷(ppm)', '氧化亚氮(ppm)', 'CO2(ppm)', 'VOCs(ppb)',
            'DO(mg/L)', 'pH', '液温', '电导率(uS/cm)']
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 4: print('  SKIP'); return
    
    hdf = df[cols].dropna()
    if len(hdf) < 5: print('  SKIP: 样本不足'); return
    
    X = (hdf.values - hdf.values.mean(axis=0)) / hdf.values.std(axis=0)
    linked = linkage(X, method='ward')
    
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    seasons = df.loc[hdf.index, '季节'].values
    lc = [SEASON_COLORS.get(s, '#999') for s in seasons]
    
    dn = dendrogram(linked, ax=ax, leaf_rotation=90, leaf_font_size=10,
                   labels=[f'R{i+1}' for i in range(len(hdf))],
                   color_threshold=0.7*max(linked[:,2]),
                   above_threshold_color='#999')
    
    for idx, lbl in enumerate(ax.get_xticklabels()):
        if idx < len(lc): lbl.set_color(lc[idx])
    
    ax.set_title('层次聚类分析 (Ward法)', fontsize=18, fontweight='bold', pad=15)
    ax.set_xlabel('样本', fontsize=13); ax.set_ylabel('欧氏距离', fontsize=13)
    for sp in ax.spines.values(): sp.set_linewidth(1.2)
    ax.grid(axis='y', alpha=0.25, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor=SEASON_COLORS['冬季'], alpha=0.7, label='冬季'),
                      Patch(facecolor=SEASON_COLORS['春季'], alpha=0.7, label='春季')],
             fontsize=11, frameon=True, edgecolor='#CCC')
    plt.tight_layout()
    save_fig(fig, '图6_HCA聚类图')
    plt.close()


# ============================================================================
# 图7: 回归分析
# ============================================================================
def fig7_reg(df):
    print('\n[图7] 回归分析...')
    regs = [('DO(mg/L)', '甲烷(ppm)', 'DO 与 CH$_4$ 的关系', '图7a_DO_CH4回归'),
            ('TOC(mg/L)', 'CO2(ppm)', 'TOC 与 CO$_2$ 的关系', '图7b_TOC_CO2回归'),
            ('总氮(mg/L)', 'TOC(mg/L)', 'TN 与 TOC 的关系', '图7c_TN_TOC回归')]
    
    for xc, yc, title, fn in regs:
        if xc not in df.columns or yc not in df.columns:
            print(f'  SKIP: {fn}'); continue
        
        xd = pd.to_numeric(df[xc], errors='coerce').dropna()
        yd = pd.to_numeric(df[yc], errors='coerce').dropna()
        common = xd.index.intersection(yd.index)
        x, y = xd[common].values, yd[common].values
        if len(x) < 5: print(f'  SKIP: {fn} 样本不足'); continue
        
        slope, inter, rv, pv, _ = stats.linregress(x, y)
        r2 = rv**2
        
        fig, ax = plt.subplots(figsize=(7, 6), facecolor='white')
        seasons = df.loc[common, '季节'].values
        for s in ['冬季', '春季']:
            m = seasons == s
            if m.sum() > 0:
                ax.scatter(x[m], y[m], c=[SEASON_COLORS[s]], label=s,
                          s=80, alpha=0.7, edgecolors='#333', linewidth=0.5, zorder=5)
        
        xs = np.sort(x)
        yp = slope*xs + inter
        ax.plot(xs, yp, color='#D55E00', lw=2.5, zorder=4)
        
        n = len(x)
        ypa = slope*x + inter
        res = y - ypa
        mse = np.sum(res**2)/(n-2)
        se = np.sqrt(mse*(1/n + (xs-x.mean())**2/np.sum((x-x.mean())**2)))
        ci = 1.96*se
        ax.fill_between(xs, yp-ci, yp+ci, alpha=0.15, color='#D55E00')
        
        txt = f'y = {slope:.3f}x + {inter:.2f}\nR² = {r2:.3f}\nr = {rv:.3f}\np = {pv:.2e}\n{sig_stars(pv)}'
        ax.text(0.05, 0.95, txt, transform=ax.transAxes, fontsize=11,
               verticalalignment='top',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#BBB', alpha=0.9))
        
        ax.set_xlabel(label_map(xc), fontsize=12)
        ax.set_ylabel(label_map(yc), fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11, frameon=True, edgecolor='#CCC')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_fig(fig, fn)
        plt.close()


# ============================================================================
# 图8: 堆叠柱状图
# ============================================================================
def fig8_stacked(df):
    print('\n[图8] 堆叠柱状图...')
    has_gas = '气相碳' in df.columns and df['气相碳'].notna().sum() > 0
    has_liq = '液相碳' in df.columns and df['液相碳'].notna().sum() > 0
    has_solid = '有机碳(g/kg)' in df.columns and df['有机碳(g/kg)'].notna().sum() > 0
    
    if not (has_gas or has_liq or has_solid):
        print('  SKIP'); return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
    
    for idx, season in enumerate(['冬季', '春季']):
        ax = axes[idx]
        sd = df[df['季节'] == season].copy()
        if len(sd) == 0:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14)
            ax.set_title(season, fontsize=14, fontweight='bold')
            continue
        
        pts = sd['采样点'].values if '采样点' in sd.columns else [f'R{i+1}' for i in range(len(sd))]
        bottom = np.zeros(len(sd))
        bars, lbls = [], []
        
        if has_gas:
            bars.append(sd['气相碳'].fillna(0).values); lbls.append('气相碳')
        if has_liq:
            bars.append(sd['液相碳'].fillna(0).values); lbls.append('液相碳')
        if has_solid:
            bars.append(sd['有机碳(g/kg)'].fillna(0).values); lbls.append('固相碳')
        
        colors = ['#56B4E9', '#009E73', '#D55E00']
        for i, (bv, lb, c) in enumerate(zip(bars, lbls, colors)):
            ax.bar(range(len(sd)), bv, bottom=bottom, color=c, label=lb,
                  alpha=0.8, edgecolor='white', linewidth=0.5, width=0.6)
            bottom += bv
        
        ax.set_xticks(range(len(sd)))
        ax.set_xticklabels(pts, rotation=45, ha='right', fontsize=10)
        ax.set_ylabel('碳浓度 (相对值)', fontsize=12)
        ax.set_title(season, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11, frameon=True, edgecolor='#CCC')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(axis='y', alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)
    
    fig.suptitle('各采样点碳分布堆叠图', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图8_堆叠柱状图')
    plt.close()


# ============================================================================
# 图9: 空间分布图（沿程变化）
# ============================================================================
def fig9_spatial(df):
    print('\n[图9] 空间分布图...')
    vars = ['甲烷(ppm)', 'CO2(ppm)', 'TOC(mg/L)', 'DO(mg/L)', 'pH', '液温']
    vars = [c for c in vars if c in df.columns]
    if not vars: print('  SKIP'); return
    
    n = len(vars); nc = min(3, n); nr = (n + nc - 1)//nc
    fig, axes = plt.subplots(nr, nc, figsize=(5.5*nc, 4.5*nr), facecolor='white')
    axes = axes.flatten()
    
    for i, var in enumerate(vars):
        ax = axes[i]
        d = pd.to_numeric(df[var], errors='coerce')
        for s in ['冬季', '春季']:
            m = df['季节'] == s
            sd = d[m]
            if len(sd) > 0:
                ax.plot(range(len(sd)), sd.values, marker='o', linestyle='-', lw=1.5, markersize=7,
                       color=SEASON_COLORS[s], label=s, alpha=0.8,
                       markerfacecolor=SEASON_COLORS[s], markeredgecolor='white', markeredgewidth=0.5)
        ax.set_xlabel('采样点序号', fontsize=11)
        ax.set_ylabel(label_map(var), fontsize=11)
        ax.set_title(label_map(var), fontsize=12, fontweight='bold')
        if i == 0: ax.legend(fontsize=10, frameon=True, edgecolor='#CCC')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)
    
    for i in range(n, len(axes)): axes[i].set_visible(False)
    fig.suptitle('沿程空间分布变化', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图9_空间分布图')
    plt.close()


# ============================================================================
# 图10: 描述统计表
# ============================================================================
def fig10_stats_table(df):
    print('\n[图10] 描述统计表...')
    vars = ['甲烷(ppm)', '氧化亚氮(ppm)', 'CO2(ppm)', 'VOCs(ppb)',
            'TOC(mg/L)', '总氮(mg/L)', '总磷(mg/L)', '铵态氮(mg/L)', '硝态氮(mg/L)',
            'COD(mg/L)', 'DO(mg/L)', 'pH', '液温', '电导率(uS/cm)']
    vars = [c for c in vars if c in df.columns]
    if not vars: print('  SKIP'); return
    
    fig, ax = plt.subplots(figsize=(14, len(vars)*0.6+1), facecolor='white')
    ax.axis('off')
    
    col_lbls = ['变量', '冬季均值', '冬季标准差', '春季均值', '春季标准差', 'p值', '显著性']
    cells = []
    for var in vars:
        d = pd.to_numeric(df[var], errors='coerce')
        wd = d[df['季节']=='冬季'].dropna()
        sd = d[df['季节']=='春季'].dropna()
        wm = f'{wd.mean():.3f}' if len(wd)>0 else '-'
        ws = f'{wd.std():.3f}' if len(wd)>1 else '-'
        sm = f'{sd.mean():.3f}' if len(sd)>0 else '-'
        ss = f'{sd.std():.3f}' if len(sd)>1 else '-'
        if len(wd)>1 and len(sd)>1:
            _, p = stats.mannwhitneyu(wd, sd, alternative='two-sided')
            ps = f'{p:.4f}'; sg = sig_stars(p)
        else:
            ps = '-'; sg = '-'
        cells.append([label_map(var), wm, ws, sm, ss, ps, sg])
    
    tbl = ax.table(cellText=cells, colLabels=col_lbls, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.5)
    for k, c in tbl.get_celld().items():
        c.set_edgecolor('#CCC'); c.set_linewidth(0.5)
        if k[0] == 0: c.set_facecolor('#0072B2'); c.set_text_props(color='white', fontweight='bold', fontsize=10)
        elif k[0] % 2 == 0: c.set_facecolor('#F5F5F5')
        else: c.set_facecolor('white')
    ax.set_title('冬春季数据描述统计与差异检验', fontsize=18, fontweight='bold', pad=20)
    plt.tight_layout()
    save_fig(fig, '图10_描述统计表')
    plt.close()


# ============================================================================
# 图11: 固相指标箱线图（春季特有）
# ============================================================================
def fig11_solid_box(df):
    print('\n[图11] 固相指标箱线图...')
    vars = ['有机碳(g/kg)', 'DOC(mg/kg)', '全磷(g/kg)', '无机碳(g/kg)']
    vars = [c for c in vars if c in df.columns]
    if not vars: print('  SKIP'); return
    
    n = len(vars); nc = min(4, n); nr = (n + nc - 1)//nc
    fig, axes = plt.subplots(nr, nc, figsize=(5*nc, 4.5*nr), facecolor='white')
    axes = axes.flatten()
    
    for i, var in enumerate(vars):
        ax = axes[i]
        d = pd.to_numeric(df[var], errors='coerce')
        sd = d[df['季节']=='春季'].dropna()
        if len(sd) > 0:
            ax.boxplot(sd, patch_artist=True, widths=0.45,
                      medianprops={'color':'black','linewidth':1.5},
                      boxprops={'facecolor':'#D55E00','alpha':0.7,'linewidth':1.2},
                      flierprops={'marker':'o','markerfacecolor':'#666','markersize':5,'alpha':0.5})
            jit = np.random.normal(1, 0.05, len(sd))
            ax.scatter(jit, sd, alpha=0.6, s=35, color='#D55E00', edgecolors='white', linewidth=0.5, zorder=5)
        ax.set_xticklabels(['春季'], fontsize=11)
        ax.set_ylabel(label_map(var), fontsize=11)
        ax.set_title(label_map(var), fontsize=12, fontweight='bold')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(axis='y', alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)
    
    for i in range(n, len(axes)): axes[i].set_visible(False)
    fig.suptitle('春季固相指标分布', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图11_固相指标箱线图')
    plt.close()


# ============================================================================
# 图12: 环境因子对比图
# ============================================================================
def fig12_env_factors(df):
    print('\n[图12] 环境因子对比...')
    vars = ['DO(mg/L)', 'pH', '液温', '电导率(uS/cm)', '气温℃', 'NaCl(mg/L)']
    vars = [c for c in vars if c in df.columns]
    if not vars: print('  SKIP'); return
    
    n = len(vars); nc = min(3, n); nr = (n + nc - 1)//nc
    fig, axes = plt.subplots(nr, nc, figsize=(5.5*nc, 4.5*nr), facecolor='white')
    axes = axes.flatten()
    
    for i, var in enumerate(vars):
        ax = axes[i]
        d = pd.to_numeric(df[var], errors='coerce')
        wd = d[df['季节']=='冬季'].dropna()
        sd = d[df['季节']=='春季'].dropna()
        
        dl, lbls, cols = [], [], []
        for dd, ss, cc in [(wd,'冬季',SEASON_COLORS['冬季']),(sd,'春季',SEASON_COLORS['春季'])]:
            if len(dd) > 0: dl.append(dd); lbls.append(ss); cols.append(cc)
        
        if dl:
            bp = ax.boxplot(dl, patch_artist=True, widths=0.45,
                           medianprops={'color':'black','linewidth':1.5},
                           flierprops={'marker':'o','markerfacecolor':'#666','markersize':4,'alpha':0.4},
                           boxprops={'linewidth':1.2}, whiskerprops={'linewidth':1.2}, capprops={'linewidth':1.2})
            for p, c in zip(bp['boxes'], cols): p.set_facecolor(c); p.set_alpha(0.7)
            for j, (dd_, c) in enumerate(zip(dl, cols)):
                if len(dd_) > 0:
                    jit = np.random.normal(j+1, 0.05, len(dd_))
                    ax.scatter(jit, dd_, alpha=0.5, s=25, color=c, edgecolors='white', linewidth=0.5, zorder=5)
            ax.set_xticklabels(lbls, fontsize=11)
            if len(dl)==2 and len(dl[0])>1 and len(dl[1])>1:
                _, p = stats.mannwhitneyu(dl[0], dl[1], alternative='two-sided')
                ymax = max(max(d) for d in dl); ymin = min(min(d) for d in dl)
                yr = ymax - ymin if ymax != ymin else ymax*0.2
                yp = ymax + yr*0.1
                ax.plot([1,1,2,2], [yp, yp+yr*0.04, yp+yr*0.04, yp], color='black', lw=1.2)
                ax.text(1.5, yp+yr*0.06, sig_stars(p), ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        ax.set_ylabel(label_map(var), fontsize=11)
        ax.set_title(label_map(var), fontsize=12, fontweight='bold')
        for sp in ax.spines.values(): sp.set_linewidth(1.2)
        ax.grid(axis='y', alpha=0.25, linestyle='--')
        ax.set_axisbelow(True)
    
    for i in range(n, len(axes)): axes[i].set_visible(False)
    fig.suptitle('冬春季环境因子对比', fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_fig(fig, '图12_环境因子对比')
    plt.close()


# ============================================================================
# 主函数
# ============================================================================
def main():
    print('='*60)
    print('硕士论文级科研绘图与统计分析系统 v5.0')
    print('基于冬春数据.xlsx')
    print('='*60)
    
    df = load_data()
    if df is None or len(df) == 0:
        print('错误：数据加载失败')
        return
    
    print(f'\n数据概览: {len(df)} 行, {len(df.columns)} 列')
    for s in ['冬季', '春季']:
        print(f'  {s}: {len(df[df["季节"]==s])} 个样本')
    for z in ['教学实验区', '生活区']:
        print(f'  {z}: {len(df[df["功能区"]==z])} 个样本')
    
    print('\n' + '='*60)
    print('开始生成图件...')
    print('='*60)
    
    fig1_pie(df)
    fig2_gas_box(df)
    fig2b_gas_bar(df)
    fig3_liquid_box(df)
    fig4_corr(df)
    fig5_pca(df)
    fig6_hca(df)
    fig7_reg(df)
    fig8_stacked(df)
    fig9_spatial(df)
    fig10_stats_table(df)
    fig11_solid_box(df)
    fig12_env_factors(df)
    
    print('\n' + '='*60)
    print('全部图件生成完成！')
    print(f'输出目录: {OUTPUT_DIR}')
    print('='*60)


if __name__ == '__main__':
    main()
