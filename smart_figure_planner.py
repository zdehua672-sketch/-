# -*- coding: utf-8 -*-
"""
智能作图规划器 — 数据驱动的图表生成系统

核心流程：
1. 数据质量评估 → 确定哪些变量可作图
2. AI作图规划 → 决定做什么图、用哪些数据
3. 精准数据提取 → 只取作图需要的数据
4. 质量检验 → 确保图表合格
"""

import pandas as pd
import numpy as np
import logging
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================
# 1. 数据质量仪表盘
# ============================================================

@dataclass
class VariableQuality:
    """单个变量的质量评估"""
    name: str
    total_count: int          # 总样本数
    valid_count: int          # 有效样本数
    missing_rate: float       # 缺失率 (0-1)
    plottable: bool           # 是否可作图
    plottable_level: str      # 'good' / 'caution' / 'skip'
    reason: str               # 不可作图的原因
    phase: str                # 'gas' / 'liquid' / 'solid' / 'other'
    dtype: str                # 'numeric' / 'categorical'


@dataclass
class DataQualityReport:
    """数据质量报告"""
    total_samples: int
    variables: List[VariableQuality]
    plottable_vars: List[str]       # 可作图的变量名
    caution_vars: List[str]         # 谨慎使用的变量名
    skipped_vars: List[str]         # 跳过的变量名
    phase_summary: Dict[str, dict]  # 各相态的质量汇总


class DataQualityDashboard:
    """
    数据质量仪表盘

    评估每个变量的可作图性，输出质量报告。
    """

    # 相态关键词映射
    PHASE_KEYWORDS = {
        'gas': ['甲烷', 'CH4', 'CO2', 'O2', 'VOCs', 'H2S', 'N2O', 'NO2', '氧化亚氮', '本底值'],
        'liquid': ['DO', 'pH', 'TOC', 'TC', 'IC', 'COD', '总氮', '总磷', '铵态氮', '硝态氮',
                   'NaCl', '电导率', '液温', 'mg/L'],
        'solid': ['固总碳', '有机碳', '无机碳', 'DOC', '全磷', 'g/kg', 'mg/kg'],
    }

    # 缺失率阈值
    THRESHOLD_GOOD = 0.30      # < 30% 缺失 → 可作图
    THRESHOLD_CAUTION = 0.70   # 30-70% → 谨慎使用
    # > 70% → 跳过

    # 最小有效样本量
    MIN_SAMPLE_SIZE = 10

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.report = None

    def assess(self) -> DataQualityReport:
        """评估数据质量，生成报告"""
        variables = []

        for col in self.df.columns:
            var_quality = self._assess_variable(col)
            variables.append(var_quality)

        # 分类
        plottable = [v.name for v in variables if v.plottable_level == 'good']
        caution = [v.name for v in variables if v.plottable_level == 'caution']
        skipped = [v.name for v in variables if v.plottable_level == 'skip']

        # 相态汇总
        phase_summary = self._summarize_phases(variables)

        self.report = DataQualityReport(
            total_samples=len(self.df),
            variables=variables,
            plottable_vars=plottable,
            caution_vars=caution,
            skipped_vars=skipped,
            phase_summary=phase_summary,
        )

        logger.info(f"数据质量评估完成: {len(plottable)}可作图, {len(caution)}谨慎, {len(skipped)}跳过")
        return self.report

    def _assess_variable(self, col: str) -> VariableQuality:
        """评估单个变量"""
        series = self.df[col]
        total = len(series)
        valid = series.notna().sum()
        missing_rate = 1 - valid / total if total > 0 else 1.0

        # 判断数据类型
        if pd.api.types.is_numeric_dtype(series):
            dtype = 'numeric'
        else:
            dtype = 'categorical'

        # 判断相态
        phase = self._classify_phase(col)

        # 判断可作图性
        if missing_rate < self.THRESHOLD_GOOD and valid >= self.MIN_SAMPLE_SIZE:
            plottable = True
            level = 'good'
            reason = ''
        elif missing_rate < self.THRESHOLD_CAUTION and valid >= self.MIN_SAMPLE_SIZE:
            plottable = True
            level = 'caution'
            reason = f'缺失率{missing_rate:.0%}，样本量{valid}偏少'
        else:
            plottable = False
            level = 'skip'
            if valid < self.MIN_SAMPLE_SIZE:
                reason = f'有效样本仅{valid}个，不足{self.MIN_SAMPLE_SIZE}'
            else:
                reason = f'缺失率{missing_rate:.0%}，数据严重不足'

        return VariableQuality(
            name=col,
            total_count=total,
            valid_count=valid,
            missing_rate=missing_rate,
            plottable=plottable,
            plottable_level=level,
            reason=reason,
            phase=phase,
            dtype=dtype,
        )

    def _classify_phase(self, col: str) -> str:
        """根据列名关键词判断相态"""
        col_lower = col.lower()
        for phase, keywords in self.PHASE_KEYWORDS.items():
            if any(kw.lower() in col_lower for kw in keywords):
                return phase
        return 'other'

    def _summarize_phases(self, variables: List[VariableQuality]) -> Dict[str, dict]:
        """汇总各相态的质量"""
        summary = {}
        for phase in ['gas', 'liquid', 'solid', 'other']:
            phase_vars = [v for v in variables if v.phase == phase]
            if not phase_vars:
                continue
            summary[phase] = {
                'total': len(phase_vars),
                'plottable': len([v for v in phase_vars if v.plottable_level == 'good']),
                'caution': len([v for v in phase_vars if v.plottable_level == 'caution']),
                'skipped': len([v for v in phase_vars if v.plottable_level == 'skip']),
                'variables': [v.name for v in phase_vars if v.plottable],
            }
        return summary

    def format_report(self) -> str:
        """格式化质量报告为可读文本"""
        if not self.report:
            self.assess()

        r = self.report
        lines = [
            f"=== 数据质量报告 ===",
            f"总样本数: {r.total_samples}",
            f"可作图变量: {len(r.plottable_vars)}个",
            f"谨慎使用: {len(r.caution_vars)}个",
            f"跳过: {len(r.skipped_vars)}个",
            "",
            "--- 可作图变量 ---",
        ]

        for v in r.variables:
            if v.plottable_level == 'good':
                lines.append(f"  ✅ {v.name} (n={v.valid_count}, 缺失{v.missing_rate:.0%}, {v.phase})")

        if r.caution_vars:
            lines.append("")
            lines.append("--- 谨慎使用 ---")
            for v in r.variables:
                if v.plottable_level == 'caution':
                    lines.append(f"  ⚠️ {v.name} (n={v.valid_count}, 缺失{v.missing_rate:.0%}) - {v.reason}")

        if r.skipped_vars:
            lines.append("")
            lines.append("--- 跳过 ---")
            for v in r.variables:
                if v.plottable_level == 'skip':
                    lines.append(f"  ❌ {v.name} (n={v.valid_count}, 缺失{v.missing_rate:.0%}) - {v.reason}")

        lines.append("")
        lines.append("--- 相态汇总 ---")
        for phase, info in r.phase_summary.items():
            lines.append(f"  {phase}: {info['plottable']}可作图, {info['caution']}谨慎, {info['skipped']}跳过")

        return '\n'.join(lines)


# ============================================================
# 2. AI 作图规划器
# ============================================================

@dataclass
class FigurePlan:
    """单个图表的规划"""
    chart_type: str           # 'boxplot' / 'heatmap' / 'scatter' / 'bar' / 'violin' / 'regression'
    title: str                # 图表标题
    variables: List[str]      # 要使用的变量
    group_col: Optional[str]  # 分组变量（如季节）
    purpose: str              # 这张图要回答什么问题
    priority: int             # 优先级 1-5（1最高）
    section: str              # 'results' / 'discussion'
    data_query: str           # 数据提取描述
    caption: str              # 图表说明


@dataclass
class FigurePlanSet:
    """完整的作图计划"""
    plans: List[FigurePlan]
    quality_report: DataQualityReport
    findings_summary: str


class SmartFigurePlanner:
    """
    智能作图规划器

    基于数据质量和findings，规划最优的图表组合。
    """

    def __init__(self, df: pd.DataFrame, findings: list, language: str = 'zh'):
        self.df = df
        self.findings = findings
        self.language = language
        self.dashboard = DataQualityDashboard(df)

    def plan(self) -> FigurePlanSet:
        """生成作图计划"""
        # Step 1: 数据质量评估
        quality_report = self.dashboard.assess()

        # Step 2: 分析 findings
        findings_summary = self._summarize_findings()

        # Step 3: 生成作图计划
        plans = self._generate_plans(quality_report, findings_summary)

        # Step 4: 按优先级排序
        plans.sort(key=lambda p: p.priority)

        result = FigurePlanSet(
            plans=plans,
            quality_report=quality_report,
            findings_summary=findings_summary,
        )

        logger.info(f"作图计划生成完成: {len(plans)}个图表")
        return result

    def _summarize_findings(self) -> str:
        """汇总关键发现"""
        if not self.findings:
            return "暂无发现"

        lines = []

        # 按类型分组
        by_type = {}
        for f in self.findings:
            ftype = f.get('type', 'unknown')
            if ftype not in by_type:
                by_type[ftype] = []
            by_type[ftype].append(f)

        # 季节差异
        seasonal = by_type.get('group_difference', [])
        if seasonal:
            significant = [f for f in seasonal if f.get('data', {}).get('p', 1) < 0.05]
            lines.append(f"季节差异: {len(significant)}个显著 (p<0.05)")
            for f in significant[:5]:
                lines.append(f"  - {f.get('variable', '?')}: p={f.get('data', {}).get('p', 0):.4f}")

        # 相关性
        correlations = by_type.get('correlation', [])
        if correlations:
            strong = [f for f in correlations if abs(f.get('data', {}).get('r', 0)) > 0.5]
            lines.append(f"强相关: {len(strong)}个 (|r|>0.5)")
            for f in strong[:5]:
                lines.append(f"  - {f.get('variables', ['?','?'])[0]} vs {f.get('variables', ['?','?'])[1]}: r={f.get('data', {}).get('r', 0):.3f}")

        # 异常值
        outliers = by_type.get('outlier', [])
        if outliers:
            lines.append(f"异常值: {len(outliers)}个")

        # 跨相态关联
        cross_phase = by_type.get('cross_phase', [])
        if cross_phase:
            lines.append(f"跨相态关联: {len(cross_phase)}个")

        return '\n'.join(lines) if lines else "暂无显著发现"

    def _generate_plans(self, quality_report: DataQualityReport,
                        findings_summary: str) -> List[FigurePlan]:
        """基于数据质量和发现生成作图计划"""
        plans = []
        plottable = set(quality_report.plottable_vars)
        caution = set(quality_report.caution_vars)

        # 规则1: 季节对比箱线图（核心图，优先级1）
        seasonal_vars = self._find_seasonal_diff_vars(plottable, caution)
        if seasonal_vars:
            plans.append(FigurePlan(
                chart_type='boxplot',
                title='冬春两季关键变量对比',
                variables=seasonal_vars[:8],  # 最多8个变量
                group_col='季节',
                purpose='展示冬春两季碳污染物的差异',
                priority=1,
                section='results',
                data_query=f'提取 {seasonal_vars[:8]} 按季节分组',
                caption='冬春季关键变量箱线图比较，* p<0.05',
            ))

        # 规则2: 相关性热图（核心图，优先级1）
        corr_vars = self._find_correlation_vars(plottable)
        if len(corr_vars) >= 3:
            plans.append(FigurePlan(
                chart_type='heatmap',
                title='关键变量Pearson相关性矩阵',
                variables=corr_vars,
                group_col=None,
                purpose='展示变量间的相关关系',
                priority=1,
                section='results',
                data_query=f'提取 {corr_vars} 计算相关系数',
                caption='关键变量Pearson相关性矩阵，* p<0.05',
            ))

        # 规则3: 跨相态散点图（支撑图，优先级2）
        gas_vars = [v for v in plottable if quality_report.variables[[vv.name for vv in quality_report.variables].index(v)].phase == 'gas']
        liquid_vars = [v for v in plottable if quality_report.variables[[vv.name for vv in quality_report.variables].index(v)].phase == 'liquid']

        if gas_vars and liquid_vars:
            # 找最强的跨相态关联
            cross_pairs = self._find_cross_phase_pairs(gas_vars, liquid_vars)
            if cross_pairs:
                x, y = cross_pairs[0]
                plans.append(FigurePlan(
                    chart_type='scatter',
                    title=f'{x} vs {y} 跨相态关联',
                    variables=[x, y],
                    group_col='季节',
                    purpose='展示气相-液相变量的关联',
                    priority=2,
                    section='results',
                    data_query=f'提取 {x}, {y}, 季节',
                    caption=f'气相-液相变量耦合关系，标注Pearson相关系数',
                ))

        # 规则4: 空间分布图（支撑图，优先级2）
        if '采样点' in self.df.columns and gas_vars:
            plans.append(FigurePlan(
                chart_type='bar',
                title='气体污染物空间分布',
                variables=gas_vars[:4],
                group_col='采样点',
                purpose='展示不同采样点的气体浓度分布',
                priority=2,
                section='results',
                data_query=f'提取 {gas_vars[:4]} 按采样点分组',
                caption='气体污染物空间分布，误差棒表示标准误',
            ))

        # 规则5: 季节显著变量小提琴图（支撑图，优先级2）
        sig_vars = self._find_significant_vars(plottable, caution)
        if sig_vars:
            plans.append(FigurePlan(
                chart_type='violin',
                title='季节差异显著变量对比',
                variables=sig_vars[:6],
                group_col='季节',
                purpose='详细展示显著差异变量的分布',
                priority=2,
                section='results',
                data_query=f'提取 {sig_vars[:6]} 按季节分组',
                caption='季节差异显著变量对比，* p<0.05',
            ))

        # 规则6: PCA双标图（探索图，优先级3）
        pca_vars = [v for v in corr_vars if v in plottable]
        if len(pca_vars) >= 4:
            plans.append(FigurePlan(
                chart_type='pca',
                title='主成分分析双标图',
                variables=pca_vars,
                group_col='季节',
                purpose='降维展示数据结构和聚类特征',
                priority=3,
                section='results',
                data_query=f'提取 {pca_vars} 进行PCA',
                caption='PCA双标图，展示主成分载荷和样本分布',
            ))

        # 规则7: 异常值剖面图（探索图，优先级3）
        outliers = [f for f in self.findings if f.get('type') == 'anomaly_story']
        if outliers and gas_vars:
            plans.append(FigurePlan(
                chart_type='profile',
                title='异常采样点特征剖面',
                variables=gas_vars[:5],
                group_col='采样点',
                purpose='展示异常采样点的环境特征',
                priority=3,
                section='discussion',
                data_query=f'提取异常采样点的 {gas_vars[:5]}',
                caption='异常采样点特征剖面图，标准化后展示',
            ))

        return plans

    def _find_seasonal_diff_vars(self, plottable: set, caution: set) -> List[str]:
        """找到有季节差异的变量"""
        seasonal = []
        for f in self.findings:
            if f.get('type') == 'group_difference':
                var = f.get('variable', '')
                p = f.get('data', {}).get('p', 1)
                if var in plottable and p < 0.1:
                    seasonal.append((var, p))

        # 按p值排序
        seasonal.sort(key=lambda x: x[1])
        return [v for v, p in seasonal]

    def _find_correlation_vars(self, plottable: set) -> List[str]:
        """找到有强相关性的变量"""
        corr_vars = set()
        for f in self.findings:
            if f.get('type') == 'correlation':
                vars_ = f.get('variables', [])
                r = abs(f.get('data', {}).get('r', 0))
                if r > 0.3 and all(v in plottable for v in vars_):
                    corr_vars.update(vars_)

        return list(corr_vars)

    def _find_cross_phase_pairs(self, gas_vars: list, liquid_vars: list) -> List[Tuple[str, str]]:
        """找到跨相态的变量对"""
        pairs = []
        for f in self.findings:
            if f.get('type') == 'cross_phase':
                vars_ = f.get('variables', [])
                if len(vars_) == 2:
                    v1, v2 = vars_
                    if (v1 in gas_vars and v2 in liquid_vars) or \
                       (v1 in liquid_vars and v2 in gas_vars):
                        pairs.append((v1, v2))

        return pairs

    def _find_significant_vars(self, plottable: set, caution: set) -> List[str]:
        """找到显著差异的变量"""
        sig = []
        for f in self.findings:
            if f.get('type') == 'group_difference':
                var = f.get('variable', '')
                p = f.get('data', {}).get('p', 1)
                if var in (plottable | caution) and p < 0.05:
                    sig.append(var)
        return sig


# ============================================================
# 3. 精准数据提取器
# ============================================================

class TargetedDataExtractor:
    """
    精准数据提取器

    根据作图计划，从原始数据中提取精准的数据子集。
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def extract(self, plan: FigurePlan) -> pd.DataFrame:
        """根据作图计划提取数据"""
        # 确定需要的列
        columns = list(plan.variables)
        if plan.group_col and plan.group_col not in columns:
            columns.append(plan.group_col)

        # 添加采样点信息（如果有）
        if '采样点' in self.df.columns and '采样点' not in columns:
            columns.append('采样点')

        # 只取存在的列
        columns = [c for c in columns if c in self.df.columns]

        # 提取数据
        subset = self.df[columns].copy()

        # 处理缺失值
        subset = self._handle_missing(subset, plan)

        logger.info(f"数据提取: {plan.title} -> {subset.shape}")
        return subset

    def _handle_missing(self, df: pd.DataFrame, plan: FigurePlan) -> pd.DataFrame:
        """处理缺失值"""
        # 对于数值列，删除全为NaN的行
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            df = df.dropna(subset=numeric_cols, how='all')

        # 对于分组列，删除NaN
        if plan.group_col and plan.group_col in df.columns:
            df = df.dropna(subset=[plan.group_col])

        return df


# ============================================================
# 4. 图表质量验证器
# ============================================================

@dataclass
class FigureQualityResult:
    """图表质量检验结果"""
    passed: bool
    score: float           # 0-100
    issues: List[str]      # 问题列表
    suggestions: List[str] # 改进建议


class FigureQualityValidator:
    """
    图表质量验证器

    检查生成的图表是否符合质量标准。
    """

    MIN_SAMPLE_SIZE = 10

    def validate(self, fig, metadata: dict, data: pd.DataFrame) -> FigureQualityResult:
        """验证图表质量"""
        issues = []
        suggestions = []
        score = 100

        # 检查1: 样本量
        n = len(data)
        if n < self.MIN_SAMPLE_SIZE:
            issues.append(f"样本量不足: n={n} (最少{self.MIN_SAMPLE_SIZE})")
            score -= 30

        # 检查2: 变量有效性
        variables = metadata.get('variables', [])
        for var in variables:
            if var in data.columns:
                valid = data[var].notna().sum()
                if valid < self.MIN_SAMPLE_SIZE:
                    issues.append(f"变量 {var} 有效样本仅 {valid} 个")
                    score -= 10

        # 检查3: 分组平衡性
        group_col = metadata.get('group_col')
        if group_col and group_col in data.columns:
            group_counts = data[group_col].value_counts()
            min_group = group_counts.min()
            max_group = group_counts.max()
            if min_group < 3:
                issues.append(f"分组 {group_col} 中有组样本量过少: {min_group}")
                score -= 20
            if max_group / min_group > 5 if min_group > 0 else False:
                suggestions.append("分组样本量差异较大，考虑标注样本量")

        # 检查4: 异常值影响
        for var in variables:
            if var in data.columns and pd.api.types.is_numeric_dtype(data[var]):
                q1 = data[var].quantile(0.25)
                q3 = data[var].quantile(0.75)
                iqr = q3 - q1
                outliers = ((data[var] < q1 - 3*iqr) | (data[var] > q3 + 3*iqr)).sum()
                if outliers > len(data) * 0.1:
                    suggestions.append(f"变量 {var} 有 {outliers} 个极端异常值，考虑标注")

        passed = score >= 60
        return FigureQualityResult(
            passed=passed,
            score=max(0, score),
            issues=issues,
            suggestions=suggestions,
        )


# ============================================================
# 5. 主接口
# ============================================================

def plan_figures(df: pd.DataFrame, findings: list, language: str = 'zh') -> FigurePlanSet:
    """
    规划图表的主接口

    Parameters
    ----------
    df : pd.DataFrame, 原始数据
    findings : list, DataExplorer 的发现
    language : str, 语言

    Returns
    -------
    FigurePlanSet, 作图计划
    """
    planner = SmartFigurePlanner(df, findings, language)
    return planner.plan()
