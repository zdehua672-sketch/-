# -*- coding: utf-8 -*-
"""
数据全貌扫描器 - 在任何图表生成之前运行
自动枚举所有列、统计摘要、识别配对列/分组列
"""
import pandas as pd
import numpy as np
from scipy import stats
import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def profile_excel(path: str) -> dict:
    """
    扫描Excel文件的所有sheet，输出完整数据清单。

    Returns
    -------
    dict: {
        'sheets': {sheet_name: column_profile_list},
        'paired_columns': [(col_a, col_b, reason), ...],
        'numeric_columns': [(sheet, col, stats), ...],
        'categorical_columns': [(sheet, col, values), ...],
        'seasons': [sheet_name, ...],
        'recommendations': [str, ...],
    }
    """
    xls = pd.ExcelFile(path)
    result = {
        'file': path,
        'sheets': {},
        'paired_columns': [],
        'numeric_columns': [],
        'categorical_columns': [],
        'seasons': xls.sheet_names,
        'recommendations': [],
    }

    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        columns = []

        for col in df.columns:
            series = df[col]
            profile = {
                'name': col,
                'dtype': str(series.dtype),
                'non_null': int(series.notna().sum()),
                'null_pct': f'{series.isna().mean():.0%}',
                'n_unique': int(series.nunique()),
            }

            # 尝试转数值
            numeric = pd.to_numeric(series, errors='coerce')
            if numeric.notna().sum() >= 2:
                profile['type'] = 'numeric'
                profile['mean'] = round(numeric.mean(), 2)
                profile['median'] = round(numeric.median(), 2)
                profile['min'] = round(numeric.min(), 2)
                profile['max'] = round(numeric.max(), 2)
                profile['std'] = round(numeric.std(), 2)
                if numeric.mean() != 0:
                    profile['cv'] = round(numeric.std() / abs(numeric.mean()), 2)
                else:
                    profile['cv'] = None
                # 标记极端偏态
                if numeric.skew() > 3:
                    profile['skew_warning'] = 'extreme_right_skew'
                result['numeric_columns'].append((sheet_name, col, profile))
            elif series.dtype == 'object' or series.dtype == 'string':
                vals = series.dropna().unique()
                profile['type'] = 'categorical'
                profile['values'] = list(vals[:10])  # 最多显示10个
                if len(vals) <= 10:
                    profile['all_values'] = dict(series.value_counts())
                result['categorical_columns'].append((sheet_name, col, profile))
            else:
                profile['type'] = 'other'

            columns.append(profile)

        result['sheets'][sheet_name] = columns

    # 识别配对列（如 VOCs / VOCs本底值）
    for sheet_name, columns in result['sheets'].items():
        col_names = [c['name'] for c in columns]
        for i, name in enumerate(col_names):
            # 检查是否有"本底值"配对
            if '本底值' not in name:
                bg_variants = [name + '本底值', name.replace(')', '') + '本底值)',
                              name + '_本底', '本底_' + name]
                for bg in bg_variants:
                    if bg in col_names:
                        result['paired_columns'].append((sheet_name, name, bg, '实测值-本底值配对'))
                        break
                # 检查ppm/ppb配对模式
                if 'ppm' in name or 'ppb' in name:
                    base = name.split('(')[0].split('（')[0].strip()
                    for other in col_names:
                        if other != name and base in other and '本底' in other:
                            result['paired_columns'].append((sheet_name, name, other, '浓度-本底配对'))

    # 识别采样点分组
    id_cols = []
    for sheet_name, columns in result['sheets'].items():
        for c in columns:
            if any(k in c['name'] for k in ['采样点', '检查井', '编号', 'ID']):
                id_cols.append((sheet_name, c['name']))
    result['id_columns'] = id_cols

    # 生成推荐
    seen_numeric = set()
    for sheet, col, profile in result['numeric_columns']:
        if col not in seen_numeric and '本底' not in col:
            seen_numeric.add(col)
    result['recommendations'].append(
        f'共发现 {len(seen_numeric)} 个独立数值指标: {", ".join(sorted(seen_numeric))}'
    )
    if result['paired_columns']:
        result['recommendations'].append(
            f'发现 {len(result["paired_columns"])} 对本底值配对，建议做净排放分析(实测-本底)'
        )
    if len(result['seasons']) > 1:
        result['recommendations'].append(
            f'发现 {len(result["seasons"])} 个季节sheet: {", ".join(result["seasons"])}，建议做季节对比图'
        )

    return result


def print_profile(profile: dict):
    """打印数据清单"""
    print('=' * 60)
    print(f'数据文件: {profile["file"]}')
    print(f'Sheet数: {len(profile["sheets"])} ({", ".join(profile["seasons"])})')
    print('=' * 60)

    for sheet_name, columns in profile['sheets'].items():
        print(f'\n--- Sheet: {sheet_name} ({len(columns)}列, {columns[0].get("non_null","?")}行) ---')
        print(f'{"列名":<30} {"类型":<10} {"非空":<6} {"空%":<6} {"均值":<12} {"范围":<20} {"CV":<6}')
        print('-' * 95)
        for c in columns:
            name = c['name'][:28]
            ctype = c['type']
            non_null = str(c['non_null'])
            null_pct = c['null_pct']
            if ctype == 'numeric':
                mean = f'{c["mean"]:.2f}'
                rng = f'[{c["min"]:.1f}, {c["max"]:.1f}]'
                cv = str(c.get('cv', '-'))
                if c.get('skew_warning'):
                    name += ' *偏态'
            else:
                mean = '-'
                rng = f'{c["n_unique"]}类'
                cv = '-'
            print(f'{name:<30} {ctype:<10} {non_null:<6} {null_pct:<6} {mean:<12} {rng:<20} {cv:<6}')

    if profile['paired_columns']:
        print('\n--- 本底值配对列 ---')
        for sheet, a, b, reason in profile['paired_columns']:
            print(f'  {sheet}: {a} <-> {b} ({reason})')

    if profile['id_columns']:
        print('\n--- 采样点ID列 ---')
        for sheet, col in profile['id_columns']:
            print(f'  {sheet}: {col}')

    print('\n--- 推荐 ---')
    for i, rec in enumerate(profile['recommendations'], 1):
        print(f'  {i}. {rec}')

    print()


# ============================================================================
# deep_profile - 深度数据理解（在 profile_excel 基础上扩展）
# ============================================================================

def _detect_outliers(series):
    """异常值检测：IQR + Z-score 双方法"""
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric) < 4:
        return {'method': 'none', 'count': 0, 'ratio': 0.0, 'direction': 'none'}

    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    iqr_outliers = numeric[(numeric < lower) | (numeric > upper)]

    mean = numeric.mean()
    std = numeric.std()
    z_outliers = pd.Series([], dtype=float)
    if std > 0:
        z_scores = (numeric - mean).abs() / std
        z_outliers = numeric[z_scores > 3]

    # 取两种方法的并集
    all_outliers = set(iqr_outliers.index) | set(z_outliers.index)
    n_outliers = len(all_outliers)

    if n_outliers == 0:
        direction = 'none'
    else:
        outlier_vals = numeric.loc[list(all_outliers)]
        n_high = (outlier_vals > upper).sum() if iqr > 0 else 0
        n_low = (outlier_vals < lower).sum() if iqr > 0 else 0
        if n_high > 0 and n_low > 0:
            direction = '双向'
        elif n_high > 0:
            direction = '偏高'
        else:
            direction = '偏低'

    return {
        'method': 'IQR+Z',
        'count': n_outliers,
        'ratio': round(n_outliers / len(numeric), 3),
        'direction': direction,
        'iqr_bounds': (round(lower, 4), round(upper, 4)),
    }


def _analyze_missing_pattern(df, col):
    """缺失模式分析"""
    series = df[col]
    n_total = len(series)
    n_missing = series.isna().sum()
    ratio = n_missing / n_total if n_total > 0 else 0

    if n_missing == 0:
        return {'pattern': 'complete', 'ratio': 0.0, 'suggestion': '无需处理'}

    # 检查是否按组缺失（检查其他分类列）
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    pattern = 'random'
    suggestion = '可插值或删除'

    for cat_col in cat_cols:
        if cat_col == col:
            continue
        groups = df.groupby(cat_col)[col]
        missing_by_group = groups.apply(lambda x: x.isna().mean())
        if missing_by_group.std() > 0.3:
            # 某个组缺失率远高于其他组
            worst_group = missing_by_group.idxmax()
            worst_rate = missing_by_group.max()
            pattern = f'按{cat_col}缺失({worst_group}: {worst_rate:.0%})'
            suggestion = f'检查{cat_col}={worst_group}的采样流程'
            break

    if ratio > 0.5:
        pattern = '大面积缺失'
        suggestion = '考虑删除该列'

    return {'pattern': pattern, 'ratio': round(ratio, 3), 'suggestion': suggestion}


def _classify_distribution(series):
    """分布形态识别"""
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric) < 5:
        return {'shape': '数据不足', 'skewness': None, 'kurtosis': None, 'normality': None, 'suggested_test': '非参数'}

    skew = numeric.skew()
    kurt = numeric.kurtosis()

    # Shapiro-Wilk 正态性检验
    if len(numeric) >= 3:
        try:
            _, p_normal = stats.shapiro(numeric)
        except Exception:
            p_normal = 0.0
    else:
        p_normal = 0.0

    is_normal = p_normal > 0.05

    # 判断分布形态
    if is_normal:
        shape = '正态'
    elif abs(skew) < 0.5:
        shape = '近似正态'
    elif skew > 1:
        shape = '严重右偏'
    elif skew > 0.5:
        shape = '右偏'
    elif skew < -1:
        shape = '严重左偏'
    elif skew < -0.5:
        shape = '左偏'
    else:
        shape = '近似对称'

    # 双峰检测（Hartigan's dip test 简化版：看峰度）
    if kurt < -1:
        shape = '平坦/可能双峰'

    suggested_test = '参数检验' if is_normal else '非参数检验'

    return {
        'shape': shape,
        'skewness': round(skew, 3),
        'kurtosis': round(kurt, 3),
        'normality_p': round(p_normal, 4),
        'is_normal': is_normal,
        'suggested_test': suggested_test,
    }


def _scan_variable_relations(df, numeric_cols, domain_pairs=None):
    """变量关系预扫描"""
    if domain_pairs is None:
        # 环境工程领域常见因果假设
        domain_pairs = [
            ('TOC（mg/L)', 'CH4平均值', '有机碳→甲烷'),
            ('TOC（mg/L)', 'CO2', '有机碳→二氧化碳'),
            ('DO(mg/L)', 'CH4平均值', '溶解氧抑制甲烷'),
            ('COD（mg/L)', 'CH4平均值', 'COD→甲烷'),
            ('TOC（mg/L)', '总氮（mg/L)', '碳氮耦合'),
            ('铵态氮（mg/L)', 'CH4平均值', '氮转化→甲烷'),
            ('固总碳（g/kg)', '有机碳（g/kg)', '固相碳组分'),
            ('pH', 'CH4平均值', 'pH→甲烷'),
            ('液温', 'CH4平均值', '温度→甲烷'),
        ]

    results = {'strong_pairs': [], 'domain_pairs': [], 'correlation_matrix': None}

    # 两两相关性扫描
    valid_cols = [c for c in numeric_cols if c in df.columns]
    if len(valid_cols) < 2:
        return results

    corr_matrix = df[valid_cols].corr(method='spearman')
    results['correlation_matrix'] = corr_matrix

    # 找强相关对
    for i in range(len(valid_cols)):
        for j in range(i + 1, len(valid_cols)):
            r = corr_matrix.iloc[i, j]
            if abs(r) > 0.6:
                # 计算 p 值
                try:
                    _, p = stats.spearmanr(df[valid_cols[i]].dropna(), df[valid_cols[j]].dropna())
                except Exception:
                    p = 1.0
                if p < 0.05:
                    results['strong_pairs'].append({
                        'var1': valid_cols[i],
                        'var2': valid_cols[j],
                        'r': round(r, 3),
                        'p': round(p, 4),
                        'direction': '正相关' if r > 0 else '负相关',
                    })

    # 领域因果对检查
    available_cols = set(valid_cols)
    for x, y, desc in domain_pairs:
        if x in available_cols and y in available_cols:
            try:
                r, p = stats.spearmanr(
                    df[x].dropna().values,
                    df[y].dropna().values[:len(df[x].dropna())]
                )
            except Exception:
                r, p = 0, 1
            results['domain_pairs'].append({
                'var1': x, 'var2': y, 'description': desc,
                'r': round(r, 3), 'p': round(p, 4),
                'significant': p < 0.05,
            })

    return results


def _discover_spatiotemporal_structure(df, numeric_cols, group_col='季节', spatial_col=None):
    """空间/时间结构发现"""
    results = {'seasonal_diff': [], 'spatial_trend': []}

    # 季节差异检测
    if group_col and group_col in df.columns:
        groups = df[group_col].unique()
        if len(groups) >= 2:
            for col in numeric_cols:
                if col not in df.columns:
                    continue
                g1_data = df[df[group_col] == groups[0]][col].dropna()
                g2_data = df[df[group_col] == groups[1]][col].dropna()
                if len(g1_data) >= 3 and len(g2_data) >= 3:
                    try:
                        _, p = stats.mannwhitneyu(g1_data, g2_data, alternative='two-sided')
                    except Exception:
                        p = 1.0
                    if p < 0.05:
                        results['seasonal_diff'].append({
                            'variable': col,
                            'p': round(p, 4),
                            'group1_mean': round(g1_data.mean(), 3),
                            'group2_mean': round(g2_data.mean(), 3),
                            'higher': str(groups[0]) if g1_data.mean() > g2_data.mean() else str(groups[1]),
                        })

    # 空间梯度检测（如果有空间列）
    spatial_candidates = [c for c in df.columns if any(k in str(c) for k in
                          ['采样点', '位置', 'distance', '管口', '中段', '末端', '编号'])]
    if spatial_col:
        spatial_candidates = [spatial_col] + spatial_candidates

    for sp_col in spatial_candidates[:1]:  # 只取第一个空间列
        if sp_col not in df.columns:
            continue
        for col in numeric_cols:
            if col not in df.columns:
                continue
            try:
                valid = df[[sp_col, col]].dropna()
                if len(valid) >= 5:
                    r, p = stats.spearmanr(valid[sp_col], valid[col])
                    if abs(r) > 0.5 and p < 0.05:
                        results['spatial_trend'].append({
                            'variable': col,
                            'spatial_col': sp_col,
                            'r': round(r, 3),
                            'p': round(p, 4),
                            'direction': '递增' if r > 0 else '递减',
                        })
            except Exception:
                pass

    return results


def _score_variable_quality(series, dist_result, outlier_result, missing_result):
    """数据质量综合评分 (0-100)"""
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric) < 3:
        return 0

    # 完整性 (0-30分)
    completeness = (1 - missing_result['ratio']) * 30

    # 稳定性 (0-25分) - 异常值越少越好
    outlier_penalty = min(outlier_result['ratio'] * 50, 25)
    stability = 25 - outlier_penalty

    # 信息量 (0-25分) - CV适中最好（太低没信息，太高不可靠）
    cv = numeric.std() / abs(numeric.mean()) if numeric.mean() != 0 else 0
    if cv < 0.05:
        info_score = 5  # 几乎无变异
    elif cv < 0.3:
        info_score = 25  # 理想范围
    elif cv < 1.0:
        info_score = 20  # 中等变异
    elif cv < 3.0:
        info_score = 10  # 高变异
    else:
        info_score = 5   # 极端变异

    # 可分析性 (0-20分) - 分布是否适合统计检验
    if dist_result['is_normal']:
        analysis_score = 20
    elif dist_result['shape'] in ['右偏', '左偏', '近似正态', '近似对称']:
        analysis_score = 15
    else:
        analysis_score = 8

    total = round(completeness + stability + info_score + analysis_score)
    return min(100, max(0, total))


def deep_profile(path: str, group_col: str = '季节') -> dict:
    """
    深度数据理解：在 profile_excel 基础上扩展6个维度。

    Parameters
    ----------
    path : str, Excel文件路径
    group_col : str, 分组列名（默认'季节'）

    Returns
    -------
    dict: 在 profile_excel 结果基础上追加:
        - outliers: {col: outlier_info}
        - missing_patterns: {col: missing_info}
        - distributions: {col: dist_info}
        - variable_relations: {strong_pairs, domain_pairs}
        - spatiotemporal: {seasonal_diff, spatial_trend}
        - quality_scores: [(col, score), ...]
        - deep_recommendations: [str, ...]
    """
    from scipy import stats as _stats

    # 先调用原 profile_excel 获取基础信息
    base = profile_excel(path)

    xls = pd.ExcelFile(path)
    all_dfs = {}
    for sheet_name in xls.sheet_names:
        all_dfs[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)

    # 合并所有 sheet 的数据用于整体分析
    df_all = pd.concat(all_dfs.values(), ignore_index=True) if len(all_dfs) > 1 else list(all_dfs.values())[0]

    # 收集所有数值列
    all_numeric = []
    for sheet, col, profile in base['numeric_columns']:
        if col not in all_numeric and '本底' not in col:
            all_numeric.append(col)

    result = dict(base)  # 保留基础结果

    # --- 1. 异常值检测 ---
    outliers = {}
    for col in all_numeric:
        if col in df_all.columns:
            outliers[col] = _detect_outliers(df_all[col])
    result['outliers'] = outliers

    # --- 2. 缺失模式分析 ---
    missing_patterns = {}
    for col in df_all.columns:
        info = _analyze_missing_pattern(df_all, col)
        if info['ratio'] > 0:
            missing_patterns[col] = info
    result['missing_patterns'] = missing_patterns

    # --- 3. 分布形态识别 ---
    distributions = {}
    for col in all_numeric:
        if col in df_all.columns:
            distributions[col] = _classify_distribution(df_all[col])
    result['distributions'] = distributions

    # --- 4. 变量关系预扫描 ---
    result['variable_relations'] = _scan_variable_relations(df_all, all_numeric)

    # --- 5. 空间/时间结构发现 ---
    result['spatiotemporal'] = _discover_spatiotemporal_structure(df_all, all_numeric, group_col)

    # --- 6. 数据质量综合评分 ---
    quality_scores = []
    for col in all_numeric:
        if col in df_all.columns:
            dist = distributions.get(col, {'is_normal': False, 'shape': '未知'})
            outlier = outliers.get(col, {'ratio': 0})
            missing = missing_patterns.get(col, {'ratio': 0})
            score = _score_variable_quality(df_all[col], dist, outlier, missing)
            quality_scores.append((col, score))
    quality_scores.sort(key=lambda x: x[1], reverse=True)
    result['quality_scores'] = quality_scores

    # --- 7. 深度推荐 ---
    deep_recs = []

    # 基于异常值
    high_outlier_cols = [col for col, info in outliers.items() if info['ratio'] > 0.1]
    if high_outlier_cols:
        deep_recs.append(f'异常值警告: {", ".join(high_outlier_cols)} 异常值比例>10%，建议检查数据质量或使用稳健统计方法')

    # 基于分布
    non_normal = [col for col, info in distributions.items() if not info.get('is_normal', True)]
    if non_normal:
        deep_recs.append(f'{len(non_normal)}个变量非正态分布，组间比较应使用Mann-Whitney U而非t检验')

    # 基于变量关系
    rels = result['variable_relations']
    if rels['strong_pairs']:
        pairs_str = ', '.join([f"{p['var1']}↔{p['var2']}(r={p['r']})" for p in rels['strong_pairs'][:3]])
        deep_recs.append(f'发现强相关变量对: {pairs_str}，建议做回归分析或共线性检查')

    # 基于领域因果
    sig_domain = [p for p in rels.get('domain_pairs', []) if p['significant']]
    if sig_domain:
        pairs_str = ', '.join([f"{p['description']}(r={p['r']})" for p in sig_domain[:3]])
        deep_recs.append(f'领域假设验证通过: {pairs_str}，建议在Discussion中讨论机制')

    # 基于时空结构
    st = result['spatiotemporal']
    if st['seasonal_diff']:
        vars_str = ', '.join([d['variable'] for d in st['seasonal_diff'][:5]])
        deep_recs.append(f'季节差异显著变量: {vars_str}，建议做季节分组对比图')

    if st['spatial_trend']:
        vars_str = ', '.join([f"{d['variable']}({d['direction']})" for d in st['spatial_trend'][:5]])
        deep_recs.append(f'空间梯度变量: {vars_str}，建议做沿程变化折线图')

    # 基于质量评分
    low_quality = [col for col, score in quality_scores if score < 50]
    if low_quality:
        deep_recs.append(f'低质量变量(score<50): {", ".join(low_quality)}，建议谨慎使用或做数据清洗')

    result['deep_recommendations'] = deep_recs

    return result


def print_deep_profile(profile: dict):
    """打印深度分析结果"""
    # 先打印基础信息
    print_profile(profile)

    print('=' * 60)
    print('深度数据分析')
    print('=' * 60)

    # 异常值
    outliers = profile.get('outliers', {})
    if outliers:
        print('\n--- 异常值检测 ---')
        print(f'{"变量":<25} {"数量":<6} {"比例":<8} {"方向":<8} {"IQR边界":<20}')
        print('-' * 70)
        for col, info in outliers.items():
            if info['count'] > 0:
                bounds = f"[{info.get('iqr_bounds', (0,0))[0]:.2f}, {info.get('iqr_bounds', (0,0))[1]:.2f}]"
                print(f'{col[:24]:<25} {info["count"]:<6} {info["ratio"]:.1%}{"":<3} {info["direction"]:<8} {bounds:<20}')

    # 缺失模式
    missing = profile.get('missing_patterns', {})
    if missing:
        print('\n--- 缺失模式分析 ---')
        for col, info in missing.items():
            print(f'  {col}: {info["pattern"]} (缺失{info["ratio"]:.1%}) → {info["suggestion"]}')

    # 分布形态
    dists = profile.get('distributions', {})
    if dists:
        print('\n--- 分布形态 ---')
        print(f'{"变量":<25} {"形态":<10} {"偏度":<8} {"峰度":<8} {"正态p":<8} {"建议":<10}')
        print('-' * 72)
        for col, info in dists.items():
            print(f'{col[:24]:<25} {info["shape"]:<10} '
                  f'{str(info["skewness"]):<8} {str(info["kurtosis"]):<8} '
                  f'{str(info["normality_p"]):<8} {info["suggested_test"]:<10}')

    # 变量关系
    rels = profile.get('variable_relations', {})
    if rels.get('strong_pairs'):
        print('\n--- 强相关变量对 (|r|>0.6, p<0.05) ---')
        for p in rels['strong_pairs']:
            print(f'  {p["var1"]} ↔ {p["var2"]}: r={p["r"]}, p={p["p"]} ({p["direction"]})')

    if rels.get('domain_pairs'):
        print('\n--- 领域假设验证 ---')
        for p in rels['domain_pairs']:
            sig = '✓' if p['significant'] else '✗'
            print(f'  {sig} {p["description"]}: {p["var1"]}→{p["var2"]}, r={p["r"]}, p={p["p"]}')

    # 时空结构
    st = profile.get('spatiotemporal', {})
    if st.get('seasonal_diff'):
        print('\n--- 季节差异显著变量 ---')
        for d in st['seasonal_diff']:
            print(f'  {d["variable"]}: p={d["p"]}, 更高={d["higher"]} '
                  f'(冬={d["group1_mean"]}, 春={d["group2_mean"]})')

    if st.get('spatial_trend'):
        print('\n--- 空间梯度变量 ---')
        for d in st['spatial_trend']:
            print(f'  {d["variable"]}: {d["direction"]} (r={d["r"]}, p={d["p"]})')

    # 质量评分
    scores = profile.get('quality_scores', [])
    if scores:
        print('\n--- 数据质量评分 (0-100) ---')
        for col, score in scores:
            bar = '█' * (score // 5) + '░' * (20 - score // 5)
            print(f'  {col[:24]:<25} {bar} {score}')

    # 深度推荐
    recs = profile.get('deep_recommendations', [])
    if recs:
        print('\n--- 深度推荐 ---')
        for i, rec in enumerate(recs, 1):
            print(f'  {i}. {rec}')

    print()


if __name__ == '__main__':
    # 默认扫描桌面冬春数据
    default_path = r'C:\Users\Administrator\Desktop\冬春数据.xlsx'
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = default_path

    if not os.path.exists(path):
        print(f'File not found: {path}')
        sys.exit(1)

    profile = profile_excel(path)
    print_profile(profile)

    # 深度分析
    deep = deep_profile(path)
    print_deep_profile(deep)
