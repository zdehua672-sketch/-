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
                if self.df[col].dropna().shape[0] >= 3:
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
        self._explore_anomalies()
        self._explore_extremes()

        # 按重要性排序
        self.findings.sort(key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x['importance'], 4))

        print(f"\n共发现 {len(self.findings)} 个值得关注的模式")
        return self.findings

    def _explore_distributions(self):
        """探索每个变量的分布特征"""
        print("\n[探索1] 分布特征...")
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
        """探索变量间的相关性"""
        print("\n[探索3] 相关性发现...")
        if len(self.numeric_cols) < 2:
            return

        # 只用有足够数据的列
        valid_cols = [c for c in self.numeric_cols if self.df[c].dropna().shape[0] >= 8]
        if len(valid_cols) < 2:
            return

        df_clean = self.df[valid_cols].dropna()
        if len(df_clean) < 5:
            # 尝试逐对计算
            for i, c1 in enumerate(valid_cols):
                for c2 in valid_cols[i+1:]:
                    pair = self.df[[c1, c2]].dropna()
                    if len(pair) < 5:
                        continue
                    # 跳过常量列
                    if pair[c1].std() == 0 or pair[c2].std() == 0:
                        continue
                    r, p = stats.pearsonr(pair[c1], pair[c2])
                    if abs(r) > 0.5 and p < 0.05:
                        direction = '正' if r > 0 else '负'
                        self.findings.append({
                            'type': 'correlation',
                            'variables': (c1, c2),
                            'importance': 'critical' if abs(r) > 0.8 else 'high',
                            'detail': f'{c1}与{c2}呈显著{direction}相关(r={r:.3f}, p={p:.4f}, n={len(pair)})',
                            'data': {'r': r, 'p': p, 'n': len(pair)},
                        })
                        print(f"  [!!] {c1} vs {c2}: r={r:.3f}, p={p:.4f}")
            return

        # 跳过常量列
        valid_cols = [c for c in valid_cols if df_clean[c].std() > 0]
        if len(valid_cols) < 2:
            return

        corr = df_clean[valid_cols].corr()
        for i, c1 in enumerate(valid_cols):
            for c2 in valid_cols[i+1:]:
                r = corr.loc[c1, c2]
                if pd.isna(r):
                    continue
                # 计算p值
                n = len(df_clean)
                if n < 3:
                    continue
                t_stat = r * np.sqrt((n-2)/(1-r**2)) if abs(r) < 1 else 0
                p = 2 * stats.t.sf(abs(t_stat), n-2)

                if abs(r) > 0.5 and p < 0.05:
                    direction = '正' if r > 0 else '负'
                    strength = '强' if abs(r) > 0.8 else ('较强' if abs(r) > 0.6 else '中等')
                    self.findings.append({
                        'type': 'correlation',
                        'variables': (c1, c2),
                        'importance': 'critical' if abs(r) > 0.8 else 'high',
                        'detail': f'{c1}与{c2}呈{strength}{direction}相关(r={r:.3f}, p={p:.4f})',
                        'data': {'r': r, 'p': p, 'n': n},
                    })
                    print(f"  [{'!!' if abs(r) > 0.7 else '!'}] {c1} vs {c2}: r={r:.3f}")

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
                    if all(len(g) >= 8 for g in group_data):
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
                except Exception:
                    continue

                if p < 0.05:
                    means = [g.mean() for g in group_data]
                    higher_idx = np.argmax(means)
                    lower_idx = np.argmin(means)
                    sig = '***' if p < 0.001 else ('**' if p < 0.01 else '*')

                    self.findings.append({
                        'type': 'group_difference',
                        'variable': col,
                        'group_col': gcol,
                        'importance': 'critical' if p < 0.001 else 'high',
                        'detail': f'{col}在{gcol}间差异显著({method}, p={p:.4f}{sig}): {groups[higher_idx]}({means[higher_idx]:.2f}) > {groups[lower_idx]}({means[lower_idx]:.2f})',
                        'data': {'method': method, 'p': p, 'groups': list(groups), 'means': means, 'sig': sig},
                    })
                    print(f"  [{'!!' if p < 0.001 else '!'}] {col}: {groups[higher_idx]}({means[higher_idx]:.2f}) vs {groups[lower_idx]}({means[lower_idx]:.2f}) {sig}")

    def _explore_anomalies(self):
        """探索数据中的异常模式"""
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
        """写Results章节 — 按发现的重要性组织"""
        lines = ['# 3 结果\n']
        section_num = 1

        # 按类型分组
        by_type = {}
        for f in self.findings:
            t = f['type']
            by_type.setdefault(t, []).append(f)

        # 1. 描述性统计（基础）
        desc_findings = by_type.get('distribution', []) + by_type.get('high_variability', [])
        if desc_findings:
            lines.append(f'## 3.{section_num} 采样数据基本特征\n')
            lines.append(self._write_descriptive())
            lines.append('')
            section_num += 1

        # 2. 组间差异（如果有）
        group_findings = by_type.get('group_difference', [])
        if group_findings:
            lines.append(f'## 3.{section_num} 冬春季节差异\n')
            lines.append(self._write_group_differences(group_findings))
            lines.append('')
            section_num += 1

        # 3. 相关性发现
        corr_findings = by_type.get('correlation', [])
        if corr_findings:
            lines.append(f'## 3.{section_num} 变量间相关关系\n')
            lines.append(self._write_correlations(corr_findings))
            lines.append('')
            section_num += 1

        # 4. 异常值和极值
        outlier_findings = by_type.get('outlier', []) + by_type.get('extreme_max', [])
        if outlier_findings:
            lines.append(f'## 3.{section_num} 异常值与极值特征\n')
            lines.append(self._write_outliers(outlier_findings))
            lines.append('')
            section_num += 1

        # 5. 其他发现
        other_findings = by_type.get('ratio_pattern', []) + by_type.get('data_quality', [])
        if other_findings:
            lines.append(f'## 3.{section_num} 其他发现\n')
            for f in other_findings:
                lines.append(f'{f["detail"]}。\n')
            lines.append('')

        return '\n'.join(lines)

    def _write_descriptive(self) -> str:
        """写描述性统计"""
        lines = []
        # 找出变异最大的变量
        cv_list = []
        for col in self.df.select_dtypes(include=[np.number]).columns:
            data = self.df[col].dropna()
            if len(data) < 3:
                continue
            cv = (data.std() / data.mean() * 100) if data.mean() != 0 else 0
            cv_list.append((col, cv, data.mean(), data.std(), data.min(), data.max(), len(data)))

        cv_list.sort(key=lambda x: -x[1])

        for col, cv, mean, std, min_val, max_val, n in cv_list[:8]:
            if cv > 100:
                desc = '高变异'
            elif cv > 30:
                desc = '中等变异'
            else:
                desc = '低变异'
            lines.append(f'{col}的变化范围为{min_val:.2f}~{max_val:.2f}，平均值为{mean:.2f}±{std:.2f}(n={n})，变异系数CV={cv:.1f}%，属于{desc}。')

        return '\n'.join(lines)

    def _write_group_differences(self, findings: list) -> str:
        """写组间差异"""
        lines = []
        sig_findings = [f for f in findings if f['data']['sig'] in ['***', '**']]
        ns_findings = [f for f in findings if f['data']['sig'] == '*']

        if sig_findings:
            lines.append(f'冬春两季比较显示，{len(sig_findings)}个指标存在极显著差异(p<0.01)：')
            for f in sig_findings:
                d = f['data']
                lines.append(f'{f["variable"]}在{d["groups"][np.argmax(d["means"])]}({max(d["means"]):.2f})显著高于{d["groups"][np.argmin(d["means"])]}({min(d["means"]):.2f})({d["method"]}，p={d["p"]:.4f}{d["sig"]})。')

        if ns_findings:
            lines.append(f'\n另有{len(ns_findings)}个指标在0.05水平上差异显著：')
            for f in ns_findings:
                d = f['data']
                lines.append(f'{f["variable"]}({d["method"]}，p={d["p"]:.4f}{d["sig"]})。')

        return '\n'.join(lines)

    def _write_correlations(self, findings: list) -> str:
        """写相关性发现"""
        lines = []
        # 按相关系数绝对值排序
        findings.sort(key=lambda x: -abs(x['data']['r']))

        for f in findings:
            d = f['data']
            v1, v2 = f['variables']
            direction = '正' if d['r'] > 0 else '负'
            strength = '强' if abs(d['r']) > 0.8 else ('较强' if abs(d['r']) > 0.6 else '中等')
            lines.append(f'{v1}与{v2}呈{strength}{direction}相关(Pearson r={d["r"]:.3f}, p={d["p"]:.4f}, n={d["n"]})。')

        return '\n'.join(lines)

    def _write_outliers(self, findings: list) -> str:
        """写异常值和极值"""
        lines = []
        for f in findings:
            lines.append(f'{f["detail"]}。')
        return '\n'.join(lines)

    def write_discussion(self) -> str:
        """写Discussion章节 — 基于发现 + 知识库支撑 + 推理链追踪"""
        lines = ['# 4 讨论\n']
        section_num = 1

        # 按重要性排序讨论
        critical_findings = [f for f in self.findings if f['importance'] in ['critical', 'high']]

        for f in critical_findings[:6]:  # 最多讨论6个重要发现
            title = self._finding_title(f)
            lines.append(f'## 4.{section_num} {title}\n')

            # 从知识库召回相关知识
            ctx = self._recall_knowledge(f)

            # 基于发现+知识写讨论
            para = self._discuss_finding(f, ctx)
            lines.append(para)
            lines.append('')

            # 记录推理链
            self._track_rationale(f, ctx, para)

            section_num += 1

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
        complete = sum(1 for r in self.rationale_rows if r['completeness'] >= 0.8)
        partial = sum(1 for r in self.rationale_rows if 0.3 <= r['completeness'] < 0.8)
        weak = sum(1 for r in self.rationale_rows if r['completeness'] < 0.3)

        lines.append(f'共{len(self.rationale_rows)}条推理链：')
        lines.append(f'- 完整(≥80%): {complete}条')
        lines.append(f'- 部分(30-80%): {partial}条')
        lines.append(f'- 薄弱(<30%): {weak}条\n')

        for i, r in enumerate(self.rationale_rows, 1):
            icon = '✓' if r['completeness'] >= 0.8 else ('△' if r['completeness'] >= 0.3 else '✗')
            lines.append(f'{i}. [{icon}] {r["finding"]}')
            if r['mechanism']:
                lines.append(f'   机制: {r["mechanism"]}')
            if r['citation']:
                lines.append(f'   引用: {r["citation"]}')
            lines.append('')

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
