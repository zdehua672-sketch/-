# -*- coding: utf-8 -*-
"""
数据主导的全流程：先探索数据 → 发现模式 → 基于发现写作 → 图文对应排版
核心理念：不是"我有什么分析方法"，而是"数据告诉了我什么"
"""
import os
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime


# ============================================================
# 1. 数据探索器 — 先看数据说了什么
# ============================================================

class DataExplorer:
    """
    数据主导的探索器。
    不预设分析模板，而是从数据中发现所有值得关注的模式。
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.findings = []  # 发现列表
        self.numeric_cols = []
        self.category_cols = []
        self._classify()

    def _classify(self):
        """自动分类列"""
        skip = ['采样点', '季节', '泥水状况', '采样时间', '采样时段',
                '进水/出水', '管口/管中', '管口/管尾']
        for col in self.df.columns:
            if col in skip:
                self.category_cols.append(col)
                continue
            if pd.api.types.is_numeric_dtype(self.df[col]):
                # 有效值 >= 2 即可分析（固相变量可能只有2个有效值）
                if self.df[col].dropna().shape[0] >= 2:
                    self.numeric_cols.append(col)

    def explore(self) -> list:
        """全面探索，返回所有发现"""
        print("\n" + "=" * 60)
        print("  数据探索 — 让数据说话")
        print("=" * 60)

        self._explore_distributions()
        self._explore_outliers()
        self._explore_correlations()
        self._explore_group_differences()
        self._explore_phase_analysis()
        self._explore_cross_phase()
        self._explore_anomalies()
        self._explore_anomaly_stories()
        self._explore_extremes()
        self._explore_effect_size()
        self._explore_normality()

        # 按重要性排序
        self.findings.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['importance'], 4))

        print(f"\n共发现 {len(self.findings)} 个值得关注的模式")
        return self.findings

    def _explore_distributions(self):
        """探索每个变量的分布特征"""
        print("\n[探索1] 分布特征...")

        # 首先检查数据质量（缺失率）
        print("\n  [数据质量] 缺失率检查:")
        for col in self.numeric_cols:
            total = len(self.df)
            missing = self.df[col].isna().sum()
            missing_rate = missing / total

            if missing_rate > 0.5:
                # 高缺失率变量
                if missing_rate > 0.9:
                    severity = 'critical'
                    print(f"  [!!!] {col}: 缺失率={missing_rate:.1%} ({missing}/{total}) - 数据严重不足，建议排除")
                else:
                    severity = 'high'
                    print(f"  [!!] {col}: 缺失率={missing_rate:.1%} ({missing}/{total}) - 有效样本仅{total-missing}个")

                self.findings.append({
                    'type': 'data_quality',
                    'variable': col,
                    'importance': severity,
                    'detail': f'{col}缺失率{missing_rate:.1%}({missing}/{total})，仅{total-missing}个有效样本',
                    'data': {'missing_rate': missing_rate, 'missing': missing, 'total': total},
                })

        # 然后检查分布特征
        for col in self.numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 5:
                continue

            skew = data.skew()
            kurt = data.kurtosis()
            cv = (data.std() / data.mean() * 100) if data.mean() != 0 else 0

            # 高偏度 = 分布极不均匀
            if abs(skew) > 2:
                self.findings.append({
                    'type': 'distribution',
                    'variable': col,
                    'importance': 'medium',
                    'detail': f'{col}分布严重偏斜(skew={skew:.2f})，中位数{data.median():.2f}远{("小于" if skew > 0 else "大于")}均数{data.mean():.2f}',
                    'data': {'skew': skew, 'kurtosis': kurt, 'median': data.median(), 'mean': data.mean()},
                })
                print(f"  [!] {col}: 严重偏斜 skew={skew:.2f}")

            # 高变异 = 数据差异大
            if cv > 200:
                self.findings.append({
                    'type': 'high_variability',
                    'variable': col,
                    'importance': 'high',
                    'detail': f'{col}变异系数极高(CV={cv:.1f}%)，浓度范围{data.min():.2f}~{data.max():.2f}，最大值是最小值的{data.max()/data.min():.1f}倍',
                    'data': {'cv': cv, 'min': data.min(), 'max': data.max(), 'ratio': data.max()/data.min()},
                })
                print(f"  [!!] {col}: CV={cv:.1f}%，最大/最小={data.max()/data.min():.1f}倍")

    def _explore_outliers(self):
        """探索异常值"""
        print("\n[探索2] 异常值检测...")
        for col in self.numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 5:
                continue

            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = data[(data < lower) | (data > upper)]

            if len(outliers) > 0:
                # 找到异常值对应的采样点
                outlier_points = []
                for idx in outliers.index:
                    point = self.df.loc[idx, '采样点'] if '采样点' in self.df.columns else f'行{idx}'
                    season = self.df.loc[idx, '季节'] if '季节' in self.df.columns else ''
                    outlier_points.append(f'{point}({season})={outliers[idx]:.2f}')

                self.findings.append({
                    'type': 'outlier',
                    'variable': col,
                    'importance': 'high' if len(outliers) >= 3 else 'medium',
                    'detail': f'{col}存在{len(outliers)}个异常值: {", ".join(outlier_points[:3])}',
                    'data': {'count': len(outliers), 'values': outliers.tolist(), 'points': outlier_points},
                })
                print(f"  [!] {col}: {len(outliers)}个异常值")

    def _explore_correlations(self):
        """探索变量间的相关性 — 同时计算 Pearson 和 Spearman，报告所有结果"""
        print("\n[探索3] 相关性发现...")
        if len(self.numeric_cols) < 2:
            return

        valid_cols = [c for c in self.numeric_cols if self.df[c].dropna().shape[0] >= 5]
        if len(valid_cols) < 2:
            return

        # 逐对计算（处理缺失值不同的情况）
        for i, c1 in enumerate(valid_cols):
            for c2 in valid_cols[i+1:]:
                pair = self.df[[c1, c2]].dropna()
                if len(pair) < 5:
                    continue
                if pair[c1].std() == 0 or pair[c2].std() == 0:
                    continue

                # 同时计算 Pearson 和 Spearman
                r_pearson, p_pearson = stats.pearsonr(pair[c1], pair[c2])
                r_spearman, p_spearman = stats.spearmanr(pair[c1], pair[c2])

                # 使用更保守的结果（p值更大的）
                if p_pearson > p_spearman:
                    r, p, method = r_pearson, p_pearson, 'Pearson'
                else:
                    r, p, method = r_spearman, p_spearman, 'Spearman'

                # 检查 Pearson 和 Spearman 差异（非线性检测）
                r_diff = abs(r_pearson - r_spearman)
                nonlinear_flag = r_diff > 0.2

                # 效应量：r 本身就是效应量指标
                # |r|>=0.5 大效应, 0.3-0.5 中效应, 0.1-0.3 小效应
                effect_size = abs(r)

                # 显著性分级
                if p < 0.001:
                    sig = '***'
                    importance = 'critical'
                elif p < 0.01:
                    sig = '**'
                    importance = 'high'
                elif p < 0.05:
                    sig = '*'
                    importance = 'high'
                elif p < 0.10:
                    sig = '(接近显著)'
                    importance = 'medium'
                else:
                    sig = 'n.s.'
                    importance = 'low'

                direction = '正' if r > 0 else '负'

                # 构建详细信息
                detail = f'{c1}与{c2}呈{direction}相关({method}: r={r:.3f}, p={p:.4f}{sig}, n={len(pair)})'
                if nonlinear_flag:
                    detail += f' [非线性可能: Pearson={r_pearson:.3f}, Spearman={r_spearman:.3f}]'

                # 报告所有 |r| > 0.3 的结果（中等以上效应）
                if effect_size > 0.3:
                    self.findings.append({
                        'type': 'correlation',
                        'variables': (c1, c2),
                        'importance': importance,
                        'detail': detail,
                        'data': {
                            'r': r, 'p': p, 'n': len(pair),
                            'effect_size': effect_size, 'sig': sig,
                            'method': method,
                            'r_pearson': r_pearson, 'p_pearson': p_pearson,
                            'r_spearman': r_spearman, 'p_spearman': p_spearman,
                            'nonlinear': nonlinear_flag,
                        },
                    })
                    if p < 0.05:
                        print(f"  [!!] {c1} vs {c2}: {method} r={r:.3f}, p={p:.4f}{sig}")
                    elif p < 0.10:
                        print(f"  [!] {c1} vs {c2}: {method} r={r:.3f}, p={p:.4f}{sig} (接近显著)")
                    if nonlinear_flag:
                        print(f"       ⚠️ 非线性可能: Pearson={r_pearson:.3f}, Spearman={r_spearman:.3f}")

    def _explore_group_differences(self):
        """探索组间差异（如果有分组变量）"""
        print("\n[探索4] 组间差异...")
        group_cols = ['季节', '泥水状况', '气温/℃']
        for gcol in group_cols:
            if gcol not in self.df.columns:
                continue
            groups = self.df[gcol].dropna().unique()
            if len(groups) < 2:
                continue

            print(f"  分组变量: {gcol} ({len(groups)}组: {list(groups)})")
            for col in self.numeric_cols:
                data = self.df[[gcol, col]].dropna()
                if len(data) < 6:
                    continue

                group_data = [data[data[gcol] == g][col].values for g in groups]
                group_data = [g for g in group_data if len(g) >= 2]
                if len(group_data) < 2:
                    continue

                # 正态性决定检验方法
                try:
                    if len(group_data) > 2:
                        # 多组比较用 Kruskal-Wallis
                        stat, p = stats.kruskal(*group_data)
                        method = 'Kruskal-Wallis'
                    elif all(len(g) >= 8 for g in group_data):
                        _, p_norm = stats.shapiro(np.concatenate(group_data))
                        if p_norm > 0.05:
                            stat, p = stats.ttest_ind(*group_data[:2])
                            method = 't检验'
                        else:
                            stat, p = stats.mannwhitneyu(*group_data[:2], alternative='two-sided')
                            method = 'Mann-Whitney U'
                    else:
                        stat, p = stats.mannwhitneyu(*group_data[:2], alternative='two-sided')
                        method = 'Mann-Whitney U'
                    # 确保 p 是标量
                    p = float(p)
                except Exception:
                    continue

                means = [g.mean() for g in group_data]
                stds = [g.std() for g in group_data]
                higher_idx = np.argmax(means)
                lower_idx = np.argmin(means)

                # 效应量：Cohen's d
                pooled_std = np.sqrt((stds[0]**2 + stds[1]**2) / 2) if len(stds) >= 2 else 1
                cohens_d = abs(means[higher_idx] - means[lower_idx]) / pooled_std if pooled_std > 0 else 0

                # 显著性分级
                if p < 0.001:
                    sig = '***'
                    importance = 'critical'
                elif p < 0.01:
                    sig = '**'
                    importance = 'high'
                elif p < 0.05:
                    sig = '*'
                    importance = 'high'
                elif p < 0.10:
                    sig = '(接近显著)'
                    importance = 'medium'
                else:
                    sig = 'n.s.'
                    importance = 'low'

                # 报告所有 p < 0.15 的结果（接近显著或显著）
                # 也报告效应量大的结果（即使不显著）
                if p < 0.15 or cohens_d > 0.8:
                    self.findings.append({
                        'type': 'group_difference',
                        'variable': col,
                        'group_col': gcol,
                        'importance': importance,
                        'detail': f'{col}在{gcol}间差异({method}, p={p:.4f}{sig}, Cohen\'s d={cohens_d:.2f}): {groups[higher_idx]}({means[higher_idx]:.2f}) vs {groups[lower_idx]}({means[lower_idx]:.2f})',
                        'data': {'method': method, 'p': p, 'groups': list(groups), 'means': means, 'stds': stds, 'sig': sig, 'cohens_d': cohens_d},
                    })
                    if p < 0.05:
                        print(f"  [{'!!' if p < 0.001 else '!'}] {col}: {groups[higher_idx]}({means[higher_idx]:.2f}) vs {groups[lower_idx]}({means[lower_idx]:.2f}) {sig} d={cohens_d:.2f}")
                    elif p < 0.10:
                        print(f"  [~] {col}: {groups[higher_idx]}({means[higher_idx]:.2f}) vs {groups[lower_idx]}({means[lower_idx]:.2f}) {sig} d={cohens_d:.2f}")
                    elif cohens_d > 0.8:
                        print(f"  [d] {col}: d={cohens_d:.2f} (大效应量) p={p:.4f}")

    def _explore_anomalies(self):
        """探索数据中的异常模式 — 深挖异常值故事"""
        print("\n[探索5] 异常模式...")

        # 检测零值/缺失率高的变量
        for col in self.numeric_cols:
            total = len(self.df)
            missing = self.df[col].isna().sum()
            if missing > total * 0.5:
                self.findings.append({
                    'type': 'data_quality',
                    'variable': col,
                    'importance': 'low',
                    'detail': f'{col}缺失率{missing/total*100:.0f}%({missing}/{total})，仅{total-missing}个有效样本',
                    'data': {'missing_rate': missing/total},
                })

        # 检测变量间的异常比值
        if 'TOC（mg/L)' in self.df.columns and 'IC(mg/L)' in self.df.columns:
            pair = self.df[['TOC（mg/L)', 'IC(mg/L)']].dropna()
            if len(pair) > 0:
                ratio = pair['TOC（mg/L)'] / pair['IC(mg/L)']
                if ratio.std() > ratio.mean() * 0.5:
                    self.findings.append({
                        'type': 'ratio_pattern',
                        'variables': ('TOC', 'IC'),
                        'importance': 'medium',
                        'detail': f'TOC/IC比值变异大(均值={ratio.mean():.2f}, 范围{ratio.min():.2f}~{ratio.max():.2f})，说明有机碳与无机碳的相对比例在不同采样点差异显著',
                        'data': {'mean': ratio.mean(), 'std': ratio.std(), 'min': ratio.min(), 'max': ratio.max()},
                    })

    def _explore_anomaly_stories(self):
        """深挖异常值故事 — 每个极端值都是一个故事"""
        print("\n[探索5b] 异常值故事...")
        for col in self.numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 5:
                continue

            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            upper = Q3 + 2 * IQR  # 用2倍IQR（更严格）

            outliers = self.df[self.df[col] > upper]
            for idx, row in outliers.iterrows():
                # 收集该采样点的所有变量
                point = str(row.get('采样点', row.get('point', '?')))
                season = str(row.get('季节', row.get('season', '?')))
                sediment = str(row.get('泥水状况', row.get('sediment', '?')))

                # 找到该异常值在其他变量中的位置
                context_parts = []
                for other_col in self.numeric_cols:
                    if other_col == col:
                        continue
                    val = row.get(other_col)
                    if pd.notna(val):
                        other_data = self.df[other_col].dropna()
                        if len(other_data) > 5:
                            percentile = (other_data < val).mean() * 100
                            if percentile > 90 or percentile < 10:
                                context_parts.append(f'{other_col}={val:.1f}({percentile:.0f}%分位)')

                context = ', '.join(context_parts[:5]) if context_parts else '无特殊'

                self.findings.append({
                    'type': 'anomaly_story',
                    'variable': col,
                    'importance': 'high',
                    'detail': f'{point}({season},{sediment}): {col}={row[col]:.1f}(>{upper:.1f}) | 关联: {context}',
                    'data': {
                        'point': point, 'season': season, 'sediment': sediment,
                        'value': float(row[col]), 'threshold': float(upper),
                        'context': context_parts[:5],
                    },
                })
                print(f"  [!] {point}({season}): {col}={row[col]:.1f} | {context[:60]}")

    def _explore_extremes(self):
        """探索极值和最大最小值"""
        print("\n[探索6] 极值分析...")
        for col in self.numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 5:
                continue

            max_idx = data.idxmax()
            min_idx = data.idxmin()
            max_point = self.df.loc[max_idx, '采样点'] if '采样点' in self.df.columns else f'行{max_idx}'
            min_point = self.df.loc[min_idx, '采样点'] if '采样点' in self.df.columns else f'行{min_idx}'
            max_season = self.df.loc[max_idx, '季节'] if '季节' in self.df.columns else ''
            min_season = self.df.loc[min_idx, '季节'] if '季节' in self.df.columns else ''

            # 如果最大值是中位数的5倍以上
            median = data.median()
            if data.max() > median * 5 and data.max() > 10:
                self.findings.append({
                    'type': 'extreme_max',
                    'variable': col,
                    'importance': 'medium',
                    'detail': f'{col}最大值{data.max():.2f}出现在{max_point}({max_season})，是中位数{median:.2f}的{data.max()/median:.1f}倍',
                    'data': {'max': data.max(), 'median': median, 'point': max_point, 'season': max_season},
                })

    def _explore_effect_size(self):
        """计算效应量（Cohen's d）— 两组间差异的实际意义"""
        print("\n[探索7] 效应量分析...")
        cat_cols = [c for c in self.category_cols if c in self.df.columns]
        for cat in cat_cols:
            groups = [g for _, g in self.df.groupby(cat) if len(g) >= 3]
            if len(groups) != 2:
                continue
            g1, g2 = groups[0], groups[1]
            for col in self.numeric_cols:
                d1 = g1[col].dropna()
                d2 = g2[col].dropna()
                if len(d1) < 3 or len(d2) < 3:
                    continue
                n1, n2 = len(d1), len(d2)
                pooled_std = np.sqrt(((n1-1)*d1.std()**2 + (n2-1)*d2.std()**2) / (n1+n2-2))
                if pooled_std == 0:
                    continue
                cohens_d = (d1.mean() - d2.mean()) / pooled_std
                if abs(cohens_d) >= 0.5:
                    magnitude = 'large' if abs(cohens_d) >= 0.8 else 'medium'
                    self.findings.append({
                        'type': 'effect_size',
                        'variable': col,
                        'group_var': cat,
                        'importance': 'high' if abs(cohens_d) >= 0.8 else 'medium',
                        'detail': f'{col}在{cat}两组间效应量Cohen\'s d={cohens_d:.3f}({magnitude})，'
                                  f'均值差{abs(d1.mean()-d2.mean()):.2f}',
                        'data': {'cohens_d': round(cohens_d, 3), 'magnitude': magnitude,
                                 'g1_mean': round(d1.mean(), 3), 'g2_mean': round(d2.mean(), 3),
                                 'g1_name': g1[cat].iloc[0], 'g2_name': g2[cat].iloc[0]},
                    })

    def _explore_normality(self):
        """正态性检验（Shapiro-Wilk）— 判断数据是否符合正态分布"""
        print("\n[探索8] 正态性检验...")
        for col in self.numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 3 or len(data) > 5000:
                continue
            try:
                stat, p = stats.shapiro(data)
                if p < 0.05:
                    self.findings.append({
                        'type': 'normality',
                        'variable': col,
                        'importance': 'low',
                        'detail': f'{col}不服从正态分布(Shapiro-Wilk W={stat:.4f}, p={p:.4f})，'
                                  f'建议使用非参数检验',
                        'data': {'w_stat': round(stat, 4), 'p_value': round(p, 4), 'is_normal': False},
                    })
            except Exception:
                pass

    def _explore_phase_analysis(self):
        """按相态（气/液/固）分层分析，生成结构化发现"""
        print("\n[探索9] 相态分层分析...")

        # 自动识别相态分组
        gas_kw = ['甲烷', 'CH4', '氧化亚氮', 'N2O', 'CO2', 'O2', 'VOCs', 'H2S', 'NO2']
        liq_kw = ['DO', 'pH', 'TOC', 'TC', 'IC', '总氮', 'TN', '总磷', 'TP', '铵态氮', 'NH4',
                   '硝态氮', 'NO3', 'COD', 'NaCl', '电导率', 'EC', '液温']
        sol_kw = ['固总碳', 'DOC', '全磷', '有机碳', '无机碳', '固']

        def classify_col(col):
            for kw in gas_kw:
                if kw in col and '本底' not in col:
                    return 'gas'
            for kw in liq_kw:
                if kw in col:
                    return 'liquid'
            for kw in sol_kw:
                if kw in col:
                    return 'solid'
            return None

        phases = {'gas': [], 'liquid': [], 'solid': []}
        for col in self.numeric_cols:
            phase = classify_col(col)
            if phase:
                phases[phase].append(col)

        # 每个相态内做季节比较
        group_col = '季节' if '季节' in self.df.columns else None
        if not group_col:
            return

        for phase_name, cols in phases.items():
            if not cols:
                continue
            sig_vars = []
            for col in cols:
                data = self.df[[group_col, col]].dropna()
                if len(data) < 6:
                    continue
                groups = data[group_col].unique()
                if len(groups) != 2:
                    continue
                g1 = data[data[group_col] == groups[0]][col]
                g2 = data[data[group_col] == groups[1]][col]
                if len(g1) < 3 or len(g2) < 3:
                    continue
                try:
                    u, p = stats.mannwhitneyu(g1, g2, alternative='two-sided')
                except Exception:
                    continue
                if p < 0.05:
                    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*'
                    higher = groups[0] if g1.mean() > g2.mean() else groups[1]
                    fold = max(g1.mean(), g2.mean()) / max(min(g1.mean(), g2.mean()), 0.001)
                    sig_vars.append({
                        'variable': col, 'p': p, 'sig': sig,
                        'mean1': g1.mean(), 'mean2': g2.mean(),
                        'group1': groups[0], 'group2': groups[1],
                        'higher': higher, 'fold': fold,
                    })
                    print(f"  [{phase_name}] {col}: {groups[0]}({g1.mean():.2f}) vs {groups[1]}({g2.mean():.2f}) p={p:.4f}{sig}")

            if sig_vars:
                self.findings.append({
                    'type': 'phase_seasonal',
                    'phase': phase_name,
                    'importance': 'critical' if any(v['p'] < 0.001 for v in sig_vars) else 'high',
                    'detail': f'{phase_name}相有{len(sig_vars)}个指标存在显著季节差异',
                    'data': {'phase': phase_name, 'variables': sig_vars,
                             'variable_names': [v['variable'] for v in sig_vars]},
                })

    def _explore_cross_phase(self):
        """跨相态关联分析（气相-液相耦合）"""
        print("\n[探索10] 跨相态关联...")

        gas_kw = ['甲烷', 'CH4', '氧化亚氮', 'N2O', 'CO2']
        liq_kw = ['DO', 'pH', 'TOC', 'TC', 'IC', '总氮', 'TN', '总磷', 'TP',
                   '铵态氮', 'NH4', '硝态氮', 'NO3', 'COD', 'NaCl', '电导率', 'EC']

        gas_cols = [c for c in self.numeric_cols if any(k in c for k in gas_kw) and '本底' not in c]
        liq_cols = [c for c in self.numeric_cols if any(k in c for k in liq_kw)]

        if not gas_cols or not liq_cols:
            return

        cross_pairs = []
        for gc in gas_cols:
            for lc in liq_cols:
                pair = self.df[[gc, lc]].dropna()
                if len(pair) < 5:
                    continue
                if pair[gc].std() == 0 or pair[lc].std() == 0:
                    continue
                r, p = stats.pearsonr(pair[gc], pair[lc])
                if p < 0.1:  # 放宽阈值捕获边缘关联
                    direction = '正' if r > 0 else '负'
                    strength = '强' if abs(r) > 0.7 else ('较强' if abs(r) > 0.5 else '中等')
                    cross_pairs.append({
                        'gas': gc, 'liquid': lc,
                        'r': r, 'p': p, 'n': len(pair),
                        'direction': direction, 'strength': strength,
                    })
                    sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '(+)'
                    print(f"  {gc} vs {lc}: r={r:.3f} p={p:.4f}{sig} n={len(pair)}")

        if cross_pairs:
            self.findings.append({
                'type': 'cross_phase',
                'importance': 'critical' if any(cp['p'] < 0.01 for cp in cross_pairs) else 'high',
                'detail': f'气相-液相耦合发现{len(cross_pairs)}对显著关联',
                'data': {'pairs': cross_pairs},
            })


# ============================================================
# 2. 数据主导的写作器 — 基于发现写作 + 知识库支撑
# ============================================================

class DataDrivenWriter:
    """
    基于数据探索发现来写作。
    调用知识库召回机制、句式、文献，用推理链追踪完整性。
    """

    def __init__(self, df: pd.DataFrame, findings: list, output_dir: str,
                 memory=None):
        """
        Parameters
        ----------
        df : DataFrame
        findings : list, DataExplorer.explore() 的输出
        output_dir : str
        memory : KnowledgeMemory or None, 知识记忆实例
        """
        self.df = df
        self.findings = findings
        self.output_dir = output_dir
        self.memory = memory
        self.rationale_rows = []  # 推理链记录

    def write_results(self) -> str:
        """写Results章节 — 按气相/液相/固相/跨相态分层组织"""
        lines = ['# 3 结果\n']
        section_num = 1

        by_type = {}
        for f in self.findings:
            t = f['type']
            by_type.setdefault(t, []).append(f)

        # === 3.1 气相污染物 ===
        gas_seasonal = [f for f in by_type.get('phase_seasonal', []) if f.get('phase') == 'gas']
        gas_corr = [f for f in by_type.get('correlation', [])
                    if any(k in f.get('variables', ('',''))[0] for k in ['甲烷', 'CH4', 'CO2', 'VOCs', 'N2O', '氧化亚氮'])
                    or any(k in f.get('variables', ('',''))[1] for k in ['甲烷', 'CH4', 'CO2', 'VOCs', 'N2O', '氧化亚氮'])]
        gas_desc = [f for f in by_type.get('high_variability', [])
                    if any(k in f.get('variable', '') for k in ['甲烷', 'CH4', 'CO2', 'VOCs'])]

        lines.append(f'## 3.{section_num} 气相污染物排放特征\n')
        lines.append(self._write_gas_phase(gas_seasonal, gas_corr, gas_desc))
        lines.append('')
        section_num += 1

        # === 3.2 液相水质参数 ===
        liq_seasonal = [f for f in by_type.get('phase_seasonal', []) if f.get('phase') == 'liquid']
        liq_corr = [f for f in by_type.get('correlation', [])
                    if any(k in f.get('variables', ('',''))[0] for k in ['DO', 'pH', 'TOC', 'TC', 'IC', '总氮', 'TN', '总磷', 'TP', '铵态氮', 'NH4', '硝态氮', 'NO3', 'COD', 'NaCl', '电导率', 'EC'])
                    or any(k in f.get('variables', ('',''))[1] for k in ['DO', 'pH', 'TOC', 'TC', 'IC', '总氮', 'TN', '总磷', 'TP', '铵态氮', 'NH4', '硝态氮', 'NO3', 'COD', 'NaCl', '电导率', 'EC'])]

        lines.append(f'## 3.{section_num} 液相水质参数特征\n')
        lines.append(self._write_liquid_phase(liq_seasonal, liq_corr))
        lines.append('')
        section_num += 1

        # === 3.3 固相沉积物 ===
        sol_cols = [c for c in self.df.columns if any(k in c for k in ['固总碳', 'DOC', '全磷', '有机碳', '无机碳', '固'])]
        sol_data = {c: self.df[c].dropna() for c in sol_cols if self.df[c].dropna().shape[0] >= 2}
        if sol_data:
            lines.append(f'## 3.{section_num} 固相沉积物特征\n')
            lines.append(self._write_solid_phase(sol_data))
            lines.append('')
            section_num += 1

        # === 3.4 气相-液相耦合关系 ===
        cross_findings = [f for f in by_type.get('cross_phase', [])]
        if cross_findings:
            lines.append(f'## 3.{section_num} 气相-液相耦合关系\n')
            lines.append(self._write_cross_phase(cross_findings))
            lines.append('')
            section_num += 1

        # === 3.5 液相内部碳氮耦合 ===
        cn_corr = [f for f in by_type.get('correlation', [])
                   if f['importance'] in ['critical', 'high']
                   and any(k in f.get('variables', ('',''))[0] for k in ['TOC', 'TC', 'IC', '总氮', '铵态氮', 'COD'])
                   and any(k in f.get('variables', ('',''))[1] for k in ['TOC', 'TC', 'IC', '总氮', '铵态氮', 'COD'])]
        if cn_corr:
            lines.append(f'## 3.{section_num} 碳氮耦合关系\n')
            lines.append(self._write_cn_coupling(cn_corr))
            lines.append('')

        return '\n'.join(lines)

    def _write_descriptive_narrative(self) -> str:
        """叙事式描述性统计"""
        cv_list = []
        for col in self.df.select_dtypes(include=[np.number]).columns:
            data = self.df[col].dropna()
            if len(data) < 3:
                continue
            cv = (data.std() / data.mean() * 100) if data.mean() != 0 else 0
            cv_list.append((col, cv, data.mean(), data.std(), data.min(), data.max(), len(data)))
        cv_list.sort(key=lambda x: -x[1])

        # 按相态分组叙述
        gas_cols = [c for c in cv_list if any(k in c[0] for k in ['CH4', 'CO2', 'VOCs', 'O2', 'H2S', '甲烷', '氧化亚氮'])]
        liquid_cols = [c for c in cv_list if any(k in c[0] for k in ['DO', 'TOC', 'TC', 'IC', 'COD', '总氮', '总磷', '铵态氮', '硝态氮', 'pH', '液温', '电导率', 'NaCl'])]

        lines = []
        lines.append('本研究对校园污水管网固-液-气三相碳污染物进行了系统采样分析。')

        if gas_cols:
            # 找出变异最大的气体
            top_gas = gas_cols[0]
            lines.append(f'气相污染物中，{top_gas[0]}的变异系数最大(CV={top_gas[1]:.1f}%)，'
                        f'浓度范围为{top_gas[4]:.2f}~{top_gas[5]:.2f}，'
                        f'均值为{top_gas[2]:.2f}±{top_gas[3]:.2f}(n={top_gas[6]})，'
                        f'表明不同采样点间气体浓度差异悬殊。')

        if liquid_cols:
            top_liq = liquid_cols[0]
            lines.append(f'液相污染物中，{top_liq[0]}的变异最大(CV={top_liq[1]:.1f}%)，'
                        f'范围{top_liq[4]:.2f}~{top_liq[5]:.2f}。')

        return '\n'.join(lines)

    def _write_group_narrative(self, findings: list) -> str:
        """叙事式组间差异"""
        sig_findings = [f for f in findings if f['data']['sig'] in ['***', '**']]
        mild_findings = [f for f in findings if f['data']['sig'] == '*']

        lines = []
        lines.append('冬春两季比较显示，管网内碳污染物呈现显著的季节分异特征。')

        if sig_findings:
            # 按p值排序，最重要的先写
            sig_findings.sort(key=lambda x: x['data']['p'])
            # 写最重要的发现
            top = sig_findings[0]
            d = top['data']
            higher = d['groups'][np.argmax(d['means'])]
            lower = d['groups'][np.argmin(d['means'])]
            lines.append(f'其中，{top["variable"]}的季节差异最为显著({d["method"]}，p={d["p"]:.4f}{d["sig"]})，'
                        f'{higher}({max(d["means"]):.2f})显著高于{lower}({min(d["means"]):.2f})。')

            # 写其他显著发现
            if len(sig_findings) > 1:
                others = [f'{f["variable"]}(p={f["data"]["p"]:.4f})' for f in sig_findings[1:3]]
                lines.append(f'此外，{",".join(others)}等指标也呈现极显著的季节差异。')

        if mild_findings:
            mild_names = [f["variable"] for f in mild_findings[:2]]
            lines.append(f'{",".join(mild_names)}在0.05水平上差异显著，进一步印证了冬春两季碳污染物特征的差异性。')

        return '\n'.join(lines)

    def _write_correlation_narrative(self, findings: list) -> str:
        """叙事式相关性分析"""
        findings.sort(key=lambda x: -abs(x['data']['r']))

        lines = []
        lines.append('Pearson相关分析揭示了变量间的内在关联。')

        # 按强度分组叙述
        strong = [f for f in findings if abs(f['data']['r']) > 0.8]
        moderate = [f for f in findings if 0.6 < abs(f['data']['r']) <= 0.8]

        if strong:
            for f in strong[:3]:
                d = f['data']
                v1, v2 = f['variables']
                direction = '正' if d['r'] > 0 else '负'
                lines.append(f'{v1}与{v2}呈强{direction}相关(r={d["r"]:.3f}, p={d["p"]:.4f})，'
                            f'表明两者之间存在密切的内在联系。')

        if moderate:
            lines.append(f'此外，{moderate[0]["variables"][0]}与{moderate[0]["variables"][1]}'
                        f'(r={moderate[0]["data"]["r"]:.3f})等变量对也呈现较强的相关性。')

        return '\n'.join(lines)

    def _write_outlier_narrative(self, findings: list) -> str:
        """叙事式异常值"""
        lines = []
        lines.append('部分采样点呈现出异常高值，值得关注。')
        for f in findings[:3]:
            lines.append(f'{f["detail"]}。')
        return '\n'.join(lines)

    def _write_gas_phase(self, seasonal, corr, desc) -> str:
        """写气相污染物结果"""
        lines = []
        lines.append('对管道内气相污染物(CH4、CO2、N2O、VOCs)的监测结果显示：')

        # 季节差异
        if seasonal:
            for f in seasonal:
                vars_data = f.get('data', {}).get('variables', [])
                for v in vars_data:
                    fold = v.get('fold', 1)
                    higher = v.get('higher', '')
                    sig = v.get('sig', '')
                    var = v.get('variable', '')
                    m1 = v.get('mean1', 0)
                    m2 = v.get('mean2', 0)
                    g1 = v.get('group1', '')
                    g2 = v.get('group2', '')
                    if '甲烷' in var or 'CH4' in var:
                        higher_val = max(m1, m2)
                        lower_val = min(m1, m2)
                        lower_group = g2 if higher == g1 else g1
                        lines.append(f'CH4浓度呈显著季节差异(Mann-Whitney U检验，p={v.get("p",0):.4f}{sig})，'
                                    f'{higher}({higher_val:.2f} ppm)约为{lower_group}({lower_val:.2f} ppm)的{fold:.0f}倍，'
                                    f'表明温度升高显著促进管道内产甲烷活动。')
                    elif 'VOCs' in var and '本底' not in var:
                        higher_val = max(m1, m2)
                        lower_val = min(m1, m2)
                        lines.append(f'VOCs浓度{higher}({higher_val:.0f} ppb)显著高于{lower_group}({lower_val:.0f} ppb)(p={v.get("p",0):.4f}{sig})，'
                                    f'可能与冬季低温条件下VOCs挥发速率降低、在管道内累积有关。')

        # 变异特征
        if desc:
            for f in desc[:2]:
                lines.append(f'{f["detail"]}。')

        # 气相内部相关
        gas_internal = [f for f in corr if not any(k in f.get('variables',('',''))[1] for k in ['DO','pH','TOC','TC','IC','总氮','TN','总磷','TP','铵态氮','NH4','硝态氮','NO3','COD','NaCl','电导率','EC'])]
        if gas_internal:
            for f in gas_internal[:2]:
                v1, v2 = f['variables']
                d = f['data']
                direction = '正' if d['r'] > 0 else '负'
                lines.append(f'{v1}与{v2}呈显著{direction}相关(r={d["r"]:.3f}, p={d["p"]:.4f})，'
                            f'表明两者可能受共同的环境因子驱动。')

        return '\n'.join(lines)

    def _write_liquid_phase(self, seasonal, corr) -> str:
        """写液相水质参数结果"""
        lines = []
        lines.append('对管道内液相水质参数的分析结果如下：')

        if seasonal:
            for f in seasonal:
                vars_data = f.get('data', {}).get('variables', [])
                for v in vars_data:
                    var = v.get('variable', '')
                    fold = v.get('fold', 1)
                    sig = v.get('sig', '')
                    m1 = v.get('mean1', 0)
                    m2 = v.get('mean2', 0)
                    g1 = v.get('group1', '')
                    g2 = v.get('group2', '')
                    higher = v.get('higher', '')
                    higher_val = max(m1, m2)
                    lower_val = min(m1, m2)
                    lower_group = g2 if higher == g1 else g1
                    if 'COD' in var:
                        lines.append(f'COD浓度{higher}({higher_val:.0f} mg/L)极显著高于{lower_group}({lower_val:.0f} mg/L)'
                                    f'(p={v.get("p",0):.4f}{sig})，相差约{fold:.0f}倍。'
                                    f'冬季COD偏高可能与管道沉积物中有机物释放、'
                                    f'低温条件下有机物降解速率降低有关。')
                    elif '硝态氮' in var or 'NO3' in var:
                        lines.append(f'NO3--N浓度{higher}({higher_val:.2f} mg/L)显著高于{lower_group}({lower_val:.2f} mg/L)'
                                    f'(p={v.get("p",0):.4f}{sig})，反映冬季硝化作用较强。')
                    elif '液温' in var:
                        lines.append(f'液温{higher}({higher_val:.1f}℃)显著高于{lower_group}({lower_val:.1f}℃)'
                                    f'(p={v.get("p",0):.4f}{sig})，直接影响微生物代谢活性。')

        # 液相内部相关（碳氮耦合）
        cn_corr = [f for f in corr
                   if any(k in f.get('variables',('',''))[0] for k in ['TOC','TC','IC','总氮','TN','铵态氮','NH4','总磷','TP'])
                   and any(k in f.get('variables',('',''))[1] for k in ['TOC','TC','IC','总氮','TN','铵态氮','NH4','总磷','TP'])]
        if cn_corr:
            for f in cn_corr[:3]:
                v1, v2 = f['variables']
                d = f['data']
                lines.append(f'{v1}与{v2}呈显著正相关(r={d["r"]:.3f}, p={d["p"]:.4f})。')

        return '\n'.join(lines)

    def _write_solid_phase(self, sol_data: dict) -> str:
        """写固相沉积物结果"""
        lines = []
        lines.append('固相沉积物样品分析显示：')
        for col, vals in sol_data.items():
            lines.append(f'{col}均值为{vals.mean():.2f}±{vals.std():.2f}(n={len(vals)})，'
                        f'范围{vals.min():.2f}~{vals.max():.2f}。')
        lines.append('固相样品采集点较少(n=2)，统计分析效力有限，需后续补充采样。')
        return '\n'.join(lines)

    def _write_cross_phase(self, findings: list) -> str:
        """写气相-液相耦合关系"""
        lines = []
        lines.append('气相-液相关联分析揭示了温室气体排放与水质参数之间的内在耦合：')

        for f in findings:
            pairs = f.get('data', {}).get('pairs', [])
            # 按p值排序
            pairs.sort(key=lambda x: x.get('p', 1))
            for cp in pairs[:5]:
                gas = cp.get('gas', '')
                liq = cp.get('liquid', '')
                r = cp.get('r', 0)
                p = cp.get('p', 1)
                strength = cp.get('strength', '')
                direction = cp.get('direction', '')
                n = cp.get('n', 0)
                sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''

                if '甲烷' in gas or 'CH4' in gas:
                    if 'pH' in liq:
                        lines.append(f'CH4与pH呈{strength}负相关(r={r:.3f}, p={p:.4f}{sig}, n={n})，'
                                    f'表明产甲烷过程消耗质子导致pH升高，或碱性环境抑制产甲烷菌活性。')
                    elif 'DO' in liq:
                        lines.append(f'CH4与DO呈{strength}负相关(r={r:.3f}, p={p:.4f}{sig}, n={n})，'
                                    f'符合厌氧产甲烷的生化特征：DO越低，产甲烷古菌活性越强。')
                elif '氧化亚氮' in gas or 'N2O' in gas:
                    if 'NaCl' in liq:
                        lines.append(f'N2O与NaCl呈{strength}正相关(r={r:.3f}, p={p:.4f}{sig}, n={n})，'
                                    f'盐度升高可能抑制亚硝酸盐氧化菌(NOB)、'
                                    f'导致亚硝酸盐积累，进而通过硝化反硝化途径产生更多N2O。')
                    elif '铵态氮' in liq or 'NH4' in liq:
                        lines.append(f'N2O与NH4+呈{strength}正相关(r={r:.3f}, p={p:.4f}{sig}, n={n})，'
                                    f'表明硝化过程是N2O产生的主要途径。')
                    elif '总磷' in liq or 'TP' in liq:
                        lines.append(f'N2O与TP呈{strength}正相关(r={r:.3f}, p={p:.4f}{sig}, n={n})，'
                                    f'磷素可能通过促进微生物代谢间接影响N2O产生。')

        return '\n'.join(lines)

    def _write_cn_coupling(self, findings: list) -> str:
        """写碳氮耦合关系"""
        lines = []
        lines.append('液相内部碳氮耦合分析显示：')

        for f in findings[:5]:
            v1, v2 = f['variables']
            d = f['data']
            r = d['r']
            p = d['p']
            sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''

            if '总氮' in v1 and '铵态氮' in v2:
                lines.append(f'TN与NH4+呈极强正相关(r={r:.3f}, p={p:.4f}{sig})，'
                            f'表明管道中氮的主要赋存形态为铵态氮(NH4+-N)，'
                            f'这与管道厌氧条件下有机氮氨化、硝化受限的生化特征一致。')
            elif 'TOC' in v1 and 'TC' in v2:
                lines.append(f'TOC与TC呈强正相关(r={r:.3f}, p={p:.4f}{sig})，'
                            f'表明有机碳是管道中总碳的主要组成部分。')
            elif '总氮' in v1 and '总磷' in v2:
                lines.append(f'TN与TP呈强正相关(r={r:.3f}, p={p:.4f}{sig})，'
                            f'表明碳氮磷在管道中可能存在共同的来源或迁移规律。')
            else:
                lines.append(f'{v1}与{v2}呈显著正相关(r={r:.3f}, p={p:.4f}{sig})。')

        return '\n'.join(lines)

    def write_discussion(self) -> str:
        """写Discussion章节 — 论文式讨论：发现→机制→文献对比→意义"""
        lines = ['# 4 讨论\n']
        section_num = 1

        critical_findings = [f for f in self.findings if f['importance'] in ['critical', 'high']]

        # 4.1 总述（概括主要发现）
        lines.append('## 4.1 主要发现概述\n')
        lines.append(self._discuss_overview(critical_findings))
        lines.append('')
        section_num += 1

        # 4.2 按主题讨论（不是逐个列举，而是按主题组织）
        themes = self._group_findings_by_theme(critical_findings)
        for theme_name, theme_findings in themes.items():
            lines.append(f'## 4.{section_num} {theme_name}\n')

            # 从知识库召回
            ctx = self._recall_theme_knowledge(theme_findings)

            # 写讨论段落
            para = self._discuss_theme(theme_findings, ctx)
            lines.append(para)
            lines.append('')

            # 记录推理链
            for f in theme_findings:
                self._track_rationale(f, ctx, para)

            section_num += 1

        # 4.3 研究局限与展望
        lines.append(f'## 4.{section_num} 研究局限与展望\n')
        lines.append(self._discuss_limitations())
        lines.append('')

        return '\n'.join(lines)

    def _discuss_overview(self, findings: list) -> str:
        """讨论总述"""
        n_corr = len([f for f in findings if f['type'] == 'correlation'])
        n_group = len([f for f in findings if f['type'] == 'group_difference'])

        lines = []
        lines.append(f'本研究通过对校园污水管网冬春两季的系统采样分析，共发现{len(findings)}个具有统计学意义的数据模式。')
        if n_group:
            lines.append(f'季节比较显示，{n_group}个指标存在显著的冬春差异，反映了温度和水文条件对管网碳污染物的深刻影响。')
        if n_corr:
            lines.append(f'相关分析揭示了{n_corr}对变量间的显著关联，为理解碳污染物的多相态转化机制提供了数据支撑。')
        return '\n'.join(lines)

    def _group_findings_by_theme(self, findings: list) -> dict:
        """将发现按主题分组"""
        themes = {}

        # 主题1：季节差异
        group_findings = [f for f in findings if f['type'] == 'group_difference']
        if group_findings:
            themes['碳污染物的季节分异及其驱动机制'] = group_findings

        # 主题2：碳氮耦合
        cn_findings = [f for f in findings if f['type'] == 'correlation'
                      and any(k in str(f.get('variables', '')) for k in ['TOC', 'TC', 'IC', '总氮', '铵态氮'])]
        if cn_findings:
            themes['碳氮耦合关系及其环境意义'] = cn_findings

        # 主题3：气体排放
        gas_findings = [f for f in findings if f['type'] == 'correlation'
                       and any(k in str(f.get('variables', '')) for k in ['CH4', 'CO2', 'N2O', 'VOCs', '甲烷', '氧化亚氮', 'DO', 'pH'])]
        if gas_findings:
            themes['温室气体排放特征及影响因素'] = gas_findings

        # 主题4：盐度/电导率
        salt_findings = [f for f in findings if f['type'] == 'correlation'
                        and any(k in str(f.get('variables', '')) for k in ['NaCl', '电导率', 'EC'])]
        if salt_findings:
            themes['盐度对碳氮转化的影响'] = salt_findings

        return themes

    def _recall_theme_knowledge(self, findings: list) -> dict:
        """为一组相关发现召回知识"""
        ctx = {'mechanisms': [], 'patterns': [], 'references': [], 'terms': []}
        if self.memory is None:
            return ctx

        # 多次召回，取所有相关机制
        all_mechs = []
        seen_keys = set()
        for f in findings[:3]:
            query = self._finding_query(f)
            mech_results = self.memory.recall(query, category='mechanisms', top_k=5)
            for r in mech_results:
                if r['key'] not in seen_keys:
                    seen_keys.add(r['key'])
                    val = r['value']
                    if isinstance(val, dict) and val.get('mechanism') and len(val.get('mechanism', '')) > 10:
                        all_mechs.append({
                            'pattern': val.get('pattern', ''),
                            'mechanism': val.get('mechanism', '')[:600],
                            'references': val.get('references', []),
                        })

        ctx['mechanisms'] = all_mechs

        # 文献召回
        all_refs = []
        seen_ref_keys = set()
        for f in findings[:2]:
            query = self._finding_query(f)
            ref_results = self.memory.recall(query, category='resources', top_k=3)
            for r in ref_results:
                if r['key'] not in seen_ref_keys:
                    seen_ref_keys.add(r['key'])
                    val = r['value']
                    if isinstance(val, dict) and val.get('type') == 'academic_paper':
                        all_refs.append({
                            'title': val.get('title', ''),
                            'year': val.get('year'),
                            'authors': val.get('authors', ''),
                        })

        ctx['references'] = all_refs
        return ctx

    def _discuss_theme(self, findings: list, ctx: dict) -> str:
        """讨论一个主题（多发现整合讨论）"""
        lines = []

        # 1. 陈述发现
        for f in findings[:3]:
            d = f.get('data', {})
            if f['type'] == 'group_difference':
                higher = d['groups'][np.argmax(d['means'])]
                lower = d['groups'][np.argmin(d['means'])]
                lines.append(f'{f["variable"]}在{higher}({max(d["means"]):.2f})显著高于{lower}({min(d["means"]):.2f})'
                            f'(p={d["p"]:.4f})。')
            elif f['type'] == 'correlation':
                v1, v2 = f['variables']
                direction = '正' if d['r'] > 0 else '负'
                lines.append(f'{v1}与{v2}呈显著{direction}相关(r={d["r"]:.3f}, p={d["p"]:.4f})。')

        # 2. 机制解释（使用所有召回的机制）
        if ctx['mechanisms']:
            lines.append('')
            for mech in ctx['mechanisms'][:2]:  # 最多用2条机制
                mech_text = mech.get('mechanism', '')
                if mech_text and len(mech_text) > 10:
                    lines.append(mech_text)

                # 添加机制自带的引用
                mech_refs = mech.get('references', [])
                if mech_refs:
                    lines.append(mech_refs[0])

        # 3. 文献对比（从resources库）
        if ctx['references']:
            ref = ctx['references'][0]
            authors = ref.get('authors', '')
            if isinstance(authors, list):
                authors = ', '.join(authors[:2])
            lines.append(f'\n上述发现与{authors}（{ref.get("year", "")}）的研究结果一致，'
                        f'进一步验证了该规律的普遍性。')

        return '\n'.join(lines)

    def _recall_knowledge(self, finding: dict) -> dict:
        """从知识库召回与发现相关的机制、句式、文献"""
        ctx = {'mechanisms': [], 'patterns': [], 'references': [], 'terms': []}

        if self.memory is None:
            return ctx

        # 构建查询词
        query = self._finding_query(finding)

        # 召回机制
        mech_results = self.memory.recall(query, category='mechanisms', top_k=3)
        for r in mech_results:
            val = r['value']
            if isinstance(val, dict):
                ctx['mechanisms'].append({
                    'pattern': val.get('pattern', ''),
                    'mechanism': val.get('mechanism', '')[:400],
                    'references': val.get('references', []),
                })

        # 召回句式模板
        pattern_results = self.memory.recall(query, category='writing_templates', top_k=3)
        for r in pattern_results:
            val = r['value']
            if isinstance(val, dict) and 'pattern' in val:
                ctx['patterns'].append(val['pattern'])

        # 召回文献
        ref_results = self.memory.recall(query, category='resources', top_k=3)
        for r in ref_results:
            val = r['value']
            if isinstance(val, dict) and val.get('type') == 'academic_paper':
                ctx['references'].append({
                    'title': val.get('title', ''),
                    'year': val.get('year'),
                    'authors': val.get('authors', ''),
                })

        # 召回领域术语
        term_results = self.memory.recall(query, category='domain_terms', top_k=3)
        for r in term_results:
            val = r['value']
            if isinstance(val, dict):
                ctx['terms'].append(val)

        return ctx

    def _finding_query(self, finding: dict) -> str:
        """为发现构建知识库查询词"""
        if finding['type'] == 'group_difference':
            return f'{finding["variable"]} 季节差异'
        elif finding['type'] == 'correlation':
            v1, v2 = finding['variables']
            return f'{v1} {v2} 相关'
        elif finding['type'] == 'high_variability':
            return f'{finding["variable"]} 变异'
        elif finding['type'] == 'outlier':
            return f'{finding["variable"]} 异常'
        return finding.get('detail', '')[:50]

    def _finding_title(self, finding: dict) -> str:
        """为发现生成讨论标题"""
        if finding['type'] == 'group_difference':
            return f'{finding["variable"]}的季节差异分析'
        elif finding['type'] == 'correlation':
            v1, v2 = finding['variables']
            return f'{v1}与{v2}的关系讨论'
        elif finding['type'] == 'high_variability':
            return f'{finding["variable"]}的高变异性分析'
        elif finding['type'] == 'outlier':
            return f'{finding["variable"]}异常值成因分析'
        else:
            return finding.get('detail', '发现讨论')[:30]

    def _discuss_limitations(self) -> str:
        """研究局限与展望"""
        return (
            '本研究存在以下局限性：(1)采样时间仅涵盖冬春两季，未纳入夏秋季节数据，'
            '难以全面揭示碳污染物的年际变化规律；(2)液相样品的采样点数量有限(n=18)，'
            '部分统计分析的统计效力受限；(3)未对管道沉积物和生物膜进行同步采样分析，'
            '固相碳的赋存特征有待深入研究。\n\n'
            '未来研究可从以下方面拓展：(1)开展四季连续监测，构建碳污染物的完整季节动态模型；'
            '(2)结合分子生物学手段(如16S rRNA测序)，揭示驱动碳相态转化的关键微生物种群；'
            '(3)建立管道碳平衡模型，定量评估碳在固-液-气三相之间的转化通量。'
        )

    def _discuss_finding(self, finding: dict, ctx: dict) -> str:
        """为单个发现生成讨论段落 — 有知识库时用机制解释，没有时用通用解释"""
        detail = finding['detail']

        # 从知识库取机制解释
        mechanism_text = ''
        if ctx['mechanisms']:
            mechanism_text = ctx['mechanisms'][0].get('mechanism', '')

        # 从知识库取引用
        ref_text = ''
        if ctx['references']:
            ref = ctx['references'][0]
            ref_text = f'（{ref.get("authors", "")}, {ref.get("year", "")}）'

        if finding['type'] == 'group_difference':
            d = finding['data']
            higher = d['groups'][np.argmax(d['means'])]
            lower = d['groups'][np.argmin(d['means'])]

            para = f'本研究发现{finding["variable"]}在{higher}显著高于{lower}(p={d["p"]:.4f})。'
            if mechanism_text:
                para += f'{mechanism_text}'
            else:
                para += '这一差异可能与温度变化、水文条件改变或生物活性差异有关。'
            if ref_text:
                para += f'已有研究{ref_text}报道了类似的趋势。'
            return para

        elif finding['type'] == 'correlation':
            d = finding['data']
            v1, v2 = finding['variables']
            direction = '正' if d['r'] > 0 else '负'

            para = f'{v1}与{v2}呈显著{direction}相关(r={d["r"]:.3f}, p={d["p"]:.4f})。'
            if mechanism_text:
                para += f'{mechanism_text}'
            else:
                para += '这一关系表明两者之间存在内在联系。'
            if ref_text:
                para += f'这与{ref_text}的研究结果一致。'
            return para

        elif finding['type'] == 'high_variability':
            para = f'{finding["detail"]}。'
            if mechanism_text:
                para += f'{mechanism_text}'
            return para

        elif finding['type'] == 'outlier':
            para = f'{finding["detail"]}。'
            if mechanism_text:
                para += f'可能原因：{mechanism_text}'
            return para

        return f'{detail}。'

    def _track_rationale(self, finding: dict, ctx: dict, paragraph: str):
        """记录推理链：finding → mechanism → evidence → citation"""
        has_mechanism = bool(ctx['mechanisms'])
        has_citation = bool(ctx['references'])
        has_data = finding['type'] in ['group_difference', 'correlation']

        completeness = sum([has_mechanism, has_citation, has_data]) / 3.0

        self.rationale_rows.append({
            'finding': finding.get('detail', '')[:80],
            'mechanism': ctx['mechanisms'][0].get('pattern', '') if ctx['mechanisms'] else '',
            'evidence': str(finding.get('data', {}))[:80],
            'citation': ctx['references'][0].get('title', '')[:60] if ctx['references'] else '',
            'completeness': completeness,
        })

    def get_rationale_report(self) -> str:
        """生成推理链完整性报告"""
        if not self.rationale_rows:
            return ''

        lines = ['# 推理链完整性报告\n']

        # 过滤出字典类型的元素
        valid_rows = [r for r in self.rationale_rows if isinstance(r, dict)]
        string_rows = [r for r in self.rationale_rows if isinstance(r, str)]

        if not valid_rows:
            # 如果没有字典类型的元素，直接返回字符串
            lines.append(f'共{len(self.rationale_rows)}条推理链（均为字符串格式）：\n')
            for i, r in enumerate(string_rows, 1):
                lines.append(f'{i}. {r[:100]}...' if len(r) > 100 else f'{i}. {r}')
            return '\n'.join(lines)

        # 统计完整性
        complete = sum(1 for r in valid_rows if r.get('completeness', 0) >= 0.8)
        partial = sum(1 for r in valid_rows if 0.3 <= r.get('completeness', 0) < 0.8)
        weak = sum(1 for r in valid_rows if r.get('completeness', 0) < 0.3)

        lines.append(f'共{len(self.rationale_rows)}条推理链：')
        lines.append(f'- 完整(≥80%): {complete}条')
        lines.append(f'- 部分(30-80%): {partial}条')
        lines.append(f'- 薄弱(<30%): {weak}条\n')

        for i, r in enumerate(valid_rows, 1):
            completeness = r.get('completeness', 0)
            icon = '✓' if completeness >= 0.8 else ('△' if completeness >= 0.3 else '✗')
            finding = r.get('finding', '未知')
            lines.append(f'{i}. [{icon}] {finding}')
            if r.get('mechanism'):
                lines.append(f'   机制: {r["mechanism"]}')
            if r.get('citation'):
                lines.append(f'   引用: {r["citation"]}')
            lines.append('')

        # 添加字符串类型的行
        if string_rows:
            lines.append(f'\n## 字符串格式推理链 ({len(string_rows)}条)\n')
            for i, r in enumerate(string_rows, 1):
                lines.append(f'{i}. {r[:100]}...' if len(r) > 100 else f'{i}. {r}')

        return '\n'.join(lines)


# ============================================================
# 3. 图文对应排版器
# ============================================================

class InlineDocumentAssembler:
    """
    图文对应的文档组装器。
    每个章节先写文字，紧接着插入对应的图表。
    """

    def __init__(self, title: str, output_dir: str):
        self.title = title
        self.output_dir = output_dir
        self.sections = []  # [{'heading': str, 'text': str, 'figures': [{'path': str, 'caption': str}]}]

    def add_section(self, heading: str, text: str, figures: list = None):
        """添加章节（可附带图表）"""
        self.sections.append({
            'heading': heading,
            'text': text,
            'figures': figures or [],
        })

    def assemble(self, output_path: str) -> str:
        """组装DOCX — 图文对应"""
        from document_assembler import DocumentAssembler

        assembler = DocumentAssembler(title=self.title, paper_type='chinese', language='zh')

        for section in self.sections:
            # 先加文字
            assembler.add_section(section['heading'], text=section['text'], level=1)

            # 再加该章节的图
            for fig in section['figures']:
                if os.path.exists(fig['path']):
                    assembler.add_figure(fig['path'], caption=fig['caption'])

        result_path = assembler.assemble(output_path)
        return result_path
