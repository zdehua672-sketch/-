# -*- coding: utf-8 -*-
"""
数据全貌扫描器 - 在任何图表生成之前运行
自动枚举所有列、统计摘要、识别配对列/分组列
"""
import pandas as pd
import numpy as np
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
