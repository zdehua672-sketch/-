"""
=============================================================================
动机规划器 - Motivation Planner
借鉴 PaperSpine 的 motivation-first 工作流

核心思想：在写任何东西之前，必须先想清楚"这篇论文到底要说什么"。
不是凭空编 motivation，而是从数据分析结果、文献矩阵、领域机制中推导。

两个核心产出：
  1. MotivationOptions — 3-5个动机选项供用户选择
  2. ConfirmedMotivation — 用户确认后的动机（写作的"宪法"）

同时升级 Writing Rationale Matrix 为"写作蓝图"（执行计划），而非事后回顾。
=============================================================================
"""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class MotivationOption:
    """一个动机选项"""
    option_id: str                          # A/B/C/D/E
    one_sentence: str                       # 一句话动机
    field_problem: str                      # 领域问题
    specific_gap: str                       # 具体空白
    core_innovation: str                    # 核心创新点
    evidence_support: str                   # 支撑证据摘要
    risk: str                               # 风险/局限
    emphasis: str                           # 写作时应强调什么
    de_emphasis: str                        # 写作时应弱化什么

    def to_markdown_row(self) -> str:
        return (
            f"| {self.option_id} | {self.one_sentence} | {self.field_problem[:30]} | "
            f"{self.specific_gap[:30]} | {self.core_innovation[:30]} | {self.risk[:20]} |"
        )


@dataclass
class ConfirmedMotivation:
    """用户确认后的动机 -- 写作的宪法"""
    source: str                             # user_provided / selected_option / edited_option
    motivation_statement: str               # 确认的动机陈述
    red_thread: str                         # 一句话红线
    field_problem: str                      # 领域问题
    specific_gap: str                       # 具体空白
    design_response: str                    # 设计响应
    main_evidence: str                      # 主要证据
    prioritized_claims: list = field(default_factory=list)   # 优先主张
    claims_to_avoid: list = field(default_factory=list)      # 应避免的主张
    section_consequences: dict = field(default_factory=dict) # 各章节的动机后果
    rejected_options: list = field(default_factory=list)     # 被拒绝的选项及原因
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_markdown(self) -> str:
        lines = [
            "# 确认的动机 (Confirmed Motivation)",
            "",
            "| 字段 | 内容 |",
            "|------|------|",
            f"| 来源 | {self.source} |",
            f"| 动机陈述 | {self.motivation_statement} |",
            f"| 一句话红线 | {self.red_thread} |",
            f"| 领域问题 | {self.field_problem} |",
            f"| 研究空白 | {self.specific_gap} |",
            f"| 设计响应 | {self.design_response} |",
            f"| 主要证据 | {self.main_evidence[:100]} |",
            "",
        ]

        if self.prioritized_claims:
            lines.append("## 优先主张")
            for c in self.prioritized_claims:
                lines.append(f"- {c}")
            lines.append("")

        if self.claims_to_avoid:
            lines.append("## 应避免的主张")
            for c in self.claims_to_avoid:
                lines.append(f"- ~~{c}~~")
            lines.append("")

        if self.section_consequences:
            lines.append("## 各章节的动机约束")
            lines.append("")
            lines.append("| 章节 | 动机要求 | 应避免 |")
            lines.append("|------|---------|--------|")
            for sec, cons in self.section_consequences.items():
                requires = cons.get('requires', '')
                avoid = cons.get('avoid', '')
                lines.append(f"| {sec} | {requires[:50]} | {avoid[:40]} |")
            lines.append("")

        if self.rejected_options:
            lines.append("## 被拒绝的选项")
            for rej in self.rejected_options:
                lines.append(f"- ~~{rej.get('option', '')}~~: {rej.get('reason', '')}")
            lines.append("")

        return '\n'.join(lines)


@dataclass
class SectionBlueprint:
    """一个章节的写作蓝图"""
    section_name: str                       # 章节名
    communicative_job: str                  # 交际功能
    motivation_link: str                    # 与动机的关联
    exemplar_pattern: str                   # 范文中学到的模式
    target_moves: list = field(default_factory=list)  # 目标动作列表
    evidence_items: list = field(default_factory=list) # 支撑证据
    style_constraints: str = ""             # 风格约束
    target_length: str = ""                 # 目标长度


@dataclass
class WritingBlueprint:
    """
    写作蓝图 — 写作的执行计划
    PaperSpine 的 writing_rationale_matrix 的升级版
    在写作前创建，不是事后回顾
    """
    confirmed_motivation: ConfirmedMotivation
    section_blueprints: list = field(default_factory=list)  # list of SectionBlueprint
    global_framework_rationale: str = ""    # 全局框架理由
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_markdown(self) -> str:
        lines = [
            "# 写作蓝图 (Writing Blueprint)",
            "",
            "> 本文件是写作的执行计划，不是事后回顾。每个章节在写作前就规划好其功能、",
            "> 动机关联、证据支撑和风格约束。",
            "",
            "## 全局框架理由",
            "",
            self.global_framework_rationale or "（待填写）",
            "",
            "## 动机红线",
            "",
            f"**{self.confirmed_motivation.red_thread}**",
            "",
            "## 章节蓝图",
            "",
            "| # | 章节 | 交际功能 | 动机关联 | 证据支撑 | 目标动作 |",
            "|---|------|---------|---------|---------|---------|",
        ]

        for i, bp in enumerate(self.section_blueprints):
            moves = '; '.join(bp.target_moves[:3]) if bp.target_moves else ''
            evidence = '; '.join(bp.evidence_items[:2]) if bp.evidence_items else ''
            lines.append(
                f"| {i+1} | {bp.section_name} | {bp.communicative_job[:30]} | "
                f"{bp.motivation_link[:30]} | {evidence[:30]} | {moves[:40]} |"
            )

        lines.append("")

        # 详细蓝图
        for i, bp in enumerate(self.section_blueprints):
            lines.append(f"### {i+1}. {bp.section_name}")
            lines.append("")
            lines.append(f"- **交际功能**: {bp.communicative_job}")
            lines.append(f"- **动机关联**: {bp.motivation_link}")
            if bp.exemplar_pattern:
                lines.append(f"- **范文模式**: {bp.exemplar_pattern}")
            if bp.target_moves:
                lines.append(f"- **目标动作**:")
                for move in bp.target_moves:
                    lines.append(f"  - {move}")
            if bp.evidence_items:
                lines.append(f"- **证据支撑**:")
                for ev in bp.evidence_items:
                    lines.append(f"  - {ev}")
            if bp.style_constraints:
                lines.append(f"- **风格约束**: {bp.style_constraints}")
            if bp.target_length:
                lines.append(f"- **目标长度**: {bp.target_length}")
            lines.append("")

        return '\n'.join(lines)

    def to_execution_table(self) -> str:
        """
        导出为 PaperSpine 风格的执行表
        每行一个写作单元，包含完整的决策理由
        """
        lines = [
            "# 写作执行表 (Writing Execution Table)",
            "",
            "| Row | 写作单元 | 功能 | 动机关联 | 参考/SOTA模式 | 证据/引用锚点 | 计划修改 | 最终检查 |",
            "|-----|---------|------|---------|-------------|-------------|---------|---------|",
        ]

        row_id = 1
        # 第一行：全局框架
        lines.append(
            f"| {row_id} | 全文框架 | {self.global_framework_rationale[:40]} | "
            f"{self.confirmed_motivation.motivation_statement[:30]} | "
            f"（范文学习） | （用户证据） | 确立结构 | 首尾呼应 |"
        )
        row_id += 1

        for bp in self.section_blueprints:
            for j, move in enumerate(bp.target_moves):
                evidence = bp.evidence_items[j] if j < len(bp.evidence_items) else ''
                lines.append(
                    f"| {row_id} | {bp.section_name}{'.' + str(j+1) if len(bp.target_moves) > 1 else ''} | "
                    f"{move[:30]} | {bp.motivation_link[:25]} | "
                    f"{bp.exemplar_pattern[:20]} | {evidence[:25]} | "
                    f"{move[:20]} | {bp.style_constraints[:20] if bp.style_constraints else '—'} |"
                )
                row_id += 1

        return '\n'.join(lines)


# ============================================================================
# 动机生成器
# ============================================================================

class MotivationGenerator:
    """
    从分析结果中推导动机选项

    不是编造 motivation，而是从数据中发现"这篇论文最值得说什么"。
    输入：分析结果 + 文献矩阵 + 领域机制
    输出：3-5个动机选项
    """

    def __init__(self, analysis_results: dict = None, literature_matrix: str = "",
                 mechanisms=None, language: str = 'zh'):
        self.results = analysis_results or {}
        self.literature = literature_matrix
        self.mechanisms = mechanisms
        self.language = language

    def generate_options(self) -> list:
        """
        生成动机选项

        策略：从数据分析结果中提取"最强发现"，组合为动机候选
        """
        options = []
        option_id = ord('A')

        # 策略1: 从显著相关性中提取
        corr_options = self._extract_from_correlations()
        for opt in corr_options:
            opt.option_id = chr(option_id)
            options.append(opt)
            option_id += 1

        # 策略2: 从组间差异中提取
        diff_options = self._extract_from_differences()
        for opt in diff_options:
            opt.option_id = chr(option_id)
            options.append(opt)
            option_id += 1

        # 策略3: 从PCA模式中提取
        pca_options = self._extract_from_pca()
        for opt in pca_options:
            opt.option_id = chr(option_id)
            options.append(opt)
            option_id += 1

        # 策略4: 从碳平衡中提取
        balance_options = self._extract_from_carbon_balance()
        for opt in balance_options:
            opt.option_id = chr(option_id)
            options.append(opt)
            option_id += 1

        # 限制为3-5个
        if len(options) > 5:
            options = options[:5]

        # 如果不够3个，补充通用选项
        while len(options) < 3:
            opt = self._generate_generic_option(chr(option_id))
            options.append(opt)
            option_id += 1

        return options

    def _extract_from_correlations(self) -> list:
        """从相关性分析中提取动机选项"""
        options = []

        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key not in self.results:
                continue

            corr = self.results[key].get('相关系数')
            pvals = self.results[key].get('p值')
            if corr is None or pvals is None:
                continue

            # 找最强相关
            best_pairs = []
            for i in range(len(corr)):
                for j in range(i + 1, len(corr)):
                    r = corr.iloc[i, j]
                    p = pvals.iloc[i, j]
                    if abs(r) > 0.5 and p < 0.05:
                        best_pairs.append((corr.index[i], corr.columns[j], r, p))

            if not best_pairs:
                continue

            # 按|r|排序
            best_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

            # 生成动机选项
            for var1, var2, r, p in best_pairs[:2]:
                direction = '正' if r > 0 else '负'
                label1 = _get_var_label(var1, self.language)
                label2 = _get_var_label(var2, self.language)

                if self.language == 'zh':
                    option = MotivationOption(
                        option_id='',
                        one_sentence=f'揭示{label1}与{label2}的{direction}相关关系及其驱动机制',
                        field_problem=f'污水管网中{label1}与{label2}的关系机制尚不清楚',
                        specific_gap=f'缺乏{label1}-{label2}耦合机制的定量研究',
                        core_innovation=f'首次系统分析{label1}与{label2}的{direction}相关(r={r:.2f})及其生物地球化学机制',
                        evidence_support=f'{method}相关分析: r={r:.3f}, p={p:.4f}',
                        risk='相关关系不等于因果关系，需进一步验证',
                        emphasis=f'{label1}-{label2}耦合的机制解释',
                        de_emphasis='其他变量的描述性统计',
                    )
                else:
                    option = MotivationOption(
                        option_id='',
                        one_sentence=f'Reveal the {direction} correlation between {label1} and {label2} and its driving mechanism',
                        field_problem=f'The relationship mechanism between {label1} and {label2} in sewage networks remains unclear',
                        specific_gap=f'Lack of quantitative studies on {label1}-{label2} coupling mechanisms',
                        core_innovation=f'First systematic analysis of {direction} correlation (r={r:.2f}) between {label1} and {label2}',
                        evidence_support=f'{method} correlation: r={r:.3f}, p={p:.4f}',
                        risk='Correlation does not imply causation',
                        emphasis=f'{label1}-{label2} coupling mechanism',
                        de_emphasis='Descriptive statistics of other variables',
                    )
                options.append(option)

        return options

    def _extract_from_differences(self) -> list:
        """从组间差异中提取动机选项"""
        if '组间比较' not in self.results:
            return []

        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']
        if len(sig) == 0:
            return []

        options = []
        n_sig = len(sig)
        sig_vars = [row['变量'] for _, row in sig.iterrows()][:3]
        sig_labels = [_get_var_label(v, self.language) for v in sig_vars]

        if self.language == 'zh':
            option = MotivationOption(
                option_id='',
                one_sentence=f'揭示校园污水管网碳污染物的冬春季节差异及驱动因素',
                field_problem='污水管网碳污染物的季节变化规律认识不足',
                specific_gap=f'缺乏多相态碳污染物季节差异的系统研究（{n_sig}个指标差异显著）',
                core_innovation=f'系统比较冬春两季{n_sig}个碳污染物指标的差异，揭示温度和水文驱动机制',
                evidence_support=f'{", ".join(sig_labels)}等{n_sig}个指标季节差异显著',
                risk='仅覆盖两个季节，未能覆盖全年',
                emphasis='季节差异的机制解释（温度、降雨、微生物活性）',
                de_emphasis='单一样点的极端值分析',
            )
        else:
            option = MotivationOption(
                option_id='',
                one_sentence='Reveal seasonal differences of carbon pollutants in campus sewage networks',
                field_problem='Seasonal variation patterns of carbon pollutants in sewage networks are poorly understood',
                specific_gap=f'Lack of systematic study on seasonal differences ({n_sig} indicators significant)',
                core_innovation=f'Systematic comparison of {n_sig} carbon pollutant indicators between winter and spring',
                evidence_support=f'{", ".join(sig_labels[:3])} etc. show significant seasonal differences',
                risk='Only two seasons covered',
                emphasis='Mechanism explanation (temperature, rainfall, microbial activity)',
                de_emphasis='Outlier analysis of individual sampling points',
            )
        options.append(option)
        return options

    def _extract_from_pca(self) -> list:
        """从PCA结果中提取动机选项"""
        if 'PCA' not in self.results:
            return []

        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', [])
        if len(var_ratio) < 2:
            return []

        cum_var = sum(var_ratio[:2]) * 100

        if self.language == 'zh':
            option = MotivationOption(
                option_id='',
                one_sentence=f'基于PCA识别校园污水管网碳污染物分布的关键控制因素',
                field_problem='影响碳污染物分布的关键因素不明确',
                specific_gap='缺乏多变量联合分析视角下的碳污染驱动因素识别',
                core_innovation=f'PCA前2主成分解释{cum_var:.1f}%方差，识别关键控制变量组合',
                evidence_support=f'PCA累计方差解释率{cum_var:.1f}%',
                risk='PCA仅反映变量间的线性关系',
                emphasis='主成分的物理解释和环境意义',
                de_emphasis='单变量的描述性分析',
            )
        else:
            option = MotivationOption(
                option_id='',
                one_sentence='Identify key controlling factors of carbon pollutant distribution via PCA',
                field_problem='Key factors controlling carbon pollutant distribution are unclear',
                specific_gap='Lack of multivariate perspective on carbon pollution drivers',
                core_innovation=f'PCA reveals key variable combinations explaining {cum_var:.1f}% variance',
                evidence_support=f'PCA cumulative variance explained: {cum_var:.1f}%',
                risk='PCA only captures linear relationships',
                emphasis='Physical interpretation of principal components',
                de_emphasis='Univariate descriptive analysis',
            )
        return [option]

    def _extract_from_carbon_balance(self) -> list:
        """从碳平衡分析中提取动机选项"""
        if '描述统计' not in self.results:
            return []

        desc = self.results['描述统计'].get('总体')
        if desc is None:
            return []

        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return []

        total = sum(phase_data.values())
        max_phase = max(phase_data, key=phase_data.get)
        max_pct = phase_data[max_phase] / total * 100

        if self.language == 'zh':
            option = MotivationOption(
                option_id='',
                one_sentence='揭示校园污水管网碳在固-液-气三相的分配格局及驱动机制',
                field_problem='管网中碳的输入-输出平衡关系不清楚',
                specific_gap='缺乏固-液-气三相碳分配比例的定量研究',
                core_innovation=f'定量揭示碳在三相的分配比例（{max_phase}占{max_pct:.1f}%为主导相）',
                evidence_support=f'碳平衡分析: {max_phase}占比{max_pct:.1f}%',
                risk='碳平衡计算基于简化模型',
                emphasis='碳相态分配的环境意义和管理启示',
                de_emphasis='绝对浓度的精确测定',
            )
        else:
            option = MotivationOption(
                option_id='',
                one_sentence='Reveal carbon distribution across solid-liquid-gas phases in campus sewage networks',
                field_problem='Carbon input-output balance in sewage networks is unclear',
                specific_gap='Lack of quantitative study on three-phase carbon distribution',
                core_innovation=f'Quantify carbon distribution ({max_phase} dominant at {max_pct:.1f}%)',
                evidence_support=f'Carbon balance: {max_phase} accounts for {max_pct:.1f}%',
                risk='Simplified mass-balance model',
                emphasis='Environmental implications of carbon phase distribution',
                de_emphasis='Precise measurement of absolute concentrations',
            )
        return [option]

    def _generate_generic_option(self, option_id: str) -> MotivationOption:
        """通用动机选项（兜底）"""
        if self.language == 'zh':
            return MotivationOption(
                option_id=option_id,
                one_sentence='系统表征校园污水管网固-液-气多相态碳污染物的赋存特征',
                field_problem='校园污水管网碳污染物的多相态赋存特征缺乏系统研究',
                specific_gap='缺乏固-液-气三相碳污染物的联合分析',
                core_innovation='首次对校园污水管网进行固-液-气三相碳污染物的系统联合分析',
                evidence_support='多相态采样+多元统计分析',
                risk='创新点不够突出',
                emphasis='多相态联合分析的方法论优势',
                de_emphasis='单一指标的深入机制',
            )
        return MotivationOption(
            option_id=option_id,
            one_sentence='Systematically characterize multiphase carbon pollutants in campus sewage networks',
            field_problem='Multiphase carbon pollutant characteristics in campus sewage networks lack systematic study',
            specific_gap='Lack of integrated solid-liquid-gas phase carbon analysis',
            core_innovation='First systematic three-phase carbon pollutant analysis in campus sewage networks',
            evidence_support='Multiphase sampling + multivariate statistical analysis',
            risk='Innovation may be insufficient',
            emphasis='Methodological advantage of multiphase analysis',
            de_emphasis='Deep mechanism of single indicators',
        )


# ============================================================================
# 动机确认管理器
# ============================================================================

class MotivationManager:
    """
    动机管理器 — 生成选项、确认动机、生成写作蓝图

    工作流：
    1. generate_options() → 生成3-5个选项
    2. confirm() → 用户确认/编辑/自写
    3. generate_blueprint() → 基于确认动机生成写作蓝图
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.options: list = []
        self.confirmed: Optional[ConfirmedMotivation] = None
        self.blueprint: Optional[WritingBlueprint] = None

    def generate_options(self, analysis_results: dict = None,
                        literature_matrix: str = "",
                        mechanisms=None, language: str = 'zh') -> list:
        """生成动机选项"""
        gen = MotivationGenerator(
            analysis_results=analysis_results,
            literature_matrix=literature_matrix,
            mechanisms=mechanisms,
            language=language,
        )
        self.options = gen.generate_options()

        # 保存选项
        self._save_options(language)
        return self.options

    def confirm(self, option_id: str = None, custom_motivation: str = None,
                edited_fields: dict = None) -> ConfirmedMotivation:
        """
        确认动机

        三种方式：
        1. option_id: 选择一个选项
        2. custom_motivation: 用户自写
        3. edited_fields: 基于某选项编辑
        """
        if custom_motivation:
            self.confirmed = ConfirmedMotivation(
                source='user_provided',
                motivation_statement=custom_motivation,
                red_thread=custom_motivation,
                field_problem='',
                specific_gap='',
                design_response='',
                main_evidence='',
            )
        elif option_id:
            selected = None
            for opt in self.options:
                if opt.option_id == option_id.upper():
                    selected = opt
                    break
            if not selected:
                raise ValueError(f"选项 {option_id} 不存在。可选: {[o.option_id for o in self.options]}")

            self.confirmed = ConfirmedMotivation(
                source='selected_option',
                motivation_statement=selected.one_sentence,
                red_thread=selected.one_sentence,
                field_problem=selected.field_problem,
                specific_gap=selected.specific_gap,
                design_response=selected.core_innovation,
                main_evidence=selected.evidence_support,
                rejected_options=[
                    {'option': o.one_sentence, 'reason': '未被选中'}
                    for o in self.options if o.option_id != option_id.upper()
                ],
            )

            if edited_fields:
                for k, v in edited_fields.items():
                    if hasattr(self.confirmed, k) and v:
                        setattr(self.confirmed, k, v)
                self.confirmed.source = 'edited_option'
        else:
            raise ValueError("需要 option_id 或 custom_motivation")

        # 生成各章节的动机约束
        self._generate_section_consequences()

        # 保存
        self._save_confirmed()
        return self.confirmed

    def generate_blueprint(self, language: str = 'zh') -> WritingBlueprint:
        """
        基于确认的动机生成写作蓝图

        这是 PaperSpine 的核心理念：写作蓝图是执行计划，不是事后回顾。
        """
        if not self.confirmed:
            raise ValueError("请先确认动机 (confirm) 再生成写作蓝图")

        blueprints = []

        if language == 'zh':
            # Introduction 蓝图
            blueprints.append(SectionBlueprint(
                section_name='Introduction / 绪论',
                communicative_job='建立研究必要性：从领域问题到研究空白到本研究',
                motivation_link=f'引出动机: {self.confirmed.field_problem} → {self.confirmed.specific_gap}',
                exemplar_pattern='漏斗结构: 背景→现状→空白→本研究',
                target_moves=[
                    '建立领域重要性（碳污染物/温室气体）',
                    '说明研究困难（多相态/管网复杂性）',
                    '综述已有方法的贡献',
                    '指出仍未解决的空白',
                    '提出本研究作为直接回应',
                    '预览证据和验证方法',
                ],
                evidence_items=[
                    '领域统计数据和政策背景',
                    '已有文献的关键发现',
                    '本研究的核心数据',
                ],
                style_constraints='学术正式，避免过度声明',
                target_length='1500-2000字',
            ))

            # Methods 蓝图
            blueprints.append(SectionBlueprint(
                section_name='Materials & Methods / 材料与方法',
                communicative_job='说明研究设计，每个选择都要回应动机',
                motivation_link=f'设计响应: {self.confirmed.design_response}',
                exemplar_pattern='分层结构: 区域→采样→分析→统计',
                target_moves=[
                    '描述研究区域（校园概况、管网布局）',
                    '说明采样方案（点位、时间、三相同步）',
                    '详述分析方法（气相/液相/固相标准方法）',
                    '说明统计方法（PCA/HCA/相关性/差异检验）',
                    '说明碳平衡计算方法',
                ],
                evidence_items=['采样点位图', '分析方法标准号', '统计参数'],
                style_constraints='精确、可重复、引用国标',
                target_length='1200-1500字',
            ))

            # Results 蓝图
            blueprints.append(SectionBlueprint(
                section_name='Results / 结果',
                communicative_job='展示数据发现，每个子节检验一个Introduction的承诺',
                motivation_link='提供证据支撑动机中的主张',
                exemplar_pattern='逻辑顺序: 描述→差异→相关→降维→平衡',
                target_moves=[
                    '描述性统计（三相碳污染物浓度范围和分布）',
                    '正态性检验（Shapiro-Wilk）',
                    '组间差异分析（冬春季节比较）',
                    '相关性分析（Pearson/Spearman）',
                    'PCA降维分析',
                    '碳平衡分析',
                ],
                evidence_items=['统计表', '相关矩阵', 'PCA载荷', '碳分配比例'],
                style_constraints='客观陈述，不解释机制（留给Discussion）',
                target_length='2000-2500字',
            ))

            # Discussion 蓝图
            blueprints.append(SectionBlueprint(
                section_name='Discussion / 讨论',
                communicative_job='解释发现的机制意义，闭合动机循环',
                motivation_link=f'解释发现如何支撑动机: {self.confirmed.motivation_statement}',
                exemplar_pattern='发现→机制→文献对比→意义',
                target_moves=[
                    f'核心发现概述（回应: {self.confirmed.motivation_statement[:30]}）',
                    '季节差异的机制解释（温度、微生物活性）',
                    '相关性的生物地球化学机制（DO-CH4、TOC-CH4）',
                    'PCA的环境意义解释',
                    '碳平衡的管理启示',
                    '局限性（诚实，但不削弱核心主张）',
                    '研究展望',
                ],
                evidence_items=[
                    self.confirmed.main_evidence,
                    'MechanismKB中的机制解释',
                    '文献引用支撑',
                ],
                style_constraints='每段都要有机制解释+文献支撑，避免空洞套话',
                target_length='2000-2500字',
            ))

            # Conclusion 蓝图
            blueprints.append(SectionBlueprint(
                section_name='Conclusion / 结论',
                communicative_job='闭合动机循环，返回到确认的动机',
                motivation_link=f'总结: {self.confirmed.red_thread}',
                exemplar_pattern='逐条总结+实践意义',
                target_moves=[
                    '逐条总结主要发现（对应Introduction的承诺）',
                    '强调核心主张（与动机红线呼应）',
                    '实践意义（碳减排/管网管理）',
                ],
                evidence_items=[self.confirmed.main_evidence],
                style_constraints='简洁有力，不引入新信息',
                target_length='300-500字',
            ))
        else:
            # English blueprints (similar structure)
            blueprints.append(SectionBlueprint(
                section_name='Introduction',
                communicative_job='Establish research necessity: from field problem to gap to this study',
                motivation_link=f'Introduce motivation: {self.confirmed.field_problem} → {self.confirmed.specific_gap}',
                exemplar_pattern='Funnel structure: background → state of art → gap → this study',
                target_moves=[
                    'Establish field importance (carbon pollutants / greenhouse gases)',
                    'Explain why the task is hard (multiphase / pipeline complexity)',
                    'Review what prior methods contributed',
                    'Identify unresolved gaps',
                    'Present this study as a direct response',
                    'Preview evidence and validation approach',
                ],
                evidence_items=['Domain statistics', 'Key literature findings', 'Core data'],
                style_constraints='Academic formal, avoid overclaiming',
                target_length='1500-2000 words',
            ))

            blueprints.append(SectionBlueprint(
                section_name='Discussion',
                communicative_job='Interpret findings and close the motivation loop',
                motivation_link=f'Explain how findings support: {self.confirmed.motivation_statement}',
                exemplar_pattern='Finding → mechanism → literature comparison → implication',
                target_moves=[
                    'Core findings overview',
                    'Mechanism explanation for key findings',
                    'Comparison with prior work',
                    'Limitations (honest, but do not undermine core claim)',
                    'Future work',
                ],
                evidence_items=[self.confirmed.main_evidence, 'Mechanism explanations', 'Literature support'],
                style_constraints='Every paragraph needs mechanism + citation, avoid empty platitudes',
                target_length='2000-2500 words',
            ))

        # 生成全局框架理由
        if language == 'zh':
            framework_rationale = (
                f'本文以"{self.confirmed.motivation_statement}"为核心动机，'
                f'采用"问题-空白-设计-证据-解释"的逻辑弧线组织全文。'
                f'Introduction从{self.confirmed.field_problem}出发，'
                f'逐步收窄到{self.confirmed.specific_gap}，'
                f'提出{self.confirmed.design_response}作为设计响应。'
                f'Results按逻辑顺序展示证据，每个子节检验一个Introduction的承诺。'
                f'Discussion用机制解释串联发现，闭合动机循环。'
                f'Conclusion返回动机红线，形成首尾呼应。'
            )
        else:
            framework_rationale = (
                f'This paper is organized around the motivation: "{self.confirmed.motivation_statement}". '
                f'The logical arc follows: problem → gap → design → evidence → interpretation. '
                f'Introduction narrows from {self.confirmed.field_problem} to {self.confirmed.specific_gap}. '
                f'Results present evidence in logical order, each subsection testing an Introduction promise. '
                f'Discussion interprets findings through mechanism explanations, closing the motivation loop. '
                f'Conclusion returns to the red thread for closure.'
            )

        self.blueprint = WritingBlueprint(
            confirmed_motivation=self.confirmed,
            section_blueprints=blueprints,
            global_framework_rationale=framework_rationale,
        )

        # 保存
        self._save_blueprint()
        return self.blueprint

    def _generate_section_consequences(self):
        """为每个章节生成动机约束"""
        if not self.confirmed:
            return

        m = self.confirmed
        if 'zh' in (m.field_problem + m.motivation_statement):
            m.section_consequences = {
                'Abstract': {
                    'requires': f'开篇点明{m.field_problem[:20]}，结尾总结{m.motivation_statement[:30]}',
                    'avoid': '不引入正文未涉及的结果',
                },
                'Introduction': {
                    'requires': f'从{m.field_problem[:20]}逐步收窄到{m.specific_gap[:20]}',
                    'avoid': '不堆砌文献，不跳过空白直接写方法',
                },
                'Methods': {
                    'requires': f'每个方法选择回应{m.design_response[:20]}',
                    'avoid': '不写成代码文档，不缺少标准号',
                },
                'Results': {
                    'requires': '每个子节检验Introduction的一个承诺',
                    'avoid': '不做机制解释（留给Discussion），不遗漏核心数据',
                },
                'Discussion': {
                    'requires': f'用机制解释串联发现，支撑{m.motivation_statement[:20]}',
                    'avoid': '不重复Results数据，不用空洞套话',
                },
                'Conclusion': {
                    'requires': f'返回动机红线: {m.red_thread[:30]}',
                    'avoid': '不引入新信息，不过度推广',
                },
            }
        else:
            m.section_consequences = {
                'Abstract': {
                    'requires': f'Open with {m.field_problem[:30]}, close with {m.motivation_statement[:30]}',
                    'avoid': 'No results not presented in main text',
                },
                'Introduction': {
                    'requires': f'Narrow from {m.field_problem[:30]} to {m.specific_gap[:30]}',
                    'avoid': 'No literature dump, no skipping gap to methods',
                },
                'Discussion': {
                    'requires': f'Mechanism explanations supporting {m.motivation_statement[:30]}',
                    'avoid': 'No repeating Results data, no empty platitudes',
                },
            }

    def _save_options(self, language: str = 'zh'):
        """保存动机选项"""
        path = os.path.join(self.output_dir, 'motivation_options.json')
        data = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'language': language,
            'options': [asdict(o) for o in self.options],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Markdown 版本
        md_path = os.path.join(self.output_dir, 'motivation_options.md')
        lines = [
            "# 动机选项 (Motivation Options)" if language == 'zh' else "# Motivation Options",
            "",
            "> 请从以下选项中选择一个作为论文的核心动机，或自行编写。",
            "",
        ]
        if language == 'zh':
            lines.append("| 选项 | 一句话动机 | 领域问题 | 研究空白 | 核心创新 | 风险 |")
            lines.append("|------|----------|---------|---------|---------|------|")
        else:
            lines.append("| Option | One-Sentence Motivation | Field Problem | Specific Gap | Core Innovation | Risk |")
            lines.append("|--------|------------------------|---------------|--------------|-----------------|------|")

        for opt in self.options:
            lines.append(opt.to_markdown_row())

        lines.extend([
            "",
            "## 用户决策" if language == 'zh' else "## User Decision",
            "",
            "选择一个选项，编辑一个选项，或写一个新的动机。" if language == 'zh' else
            "Choose one option, edit one option, or write a new motivation.",
        ])

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _save_confirmed(self):
        """保存确认的动机"""
        if not self.confirmed:
            return

        # JSON
        path = os.path.join(self.output_dir, 'confirmed_motivation.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.confirmed), f, ensure_ascii=False, indent=2)

        # Markdown
        md_path = os.path.join(self.output_dir, 'confirmed_motivation.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self.confirmed.to_markdown())

    def _save_blueprint(self):
        """保存写作蓝图"""
        if not self.blueprint:
            return

        # 写作蓝图
        md_path = os.path.join(self.output_dir, 'writing_blueprint.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self.blueprint.to_markdown())

        # 执行表
        table_path = os.path.join(self.output_dir, 'writing_execution_table.md')
        with open(table_path, 'w', encoding='utf-8') as f:
            f.write(self.blueprint.to_execution_table())

    def load(self) -> bool:
        """从文件加载已有状态"""
        # 加载确认的动机
        path = os.path.join(self.output_dir, 'confirmed_motivation.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.confirmed = ConfirmedMotivation(**data)
            return True
        return False


# ============================================================================
# 辅助函数
# ============================================================================

def _get_var_label(var: str, language: str = 'zh') -> str:
    """获取变量的可读标签"""
    labels_zh = {
        'TOC': '总有机碳(TOC)', 'DOC': '溶解性有机碳(DOC)',
        'COD': '化学需氧量(COD)', 'TN': '总氮(TN)',
        'NH4+': '铵态氮(NH4+)', 'DO': '溶解氧(DO)',
        'CH4': '甲烷(CH4)', 'CO2': '二氧化碳(CO2)',
        'O2': '氧气(O2)', 'pH': 'pH值',
        '气相碳': '气相碳', '液相碳': '液相碳', '固相碳': '固相碳',
    }
    labels_en = {
        'TOC': 'Total Organic Carbon', 'DOC': 'Dissolved Organic Carbon',
        'COD': 'Chemical Oxygen Demand', 'TN': 'Total Nitrogen',
        'NH4+': 'Ammonium Nitrogen', 'DO': 'Dissolved Oxygen',
        'CH4': 'Methane', 'CO2': 'Carbon Dioxide',
        'O2': 'Oxygen', 'pH': 'pH',
    }
    labels = labels_zh if language == 'zh' else labels_en
    for key, label in labels.items():
        if key in str(var):
            return label
    return str(var)


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        # 模拟测试
        import pandas as pd
        import numpy as np

        # 模拟分析结果
        np.random.seed(42)
        vars = ['TOC', 'DOC', 'DO', 'CH4', 'CO2', 'TN']
        corr_data = np.random.randn(6, 6)
        corr = pd.DataFrame(
            np.corrcoef(corr_data), index=vars, columns=vars
        )
        pvals = pd.DataFrame(
            np.random.uniform(0.001, 0.1, (6, 6)), index=vars, columns=vars
        )
        # 让DO-CH4有强负相关
        corr.loc['DO', 'CH4'] = -0.72
        corr.loc['CH4', 'DO'] = -0.72
        pvals.loc['DO', 'CH4'] = 0.001
        pvals.loc['CH4', 'DO'] = 0.001

        mock_results = {
            'pearson相关': {'相关系数': corr, 'p值': pvals},
            '组间比较': pd.DataFrame({
                '变量': ['TOC', 'DOC', 'CH4'],
                '显著性': ['**', '*', '***'],
                '冬季_均值': [45.2, 32.1, 1.8],
                '春季_均值': [38.5, 28.3, 2.5],
            }),
            'PCA': {'explained_variance_ratio': [0.45, 0.28, 0.12]},
            '描述统计': {
                '总体': pd.DataFrame({
                    '气相碳': [2.5, 1.2],
                    '液相碳': [35.0, 8.5],
                    '固相碳': [15.0, 5.2],
                }, index=['mean', 'std']),
            },
        }

        # 测试动机生成
        mgr = MotivationManager(output_dir='/tmp/test_motivation')
        options = mgr.generate_options(
            analysis_results=mock_results, language='zh'
        )

        print("=" * 60)
        print("生成的动机选项:")
        print("=" * 60)
        for opt in options:
            print(f"\n[{opt.option_id}] {opt.one_sentence}")
            print(f"  问题: {opt.field_problem[:50]}")
            print(f"  空白: {opt.specific_gap[:50]}")
            print(f"  创新: {opt.core_innovation[:50]}")
            print(f"  证据: {opt.evidence_support[:50]}")
            print(f"  风险: {opt.risk}")

        # 测试确认
        print("\n" + "=" * 60)
        print("确认选项 A:")
        print("=" * 60)
        confirmed = mgr.confirm(option_id='A')
        print(confirmed.to_markdown())

        # 测试写作蓝图
        print("\n" + "=" * 60)
        print("生成写作蓝图:")
        print("=" * 60)
        blueprint = mgr.generate_blueprint(language='zh')
        print(blueprint.to_markdown()[:2000])
        print("...")
        print("\n执行表预览:")
        print(blueprint.to_execution_table()[:1500])

        print("\n测试通过!")
    else:
        print("用法: python motivation_planner.py --test")
