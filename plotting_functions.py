"""
=============================================================================
绘图函数模块 - Plotting Functions
生成全部高质量论文图件
=============================================================================
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import lines as mlines
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
import numpy as np
import pandas as pd
import os
from scipy.cluster.hierarchy import dendrogram
# 使用手动实现的StandardScaler和PCA（避免sklearn依赖问题）
from statistical_analysis import StandardScaler, PCA, LinearRegression, r2_score

from academic_plot_style import (
    CHINESE_FONT, ENGLISH_FONT, TABLEAU_10, PHASE_COLORS,
    SEASON_COLORS, CARBON_COLORS, get_label, format_chemical,
    significance_stars, add_significance_bars, save_figure
)


class ThesisPlotter:
    """论文图件生成器"""

    def __init__(self, df, output_dir):
        self.df = df
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._prepare_derived_variables()

    def _prepare_derived_variables(self):
        df = self.df
        if 'CH4平均值' in df.columns and 'CO2' in df.columns:
            df['气相碳'] = pd.to_numeric(df['CH4平均值'], errors='coerce') + \
                          pd.to_numeric(df['CO2'], errors='coerce')
        if 'TC(mg/L)' in df.columns:
            df['液相碳'] = pd.to_numeric(df['TC(mg/L)'], errors='coerce')
        if '固总碳（g/kg)' in df.columns:
            df['固相碳'] = pd.to_numeric(df['固总碳（g/kg)'], errors='coerce')
        if '气相碳' in df.columns and '液相碳' in df.columns:
            df['气液碳比'] = df['气相碳'] / df['液相碳'].replace(0, np.nan)

    def plot_phase_composition(self):
        """图1: 三相碳组成饼图"""
        print("\n[生成图1] 固液气三相碳组成...")
        df = self.df
        phase_data = {}
        if '气相碳' in df.columns:
            phase_data['气相'] = df['气相碳'].mean()
        if '液相碳' in df.columns:
            phase_data['液相'] = df['液相碳'].mean()
        if '固相碳' in df.columns:
            phase_data['固相'] = df['固相碳'].mean()
        if len(phase_data) < 2:
            print("  警告: 相态数据不足")
            return
        labels = list(phase_data.keys())
        sizes = list(phase_data.values())
        colors = [PHASE_COLORS.get(l, '#999999') for l in labels]
        fig, ax = plt.subplots(figsize=(8, 8), facecolor='white')
        explode = [0.03] * len(labels)
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, colors=colors,
            autopct='%1.1f%%', pctdistance=0.78,
            startangle=90, explode=explode,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'fontsize': 13})
        for t in autotexts:
            t.set_fontsize(13)
            t.set_fontweight('bold')
            t.set_color('white')
        centre_circle = plt.Circle((0, 0), 0.40, fc='white', linewidth=0)
        ax.add_artist(centre_circle)
        ax.set_title('固液气三相碳组成', fontsize=18, pad=20, fontweight='bold')
        ax.axis('equal')
        legend_labels = [f'{l} ({s:.1f})' for l, s in zip(labels, sizes)]
        legend = ax.legend(wedges, legend_labels, title='相态 (均值)',
                          loc='center left', bbox_to_anchor=(1.05, 0.5),
                          frameon=True, edgecolor='#BBBBBB', facecolor='white', fontsize=12)
        legend.get_title().set_fontsize(13)
        plt.tight_layout()
        save_figure(fig, '图1_三相碳组成', self.output_dir)
        plt.close()
        print("  ✓ 图1已保存")

    def plot_liquid_carbon_composition(self):
        """图2: 液相碳组成堆叠柱状图"""
        print("\n[生成图2] 液相碳组成...")
        df = self.df
        if 'TOC（mg/L)' not in df.columns or 'IC(mg/L)' not in df.columns:
            print("  警告: 液相碳数据不足")
            return
        if '季节' in df.columns:
            grouped = df.groupby('季节')
            seasons = []
            toc_means = []
            ic_means = []
            for season in ['冬季', '春季']:
                if season in grouped.groups:
                    g = grouped.get_group(season)
                    seasons.append(season)
                    toc_means.append(pd.to_numeric(g['TOC（mg/L)'], errors='coerce').mean())
                    ic_means.append(pd.to_numeric(g['IC(mg/L)'], errors='coerce').mean())
        else:
            seasons = ['总体']
            toc_means = [pd.to_numeric(df['TOC（mg/L)'], errors='coerce').mean()]
            ic_means = [pd.to_numeric(df['IC(mg/L)'], errors='coerce').mean()]
        fig, ax = plt.subplots(figsize=(7, 6), facecolor='white')
        x = np.arange(len(seasons))
        width = 0.5
        ax.bar(x, toc_means, width, label='TOC', color=CARBON_COLORS['TOC'],
               edgecolor='white', linewidth=1.5)
        ax.bar(x, ic_means, width, bottom=toc_means, label='IC',
               color=CARBON_COLORS['IC'], edgecolor='white', linewidth=1.5)
        for i, (t, ic) in enumerate(zip(toc_means, ic_means)):
            total = t + ic
            ax.text(i, total + total * 0.02, f'{total:.1f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
            ax.text(i, t / 2, f'TOC\n{t:.1f}', ha='center', va='center',
                    fontsize=10, color='white', fontweight='bold')
            ax.text(i, t + ic / 2, f'IC\n{ic:.1f}', ha='center', va='center',
                    fontsize=10, color='white', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(seasons, fontsize=13)
        ax.set_ylabel('浓度 (mg/L)', fontsize=13)
        ax.set_title('液相碳组成 (TOC vs IC)', fontsize=16, fontweight='bold', pad=15)
        ax.legend(fontsize=12, frameon=True, edgecolor='#BBBBBB')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, '图2_液相碳组成', self.output_dir)
        plt.close()
        print("  ✓ 图2已保存")

    def plot_solid_carbon_composition(self):
        """图3: 固相碳组成堆叠柱状图"""
        print("\n[生成图3] 固相碳组成...")
        df = self.df
        solid_cols = ['有机碳（g/kg)', '无机碳（g/kg)']
        solid_cols = [c for c in solid_cols if c in df.columns]
        if len(solid_cols) < 2:
            print("  警告: 固相碳数据不足")
            return
        if '季节' in df.columns:
            grouped = df.groupby('季节')
            seasons = []
            means_dict = {col: [] for col in solid_cols}
            for season in ['冬季', '春季']:
                if season in grouped.groups:
                    g = grouped.get_group(season)
                    seasons.append(season)
                    for col in solid_cols:
                        means_dict[col].append(pd.to_numeric(g[col], errors='coerce').mean())
        else:
            seasons = ['总体']
            for col in solid_cols:
                means_dict[col] = [pd.to_numeric(df[col], errors='coerce').mean()]
        fig, ax = plt.subplots(figsize=(7, 6), facecolor='white')
        x = np.arange(len(seasons))
        width = 0.5
        colors = [CARBON_COLORS.get(c, '#999999') for c in solid_cols]
        labels = [get_label(c) for c in solid_cols]
        bottom = np.zeros(len(seasons))
        for i, col in enumerate(solid_cols):
            ax.bar(x, means_dict[col], width, bottom=bottom,
                   label=labels[i], color=colors[i],
                   edgecolor='white', linewidth=1.5)
            bottom += np.array(means_dict[col])
        for i in range(len(seasons)):
            cum = 0
            for col in solid_cols:
                val = means_dict[col][i]
                if val > 0:
                    ax.text(i, cum + val / 2, f'{val:.1f}',
                            ha='center', va='center', fontsize=10,
                            color='white', fontweight='bold')
                cum += val
            ax.text(i, cum + cum * 0.02, f'{cum:.1f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(seasons, fontsize=13)
        ax.set_ylabel('含量 (g/kg)', fontsize=13)
        ax.set_title('固相碳组成', fontsize=16, fontweight='bold', pad=15)
        ax.legend(fontsize=11, frameon=True, edgecolor='#BBBBBB')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, '图3_固相碳组成', self.output_dir)
        plt.close()
        print("  ✓ 图3已保存")

    def plot_gas_boxplot(self):
        """图4: 气体浓度箱线图"""
        print("\n[生成图4] 气体浓度箱线图...")
        df = self.df
        gas_vars = ['CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)']
        gas_vars = [c for c in gas_vars if c in df.columns]
        if len(gas_vars) == 0:
            print("  警告: 气体数据不足")
            return
        n_vars = len(gas_vars)
        fig, axes = plt.subplots(1, n_vars, figsize=(5 * n_vars, 5.5), facecolor='white')
        if n_vars == 1:
            axes = [axes]
        for i, var in enumerate(gas_vars):
            ax = axes[i]
            df[var] = pd.to_numeric(df[var], errors='coerce')
            if '季节' in df.columns:
                winter_data = df[df['季节'] == '冬季'][var].dropna()
                spring_data = df[df['季节'] == '春季'][var].dropna()
                bp = ax.boxplot([winter_data, spring_data],
                               patch_artist=True, widths=0.5,
                               medianprops={'color': 'black', 'linewidth': 2},
                               flierprops={'marker': 'o', 'markerfacecolor': '#333333',
                                          'markersize': 5, 'alpha': 0.5})
                colors = [SEASON_COLORS['冬季'], SEASON_COLORS['春季']]
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                for j, data in enumerate([winter_data, spring_data]):
                    jitter = np.random.normal(j + 1, 0.04, size=len(data))
                    ax.scatter(jitter, data, alpha=0.6, s=40,
                              color=colors[j], edgecolors='white', linewidth=0.5, zorder=5)
                ax.set_xticklabels(['冬季', '春季'], fontsize=12)
                if len(winter_data) > 1 and len(spring_data) > 1:
                    from scipy import stats
                    _, p_val = stats.mannwhitneyu(winter_data, spring_data, alternative='two-sided')
                    y_max = max(max(winter_data), max(spring_data))
                    y_range = y_max - min(min(winter_data), min(spring_data))
                    add_significance_bars(ax, 1, 2, y_max + y_range * 0.08,
                                         h=y_range * 0.03, p_value=p_val)
            else:
                ax.boxplot(df[var].dropna(), patch_artist=True,
                          boxprops={'facecolor': TABLEAU_10[0], 'alpha': 0.7})
            ax.set_ylabel(get_label(var), fontsize=12)
            ax.set_title(get_label(var), fontsize=14, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)
        fig.suptitle('冬春季气体浓度对比', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        save_figure(fig, '图4_气体浓度箱线图', self.output_dir)
        plt.close()
        print("  ✓ 图4已保存")

    def plot_liquid_boxplot(self):
        """图5: 液相指标箱线图"""
        print("\n[生成图5] 液相指标箱线图...")
        df = self.df
        liquid_vars = ['TOC（mg/L)', 'TC(mg/L)', 'IC(mg/L)', 'COD（mg/L)',
                       'DO(mg/L)', '总氮（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)']
        liquid_vars = [c for c in liquid_vars if c in df.columns]
        if len(liquid_vars) == 0:
            print("  警告: 液相数据不足")
            return
        n_vars = len(liquid_vars)
        n_cols = 4
        n_rows = (n_vars + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4.5 * n_rows), facecolor='white')
        axes = axes.flatten()
        for i, var in enumerate(liquid_vars):
            ax = axes[i]
            df[var] = pd.to_numeric(df[var], errors='coerce')
            if '季节' in df.columns:
                data_list = []
                labels = []
                for season in ['冬季', '春季']:
                    data = df[df['季节'] == season][var].dropna()
                    if len(data) > 0:
                        data_list.append(data)
                        labels.append(season)
                if len(data_list) > 0:
                    bp = ax.boxplot(data_list, patch_artist=True, widths=0.5,
                                   medianprops={'color': 'black', 'linewidth': 2})
                    colors = [SEASON_COLORS.get(l, TABLEAU_10[i]) for l in labels]
                    for patch, color in zip(bp['boxes'], colors):
                        patch.set_facecolor(color)
                        patch.set_alpha(0.7)
                    for j, data in enumerate(data_list):
                        jitter = np.random.normal(j + 1, 0.04, size=len(data))
                        ax.scatter(jitter, data, alpha=0.5, s=30,
                                  color=colors[j], edgecolors='white', linewidth=0.5, zorder=5)
                    ax.set_xticklabels(labels, fontsize=11)
            else:
                ax.boxplot(df[var].dropna(), patch_artist=True,
                          boxprops={'facecolor': TABLEAU_10[i % 10], 'alpha': 0.7})
            ax.set_ylabel(get_label(var), fontsize=11)
            ax.set_title(get_label(var), fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)
        for i in range(n_vars, len(axes)):
            axes[i].set_visible(False)
        fig.suptitle('冬春季液相指标对比', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        save_figure(fig, '图5_液相指标箱线图', self.output_dir)
        plt.close()
        print("  ✓ 图5已保存")

    def plot_correlation_heatmap(self):
        """图6: 相关性热图"""
        print("\n[生成图6] 相关性热图...")
        df = self.df
        corr_cols = [
            'CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)',
            'TOC（mg/L)', 'IC(mg/L)', 'TC(mg/L)', 'DO(mg/L)',
            'COD（mg/L)', '总氮（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)',
            'pH', '液温', '电导率(uS/cm)',
        ]
        corr_cols = [c for c in corr_cols if c in df.columns]
        if len(corr_cols) < 5:
            print("  警告: 相关性分析数据不足")
            return
        corr_df = df[corr_cols].copy()
        corr_df = corr_df.apply(pd.to_numeric, errors='coerce')
        corr = corr_df.corr(method='pearson')
        labels = [get_label(c) for c in corr.columns]
        fig, ax = plt.subplots(figsize=(12, 10), facecolor='white')
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
        cmap = sns.diverging_palette(240, 10, as_cmap=True)
        sns.heatmap(corr, mask=mask, annot=True, cmap=cmap,
                    fmt='.2f', center=0, vmin=-1, vmax=1,
                    linewidths=0.8, linecolor='white',
                    xticklabels=labels, yticklabels=labels,
                    annot_kws={'fontsize': 9},
                    cbar_kws={'shrink': 0.8, 'label': 'Pearson r'}, ax=ax)
        ax.set_title('多参数相关性热图', fontsize=18, fontweight='bold', pad=20)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
        plt.tight_layout()
        save_figure(fig, '图6_相关性热图', self.output_dir)
        plt.close()
        print("  ✓ 图6已保存")

    def plot_pca_biplot(self):
        """图7: PCA双标图"""
        print("\n[生成图7] PCA双标图...")
        df = self.df
        pca_cols = [
            'CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)',
            'TOC（mg/L)', 'IC(mg/L)', 'TC(mg/L)', 'DO(mg/L)',
            'COD（mg/L)', '总氮（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)',
            'pH', '液温', '电导率(uS/cm)',
        ]
        pca_cols = [c for c in pca_cols if c in df.columns]
        if len(pca_cols) < 5:
            print("  警告: PCA数据不足")
            return
        pca_df = df[pca_cols].copy()
        pca_df = pca_df.dropna()
        if len(pca_df) < 5:
            print("  警告: PCA有效样本不足")
            return
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(pca_df.values)
        pca = PCA(n_components=2)
        principal = pca.fit_transform(scaled_data)
        explained = pca.explained_variance_ratio_
        loadings = pca.components_.T
        fig, ax = plt.subplots(figsize=(9, 8), facecolor='white')
        if '季节' in df.columns:
            seasons = df.loc[pca_df.index, '季节'].values
            for season in ['冬季', '春季']:
                mask = seasons == season
                if mask.sum() > 0:
                    ax.scatter(principal[mask, 0], principal[mask, 1],
                              c=[SEASON_COLORS[season]], label=season,
                              s=100, alpha=0.7, edgecolors='#333333', linewidth=0.5)
        else:
            ax.scatter(principal[:, 0], principal[:, 1], c=TABLEAU_10[0],
                      s=100, alpha=0.7, edgecolors='#333333', linewidth=0.5)
        for i, col in enumerate(pca_cols):
            ax.arrow(0, 0, loadings[i, 0] * 3, loadings[i, 1] * 3,
                    head_width=0.08, head_length=0.08, fc='#D55E00', ec='#D55E00', alpha=0.7)
            label = get_label(col)
            ax.text(loadings[i, 0] * 3.3, loadings[i, 1] * 3.3, label,
                   fontsize=9, ha='center', va='center', color='#D55E00', fontweight='bold')
        circle = plt.Circle((0, 0), 3, fill=False, color='#999999', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.add_patch(circle)
        ax.axhline(y=0, color='#999999', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.axvline(x=0, color='#999999', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.set_xlabel(f'PC1 ({explained[0]*100:.1f}%)', fontsize=13)
        ax.set_ylabel(f'PC2 ({explained[1]*100:.1f}%)', fontsize=13)
        ax.set_title('PCA双标图', fontsize=16, fontweight='bold', pad=15)
        ax.legend(fontsize=12, frameon=True, edgecolor='#BBBBBB')
        ax.grid(alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, '图7_PCA双标图', self.output_dir)
        plt.close()
        print("  ✓ 图7已保存")

    def plot_hca_dendrogram(self):
        """图8: 层次聚类树状图"""
        print("\n[生成图8] 层次聚类树状图...")
        df = self.df
        hca_cols = [
            'CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)',
            'TOC（mg/L)', 'IC(mg/L)', 'TC(mg/L)', 'DO(mg/L)',
            'COD（mg/L)', '总氮（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)',
        ]
        hca_cols = [c for c in hca_cols if c in df.columns]
        if len(hca_cols) < 5:
            print("  警告: HCA数据不足")
            return
        hca_df = df[hca_cols].copy()
        hca_df = hca_df.dropna()
        if len(hca_df) < 5:
            print("  警告: HCA有效样本不足")
            return
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(hca_df)
        from scipy.cluster.hierarchy import linkage
        linked = linkage(scaled_data, method='ward')
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
        from scipy.cluster.hierarchy import set_link_color_palette
        set_link_color_palette(['#4E79A7', '#F28E2B', '#E15759', '#76B7B2'])
        dendrogram(linked, ax=ax, leaf_rotation=90, leaf_font_size=10,
                   labels=[f'R{i+1}' for i in range(len(hca_df))],
                   color_threshold=0.7 * max(linked[:, 2]),
                   above_threshold_color='#999999')
        ax.set_title('层次聚类分析 (Ward法)', fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('样本', fontsize=13)
        ax.set_ylabel('欧氏距离', fontsize=13)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, '图8_HCA聚类图', self.output_dir)
        plt.close()
        print("  ✓ 图8已保存")

    def plot_regression(self, x_col, y_col, title, filename):
        """通用回归分析图"""
        df = self.df
        x_data = pd.to_numeric(df[x_col], errors='coerce').dropna()
        y_data = pd.to_numeric(df[y_col], errors='coerce').dropna()
        common_idx = x_data.index.intersection(y_data.index)
        x = x_data[common_idx].values
        y = y_data[common_idx].values
        if len(x) < 5:
            print(f"  警告: {filename} 数据不足")
            return
        from scipy import stats
        model = LinearRegression()
        model.fit(x.reshape(-1, 1), y)
        y_pred = model.predict(x.reshape(-1, 1))
        r, p_value = stats.pearsonr(x, y)
        r2 = r2_score(y, y_pred)
        fig, ax = plt.subplots(figsize=(7, 6), facecolor='white')
        if '季节' in df.columns:
            seasons = df.loc[common_idx, '季节'].values
            for season in ['冬季', '春季']:
                mask = seasons == season
                if mask.sum() > 0:
                    ax.scatter(x[mask], y[mask],
                              c=[SEASON_COLORS[season]], label=season,
                              s=80, alpha=0.7, edgecolors='#333333', linewidth=0.5)
        else:
            ax.scatter(x, y, c=TABLEAU_10[0], s=80, alpha=0.7,
                      edgecolors='#333333', linewidth=0.5)
        x_sorted = np.sort(x)
        y_sorted = model.predict(x_sorted.reshape(-1, 1))
        ax.plot(x_sorted, y_sorted, color='#D55E00', linewidth=2.5, linestyle='-')
        try:
            x_smooth = np.linspace(x.min(), x.max(), 100)
            y_smooth = model.predict(x_smooth.reshape(-1, 1))
            residuals = y - y_pred
            std_err = np.std(residuals)
            ax.fill_between(x_smooth, y_smooth - 1.96 * std_err, y_smooth + 1.96 * std_err,
                           alpha=0.15, color='#D55E00')
        except:
            pass
        textstr = f'y = {model.coef_[0]:.3f}x + {model.intercept_:.2f}\n'
        textstr += f'R² = {r2:.3f}\nr = {r:.3f}\np = {p_value:.2e}\n'
        textstr += significance_stars(p_value)
        props = dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#BBBBBB', alpha=0.9)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=11,
               verticalalignment='top', bbox=props, family='monospace')
        ax.set_xlabel(get_label(x_col), fontsize=13)
        ax.set_ylabel(get_label(y_col), fontsize=13)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.legend(fontsize=11, frameon=True, edgecolor='#BBBBBB')
        ax.grid(alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, filename, self.output_dir)
        plt.close()
        print(f"  ✓ {filename}已保存")

    def plot_all_regressions(self):
        """图9-14: 所有回归分析图"""
        print("\n[生成图9-14] 回归分析图...")
        regressions = [
            ('TOC（mg/L)', 'CH4平均值', 'TOC 与 CH$_4$ 的关系', '图9_TOC_CH4回归'),
            ('TOC（mg/L)', 'CO2', 'TOC 与 CO$_2$ 的关系', '图10_TOC_CO2回归'),
            ('DO(mg/L)', 'CH4平均值', 'DO 与 CH$_4$ 的关系', '图11_DO_CH4回归'),
            ('COD（mg/L)', 'CH4平均值', 'COD 与 CH$_4$ 的关系', '图12_COD_CH4回归'),
            ('总氮（mg/L)', 'TOC（mg/L)', 'TN 与 TOC 的关系', '图13_TN_TOC回归'),
            ('铵态氮（mg/L)', 'CH4平均值', r'NH$_4^+$ 与 CH$_4$ 的关系', '图14_NH4_CH4回归'),
        ]
        for x_col, y_col, title, filename in regressions:
            if x_col in self.df.columns and y_col in self.df.columns:
                self.plot_regression(x_col, y_col, title, filename)

    def plot_spatial_distribution(self):
        """图15: 采样点空间分布"""
        print("\n[生成图15] 采样点空间分布...")
        df = self.df
        gas_vars = ['CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)']
        gas_vars = [c for c in gas_vars if c in df.columns]
        if len(gas_vars) == 0 or '采样点' not in df.columns:
            print("  警告: 空间分布数据不足")
            return
        n_vars = len(gas_vars)
        fig, axes = plt.subplots(n_vars, 1, figsize=(14, 3.5 * n_vars), facecolor='white')
        if n_vars == 1:
            axes = [axes]
        for i, var in enumerate(gas_vars):
            ax = axes[i]
            df[var] = pd.to_numeric(df[var], errors='coerce')
            if '季节' in df.columns:
                for season, color in [('冬季', SEASON_COLORS['冬季']), ('春季', SEASON_COLORS['春季'])]:
                    season_data = df[df['季节'] == season].copy()
                    season_data = season_data.sort_values('采样点')
                    ax.plot(range(len(season_data)), season_data[var].values,
                           marker='o', label=season, color=color,
                           linewidth=2, markersize=8, markerfacecolor=color,
                           markeredgecolor='white', markeredgewidth=1)
            ax.set_ylabel(get_label(var), fontsize=12)
            ax.set_title(f'{get_label(var)} 沿程变化', fontsize=13, fontweight='bold')
            ax.set_xlabel('采样点', fontsize=12)
            ax.legend(fontsize=11)
            ax.grid(alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)
        fig.suptitle('冬春季气体浓度沿程空间分布', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        save_figure(fig, '图15_空间分布图', self.output_dir)
        plt.close()
        print("  ✓ 图15已保存")

    def plot_gas_liquid_ratio(self):
        """图16: 气液碳比分布"""
        print("\n[生成图16] 气液碳比分布...")
        df = self.df
        if '气液碳比' not in df.columns:
            print("  警告: 气液碳比数据不足")
            return
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor='white')
        ax1 = axes[0]
        valid_data = df['气液碳比'].dropna()
        if len(valid_data) > 5:
            ax1.hist(valid_data, bins=15, color=TABLEAU_10[0], edgecolor='white',
                    alpha=0.7, density=True)
            from scipy import stats
            kde_x = np.linspace(valid_data.min(), valid_data.max(), 100)
            kde = stats.gaussian_kde(valid_data)
            ax1.plot(kde_x, kde(kde_x), color='#D55E00', linewidth=2)
            ax1.axvline(valid_data.mean(), color='#333333', linestyle='--', linewidth=1.5,
                       label=f'均值: {valid_data.mean():.3f}')
            ax1.legend(fontsize=11)
        ax1.set_xlabel('气液碳比', fontsize=13)
        ax1.set_ylabel('密度', fontsize=13)
        ax1.set_title('气液碳比分布', fontsize=14, fontweight='bold')
        ax1.grid(alpha=0.3, linestyle='--')
        ax2 = axes[1]
        if '季节' in df.columns:
            data_list = []
            labels = []
            for season in ['冬季', '春季']:
                data = df[df['季节'] == season]['气液碳比'].dropna()
                if len(data) > 0:
                    data_list.append(data)
                    labels.append(season)
            if len(data_list) > 0:
                bp = ax2.boxplot(data_list, patch_artist=True, widths=0.5,
                               medianprops={'color': 'black', 'linewidth': 2})
                colors = [SEASON_COLORS.get(l, TABLEAU_10[0]) for l in labels]
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                for j, data in enumerate(data_list):
                    jitter = np.random.normal(j + 1, 0.04, size=len(data))
                    ax2.scatter(jitter, data, alpha=0.5, s=30,
                              color=colors[j], edgecolors='white', linewidth=0.5, zorder=5)
                ax2.set_xticklabels(labels, fontsize=11)
        ax2.set_ylabel('气液碳比', fontsize=13)
        ax2.set_title('冬春气液碳比对比', fontsize=14, fontweight='bold')
        ax2.grid(alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        plt.tight_layout()
        save_figure(fig, '图16_气液碳比分布', self.output_dir)
        plt.close()
        print("  ✓ 图16已保存")

    def plot_carbon_balance(self):
        """图17: 碳平衡示意图"""
        print("\n[生成图17] 碳平衡示意图...")
        df = self.df
        fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')
        gas_c = df['气相碳'].mean() if '气相碳' in df.columns else 0
        liquid_c = df['液相碳'].mean() if '液相碳' in df.columns else 0
        solid_c = df['固相碳'].mean() if '固相碳' in df.columns else 0
        total_c = gas_c + liquid_c + solid_c
        from matplotlib.patches import FancyBboxPatch
        boxes = [
            (1, 6, '气相碳', f'{gas_c:.1f} ppm', PHASE_COLORS['气相']),
            (4, 3, '液相碳', f'{liquid_c:.1f} mg/L', PHASE_COLORS['液相']),
            (7, 6, '固相碳', f'{solid_c:.1f} g/kg', PHASE_COLORS['固相']),
        ]
        for x, y, name, value, color in boxes:
            box = FancyBboxPatch((x, y), 2, 2, boxstyle="round,pad=0.2",
                                facecolor=color, edgecolor='#333333', linewidth=2, alpha=0.8)
            ax.add_patch(box)
            ax.text(x + 1, y + 1.4, name, ha='center', va='center',
                   fontsize=16, fontweight='bold', color='white')
            ax.text(x + 1, y + 0.6, value, ha='center', va='center',
                   fontsize=13, color='white')
        ax.annotate('', xy=(3, 7), xytext=(1.5, 7.5),
                   arrowprops=dict(arrowstyle='->', color='#333333', lw=2))
        ax.annotate('', xy=(6, 7), xytext=(4.5, 7.5),
                   arrowprops=dict(arrowstyle='->', color='#333333', lw=2))
        ax.annotate('', xy=(4.5, 4.5), xytext=(3, 5.5),
                   arrowprops=dict(arrowstyle='->', color='#333333', lw=2))
        ax.set_title('校园污水管网碳平衡示意图', fontsize=20, fontweight='bold', pad=20)
        legend_text = (f'总碳量: {total_c:.1f}\n'
                      f'气相占比: {gas_c/total_c*100:.1f}%\n'
                      f'液相占比: {liquid_c/total_c*100:.1f}%\n'
                      f'固相占比: {solid_c/total_c*100:.1f}%')
        props = dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#BBBBBB', alpha=0.9)
        ax.text(8.5, 1, legend_text, fontsize=12, verticalalignment='bottom',
               bbox=props, family='monospace')
        plt.tight_layout()
        save_figure(fig, '图17_碳平衡示意图', self.output_dir)
        plt.close()
        print("  ✓ 图17已保存")

    def generate_all_figures(self):
        """生成全部图件"""
        print("\n" + "=" * 60)
        print("开始生成全部论文图件")
        print("=" * 60)
        self.plot_phase_composition()
        self.plot_liquid_carbon_composition()
        self.plot_solid_carbon_composition()
        self.plot_gas_boxplot()
        self.plot_liquid_boxplot()
        self.plot_correlation_heatmap()
        self.plot_pca_biplot()
        self.plot_hca_dendrogram()
        self.plot_all_regressions()
        self.plot_spatial_distribution()
        self.plot_gas_liquid_ratio()
        self.plot_carbon_balance()
        print("\n" + "=" * 60)
        print("全部图件生成完成!")
        print("=" * 60)
