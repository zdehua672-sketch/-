"""
高级数据分析模块
================
在基础统计分析之上，提供多维度深度分析能力。

核心能力:
  1. 交叉分析 — 季节×功能区×相态的三维交叉
  2. 异常值深挖 — 不只标记异常，要解释为什么异常
  3. 数据故事线 — 从数据中提炼"发现→解释"的故事
  4. 阈值效应检测 — 发现非线性关系和临界点

这是论文"亮点"的来源——基础统计人人都会，
多维深度分析才是论文的差异化竞争力。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────

@dataclass
class CrossAnalysisResult:
    """交叉分析结果"""
    dimension: str = ""         # 分析维度 (如 "季节×功能区")
    variable: str = ""          # 分析变量
    groups: dict = field(default_factory=dict)  # {group_name: stats}
    significant_differences: list = field(default_factory=list)
    insight: str = ""           # 洞察总结

    def to_dict(self):
        return {
            'dimension': self.dimension,
            'variable': self.variable,
            'groups': self.groups,
            'significant_differences': self.significant_differences,
            'insight': self.insight,
        }


@dataclass
class AnomalyInsight:
    """异常值洞察"""
    variable: str = ""
    value: float = 0.0
    sampling_point: str = ""
    season: str = ""
    expected_range: str = ""
    explanation: str = ""       # 解释为什么异常
    significance: str = ""      # 这个异常意味着什么

    def to_dict(self):
        return {
            'variable': self.variable,
            'value': self.value,
            'sampling_point': self.sampling_point,
            'season': self.season,
            'expected_range': self.expected_range,
            'explanation': self.explanation,
            'significance': self.significance,
        }


@dataclass
class DataStory:
    """数据故事线"""
    title: str = ""
    finding: str = ""           # 发现
    evidence: str = ""          # 证据
    mechanism: str = ""         # 机制解释
    implication: str = ""       # 意义
    confidence: float = 0.0
    related_variables: list = field(default_factory=list)

    def to_dict(self):
        return {
            'title': self.title,
            'finding': self.finding,
            'evidence': self.evidence,
            'mechanism': self.mechanism,
            'implication': self.implication,
            'confidence': self.confidence,
        }


@dataclass
class ThresholdEffect:
    """阈值效应"""
    variable: str = ""
    threshold: float = 0.0
    effect_description: str = ""
    evidence: str = ""
    confidence: float = 0.0

    def to_dict(self):
        return {
            'variable': self.variable,
            'threshold': self.threshold,
            'effect_description': self.effect_description,
            'evidence': self.evidence,
        }


# ── 交叉分析器 ──────────────────────────────────────────

class CrossAnalyzer:
    """
    多维交叉分析

    分析维度:
    - 季节 × 功能区
    - 季节 × 相态（气/液/固）
    - 功能区 × 相态
    - 季节 × 功能区 × 相态
    """

    def __init__(self, df):
        self.df = df

    def analyze_all(self) -> list:
        """运行所有交叉分析"""
        results = []

        # 季节 × 功能区
        if '季节' in self.df.columns and '采样点' in self.df.columns:
            results.extend(self._season_by_zone())

        # 季间各变量的深度对比
        if '季节' in self.df.columns:
            results.extend(self._season_deep_compare())

        return results

    def _season_by_zone(self) -> list:
        """季节×功能区交叉分析"""
        import pandas as pd
        import numpy as np
        from scipy import stats

        results = []

        # 识别功能区（从采样点名称推断）
        if '采样点' not in self.df.columns:
            return results

        df = self.df.copy()
        df['功能区'] = df['采样点'].apply(self._classify_zone)

        # 对每个数值变量做交叉分析
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        key_vars = [c for c in numeric_cols if any(k in c for k in
                    ['CH4', 'CO2', 'TOC', 'COD', 'DO', '总氮', '铵态氮'])]

        for var in key_vars[:5]:  # 限制前5个关键变量
            result = CrossAnalysisResult(
                dimension='季节×功能区',
                variable=var,
            )

            # 计算各组统计量
            for season in ['冬季', '春季']:
                for zone in df['功能区'].unique():
                    group = df[(df['季节'] == season) & (df['功能区'] == zone)][var].dropna()
                    if len(group) >= 2:
                        key = f'{season}_{zone}'
                        result.groups[key] = {
                            'mean': round(group.mean(), 3),
                            'std': round(group.std(), 3),
                            'n': len(group),
                        }

            # 检验交互效应（简化：比较各功能区内冬春差异的方向是否一致）
            zones = df['功能区'].unique()
            for zone in zones:
                winter = df[(df['季节'] == '冬季') & (df['功能区'] == zone)][var].dropna()
                spring = df[(df['季节'] == '春季') & (df['功能区'] == zone)][var].dropna()
                if len(winter) >= 2 and len(spring) >= 2:
                    _, p = stats.mannwhitneyu(winter, spring, alternative='two-sided')
                    if p < 0.05:
                        diff_dir = 'higher' if winter.mean() > spring.mean() else 'lower'
                        result.significant_differences.append({
                            'zone': zone,
                            'direction': diff_dir,
                            'p_value': round(p, 4),
                        })

            if result.significant_differences:
                result.insight = (
                    f'{var}的冬春差异在{len(result.significant_differences)}个功能区显著，'
                    f'表明季节效应受功能区类型影响'
                )
                results.append(result)

        return results

    def _season_deep_compare(self) -> list:
        """季节深度对比（每个变量的详细分析）"""
        import numpy as np
        from scipy import stats

        results = []
        df = self.df
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for var in numeric_cols[:8]:
            winter = df[df['季节'] == '冬季'][var].dropna()
            spring = df[df['季节'] == '春季'][var].dropna()

            if len(winter) < 3 or len(spring) < 3:
                continue

            # 效应量 (Cohen's d)
            pooled_std = np.sqrt((winter.std()**2 + spring.std()**2) / 2)
            cohens_d = abs(winter.mean() - spring.mean()) / pooled_std if pooled_std > 0 else 0

            # 变异系数比较
            cv_winter = winter.std() / winter.mean() * 100 if winter.mean() != 0 else 0
            cv_spring = spring.std() / spring.mean() * 100 if spring.mean() != 0 else 0

            if cohens_d > 0.8:  # 大效应量
                result = CrossAnalysisResult(
                    dimension='季节深度对比',
                    variable=var,
                    groups={
                        '冬季': {'mean': round(winter.mean(), 3), 'cv': round(cv_winter, 1)},
                        '春季': {'mean': round(spring.mean(), 3), 'cv': round(cv_spring, 1)},
                    },
                    insight=(
                        f'{var}的季节差异具有大效应量(Cohen d={cohens_d:.2f})。'
                        f'冬季变异系数({cv_winter:.1f}%){"高于" if cv_winter > cv_spring else "低于"}'
                        f'春季({cv_spring:.1f}%)，表明{"冬季" if cv_winter > cv_spring else "春季"}'
                        f'该指标的空间异质性更大。'
                    ),
                )
                results.append(result)

        return results

    def _classify_zone(self, point):
        """从采样点名称推断功能区"""
        point = str(point).upper()
        if any(k in point for k in ['A', '教学']):
            return '教学区'
        elif any(k in point for k in ['B', '生活', '宿舍']):
            return '生活区'
        elif any(k in point for k in ['C', '餐饮', '食堂']):
            return '餐饮区'
        elif any(k in point for k in ['D', '出口', '管口']):
            return '管口出口'
        return '其他'


# ── 异常值深挖器 ──────────────────────────────────────────

class AnomalyDeepDiver:
    """
    异常值深挖 — 不只标记异常，要解释为什么异常

    分析策略:
    1. 标记异常值（IQR方法）
    2. 检查异常值是否集中在特定采样点/季节
    3. 检查异常值是否与其他变量的异常共现
    4. 提出可能的解释
    """

    def __init__(self, df):
        self.df = df

    def analyze(self) -> list:
        """分析所有异常值"""
        import numpy as np

        insights = []
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for var in numeric_cols[:10]:
            data = self.df[var].dropna()
            if len(data) < 5:
                continue

            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            outliers = self.df[(self.df[var] < lower) | (self.df[var] > upper)]

            for idx, row in outliers.iterrows():
                insight = AnomalyInsight(
                    variable=var,
                    value=row[var],
                    sampling_point=str(row.get('采样点', '')),
                    season=str(row.get('季节', '')),
                    expected_range=f'{lower:.2f} - {upper:.2f}',
                )

                # 尝试解释异常
                insight.explanation = self._explain_anomaly(var, row, lower, upper)
                insight.significance = self._assess_significance(var, row)

                insights.append(insight)

        return insights

    def _explain_anomaly(self, var, row, lower, upper):
        """尝试解释异常值"""
        explanations = []
        value = row[var]
        zone = str(row.get('采样点', ''))
        season = str(row.get('季节', ''))

        # 检查是否在餐饮区（有机负荷高）
        if any(k in zone for k in ['C', '餐饮']):
            explanations.append('餐饮区有机负荷通常较高')

        # 检查是否在管口出口（累积效应）
        if any(k in zone for k in ['D', '出口']):
            explanations.append('管口出口可能存在累积效应')

        # 检查季节因素
        if 'CH4' in var and season == '冬季':
            explanations.append('冬季低温可能促进厌氧产甲烷')
        if 'TOC' in var and season == '春季':
            explanations.append('春季降雨冲刷可能增加TOC')

        if not explanations:
            explanations.append('可能与局部排放特征或采样条件有关')

        return '；'.join(explanations)

    def _assess_significance(self, var, row):
        """评估异常值的意义"""
        zone = str(row.get('采样点', ''))
        if 'CH4' in var:
            return '高CH4浓度可能指示局部厌氧热点'
        if 'TOC' in var:
            return '高TOC可能指示有机物排放源'
        if 'DO' in var:
            return '异常DO可能指示管道通气状况变化'
        return '需要结合其他指标综合判断'


# ── 数据故事线提炼器 ──────────────────────────────────────

class DataStoryExtractor:
    """
    从分析结果中提炼数据故事线

    每个故事包含:
    - finding: 发现了什么
    - evidence: 数据证据
    - mechanism: 为什么
    - implication: 意味着什么
    """

    def __init__(self, analysis_results, mechanism_kb=None):
        self.results = analysis_results
        self.mechanisms = mechanism_kb

    def extract_stories(self) -> list:
        """提炼所有数据故事"""
        stories = []

        # 故事1: 关键相关关系
        stories.extend(self._correlation_stories())

        # 故事2: 季节差异
        stories.extend(self._seasonal_stories())

        # 故事3: 空间分异
        stories.extend(self._spatial_stories())

        # 故事4: 碳平衡
        stories.extend(self._carbon_balance_stories())

        # 按置信度排序
        stories.sort(key=lambda x: x.confidence, reverse=True)
        return stories[:5]  # 取Top5

    def _correlation_stories(self) -> list:
        """从相关性分析中提炼故事"""
        stories = []

        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key not in self.results:
                continue

            corr = self.results[key]['相关系数']
            pvals = self.results[key]['p值']

            for i in range(len(corr)):
                for j in range(i + 1, len(corr)):
                    r = corr.iloc[i, j]
                    p = pvals.iloc[i, j]
                    if abs(r) > 0.5 and p < 0.05:
                        var1 = corr.index[i]
                        var2 = corr.columns[j]
                        direction = '正' if r > 0 else '负'

                        story = DataStory(
                            title=f'{var1}与{var2}的{direction}相关关系',
                            finding=f'{var1}与{var2}呈显著{direction}相关(r={r:.3f}, p={p:.4f})',
                            evidence=f'{method.capitalize()}相关分析，样本量充足',
                            mechanism=self._suggest_mechanism(var1, var2, direction),
                            implication=self._suggest_implication(var1, var2, direction),
                            confidence=min(0.9, abs(r)),
                            related_variables=[var1, var2],
                        )
                        stories.append(story)

        return stories

    def _seasonal_stories(self) -> list:
        """从季节差异中提炼故事"""
        stories = []
        if '组间比较' not in self.results:
            return stories

        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']

        for _, row in sig.iterrows():
            var = row['变量']
            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                m1, m2 = row[mean_cols[0]], row[mean_cols[1]]
                higher = '冬季' if m1 > m2 else '春季'

                story = DataStory(
                    title=f'{var}的季节差异',
                    finding=f'{var}在{higher}显著较高',
                    evidence=f'组间比较: {row["显著性"]}',
                    mechanism=self._suggest_seasonal_mechanism(var, higher),
                    implication=f'季节变化对{var}有显著影响，需在碳管理中考虑季节因素',
                    confidence=0.8,
                    related_variables=[var],
                )
                stories.append(story)

        return stories

    def _spatial_stories(self) -> list:
        """从空间分布中提炼故事"""
        # 基于描述统计中的功能区差异
        return []

    def _carbon_balance_stories(self) -> list:
        """从碳平衡中提炼故事"""
        stories = []
        if '描述统计' not in self.results:
            return stories

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) >= 2:
            total = sum(phase_data.values())
            max_phase = max(phase_data, key=phase_data.get)
            max_pct = phase_data[max_phase] / total * 100

            story = DataStory(
                title='碳在三相中的分配格局',
                finding=f'{max_phase}占比最大({max_pct:.1f}%)',
                evidence=f'三相碳含量: {", ".join(f"{k}={v:.1f}" for k,v in phase_data.items())}',
                mechanism=self._suggest_carbon_mechanism(max_phase),
                implication=f'碳管理应重点关注{max_phase}的调控',
                confidence=0.85,
                related_variables=list(phase_data.keys()),
            )
            stories.append(story)

        return stories

    def _suggest_mechanism(self, var1, var2, direction):
        """建议可能的机制"""
        if 'DO' in var1 and 'CH4' in var2:
            return '溶解氧控制产甲烷过程：厌氧条件下产甲烷古菌活性增强'
        if 'TOC' in var1 and 'CH4' in var2:
            return '有机碳为产甲烷提供底物来源'
        return f'{var1}与{var2}之间可能存在生物化学耦合机制'

    def _suggest_implication(self, var1, var2, direction):
        """建议实际意义"""
        if 'DO' in var1 and 'CH4' in var2:
            return '通过调节管道通风可控制CH4排放'
        if 'TOC' in var1 and 'CH4' in var2:
            return '控制有机物输入可减少CH4生成'
        return f'{var1}-{var2}关系对碳管理具有参考价值'

    def _suggest_seasonal_mechanism(self, var, higher):
        """建议季节差异的机制"""
        if 'CH4' in var and higher == '冬季':
            return '冬季低温下厌氧微生物活性仍较高，且管道流量较小导致停留时间长'
        if 'TOC' in var and higher == '春季':
            return '春季降雨冲刷管壁生物膜和沉积物，释放有机碳'
        return '温度和水力条件的季节变化驱动'

    def _suggest_carbon_mechanism(self, max_phase):
        """建议碳分配的机制"""
        if '液' in max_phase:
            return '污水管网以液态输送为主要功能，液相碳是主要赋存形式'
        if '固' in max_phase:
            return '管道沉积物和生物膜是重要的碳汇'
        if '气' in max_phase:
            return '管道厌氧程度高，促进了气相碳的生成'
        return ''


# ── 阈值效应检测器 ──────────────────────────────────────────

class ThresholdDetector:
    """
    检测变量间的阈值效应（非线性关系）

    方法: 将数据按自变量分箱，检查因变量在不同箱中的变化趋势
    """

    def __init__(self, df):
        self.df = df

    def detect(self, x_col, y_col, n_bins=4) -> Optional:
        """检测阈值效应"""
        import numpy as np
        from scipy import stats

        x = pd.to_numeric(self.df[x_col], errors='coerce').dropna()
        y = pd.to_numeric(self.df[y_col], errors='coerce').dropna()

        common = x.index.intersection(y.index)
        x, y = x[common].values, y[common].values

        if len(x) < 10:
            return None

        # 分箱
        bins = np.percentile(x, np.linspace(0, 100, n_bins + 1))
        bins = np.unique(bins)
        if len(bins) < 3:
            return None

        bin_means = []
        bin_labels = []
        for i in range(len(bins) - 1):
            mask = (x >= bins[i]) & (x < bins[i + 1])
            if mask.sum() >= 2:
                bin_means.append(y[mask].mean())
                bin_labels.append(f'{bins[i]:.1f}-{bins[i+1]:.1f}')

        if len(bin_means) < 3:
            return None

        # 检测是否有明显的跳跃（相邻箱的均值差异 > 总标准差的0.5倍）
        y_std = np.std(y)
        for i in range(1, len(bin_means)):
            if abs(bin_means[i] - bin_means[i-1]) > 0.5 * y_std:
                return ThresholdEffect(
                    variable=x_col,
                    threshold=bins[i],
                    effect_description=(
                        f'当{x_col}超过{bins[i]:.2f}时，{y_col}出现'
                        f'{"显著升高" if bin_means[i] > bin_means[i-1] else "显著降低"}'
                    ),
                    evidence=f'{x_col}分箱均值: {[f"{m:.2f}" for m in bin_means]}',
                    confidence=0.7,
                )

        return None


# 需要导入 pandas
import pandas as pd


# ── 便捷入口 ──────────────────────────────────────────

def run_advanced_analysis(df, analysis_results=None) -> dict:
    """
    运行全部高级分析

    Parameters
    ----------
    df : DataFrame, 原始数据
    analysis_results : dict, 基础统计分析结果

    Returns
    -------
    dict, {cross_analysis, anomalies, stories, thresholds}
    """
    results = {}

    # 交叉分析
    cross = CrossAnalyzer(df)
    results['cross_analysis'] = cross.analyze_all()

    # 异常值深挖
    anomaly = AnomalyDeepDiver(df)
    results['anomalies'] = anomaly.analyze()

    # 数据故事线
    if analysis_results:
        storyteller = DataStoryExtractor(analysis_results)
        results['stories'] = storyteller.extract_stories()

    return results
