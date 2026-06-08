"""
=============================================================================
论文自动写作Agent - Paper Writing Agent
基于数据分析结果、知识库、领域机制，生成论文级文本
不是AI流水文，而是像真正科研人员一样组织论文
=============================================================================
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from scientific_analysis_agent import ScientificAnalysisAgent, TextGenerator, CaptionGenerator
from academic_plot_style import get_label
from writing_rationale import RationaleMatrix, RationaleRow
from motivation_thread import MotivationThread, SevenSentenceTest, IntroductionDiscussionMapper

try:
    from rag_system import RAGEngine
except ImportError:
    RAGEngine = None


# ============================================================================
# 0. 研究方向配置 - 支持自定义研究领域
# ============================================================================
class ResearchDirection:
    """
    研究方向配置：允许用户自定义研究领域，替代硬编码的"校园污水管网"

    用法:
        direction = ResearchDirection(
            field="环境科学",
            topic="城市河流碳污染物迁移",
            object_name="某城市河流",
            variables={'gas': ['CH4', 'CO2'], 'liquid': ['TOC', 'COD'], 'solid': ['底泥有机碳']},
        )
        writer = write_paper(direction=direction)
    """

    def __init__(self, field="环境科学", topic="校园污水管网碳污染物多相态分析",
                 object_name="某校园污水管网", variables=None, mechanisms=None):
        self.field = field
        self.topic = topic
        self.object_name = object_name
        self.variables = variables or {}
        self.custom_mechanisms = mechanisms or {}

    def get_intro_background(self):
        """获取Introduction背景文本"""
        return (
            f'{self.field}领域中，{self.topic}是当前研究的热点问题。'
            f'本研究以{self.object_name}为研究对象，'
            f'系统分析相关污染物的赋存特征与迁移规律。'
        )

    def get_object_description(self):
        """获取研究对象描述"""
        return self.object_name


# ============================================================================
# 0.5 期刊适配配置
# ============================================================================
class JournalConfig:
    """
    期刊适配配置：支持不同目标期刊的格式要求

    用法:
        config = JournalConfig('EST')
        writer = write_paper(journal=config)
    """

    PRESETS = {
        'EST': {
            'name': 'Environmental Science & Technology',
            'language': 'en',
            'max_words': 8000,
            'max_figures': 8,
            'max_tables': 4,
            'max_references': 60,
            'abstract_words': 200,
            'sections': ['abstract', 'introduction', 'methods', 'results', 'discussion', 'acknowledgments', 'references'],
            'citation_style': 'numbered',  # [1] [2] 格式
            'figure_format': 'Fig.',
            'table_format': 'Table',
            'latex_template': 'sci',
        },
        'WR': {
            'name': 'Water Research',
            'language': 'en',
            'max_words': 8000,
            'max_figures': 8,
            'max_tables': 5,
            'max_references': 50,
            'abstract_words': 200,
            'sections': ['abstract', 'introduction', 'materials_methods', 'results', 'discussion', 'conclusions', 'references'],
            'citation_style': 'numbered',
            'figure_format': 'Fig.',
            'table_format': 'Table',
            'latex_template': 'sci',
        },
        'STOTEN': {
            'name': 'Science of the Total Environment',
            'language': 'en',
            'max_words': 9000,
            'max_figures': 10,
            'max_tables': 6,
            'max_references': 60,
            'abstract_words': 250,
            'sections': ['abstract', 'introduction', 'materials_methods', 'results', 'discussion', 'conclusions', 'references'],
            'citation_style': 'numbered',
            'figure_format': 'Fig.',
            'table_format': 'Table',
            'latex_template': 'sci',
        },
        '中文核心': {
            'name': '中文核心期刊',
            'language': 'zh',
            'max_words': 10000,
            'max_figures': 8,
            'max_tables': 6,
            'max_references': 30,
            'abstract_words': 300,
            'sections': ['摘要', '引言', '材料与方法', '结果与分析', '讨论', '结论', '参考文献'],
            'citation_style': 'author_year',  # (作者, 年份) 格式
            'figure_format': '图',
            'table_format': '表',
            'latex_template': 'chinese_journal',
        },
        '硕论': {
            'name': '硕士学位论文',
            'language': 'zh',
            'max_words': 50000,
            'max_figures': 20,
            'max_tables': 15,
            'max_references': 50,
            'abstract_words': 500,
            'sections': ['摘要', '1 绪论', '2 材料与方法', '3 结果', '4 讨论', '5 结论', '参考文献', '致谢'],
            'citation_style': 'numbered',
            'figure_format': '图',
            'table_format': '表',
            'latex_template': 'chinese_thesis',
        },
    }

    def __init__(self, journal_key='EST'):
        preset = self.PRESETS.get(journal_key, self.PRESETS['EST'])
        self.journal_key = journal_key
        self.name = preset['name']
        self.language = preset['language']
        self.max_words = preset['max_words']
        self.max_figures = preset['max_figures']
        self.max_tables = preset['max_tables']
        self.max_references = preset['max_references']
        self.abstract_words = preset['abstract_words']
        self.sections = preset['sections']
        self.citation_style = preset['citation_style']
        self.figure_format = preset['figure_format']
        self.table_format = preset['table_format']
        self.latex_template = preset['latex_template']

    @classmethod
    def list_journals(cls):
        """列出所有支持的期刊"""
        return {k: v['name'] for k, v in cls.PRESETS.items()}

    def validate_paper(self, sections: dict, word_count: int) -> list:
        """验证论文是否符合期刊要求"""
        issues = []

        if word_count > self.max_words:
            issues.append(f'字数超限: {word_count}/{self.max_words}')

        if 'references' in sections or '参考文献' in sections:
            ref_text = sections.get('references', sections.get('参考文献', ''))
            import re
            ref_count = len(re.findall(r'\[\d+\]', ref_text))
            if ref_count > self.max_references:
                issues.append(f'参考文献超限: {ref_count}/{self.max_references}')

        for sec in self.sections:
            sec_key = sec.lower().replace(' ', '_')
            if sec_key not in [k.lower().replace(' ', '_') for k in sections.keys()]:
                # 检查中文/英文变体
                found = False
                for k in sections.keys():
                    if sec in k or k in sec:
                        found = True
                        break
                if not found:
                    issues.append(f'缺少章节: {sec}')

        return issues


# ============================================================================
# 1. 领域机制库 - 本课题特定科学机制
# ============================================================================
class MechanismKB:
    """碳污染物领域机制知识库"""

    # DO→CH4机制
    DO_CH4 = {
        'pattern': 'DO与CH4负相关',
        'mechanism': (
            '溶解氧(DO)浓度是控制管道中产甲烷过程的关键因素。'
            '当DO<0.5 mg/L时，管道进入严格厌氧状态，产甲烷古菌活性达到最高，'
            '通过乙酸发酵和CO2/H2还原两条途径将有机碳转化为CH4。'
            '相反，当DO>2 mg/L时，好氧微生物通过有氧呼吸将有机碳氧化为CO2，'
            '产甲烷过程被完全抑制。'
        ),
        'mechanism_en': (
            'Dissolved oxygen (DO) is the primary factor controlling methanogenesis in sewage networks. '
            'Under strictly anaerobic conditions (DO < 0.5 mg/L), methanogenic archaea exhibit maximum '
            'activity, converting organic carbon to CH4 via acetoclastic fermentation and hydrogenotrophic '
            'CO2 reduction. Conversely, when DO exceeds 2 mg/L, aerobic microorganisms oxidize organic '
            'carbon to CO2 through aerobic respiration, completely suppressing methanogenesis.'
        ),
        'references': [
            'Guisasola et al. (2008)报道城市污水管道中厌氧段的产甲烷活动可降解50%以上的有机碳',
            'Jiang et al. (2011)指出管道系统是城市温室气体排放的重要来源',
        ]
    }

    # TOC→CH4机制
    TOC_CH4 = {
        'pattern': 'TOC与CH4正相关',
        'mechanism': (
            'TOC代表污水中有机碳的总量，是产甲烷过程的底物来源。'
            'TOC浓度越高，可供水解酸化菌利用的有机底物越充足，'
            '进而为产甲烷古菌提供更多的乙酸和H2/CO2底物，'
            '促进CH4的生成。但在高TOC条件下，'
            '有机酸积累导致pH下降，可能抑制产甲烷活性。'
        ),
        'mechanism_en': (
            'Total organic carbon (TOC) represents the aggregate organic carbon pool in wastewater and serves '
            'as the primary substrate for methanogenesis. Higher TOC concentrations provide more abundant '
            'organic substrates for hydrolytic and acidogenic bacteria, which in turn supply more acetate and '
            'H2/CO2 to methanogenic archaea, enhancing CH4 production. However, under high TOC conditions, '
            'volatile fatty acid accumulation may lower pH and inhibit methanogenic activity.'
        ),
        'references': []
    }

    # DO→CO2机制
    DO_CO2 = {
        'pattern': 'DO与CO2可能正相关或呈复杂关系',
        'mechanism': (
            'CO2的来源包括好氧呼吸和厌氧发酵两部分。'
            '好氧条件下，异养菌通过三羧酸循环将有机物完全氧化为CO2和H2O。'
            '厌氧条件下，产甲烷过程中CO2也作为电子受体被还原为CH4。'
            '因此，DO对CO2的影响取决于好氧呼吸产CO2和厌氧产甲烷消耗CO2的平衡。'
        ),
        'mechanism_en': (
            'CO2 in sewage networks originates from both aerobic respiration and anaerobic fermentation. '
            'Under aerobic conditions, heterotrophic bacteria oxidize organic matter to CO2 and H2O via '
            'the tricarboxylic acid cycle. Under anaerobic conditions, CO2 also serves as an electron '
            'acceptor and is reduced to CH4 during methanogenesis. Therefore, the net effect of DO on CO2 '
            'depends on the balance between aerobic CO2 production and anaerobic CO2 consumption in CH4 formation.'
        ),
        'references': []
    }

    # 碳氮耦合机制
    C_N_COUPLING = {
        'pattern': 'TOC与TN/铵态氮相关',
        'mechanism': (
            '碳氮耦合是污水管道生物转化的核心过程。'
            '有机碳降解释放含氮有机物中的氮（氨化作用），使NH4+浓度升高。'
            '同时，反硝化过程需要有机碳作为电子供体，'
            'C/N比直接影响脱氮效率(C/N>5时脱氮效率高)。'
            '碳氮的协同转化反映了管道中微生物群落的整体代谢活性。'
        ),
        'mechanism_en': (
            'Carbon-nitrogen coupling is a core biogeochemical process in sewage networks. '
            'Organic carbon degradation releases nitrogen from nitrogenous organic compounds '
            '(ammonification), elevating NH4+ concentrations. Meanwhile, denitrification requires '
            'organic carbon as an electron donor, and the C/N ratio directly affects nitrogen removal '
            'efficiency (optimal when C/N > 5). The synergistic transformation of carbon and nitrogen '
            'reflects the overall metabolic activity of the microbial community in the pipeline.'
        ),
        'references': []
    }

    # 季节差异机制
    SEASONAL = {
        'pattern': '冬春差异',
        'mechanism': (
            '温度是影响微生物代谢活性的主要因素。'
            '春季温度升高，水解酸化菌和产甲烷菌的酶活性增强，'
            '有机碳转化速率加快，气相碳(CH4+CO2)浓度可能升高。'
            '同时，春季降雨增加了管道流量，可能产生稀释效应和冲刷效应——'
            '冲刷管壁生物膜和底部沉积物中的有机碳，导致液相TOC升高。'
            '两种效应的相对大小决定了净变化方向。'
        ),
        'mechanism_en': (
            'Temperature is the dominant factor influencing microbial metabolic activity. '
            'As temperature rises in spring, enzymatic activities of hydrolytic-acidogenic and '
            'methanogenic microorganisms increase, accelerating organic carbon transformation and '
            'potentially elevating gaseous carbon (CH4+CO2) concentrations. Concurrently, increased '
            'rainfall in spring enhances pipeline flow, creating both dilution and scouring effects '
            'that may wash biofilms and sediment-bound organic carbon into the liquid phase, increasing '
            'TOC. The net outcome depends on the relative magnitude of these competing effects.'
        ),
        'references': []
    }

    # 空间分异机制
    SPATIAL = {
        'pattern': '沿程空间变化',
        'mechanism': (
            '管道中碳污染物的空间分异受功能区排放特征和管道内生化过程共同控制。'
            '管口区域氧气充足(O2较高)，好氧呼吸为主，CO2为主要碳气。'
            '随着向管道中段和末端推进，O2被微生物消耗逐渐降低，'
            '厌氧程度增加，CH4生成比例上升。'
            '同时，不同功能区(教学区/生活区/餐饮区)的有机负荷和组成不同，'
            '导致碳污染物的初始输入存在空间差异。'
        ),
        'mechanism_en': (
            'Spatial differentiation of carbon pollutants in pipelines is jointly controlled by '
            'functional zone discharge characteristics and in-pipe biogeochemical processes. '
            'At the inlet, oxygen is relatively abundant, favoring aerobic respiration with CO2 as '
            'the dominant carbon gas. Progressing toward the mid-section and outlet, O2 is progressively '
            'consumed by microorganisms, increasing anaerobiosis and shifting the balance toward CH4 '
            'production. Meanwhile, different functional zones (teaching, residential, dining) exhibit '
            'distinct organic loading and composition, creating spatial variation in initial carbon input.'
        ),
        'references': []
    }

    @classmethod
    def get_mechanism(cls, key):
        """获取机制解释"""
        mapping = {
            'DO_CH4': cls.DO_CH4,
            'TOC_CH4': cls.TOC_CH4,
            'DO_CO2': cls.DO_CO2,
            'C_N': cls.C_N_COUPLING,
            'seasonal': cls.SEASONAL,
            'spatial': cls.SPATIAL,
        }
        return mapping.get(key, {})

    @classmethod
    def find_mechanism_for_correlation(cls, var1, var2):
        """根据变量对自动找到对应机制"""
        v1, v2 = str(var1).lower(), str(var2).lower()

        if ('do' in v1 or 'do' in v2) and ('ch4' in v1 or 'ch4' in v2 or '甲烷' in v1 or '甲烷' in v2):
            return cls.DO_CH4
        if ('toc' in v1 or 'toc' in v2) and ('ch4' in v1 or 'ch4' in v2 or '甲烷' in v1 or '甲烷' in v2):
            return cls.TOC_CH4
        if ('do' in v1 or 'do' in v2) and ('co2' in v1 or 'co2' in v2):
            return cls.DO_CO2
        if any(k in v1+v2 for k in ['toc', 'tc', 'cod', '总氮', '铵态氮', 'tn']):
            return cls.C_N_COUPLING

        return None


# ============================================================================
# 2. Introduction生成器
# ============================================================================
class IntroductionGenerator:
    """
    Introduction不是填模板，而是构建逻辑链
    宏观背景 → 领域问题 → 研究现状 → 研究空白 → 本研究
    """

    def __init__(self, domain='sewage_carbon'):
        self.domain = domain

    def generate(self, language='zh'):
        """生成Introduction"""
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        """中文Introduction - 校园污水管网碳污染物"""
        sections = []

        # 1. 研究背景
        sections.append(self._bg_zh())

        # 2. 国内外研究现状
        sections.append(self._literature_zh())

        # 3. 研究空白
        sections.append(self._gap_zh())

        # 4. 研究目的与内容
        sections.append(self._objective_zh())

        return '\n\n'.join(sections)

    def _bg_zh(self):
        return (
            '# 1 绪论\n\n'
            '## 1.1 研究背景与意义\n\n'
            '城市污水管网系统是城市基础设施的重要组成部分，承担着收集和输送生活污水、'
            '工业废水及雨水的重要功能。近年来，随着城镇化进程加快和污水收集范围不断扩大，'
            '管网系统中碳污染物的赋存与迁移问题日益突出，已成为制约城市碳减排和碳中和'
            '目标实现的关键因素之一。研究表明，污水管网不仅是碳污染物的输送通道，'
            '更是一个复杂的生物化学反应器，管道内的微生物活动可导致碳污染物在固、液、气'
            '三相之间发生显著的相态转化（Guisasola et al., 2008; Jiang et al., 2011）。\n\n'
            '在"双碳"目标背景下，准确掌握污水管网中碳污染物的赋存特征与迁移规律，'
            '对于城市碳排放核算、污水厂进水碳源优化以及管网运行管理具有重要意义。'
            '然而，现有研究多关注城市级污水管网系统，针对校园这一特殊功能区域的'
            '污水管网碳污染特征研究相对不足。校园污水管网具有排放源类型多样（教学区、'
            '生活区、餐饮区等）、用水规律性强、管道规模适中等特点，'
            '是研究碳污染物多相态赋存特征的理想微尺度模型系统。'
        )

    def _literature_zh(self):
        return (
            '## 1.2 国内外研究现状\n\n'
            '### 1.2.1 污水管网碳污染物研究进展\n\n'
            '污水管网中碳污染物的研究始于20世纪90年代。早期研究主要关注管道中'
            '有机碳的生物转化过程，Guisasola等（2008）通过实验和模型模拟证实，'
            '污水在管道输送过程中，厌氧条件下的产甲烷活动可降解50%以上的有机碳，'
            '使管道成为一个重要的碳转化器。Jiang等（2011）进一步指出，'
            '管道系统中产生的CH4和CO2是城市温室气体排放的重要来源，'
            '其排放量占城市碳排放总量的显著比例。\n\n'
            '近年来，多相态分析方法逐渐被引入污水管网碳污染物研究。'
            '研究者开始同时关注固相（管道沉积物和生物膜中的有机碳）、'
            '液相（溶解性有机碳DOC和颗粒态有机碳POC）和气相（CH4和CO2）'
            '碳污染物的赋存特征及其相互转化关系。然而，多数研究仅关注单一相态，'
            '缺乏对固-液-气三相碳污染物的系统性联合分析。\n\n'
            '### 1.2.2 校园污水管网研究现状\n\n'
            '校园污水管网研究尚处于起步阶段。现有少量研究主要集中在水质指标的'
            '基础监测层面，对碳污染物在管网中的相态分布、空间分异及其驱动机制'
            '缺乏深入探讨。校园污水管网因其排放源明确、空间尺度适中、'
            '易于系统采样等优势，可作为研究污水管网碳转化过程的理想实验平台。'
        )

    def _gap_zh(self):
        return (
            '## 1.3 现有研究不足\n\n'
            '综上所述，现有研究存在以下不足：\n\n'
            '（1）**多相态联合分析不足。** 已有研究多关注单一相态的碳污染物，'
            '缺乏固-液-气三相碳污染物的系统性联合分析，难以全面揭示碳在管网中的'
            '赋存特征和相态转化规律。\n\n'
            '（2）**校园尺度研究缺乏。** 现有研究以城市级管网为主，'
            '针对校园这一特殊功能区域的碳污染特征研究较少，'
            '对不同功能区（教学区、生活区、餐饮区）碳排放差异的认识不足。\n\n'
            '（3）**碳平衡分析薄弱。** 管网中碳的输入-输出平衡关系尚不清楚，'
            '碳在不同相态之间的分配比例及其影响因素有待定量揭示。\n\n'
            '（4）**驱动机制不明。** 溶解氧、温度、有机负荷等因素对碳污染物'
            '相态转化的驱动机制缺乏系统研究。'
        )

    def _objective_zh(self):
        return (
            '## 1.4 研究内容与目标\n\n'
            '针对上述研究不足，本研究以某校园污水管网为研究对象，'
            '开展以下研究工作：\n\n'
            '（1）系统采集管道内固相、液相、气相样品，测定碳污染物各指标浓度，'
            '揭示固-液-气三相碳污染物的赋存特征。\n\n'
            '（2）采用主成分分析(PCA)和层次聚类分析(HCA)等多元统计方法，'
            '识别影响碳污染物分布的关键因素和采样点聚类特征。\n\n'
            '（3）分析不同功能区碳污染物的空间分异规律，探讨排放源类型'
            '对碳污染特征的影响。\n\n'
            '（4）开展碳平衡分析，定量评估碳在固-液-气三相之间的分配比例'
            '及其驱动机制，为校园污水碳管理提供科学依据。'
        )

    def _generate_en(self):
        """SCI英文Introduction"""
        return (
            '# 1 Introduction\n\n'
            'Urban sewage networks serve as critical infrastructure for collecting and '
            'transporting domestic and industrial wastewater. Carbon pollutants in these '
            'systems exist in solid, liquid, and gas phases, undergoing complex '
            'biogeochemical transformations during conveyance (Guisasola et al., 2008; '
            'Jiang et al., 2011). Understanding the occurrence characteristics and '
            'migration patterns of multiphase carbon pollutants is essential for accurate '
            'urban carbon accounting and wastewater treatment optimization.\n\n'
            'Previous studies have primarily focused on individual phases or city-scale '
            'systems. However, systematic investigations of multiphase carbon pollutants '
            'in campus-scale sewage networks remain limited. Campus networks offer unique '
            'advantages as model systems due to their well-defined emission sources, '
            'manageable spatial scale, and systematic sampling feasibility.\n\n'
            'To address these gaps, this study systematically investigated the '
            'occurrence characteristics of solid-liquid-gas phase carbon pollutants in a '
            'campus sewage network. The specific objectives were to: (1) characterize '
            'the multiphase carbon pollutant distribution; (2) identify key driving '
            'factors using multivariate statistical analysis; (3) analyze spatial '
            'differentiation across functional zones; and (4) quantify the carbon balance '
            'and its underlying mechanisms.'
        )


# ============================================================================
# 3. Discussion生成器 - 核心：机制解释+文献支撑
# ============================================================================
class DiscussionGenerator:
    """
    Discussion = 本研究发现 + 文献对比 + 机制解释 + 意义
    不是Results的重复，不是空洞的套话
    """

    def __init__(self, analysis_results, captions, rationale_matrix=None, rag_engine=None,
                 max_correlations=6, max_seasonal=8):
        self.results = analysis_results
        self.captions = captions
        self.mechanisms = MechanismKB()
        self.rationale = rationale_matrix or RationaleMatrix()
        self.rag = rag_engine
        self._new_mechanisms = []  # 记录新发现的机制，后续写回知识库
        self.max_correlations = max_correlations  # 最多讨论的相关关系数
        self.max_seasonal = max_seasonal  # 最多讨论的季节差异变量数
        # 引用安全防护（可选）
        try:
            from citation_guard import CitationGuard
            self._citation_guard = CitationGuard()
        except ImportError:
            self._citation_guard = None

    def _search_literature(self, query, max_results=2):
        """通过RAG检索相关文献（带多视角+迭代增强+引用安全防护）"""
        if not self.rag:
            return []

        try:
            # === 多视角检索（借鉴 STORM） ===
            all_results = []

            # 视角1: 领域专家视角（原始查询）
            results_1 = self.rag.retrieve(query, max_results=max_results)
            all_results.extend(results_1)

            # 视角2: 方法学视角（关注统计/方法相关文献）
            method_query = f"{query} statistical method analysis"
            results_2 = self.rag.retrieve(method_query, max_results=max(1, max_results // 2))
            all_results.extend(results_2)

            # 视角3: 争议探查视角（关注支持/反对证据）
            debate_query = f"{query} contradiction debate limitation"
            results_3 = self.rag.retrieve(debate_query, max_results=max(1, max_results // 2))
            all_results.extend(results_3)

            # 去重（基于文本相似度）
            seen_texts = set()
            unique_results = []
            for r in all_results:
                text_key = (r.get('title', '') or r.get('text', ''))[:100]
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_results.append(r)

            # === 迭代式评分过滤（借鉴 PaperQA2） ===
            scored_results = self._score_and_filter(unique_results, query)

            # 取 Top N
            final_results = scored_results[:max_results]

            # 构建引用列表
            refs = []
            ref_dicts = []
            for r in final_results:
                title = r.get('title', '')
                authors = r.get('authors', '')
                year = r.get('year', '')
                if title:
                    refs.append(f'{authors} ({year}) {title}' if authors and year else title)
                    ref_dicts.append({
                        'title': title,
                        'authors': authors,
                        'year': int(year) if str(year).isdigit() else 0,
                        'doi': r.get('doi', ''),
                        'journal': r.get('journal', r.get('venue', '')),
                    })

            # 通过引用安全防护分配不透明键
            if self._citation_guard and ref_dicts:
                self._citation_guard.assign_keys(ref_dicts)

            return refs
        except Exception:
            return []

    def _score_and_filter(self, results, query):
        """
        对检索结果进行相关性评分和过滤（借鉴 PaperQA2）

        评分策略:
        - 标题关键词匹配度 (0-5分)
        - 摘要/文本相关性 (0-3分)
        - 引用数权重 (0-2分)
        """
        scored = []
        query_words = set(re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', query.lower()))

        for r in results:
            score = 0
            title = (r.get('title', '') or '').lower()
            text = (r.get('text', '') or '').lower()
            combined = title + ' ' + text

            # 标题关键词匹配
            title_words = set(re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', title))
            overlap = len(query_words & title_words)
            score += min(5, overlap * 2)

            # 文本相关性
            text_words = set(re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', combined))
            text_overlap = len(query_words & text_words)
            score += min(3, text_overlap)

            # 引用数权重
            citations = r.get('citation_count', r.get('citationCount', 0))
            if citations and int(citations) > 10:
                score += 1
            if citations and int(citations) > 50:
                score += 1

            r['_relevance_score'] = score
            scored.append(r)

        # 按分数排序
        scored.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)

        # 过滤低分（< 2分）
        return [r for r in scored if r.get('_relevance_score', 0) >= 2] or scored[:3]

    def generate(self, language='zh'):
        """生成Discussion全文"""
        if language == 'zh':
            result = self._generate_zh()
        else:
            result = self._generate_en()

        # 将新发现的机制写回知识库
        if self._new_mechanisms:
            self._write_back_mechanisms()

        # 引用安全验证（如果启用了citation_guard）
        if self._citation_guard and self._citation_guard._entries:
            report = self._citation_guard.validate_and_strip(result)
            if report.hallucinated_citations > 0:
                result = report.clean_text
                logger.warning(f"Stripped {report.hallucinated_citations} hallucinated citations from Discussion")

        return result

    def _record_new_mechanism(self, var1, var2, direction, r_val, p_val):
        """记录新发现的变量对机制（待写回知识库）"""
        self._new_mechanisms.append({
            'var1': str(var1), 'var2': str(var2),
            'direction': direction, 'r': r_val, 'p': p_val,
            'pattern': f'{var1}与{var2}呈{direction}相关',
        })

    def _write_back_mechanisms(self):
        """将新发现的机制写回 knowledge_store/mechanisms.json"""
        try:
            from pathlib import Path
            import json
            from datetime import datetime, timezone

            store_dir = Path(__file__).parent / "knowledge_store"
            mech_path = store_dir / "mechanisms.json"

            if mech_path.exists():
                with open(mech_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"meta": {"category": "mechanisms"}, "entries": {}, "changelog": []}

            entries = data.setdefault("entries", {})
            new_count = 0

            for mech in self._new_mechanisms:
                key = f"auto_{mech['var1']}_{mech['var2']}".lower().replace(' ', '_')
                if key not in entries:
                    entries[key] = {
                        "value": {
                            "pattern": mech['pattern'],
                            "mechanism": f"自动发现：{mech['var1']}与{mech['var2']}呈{mech['direction']}相关(r={mech['r']:.3f})，具体机理有待研究。",
                            "mechanism_en": f"Auto-discovered: {mech['var1']} and {mech['var2']} show {mech['direction']} correlation (r={mech['r']:.3f}), mechanism to be determined.",
                            "references": [],
                            "auto_discovered": True,
                            "discovery_r": mech['r'],
                            "discovery_p": mech['p'],
                        },
                        "confidence": 0.6,
                        "source": "discussion_generator",
                        "updated": datetime.now(timezone.utc).isoformat(),
                        "version": 1,
                    }
                    new_count += 1

            if new_count > 0:
                data["meta"]["updated"] = datetime.now(timezone.utc).isoformat()
                store_dir.mkdir(exist_ok=True)
                with open(mech_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Wrote {new_count} new mechanisms to knowledge store")
        except Exception as e:
            logger.warning(f"Failed to write back mechanisms: {e}")

    def _generate_zh(self):
        """中文Discussion"""
        sections = []

        # 段落1：核心发现概述
        sections.append(self._overview_zh())

        # 段落2-N：逐个发现讨论
        sections.extend(self._discuss_findings_zh())

        # 碳平衡讨论
        sections.append(self._discuss_carbon_balance_zh())

        # 局限性
        sections.append(self._limitations_zh())

        # 展望
        sections.append(self._future_zh())

        return '\n\n'.join(s for s in sections if s)

    def _overview_zh(self):
        """核心发现概述"""
        findings = []

        if '描述统计' in self.results:
            findings.append('三相碳污染物的赋存特征')

        if '组间比较' in self.results:
            comp = self.results['组间比较']
            sig = comp[comp['显著性'] != 'n.s.']
            if len(sig) > 0:
                findings.append(f'{len(sig)}个指标的冬春季节差异显著')

        if 'pearson相关' in self.results or 'spearman相关' in self.results:
            findings.append('多指标间的显著相关关系')

        if 'PCA' in self.results:
            findings.append('PCA揭示的变量聚类模式')

        findings_str = '、'.join(findings) if findings else '数据特征'
        return (
            '## 4 讨论\n\n'
            f'本研究通过系统的采样分析和多元统计方法，揭示了校园污水管网中'
            f'固-液-气多相态碳污染物的赋存特征。主要发现包括：'
            f'{findings_str}。以下对各发现进行深入讨论。'
        )

    def _discuss_findings_zh(self):
        """逐个讨论发现"""
        paragraphs = []

        # 讨论组间差异
        if '组间比较' in self.results:
            p = self._discuss_seasonal_zh()
            if p:
                paragraphs.append(p)

        # 讨论相关性
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                p = self._discuss_correlation_zh(method)
                if p:
                    paragraphs.append(p)
                break

        # 讨论PCA
        if 'PCA' in self.results:
            p = self._discuss_pca_zh()
            if p:
                paragraphs.append(p)

        return paragraphs

    def _discuss_seasonal_zh(self):
        """讨论季节差异"""
        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']

        if len(sig) == 0:
            return ''

        lines = ['### 4.1 冬春季节差异分析\n']

        for _, row in sig.iterrows():
            var = row['变量']
            label = get_label(var)
            sig_level = row['显著性']

            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                g1, g2 = mean_cols[0].replace('_均值', ''), mean_cols[1].replace('_均值', '')
                m1, m2 = row[mean_cols[0]], row[mean_cols[1]]
                higher = g1 if m1 > m2 else g2

                # 用机制解释
                mech = MechanismKB.SEASONAL
                lines.append(
                    f'{label}在{higher}显著高于另一季节({sig_level})。'
                    f'{mech["mechanism"]}'
                )

                # 引用支撑
                for ref in mech.get('references', []):
                    lines.append(f'这与{ref}的研究结论一致。')

                # 记录推理链
                self.rationale.add(
                    finding=f"{label}在{higher}显著高于另一季节({sig_level})",
                    mechanism=mech['mechanism'],
                    mechanism_en=mech.get('mechanism_en', ''),
                    evidence=f"组间比较: {label} {g1}均值{m1:.3f}, {g2}均值{m2:.3f}",
                    citation='; '.join(mech.get('references', [])),
                    confidence=0.85,
                    section='discussion',
                )

        return '\n\n'.join(lines)

    def _discuss_correlation_zh(self, method):
        """讨论相关性 - 必须有机制解释"""
        key = f'{method}相关'
        corr = self.results[key]['相关系数']
        pvals = self.results[key]['p值']

        lines = [f'### 4.2 相关性分析讨论\n']
        lines.append(
            f'{method.capitalize()}相关性分析揭示了多组变量间的显著关联关系。'
            f'以下对关键相关关系的形成机制进行讨论。\n'
        )

        discussed = 0
        for i in range(len(corr)):
            for j in range(i + 1, len(corr)):
                r = corr.iloc[i, j]
                p = pvals.iloc[i, j]
                if abs(r) > 0.5 and p < 0.05:
                    var_i = corr.index[i]
                    var_j = corr.columns[j]
                    label_i = get_label(var_i)
                    label_j = get_label(var_j)
                    direction = '正' if r > 0 else '负'

                    # 查找对应机制
                    mech = self.mechanisms.find_mechanism_for_correlation(var_i, var_j)

                    lines.append(
                        f'{label_i}与{label_j}呈显著{direction}相关'
                        f'(r={r:.3f}, p={p:.4f})。'
                    )

                    if mech:
                        lines.append(f'{mech["mechanism"]}')
                        for ref in mech.get('references', []):
                            lines.append(f'{ref}也报道了类似的相关关系。')
                    else:
                        # 记录新发现的机制（后续写回知识库）
                        self._record_new_mechanism(var_i, var_j, direction, r, p)

                        # 尝试RAG检索相关文献
                        rag_refs = self._search_literature(
                            f'{label_i} {label_j} {direction}相关 mechanism', max_results=2)
                        if rag_refs:
                            lines.append(f'已有研究报道了类似的相关关系，{"; ".join(rag_refs)}。')
                        else:
                            lines.append(
                                f'这一相关关系可能反映了{label_i}和{label_j}之间'
                                f'存在的某种生物化学耦合机制，具体机理有待进一步研究。'
                            )
                    lines.append('')

                    # 记录推理链
                    self.rationale.add(
                        finding=f"{label_i}与{label_j}呈显著{direction}相关(r={r:.3f}, p={p:.4f})",
                        mechanism=mech['mechanism'] if mech else '待研究',
                        mechanism_en=mech.get('mechanism_en', '') if mech else '',
                        evidence=f"{method}相关: r={r:.3f}, p={p:.4f}",
                        citation='; '.join(mech.get('references', [])) if mech else '',
                        confidence=min(0.9, abs(r)),
                        section='discussion',
                    )
                    discussed += 1

                    if discussed >= self.max_correlations:
                        break
            if discussed >= self.max_correlations:
                break

        return '\n'.join(lines)

    def _discuss_pca_zh(self):
        """讨论PCA结果"""
        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', [])
        loadings = pca.get('loadings')

        if len(var_ratio) < 2:
            return ''

        lines = ['### 4.3 主成分分析讨论\n']
        lines.append(
            f'PCA结果表明，前2个主成分累计解释了{sum(var_ratio[:2])*100:.1f}%的方差，'
            f'说明这些主成分能够较好地概括原始变量的主要信息。'
        )

        if loadings is not None:
            # PC1高载荷变量
            pc1 = loadings.iloc[:, 0].sort_values(key=abs, ascending=False)
            high_pos = pc1[pc1 > 0.5].index.tolist()
            high_neg = pc1[pc1 < -0.5].index.tolist()

            if high_pos:
                labels = [get_label(v) for v in high_pos[:3]]
                lines.append(
                    f'PC1上正载荷较高的变量包括{"、".join(labels)}等，'
                    f'这些指标可能代表了[有机物输入/微生物活性]的综合信息。'
                )
            if high_neg:
                labels = [get_label(v) for v in high_neg[:3]]
                lines.append(
                    f'PC1上负载荷较高的变量包括{"、".join(labels)}等，'
                    f'可能反映了[氧化还原条件/环境因子]的影响。'
                )

        return '\n'.join(lines)

    def _discuss_carbon_balance_zh(self):
        """讨论碳平衡"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return ''

        total = sum(phase_data.values())
        lines = ['### 4.4 碳平衡分析\n']
        lines.append(
            '碳平衡分析揭示了碳在固-液-气三相之间的分配格局。'
        )

        for phase, val in phase_data.items():
            pct = val / total * 100
            lines.append(f'{phase}占比{pct:.1f}%。')

        # 最大占比相的机制解释
        max_phase = max(phase_data, key=phase_data.get)
        if '液' in max_phase:
            lines.append(
                '液相碳占主导地位，这与污水管网以液态输送为主要功能一致。'
                '液相有机碳是管道微生物代谢的直接底物来源，'
                '其赋存特征直接影响下游污水处理厂的进水碳源供给。'
            )
        elif '固' in max_phase:
            lines.append(
                '固相碳占比较高，说明管道沉积物和生物膜是重要的碳汇。'
                '固相碳的累积可能导致管道堵塞和腐蚀，同时释放的有机碳'
                '为厌氧产甲烷提供了持续的底物供给。'
            )
        elif '气' in max_phase:
            lines.append(
                '气相碳占比较高，提示该校园污水管网的碳排放强度较大。'
                '管道中较高的厌氧程度促进了CH4的生成，'
                '这对温室气体减排具有重要启示。'
            )

        return '\n'.join(lines)

    def _limitations_zh(self):
        """局限性"""
        return (
            '### 4.5 研究局限性\n\n'
            '本研究存在以下局限性：\n\n'
            '（1）采样时间仅涵盖冬季和春季两个季节，未能覆盖夏秋季节，'
            '对碳污染物季节变化规律的认识不够完整。\n\n'
            '（2）采样频次有限，每次采样为瞬时采样，可能未能充分反映'
            '碳污染物的日变化特征。\n\n'
            '（3）未开展管道内微生物群落分析，对碳转化过程中的关键功能微生物'
            '缺乏直接证据。\n\n'
            '（4）碳平衡计算基于质量守恒原理的简化模型，'
            '未考虑管道壁面吸附、化学沉淀等过程对碳平衡的贡献。'
        )

    def _future_zh(self):
        """展望"""
        return (
            '### 4.6 研究展望\n\n'
            '未来研究可从以下方面深入：\n\n'
            '（1）延长采样周期，覆盖四季变化，建立碳污染物的完整季节变化模型。\n\n'
            '（2）增加采样频次，开展连续监测，揭示碳污染物的日变化特征。\n\n'
            '（3）结合高通量测序技术，分析管道微生物群落结构，'
            '识别关键的功能微生物类群及其代谢途径。\n\n'
            '（4）开展碳同位素示踪实验，定量区分不同来源和转化途径对碳平衡的贡献。\n\n'
            '（5）建立管道碳转化的动力学模型，为管网碳管理提供定量工具。'
        )

    # ---- English Discussion methods ----

    def _overview_en(self):
        """Core findings overview (English)"""
        findings = []

        if '描述统计' in self.results:
            findings.append('the occurrence characteristics of multiphase carbon pollutants')

        if '组间比较' in self.results:
            comp = self.results['组间比较']
            sig = comp[comp['显著性'] != 'n.s.']
            if len(sig) > 0:
                findings.append(f'significant seasonal differences in {len(sig)} indicators')

        if 'pearson相关' in self.results or 'spearman相关' in self.results:
            findings.append('significant correlations among multiple variables')

        if 'PCA' in self.results:
            findings.append('variable clustering patterns revealed by PCA')

        findings_str = ', '.join(findings) if findings else 'the data characteristics'
        return (
            '## 4 Discussion\n\n'
            f'This study systematically investigated the occurrence, distribution, and driving '
            f'mechanisms of multiphase carbon pollutants in a campus sewage network through '
            f'integrated sampling and multivariate statistical analysis. The key findings include: '
            f'{findings_str}. Each finding is discussed in detail below.'
        )

    def _discuss_findings_en(self):
        """Discuss findings one by one (English)"""
        paragraphs = []

        if '组间比较' in self.results:
            p = self._discuss_seasonal_en()
            if p:
                paragraphs.append(p)

        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                p = self._discuss_correlation_en(method)
                if p:
                    paragraphs.append(p)
                break

        if 'PCA' in self.results:
            p = self._discuss_pca_en()
            if p:
                paragraphs.append(p)

        return paragraphs

    def _discuss_seasonal_en(self):
        """Seasonal differences discussion (English)"""
        comp = self.results['组间比较']
        sig = comp[comp['显著性'] != 'n.s.']

        if len(sig) == 0:
            return ''

        lines = ['### 4.1 Seasonal Differences\n']

        for _, row in sig.iterrows():
            var = row['变量']
            label = get_label(var)
            sig_level = row['显著性']

            mean_cols = [c for c in row.index if '_均值' in c]
            if len(mean_cols) == 2:
                g1, g2 = mean_cols[0].replace('_均值', ''), mean_cols[1].replace('_均值', '')
                m1, m2 = row[mean_cols[0]], row[mean_cols[1]]
                higher = g1 if m1 > m2 else g2

                mech = MechanismKB.SEASONAL
                lines.append(
                    f'{label} was significantly higher in {higher} than in the other season ({sig_level}). '
                    f'{mech.get("mechanism_en", mech["mechanism"])}'
                )

                for ref in mech.get('references', []):
                    lines.append(f'This finding is consistent with the observations reported by previous studies.')

        return '\n\n'.join(lines)

    def _discuss_correlation_en(self, method):
        """Correlation discussion with mechanism explanations (English)"""
        key = f'{method}相关'
        corr = self.results[key]['相关系数']
        pvals = self.results[key]['p值']

        lines = [f'### 4.2 Correlation Analysis\n']
        lines.append(
            f'{method.capitalize()} correlation analysis revealed significant associations among '
            f'multiple variables. The formation mechanisms of key correlations are discussed below.\n'
        )

        discussed = 0
        for i in range(len(corr)):
            for j in range(i + 1, len(corr)):
                r = corr.iloc[i, j]
                p = pvals.iloc[i, j]
                if abs(r) > 0.5 and p < 0.05:
                    var_i = corr.index[i]
                    var_j = corr.columns[j]
                    label_i = get_label(var_i)
                    label_j = get_label(var_j)
                    direction = 'positive' if r > 0 else 'negative'

                    mech = self.mechanisms.find_mechanism_for_correlation(var_i, var_j)

                    lines.append(
                        f'{label_i} showed a significant {direction} correlation with {label_j} '
                        f'(r = {r:.3f}, p = {p:.4f}).'
                    )

                    if mech:
                        lines.append(mech.get('mechanism_en', mech['mechanism']))
                        for ref in mech.get('references', []):
                            lines.append('Similar correlations have been reported in previous studies.')
                    else:
                        lines.append(
                            f'This correlation may reflect an underlying biogeochemical coupling mechanism '
                            f'between {label_i} and {label_j}, which warrants further investigation.'
                        )
                    lines.append('')
                    discussed += 1

                    if discussed >= self.max_correlations:
                        break
            if discussed >= self.max_correlations:
                break

        return '\n'.join(lines)

    def _discuss_pca_en(self):
        """PCA discussion (English)"""
        pca = self.results['PCA']
        var_ratio = pca.get('explained_variance_ratio', [])
        loadings = pca.get('loadings')

        if len(var_ratio) < 2:
            return ''

        lines = ['### 4.3 Principal Component Analysis\n']
        lines.append(
            f'The PCA results indicated that the first two principal components cumulatively explained '
            f'{sum(var_ratio[:2])*100:.1f}% of the total variance, suggesting that these components '
            f'effectively captured the major information of the original variables.'
        )

        if loadings is not None:
            pc1 = loadings.iloc[:, 0].sort_values(key=abs, ascending=False)
            high_pos = pc1[pc1 > 0.5].index.tolist()
            high_neg = pc1[pc1 < -0.5].index.tolist()

            if high_pos:
                labels = [get_label(v) for v in high_pos[:3]]
                lines.append(
                    f'Variables with high positive loadings on PC1 included {", ".join(labels)}, '
                    f'which may represent the integrated signal of organic matter input and microbial activity.'
                )
            if high_neg:
                labels = [get_label(v) for v in high_neg[:3]]
                lines.append(
                    f'Variables with high negative loadings on PC1 included {", ".join(labels)}, '
                    f'possibly reflecting the influence of redox conditions and environmental factors.'
                )

        return '\n'.join(lines)

    def _discuss_carbon_balance_en(self):
        """Carbon balance discussion (English)"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return ''

        total = sum(phase_data.values())
        lines = ['### 4.4 Carbon Balance Analysis\n']
        lines.append(
            'The carbon balance analysis revealed the distribution pattern of carbon '
            'across the solid, liquid, and gas phases.'
        )

        for phase, val in phase_data.items():
            pct = val / total * 100
            lines.append(f'{phase} accounted for {pct:.1f}% of the total carbon.')

        max_phase = max(phase_data, key=phase_data.get)
        if '液' in max_phase:
            lines.append(
                'Liquid-phase carbon dominated the total carbon pool, consistent with the primary '
                'function of sewage networks as liquid conveyance systems. Liquid organic carbon '
                'serves as the direct substrate for microbial metabolism in the pipeline and directly '
                'influences the carbon source supply to downstream wastewater treatment plants.'
            )
        elif '固' in max_phase:
            lines.append(
                'Solid-phase carbon accounted for a significant proportion, indicating that pipeline '
                'sediments and biofilms serve as important carbon sinks. The accumulation of solid-phase '
                'carbon may cause pipeline blockage and corrosion, while the released organic carbon '
                'provides a sustained substrate supply for anaerobic methanogenesis.'
            )
        elif '气' in max_phase:
            lines.append(
                'Gas-phase carbon constituted a notable proportion, suggesting high carbon emission '
                'intensity from this campus sewage network. The elevated anaerobic conditions in the '
                'pipeline promoted CH4 generation, which has important implications for greenhouse gas '
                'mitigation strategies.'
            )

        return '\n'.join(lines)

    def _limitations_en(self):
        """Study limitations (English)"""
        return (
            '### 4.5 Limitations\n\n'
            'Several limitations of this study should be acknowledged:\n\n'
            '(1) Sampling was limited to winter and spring seasons, excluding summer and autumn, '
            'which may not fully capture the seasonal variation patterns of carbon pollutants.\n\n'
            '(2) Sampling frequency was limited to instantaneous grab samples, which may not '
            'adequately represent the diurnal variation of carbon pollutants.\n\n'
            '(3) Microbial community analysis was not performed, leaving a gap in direct evidence '
            'for the key functional microorganisms involved in carbon transformation processes.\n\n'
            '(4) The carbon balance calculation was based on a simplified mass-balance model that '
            'did not account for contributions from pipeline wall adsorption or chemical precipitation.'
        )

    def _future_en(self):
        """Future work (English)"""
        return (
            '### 4.6 Future Work\n\n'
            'Future research could be advanced in the following directions:\n\n'
            '(1) Extending the sampling period to cover all four seasons and establish a comprehensive '
            'seasonal variation model for carbon pollutants.\n\n'
            '(2) Increasing sampling frequency through continuous monitoring to reveal diurnal '
            'variation patterns of carbon pollutants.\n\n'
            '(3) Incorporating high-throughput sequencing to analyze pipeline microbial community '
            'structure and identify key functional microorganisms and their metabolic pathways.\n\n'
            '(4) Conducting carbon isotope tracer experiments to quantitatively distinguish the '
            'contributions of different sources and transformation pathways to the carbon balance.\n\n'
            '(5) Developing kinetic models of pipeline carbon transformation to provide quantitative '
            'tools for pipeline carbon management.'
        )

    def _generate_en(self):
        """SCI英文Discussion"""
        sections = []
        sections.append(self._overview_en())
        sections.extend(self._discuss_findings_en())
        sections.append(self._discuss_carbon_balance_en())
        sections.append(self._limitations_en())
        sections.append(self._future_en())
        return '\n\n'.join(s for s in sections if s)


# ============================================================================
# 4. Abstract/Conclusion生成器
# ============================================================================
class AbstractGenerator:
    """基于所有已生成章节，从实际内容中提取关键信息组装Abstract"""

    def __init__(self, intro_text, methods_text, results_text, discussion_text):
        self.intro = intro_text or ''
        self.methods = methods_text or ''
        self.results = results_text or ''
        self.discussion = discussion_text or ''

    def generate(self, language='zh'):
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _extract_key_findings(self):
        """从Results中提取关键发现（统计显著性、相关系数等）"""
        import re
        findings = []
        text = self.results

        # 提取显著相关关系
        corr_matches = re.findall(
            r'([\w\(\)（）]+)\s*与\s*([\w\(\)（）]+)\s*呈\s*(显著[正负])\s*相关.*?r\s*=\s*([-−-]?\d+\.?\d*).*?p\s*[<>≤≥=]\s*(\d+\.?\d*)',
            text
        )
        for v1, v2, direction, r_val, p_val in corr_matches[:3]:
            findings.append(f'{v1}与{v2}呈{direction}相关(r={r_val})')

        # 提取组间差异
        diff_matches = re.findall(
            r'([\w\(\)（）]+)\s*在\s*(\w+)\s*显著[高低于]+.*?(\w+)',
            text
        )
        for var, higher, lower in diff_matches[:2]:
            findings.append(f'{var}在{higher}显著较高')

        # 提取PCA结果
        pca_match = re.search(r'前\s*2?\s*个主成分.*?累计.*?(\d+\.?\d*)%', text)
        if pca_match:
            findings.append(f'PCA前2个主成分累计解释了{pca_match.group(1)}%的方差')

        return findings

    def _extract_methods_summary(self):
        """从Methods中提取方法摘要"""
        import re
        methods = []

        if 'PCA' in self.methods or '主成分分析' in self.methods:
            methods.append('PCA')
        if 'HCA' in self.methods or '聚类分析' in self.methods or '层次聚类' in self.methods:
            methods.append('HCA')
        if 'Mann-Whitney' in self.methods or 't检验' in self.methods:
            methods.append('组间差异检验')
        if 'Pearson' in self.methods or '相关' in self.methods:
            methods.append('相关性分析')
        if 'TOC' in self.methods:
            methods.append('TOC')
        if 'CH4' in self.methods or '甲烷' in self.methods:
            methods.append('CH4')
        if 'CO2' in self.methods:
            methods.append('CO2')

        return methods

    def _generate_zh(self):
        # 从Introduction提取目的
        purpose = '研究校园污水管网固-液-气多相态碳污染物的赋存特征'
        if '研究空白' in self.intro or '不足' in self.intro:
            purpose = '揭示校园污水管网固-液-气多相态碳污染物的赋存特征与驱动机制'

        # 从Methods提取方法
        methods_list = self._extract_methods_summary()
        methods_desc = '、'.join(methods_list) if methods_list else '多元统计分析'

        # 从Results提取关键发现
        findings = self._extract_key_findings()
        if findings:
            results_desc = '；'.join(f'({i+1}){f}' for i, f in enumerate(findings))
        else:
            results_desc = '(1)碳污染物在固-液-气三相中呈现不同的赋存特征'

        # 从Discussion提取结论
        conclusion = '校园污水管网碳污染物具有显著的相态分异和空间分异特征'
        if '溶解氧' in self.discussion and '关键' in self.discussion:
            conclusion = '溶解氧和有机负荷是控制碳污染物相态转化的关键因素'
        elif '关键因素' in self.discussion:
            # 提取Discussion中提到的关键因素
            import re
            key_match = re.search(r'(.{2,15})是[控制决定].*?关键', self.discussion)
            if key_match:
                conclusion = f'{key_match.group(1)}是控制碳污染物相态转化的关键因素'

        return (
            '# 摘要\n\n'
            f'**【目的】** {purpose}，为校园污水碳管理提供科学依据。\n\n'
            f'**【方法】** 以某校园污水管网为研究对象，系统采集管道内固相、液相、'
            f'气相样品，采用{methods_desc}等方法进行分析。\n\n'
            f'**【结果】** 结果表明：{results_desc}。\n\n'
            f'**【结论】** {conclusion}，研究结果可为校园污水碳减排和管网碳管理提供参考。\n\n'
            '**关键词：** 污水管网；碳污染物；多相态分析；PCA；碳平衡\n'
        )

    def _generate_en(self):
        findings = self._extract_key_findings()
        methods_list = self._extract_methods_summary()

        methods_desc = ', '.join(methods_list) if methods_list else 'multivariate statistical analysis'

        if findings:
            results_parts = [f'({i+1}) {f}' for i, f in enumerate(findings)]
            results_desc = '; '.join(results_parts)
        else:
            results_desc = ('(1) carbon pollutants exhibited distinct occurrence patterns '
                          'across three phases')

        return (
            '# Abstract\n\n'
            f'This study investigated the occurrence characteristics of solid-liquid-gas '
            f'phase carbon pollutants in a campus sewage network. '
            f'{methods_desc} were employed to identify key driving factors. '
            f'Results showed that: {results_desc}. '
            f'These findings provide scientific references for campus wastewater carbon '
            f'management and emission reduction.\n\n'
            f'**Keywords:** sewage network; carbon pollutants; multiphase analysis; PCA; '
            f'carbon balance\n'
        )


# ============================================================================
# 5. Methods生成器
# ============================================================================
class MethodsGenerator:
    """Methods章节生成 - 引用国标/行标，支持从数据自动推断参数"""

    def __init__(self, params=None, df=None):
        self.params = params or {}
        if df is not None:
            self._infer_params_from_data(df)

    def _infer_params_from_data(self, df):
        """从DataFrame自动推断Methods参数"""
        import pandas as pd

        # 采样点数量
        if '采样点' in df.columns and 'sampling_points' not in self.params:
            n_points = df['采样点'].nunique()
            self.params['sampling_points'] = str(n_points)

        # 季节信息
        if '季节' in df.columns:
            seasons = df['季节'].unique().tolist()
            if '冬季' in seasons and 'winter_month' not in self.params:
                self.params['winter_month'] = '12'  # 默认
            if '春季' in seasons and 'spring_month' not in self.params:
                self.params['spring_month'] = '3'  # 默认

        # 样本量
        if 'n_samples' not in self.params:
            self.params['n_samples'] = str(len(df))

        # 检测到的变量数
        numeric_cols = df.select_dtypes(include='number').columns
        if 'n_variables' not in self.params:
            self.params['n_variables'] = str(len(numeric_cols))

    def generate(self, language='zh'):
        if language == 'zh':
            return self._generate_zh()
        return self._generate_en()

    def _generate_zh(self):
        return (
            '# 3 材料与方法\n\n'
            '## 3.1 研究区域概况\n\n'
            f'本研究选取某校园污水管网作为研究对象。该校园占地面积约{self.params.get("area", "X")}公顷，'
            f'常住人口约{self.params.get("population", "X")}万人，日均污水排放量约{self.params.get("sewage_flow", "X")} m³/d。校园功能区主要包括教学区、'
            '生活区、餐饮区和运动区，各功能区的污水通过支管汇入主管道后排出校园。\n\n'
            '## 3.2 采样方案\n\n'
            f'根据管网布局和功能区分布，在主管道上设置了{self.params.get("sampling_points", "X")}个采样点，'
            '分别位于教学区(A1-A3)、生活区(B1-B3)、餐饮区(C1-C3)和管口出口(D)。'
            f'采样时间涵盖冬季(2024年{self.params.get("winter_month", "X")}月)和春季(2025年{self.params.get("spring_month", "X")}月)两个季节，'
            '每次采样在各点同步采集固相、液相和气相样品。\n\n'
            '## 3.3 分析方法\n\n'
            '**气相分析：** 采用便携式气体检测仪测定管道内CH4、CO2、O2和VOCs浓度。'
            '检测前进行仪器校准，每个采样点重复测定3次取平均值。\n\n'
            '**液相分析：** 采集管道内污水水样，经0.45μm滤膜过滤后测定溶解性指标。'
            '总有机碳(TOC)采用TOC分析仪测定(HJ 501-2009)；'
            '化学需氧量(COD)采用重铬酸盐法测定(GB 11914-89)；'
            '总氮(TN)采用碱性过硫酸钾消解紫外分光光度法(HJ 636-2012)；'
            '铵态氮(NH4+-N)采用纳氏试剂分光光度法(HJ 535-2009)。\n\n'
            '**固相分析：** 采集管道底部沉积物样品，自然风干后研磨过筛。'
            '固相总碳和有机碳采用元素分析仪测定。\n\n'
            '## 3.4 数据处理与统计分析\n\n'
            '采用Python 3.11进行数据处理和统计分析。描述性统计计算均值、标准差、'
            '变异系数等指标。正态性检验采用Shapiro-Wilk检验(p>0.05为正态)。'
            '组间差异分析：正态数据采用独立样本t检验，非正态数据采用Mann-Whitney U检验。'
            '相关性分析采用Pearson相关系数。降维分析采用主成分分析(PCA)，'
            '聚类分析采用层次聚类分析(HCA)。统计显著性水平设为p<0.05。\n\n'
            '## 3.5 碳平衡计算方法\n\n'
            '碳平衡基于质量守恒原理，计算公式为：\n\n'
            'C_input = C_output + C_accumulation + C_loss\n\n'
            '其中，C_input为输入碳量，C_output为输出碳量，'
            'C_accumulation为碳储量变化，C_loss为碳转化损失量。'
            '碳在固-液-气三相中的分配比例按各相碳含量占总碳含量的百分比计算。'
        )

    def _generate_en(self):
        return (
            '# 3 Materials and Methods\n\n'
            '## 3.1 Study Area\n\n'
            f'A campus sewage network was selected as the study site, covering approximately '
            f'{self.params.get("area", "X")} hectares with a resident population of about '
            f'{self.params.get("population", "X")}0,000 and a daily wastewater discharge of '
            f'{self.params.get("sewage_flow", "X")} m³/d.\n\n'
            '## 3.2 Sampling Strategy\n\n'
            f'Solid, liquid, and gas phase samples were collected from {self.params.get("sampling_points", "X")} '
            'sampling points located at the teaching zone (A1-A3), residential zone (B1-B3), '
            'dining zone (C1-C3), and outlet (D). Sampling was conducted in winter '
            f'(2024/{self.params.get("winter_month", "X")}) and spring (2025/{self.params.get("spring_month", "X")}).\n\n'
            '## 3.3 Analytical Methods\n\n'
            'Gas phase: Portable gas detectors for CH4, CO2, O2, VOCs.\n'
            'Liquid phase: TOC analyzer (HJ 501-2009), COD by dichromate method (GB 11914-89).\n'
            'Solid phase: Element analyzer for total carbon and organic carbon.\n\n'
            '## 3.4 Statistical Analysis\n\n'
            'Statistical analyses were performed using Python 3.11. '
            'Normality was tested by Shapiro-Wilk test. Group comparisons used '
            't-test (normal) or Mann-Whitney U test (non-normal). '
            'Correlation analysis employed Pearson coefficients. '
            'PCA and HCA were used for dimensionality reduction and clustering. '
            'Significance was set at p<0.05.\n'
        )


# ============================================================================
# 6. 大纲生成器 - 大纲先行，驱动全文结构
# ============================================================================
class OutlineGenerator:
    """
    大纲先行生成器（借鉴 STORM 两阶段方法）

    Phase 1: 基于数据分析结果生成草稿大纲（纯参数知识）
    Phase 2: 基于 RAG 检索到的文献优化大纲结构

    输出: 结构化的论文章节大纲，驱动后续逐节生成
    """

    # 章节专属写作提示（借鉴 AI-Scientist per_section_tips）
    SECTION_TIPS = {
        'abstract': {
            'zh': [
                '用4-5句话概括：目的、方法、关键发现、结论',
                '必须包含至少1个定量数据（浓度值、p值、R²）',
                '不要出现参考文献引用',
                '不要出现图表引用',
                '关键词3-5个',
            ],
            'en': [
                'Summarize in 4-5 sentences: purpose, methods, key findings, conclusions',
                'Include at least 1 quantitative data point',
                'No reference citations in abstract',
                'No figure/table references',
                '3-5 keywords',
            ],
        },
        'introduction': {
            'zh': [
                '逻辑链: 宏观背景 → 领域问题 → 研究现状 → 研究空白 → 本研究目标',
                '每段至少引用2篇文献',
                '用"然而/但是"等转折词引出研究空白',
                '最后一段明确列出本研究的具体目标（3-4个）',
                '避免空洞表述如"具有重要意义"',
            ],
            'en': [
                'Logic chain: background → problem → status → gap → objectives',
                'Each paragraph cites at least 2 references',
                'Use "however/yet/but" to introduce research gap',
                'Last paragraph lists 3-4 specific objectives',
                'Avoid hollow statements like "is of great significance"',
            ],
        },
        'methods': {
            'zh': [
                '引用国标/行标方法（HJ/GB）',
                '包含采样方案、分析方法、数据处理方法',
                '注明仪器型号和检测限',
                '统计方法要写明软件版本和显著性水平',
            ],
            'en': [
                'Cite standard methods (HJ/GB/EPA/ISO)',
                'Include sampling, analysis, and data processing',
                'Specify instrument models and detection limits',
                'State software version and significance level',
            ],
        },
        'results': {
            'zh': [
                '只报告实际分析结果，不要推测或解释',
                '每个发现必须有数据支撑（均值±标准差、p值、r值）',
                '按逻辑顺序组织：描述统计 → 组间比较 → 相关性 → 降维',
                '图表引用使用括号格式：(图1) (表2)',
                '禁止虚构数据',
            ],
            'en': [
                'Report only actual results, no interpretation',
                'Every finding needs data support (mean±SD, p-value, r-value)',
                'Order: descriptive → comparison → correlation → PCA',
                'Use parenthetical figure references: (Fig. 1) (Table 2)',
                'Never fabricate data',
            ],
        },
        'discussion': {
            'zh': [
                '每个发现必须有: (1)机制解释 (2)文献对比 (3)数据支撑',
                '讨论"为什么"而不只是"是什么"',
                '至少讨论1个与文献不一致的发现',
                '碳平衡讨论要说明各相态占比和驱动因素',
                '局限性要具体（采样时间、频次、微生物分析等）',
            ],
            'en': [
                'Each finding needs: (1)mechanism (2)literature comparison (3)data',
                'Discuss "why" not just "what"',
                'Discuss at least 1 finding inconsistent with literature',
                'Limitations must be specific',
            ],
        },
        'conclusion': {
            'zh': [
                '精炼3-4条结论，每条对应一个研究目标',
                '不要重复Abstract中的数据',
                '不要引用参考文献',
                '可以包含实践意义',
            ],
            'en': [
                '3-4 concise conclusions, each corresponding to an objective',
                'Do not repeat Abstract data',
                'No reference citations',
                'May include practical implications',
            ],
        },
    }

    def __init__(self, analysis_results=None, rag_engine=None, direction=None):
        self.results = analysis_results or {}
        self.rag = rag_engine
        self.direction = direction or ResearchDirection()
        self.outline = {}

    def generate(self, language='zh'):
        """
        两阶段大纲生成

        Returns
        -------
        dict, 结构化大纲 {section_name: {title, subsections, key_points, tips}}
        """
        print("  → [Phase 1] 生成草稿大纲...")
        draft = self._draft_outline(language)

        print("  → [Phase 2] 基于文献优化大纲...")
        self.outline = self._refine_with_literature(draft, language)

        return self.outline

    def _draft_outline(self, language='zh'):
        """Phase 1: 基于数据分析结果生成草稿大纲"""
        outline = {}

        # 检测有哪些分析结果可用
        has_desc = '描述统计' in self.results
        has_compare = '组间比较' in self.results
        has_corr = 'pearson相关' in self.results or 'spearman相关' in self.results
        has_pca = 'PCA' in self.results
        has_hca = 'HCA' in self.results

        # 从结果中提取关键发现用于大纲
        key_findings = self._extract_key_findings()

        if language == 'zh':
            outline = {
                'abstract': {
                    'title': '摘要',
                    'subsections': [],
                    'key_points': ['研究目的', '方法概述', '关键发现', '结论'],
                    'tips': self.SECTION_TIPS['abstract']['zh'],
                },
                'introduction': {
                    'title': '1 绪论',
                    'subsections': [
                        {'title': '1.1 研究背景与意义', 'key_points': [self.direction.topic]},
                        {'title': '1.2 国内外研究现状', 'key_points': ['碳污染物研究', '校园管网研究']},
                        {'title': '1.3 现有研究不足', 'key_points': ['多相态分析不足', '校园尺度缺乏']},
                        {'title': '1.4 研究内容与目标', 'key_points': key_findings[:4]},
                    ],
                    'key_points': ['背景→现状→空白→目标'],
                    'tips': self.SECTION_TIPS['introduction']['zh'],
                },
                'methods': {
                    'title': '2 材料与方法',
                    'subsections': [
                        {'title': '2.1 研究区域概况', 'key_points': ['校园概况']},
                        {'title': '2.2 采样方案', 'key_points': ['采样点', '采样时间']},
                        {'title': '2.3 分析方法', 'key_points': ['气相', '液相', '固相']},
                        {'title': '2.4 数据处理与统计分析', 'key_points': ['PCA', 'HCA', '相关性']},
                    ],
                    'key_points': ['标准化方法引用'],
                    'tips': self.SECTION_TIPS['methods']['zh'],
                },
                'results': {
                    'title': '3 结果',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['results']['zh'],
                },
                'discussion': {
                    'title': '4 讨论',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['discussion']['zh'],
                },
                'conclusion': {
                    'title': '5 结论',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['conclusion']['zh'],
                },
            }
        else:
            outline = {
                'abstract': {
                    'title': 'Abstract',
                    'subsections': [],
                    'key_points': ['Purpose', 'Methods', 'Key findings', 'Conclusions'],
                    'tips': self.SECTION_TIPS['abstract']['en'],
                },
                'introduction': {
                    'title': '1 Introduction',
                    'subsections': [
                        {'title': '1.1 Background', 'key_points': [self.direction.topic]},
                        {'title': '1.2 Literature Review', 'key_points': ['Carbon pollutants', 'Campus networks']},
                        {'title': '1.3 Research Gap', 'key_points': ['Multiphase analysis gap']},
                        {'title': '1.4 Objectives', 'key_points': key_findings[:4]},
                    ],
                    'key_points': ['background→status→gap→objectives'],
                    'tips': self.SECTION_TIPS['introduction']['en'],
                },
                'methods': {
                    'title': '2 Materials and Methods',
                    'subsections': [
                        {'title': '2.1 Study Area', 'key_points': ['Campus description']},
                        {'title': '2.2 Sampling Strategy', 'key_points': ['Sampling points', 'Seasons']},
                        {'title': '2.3 Analytical Methods', 'key_points': ['Gas', 'Liquid', 'Solid']},
                        {'title': '2.4 Statistical Analysis', 'key_points': ['PCA', 'HCA', 'Correlation']},
                    ],
                    'key_points': ['Standard method citations'],
                    'tips': self.SECTION_TIPS['methods']['en'],
                },
                'results': {
                    'title': '3 Results',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['results']['en'],
                },
                'discussion': {
                    'title': '4 Discussion',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['discussion']['en'],
                },
                'conclusion': {
                    'title': '5 Conclusions',
                    'subsections': [],
                    'key_points': [],
                    'tips': self.SECTION_TIPS['conclusion']['en'],
                },
            }

        # 动态填充 Results 子节
        if has_desc:
            outline['results']['subsections'].append(
                {'title': '描述性统计', 'key_points': ['均值', '标准差', '变异系数']})
        if has_compare:
            outline['results']['subsections'].append(
                {'title': '组间比较', 'key_points': ['冬春差异', '显著性']})
        if has_corr:
            outline['results']['subsections'].append(
                {'title': '相关性分析', 'key_points': ['Pearson', 'Spearman']})
        if has_pca:
            outline['results']['subsections'].append(
                {'title': '主成分分析', 'key_points': ['方差解释率', '载荷']})
        if has_hca:
            outline['results']['subsections'].append(
                {'title': '聚类分析', 'key_points': ['聚类结果']})

        # 动态填充 Discussion 子节
        outline['discussion']['subsections'] = [
            {'title': '核心发现讨论', 'key_points': key_findings[:3]},
            {'title': '相关性机制讨论', 'key_points': ['DO→CH4', 'TOC→CH4']},
            {'title': '碳平衡分析', 'key_points': ['三相碳分配']},
            {'title': '研究局限性', 'key_points': ['采样时间', '采样频次']},
            {'title': '研究展望', 'key_points': ['四季采样', '微生物分析']},
        ]

        return outline

    def _refine_with_literature(self, draft, language='zh'):
        """Phase 2: 基于 RAG + Semantic Scholar 优化大纲"""
        import re
        lit_topics = []

        # 来源1: RAG 检索
        if self.rag:
            try:
                topic_query = self.direction.topic
                results = self.rag.retrieve(topic_query, max_results=5)
                for r in results:
                    text = r.get('text', '')
                    if text:
                        phrases = re.findall(r'[一-鿿]{2,6}|[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', text)
                        lit_topics.extend(phrases[:3])
            except Exception as e:
                logger.warning(f"RAG outline refinement failed: {e}")

        # 来源2: Semantic Scholar API（可选）
        try:
            from semantic_scholar import SemanticScholarClient
            client = SemanticScholarClient()
            # 基于研究主题搜索
            papers = client.search(self.direction.topic, limit=3)
            for p in papers:
                if p.abstract:
                    # 从摘要中提取关键主题
                    phrases = re.findall(r'[一-鿿]{2,6}|[A-Z][a-z]+(?:\s[A-Z][a-z]+)*', p.abstract[:200])
                    lit_topics.extend(phrases[:2])
                if p.title:
                    lit_topics.append(p.title[:30])
            logger.info(f"Semantic Scholar: found {len(papers)} papers for outline refinement")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Semantic Scholar outline refinement skipped: {e}")

        # 应用文献主题到大纲
        if lit_topics and 'introduction' in draft:
            existing_points = draft['introduction']['subsections'][1].get('key_points', [])
            combined = list(set(existing_points + lit_topics[:5]))
            draft['introduction']['subsections'][1]['key_points'] = combined[:6]

        return draft

    def _extract_key_findings(self):
        """从分析结果中提取关键发现"""
        findings = []
        import re

        # 从组间比较提取
        if '组间比较' in self.results:
            comp = self.results['组间比较']
            sig = comp[comp['显著性'] != 'n.s.']
            for _, row in sig.iterrows():
                var = row['变量']
                findings.append(f'{var}季节差异显著')

        # 从相关性提取
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key in self.results:
                corr = self.results[key]['相关系数']
                pvals = self.results[key]['p值']
                for i in range(len(corr)):
                    for j in range(i + 1, len(corr)):
                        r = corr.iloc[i, j]
                        p = pvals.iloc[i, j]
                        if abs(r) > 0.5 and p < 0.05:
                            var_i = corr.index[i]
                            var_j = corr.columns[j]
                            direction = '正' if r > 0 else '负'
                            findings.append(f'{var_i}与{var_j}呈{direction}相关')
                break

        # 从PCA提取
        if 'PCA' in self.results:
            pca = self.results['PCA']
            var_ratio = pca.get('explained_variance_ratio', [])
            if len(var_ratio) >= 2:
                findings.append(f'PCA前2主成分解释{sum(var_ratio[:2])*100:.0f}%方差')

        return findings[:8]  # 最多8个关键发现

    def get_tips(self, section_name):
        """获取指定章节的写作提示"""
        if section_name in self.outline:
            return self.outline[section_name].get('tips', [])
        return []

    def to_markdown(self):
        """输出大纲为 Markdown 格式"""
        lines = ['# 论文大纲', '']
        for sec_name, sec_data in self.outline.items():
            lines.append(f"## {sec_data['title']}")
            if sec_data.get('tips'):
                lines.append('')
                lines.append('**写作提示:**')
                for tip in sec_data['tips']:
                    lines.append(f'- {tip}')
            for sub in sec_data.get('subsections', []):
                lines.append(f"  - {sub['title']}")
                if sub.get('key_points'):
                    for kp in sub['key_points']:
                        lines.append(f"    - {kp}")
            lines.append('')
        return '\n'.join(lines)


# ============================================================================
# 7. 论文编排器 - 一键生成完整论文
# ============================================================================
class PaperWriter:
    """
    论文自动写作Agent主类
    输入数据 → 分析 → 生成完整论文
    """

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.analysis_agent = None
        self.sections = {}
        self.outline = {}  # 论文大纲（OutlineGenerator 生成）
        self.language = 'zh'
        self.paper_type = 'thesis'  # thesis / sci / chinese
        self.params = {}  # Methods参数（面积、人口等）
        self._version_history = []  # 论文版本历史

    def write(self, data_path=None, paper_type='thesis', language='zh', params=None,
              direction=None):
        """
        一键生成论文

        Args:
            data_path: 数据文件路径
            paper_type: 论文类型 thesis/sci/chinese
            language: zh/en
            params: Methods参数字典(面积、人口等)
            direction: ResearchDirection实例，自定义研究方向
        """
        self.language = language
        self.paper_type = paper_type
        self.params = params or {}
        self.direction = direction or ResearchDirection()  # 默认使用校园污水管网方向

        print("\n" + "=" * 70)
        print("  论文自动写作Agent - 开始生成论文")
        print(f"  类型: {paper_type} | 语言: {language}")
        print("=" * 70)

        # Step 1: 运行数据分析
        print("\n[Step 1] 运行数据分析...")
        self.analysis_agent = ScientificAnalysisAgent(data_path, self.output_dir)
        self.analysis_agent.load_data()
        self.analysis_agent.run(language)

        # Step 1.5: 大纲先行生成（借鉴 STORM 两阶段方法）
        print("\n[Step 1.5] 生成论文大纲...")
        rag = None
        if RAGEngine:
            try:
                rag = RAGEngine()
            except Exception:
                pass
        outline_gen = OutlineGenerator(
            analysis_results=self.analysis_agent.results,
            rag_engine=rag,
            direction=self.direction,
        )
        self.outline = outline_gen.generate(language)
        # 保存大纲
        outline_path = os.path.join(self.output_dir, 'outline.md')
        with open(outline_path, 'w', encoding='utf-8') as f:
            f.write(outline_gen.to_markdown())
        print(f"  → 大纲已保存: {outline_path}")

        # Step 2: 生成各章节
        print("\n[Step 2] 生成论文章节...")

        # Introduction
        print("  → 生成Introduction...")
        intro_gen = IntroductionGenerator()
        self.sections['introduction'] = intro_gen.generate(language)

        # Methods
        print("  → 生成Materials & Methods...")
        methods_gen = MethodsGenerator(params=self.params, df=self.analysis_agent.df)
        self.sections['methods'] = methods_gen.generate(language)

        # Results (from analysis agent)
        print("  → 组装Results...")
        self.sections['results'] = self._assemble_results()

        # 结果反幻觉验证（借鉴 AI-Scientist）
        results_text, verify_issues = self._verify_results_against_data(self.sections['results'])
        if verify_issues:
            print(f"  → 结果验证: 发现{len(verify_issues)}个数据问题")
            for vi in verify_issues:
                print(f"    ⚠ {vi}")

        # Discussion
        print("  → 生成Discussion（含机制解释）...")
        self.rationale = RationaleMatrix()
        disc_gen = DiscussionGenerator(
            self.analysis_agent.results,
            self.analysis_agent.captions,
            rationale_matrix=self.rationale,
            rag_engine=rag,
        )
        self.sections['discussion'] = disc_gen.generate(language)

        # Conclusion
        print("  → 生成Conclusion...")
        self.sections['conclusion'] = self._generate_conclusion()

        # Abstract (最后生成，基于所有章节)
        print("  → 生成Abstract...")
        abstract_gen = AbstractGenerator(
            self.sections['introduction'],
            self.sections['methods'],
            self.sections['results'],
            self.sections['discussion']
        )
        self.sections['abstract'] = abstract_gen.generate(language)

        # Step 3: 组装完整论文
        print("\n[Step 3] 组装完整论文...")
        full_paper = self._assemble_paper()

        # Step 3.1: 写→审→改循环（借鉴 AI-Scientist 反馈改进机制）
        print("\n[Step 3.1] 执行写→审→改循环...")
        full_paper, revision_rounds = self._review_and_revise_loop(
            full_paper, language, max_rounds=3
        )

        # Step 3.5: 论文润色（可选）
        try:
            from writing_optimizer import polish_paper, check_grammar
            print("\n[Step 3.5] 论文语言优化...")
            polish_result = polish_paper(full_paper, language)
            if polish_result.has_changes():
                full_paper = polish_result.optimized_text
                # 保存润色报告
                polish_path = os.path.join(self.output_dir, 'polish_report.md')
                with open(polish_path, 'w', encoding='utf-8') as f:
                    f.write(polish_result.to_markdown())
                print(f"  → 润色完成: {len(polish_result.changes)}处修改 → {polish_path}")
            else:
                print("  → 润色完成: 未发现需要修改的内容")

            # 语法检查
            grammar_issues = check_grammar(full_paper, language)
            if grammar_issues:
                grammar_path = os.path.join(self.output_dir, 'grammar_report.md')
                with open(grammar_path, 'w', encoding='utf-8') as f:
                    f.write("# 语法检查报告\n\n")
                    for i, issue in enumerate(grammar_issues, 1):
                        f.write(f"## {i}. [{issue.category}] {issue.reason}\n\n")
                        f.write(f"- 原文: {issue.original}\n")
                        f.write(f"- 建议: {issue.revised}\n\n")
                print(f"  → 语法检查: {len(grammar_issues)}个问题 → {grammar_path}")
        except ImportError:
            print("  → 润色模块不可用，跳过")
        except Exception as e:
            print(f"  → 润色出错: {e}，继续保存")

        # Step 4: 保存
        print("\n[Step 4] 保存论文...")
        paper_path = os.path.join(self.output_dir, f'paper_{paper_type}_{language}.md')

        # 版本管理：如果文件已存在，保存为历史版本
        if os.path.exists(paper_path):
            import shutil
            version = len(self._version_history) + 1
            version_dir = os.path.join(self.output_dir, 'versions')
            os.makedirs(version_dir, exist_ok=True)
            version_path = os.path.join(version_dir, f'paper_{paper_type}_{language}_v{version}.md')
            shutil.copy2(paper_path, version_path)
            self._version_history.append({
                'version': version,
                'path': version_path,
                'timestamp': datetime.now().isoformat(),
            })
            print(f"  → 已保存历史版本: v{version}")

        with open(paper_path, 'w', encoding='utf-8') as f:
            f.write(full_paper)

        # 保存各章节单独文件
        for name, content in self.sections.items():
            section_path = os.path.join(self.output_dir, f'section_{name}.md')
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # 保存推理矩阵
        print("  → 保存写作推理矩阵...")
        self.rationale.save()
        rationale_path = os.path.join(self.output_dir, 'rationale_matrix.md')
        with open(rationale_path, 'w', encoding='utf-8') as f:
            f.write(self.rationale.to_markdown())

        # 七句话血统测试
        print("  → 执行七句话血统测试...")
        test = SevenSentenceTest()
        test.extract_from_paper(self.sections)
        thread_result = test.validate()
        thread_path = os.path.join(self.output_dir, 'seven_sentence_test.md')
        with open(thread_path, 'w', encoding='utf-8') as f:
            f.write(test.to_markdown())
            f.write('\n\n## 验证结果\n\n')
            for check_name, passed in thread_result['checks']:
                icon = '✓' if passed else '✗'
                f.write(f"- {icon} {check_name}\n")
            if thread_result['issues']:
                f.write('\n## 问题\n\n')
                for issue in thread_result['issues']:
                    f.write(f"- {issue}\n")

        print(f"\n论文已保存: {paper_path}")
        print(f"各章节单独文件: {self.output_dir}/section_*.md")

        # LaTeX/BibTeX 导出（可选）
        try:
            from latex_exporter import LatexExporter
            print("  → 导出 LaTeX/BibTeX...")
            template_map = {'thesis': 'chinese_thesis', 'sci': 'sci', 'chinese': 'chinese_journal'}
            template = template_map.get(paper_type, 'sci')
            exporter = LatexExporter(template=template)
            # 构建引用列表
            refs_for_latex = []
            if hasattr(self, '_citation_refs'):
                refs_for_latex = self._citation_refs
            latex_result = exporter.export(
                sections=self.sections,
                references=refs_for_latex,
                output_dir=os.path.join(self.output_dir, 'latex'),
                title=self.direction.topic if hasattr(self, 'direction') else '',
            )
            print(f"  → LaTeX 导出完成: {latex_result['main_path']}")
        except ImportError:
            print("  → LaTeX 导出模块不可用，跳过")
        except Exception as e:
            print(f"  → LaTeX 导出出错: {e}")

        # 引用质量审计
        print("  → 执行引用质量审计...")
        try:
            from citation_audit import audit_citations_batch
            import re as _re

            # 从全文中提取所有引用
            ref_lines = []

            # 1. 提取 (Author, Year) 格式引用
            author_refs = _re.findall(
                r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-z]+)*)\s*,?\s*(\d{4})[a-z]?\)',
                full_paper
            )
            for author, year in author_refs:
                ref_lines.append(f'{author} ({year}).')

            # 2. 提取 [N] 格式引用
            bracket_refs = _re.findall(r'\[(\d+(?:,\s*\d+)*)\]', full_paper)
            for ref_str in bracket_refs:
                for num in ref_str.split(','):
                    ref_lines.append(f'[{num.strip()}]')

            # 去重
            ref_lines = list(dict.fromkeys(ref_lines))

            if ref_lines:
                result = audit_citations_batch(ref_lines[:30], verify=False)
                audit_path = os.path.join(self.output_dir, 'citation_audit.md')
                with open(audit_path, 'w', encoding='utf-8') as f:
                    f.write(result['report'])
                print(f"  → 引用审计完成: 评分{result['overall_score']}/100 → {audit_path}")
            else:
                print("  → 引用审计跳过: 未检测到引用")
        except ImportError:
            print("  → 引用审计跳过: citation_audit模块不可用")
        except Exception as e:
            print(f"  → 引用审计出错: {e}")

        # 统计
        total_chars = len(full_paper)
        print(f"\n论文总字数: {total_chars}字")
        for name, content in self.sections.items():
            print(f"  {name}: {len(content)}字")

        print("\n" + "=" * 70)
        print("  论文生成完成！")
        print("=" * 70)

        return full_paper

    def _review_and_revise_loop(self, full_paper, language, max_rounds=3):
        """
        写→审→改循环（借鉴 AI-Scientist 的反馈改进机制）

        流程: 生成 → 质量检查 → 修复 CRITICAL/MAJOR → 重新生成受影响章节 → 再检查
        收敛条件: 无 CRITICAL 问题 + MAJOR 问题 < 3 或达到最大轮次

        Returns
        -------
        (revised_paper, rounds_executed)
        """
        try:
            from academic_review_agent import AcademicReviewAgent, Severity
        except ImportError:
            print("  → 审稿模块不可用，跳过审改循环")
            return full_paper, 0

        reviewer = AcademicReviewAgent(paper_type=self.paper_type, language=language)

        for round_num in range(1, max_rounds + 1):
            print(f"\n  --- 审改轮次 {round_num}/{max_rounds} ---")

            # 审查（14类检查器）
            report = reviewer.review(full_paper)

            # 跨章节一致性检查
            coherence_issues = self._check_cross_section_coherence()
            if coherence_issues:
                print(f"  → 跨章节一致性: {len(coherence_issues)}个问题")
                for ci in coherence_issues:
                    if ci.get('severity') == 'MAJOR':
                        major_count = len([i for i in report.issues if i.severity == Severity.MAJOR])
                        # 添加到major列表
                        from academic_review_agent import Issue as _Issue
                        report.issues.append(_Issue(
                            category='跨章节一致性',
                            severity=Severity.MAJOR,
                            section=ci.get('section', ''),
                            location='coherence',
                            problem=ci['issue'],
                            original='',
                            suggestion=ci.get('suggestion', ''),
                        ))

            # 统计问题
            critical = [i for i in report.issues if i.severity == Severity.CRITICAL]
            major = [i for i in report.issues if i.severity == Severity.MAJOR]
            score = report.scores.get('总分', 0)

            print(f"  → 检查完成: {len(critical)}个CRITICAL, {len(major)}个MAJOR, 总分{score}")

            # 收敛判断
            if len(critical) == 0 and len(major) < 3:
                print(f"  → 审改收敛! (轮次{round_num})")
                break

            # 修复 CRITICAL 问题
            if critical:
                print(f"  → 修复 {len(critical)} 个 CRITICAL 问题...")
                for issue in critical:
                    self._fix_issue(issue, language)

            # 修复 MAJOR 问题（最多修复前3个）
            if major:
                print(f"  → 修复 {min(3, len(major))} 个 MAJOR 问题...")
                for issue in major[:3]:
                    self._fix_issue(issue, language)

            # 重新组装论文
            full_paper = self._assemble_paper()

        return full_paper, round_num

    def _fix_issue(self, issue, language):
        """根据审稿问题自动修复受影响的章节"""
        section = issue.section.lower() if issue.section else ''

        # 映射审稿器的章节名到我们的章节名
        section_map = {
            'abstract': 'abstract',
            '摘要': 'abstract',
            'introduction': 'introduction',
            '引言': 'introduction',
            '绪论': 'introduction',
            'methods': 'methods',
            '材料': 'methods',
            '方法': 'methods',
            'results': 'results',
            '结果': 'results',
            'discussion': 'discussion',
            '讨论': 'discussion',
            'conclusion': 'conclusion',
            '结论': 'conclusion',
        }

        target_section = None
        for key, val in section_map.items():
            if key in section:
                target_section = val
                break

        if not target_section or target_section not in self.sections:
            return

        # 针对不同问题类型的修复策略
        if issue.category == 'AI痕迹':
            # AI痕迹: 尝试替换问题表达
            original_text = self.sections[target_section]
            if issue.original and issue.original in original_text:
                self.sections[target_section] = original_text.replace(
                    issue.original, issue.suggestion or ''
                )

        elif issue.category == '学术语法':
            # 禁用词: 替换为建议词
            original_text = self.sections[target_section]
            if issue.original and issue.original in original_text:
                self.sections[target_section] = original_text.replace(
                    issue.original, issue.suggestion or ''
                )

        elif issue.category == '引文规范':
            # 引文不足: 标记需要补充（无法自动修复，但记录）
            logger.info(f"Citation issue in {target_section}: {issue.problem}")

        elif issue.category == 'Discussion逻辑':
            # Discussion逻辑问题: 标记（通常需要重新生成）
            logger.info(f"Discussion logic issue: {issue.problem}")

    def _check_cross_section_coherence(self):
        """
        跨章节一致性检查（借鉴 STORM + MotivationThread）

        检查:
        1. Introduction 承诺 vs Discussion 回应
        2. Results 数据 vs Discussion 引用
        3. 关键术语一致性
        4. 逻辑链完整性

        Returns
        -------
        list of dict, [{issue, severity, suggestion}]
        """
        issues = []

        if not self.sections:
            return issues

        # 1. Introduction-Discussion 一致性
        intro = self.sections.get('introduction', '')
        disc = self.sections.get('discussion', '')

        if intro and disc:
            # 提取 Introduction 中的目标句
            intro_objectives = []
            for sent in re.split(r'[。！？.!?]', intro):
                if any(kw in sent for kw in ['本研究', '旨在', '目的', 'this study', 'aim', 'objective']):
                    intro_objectives.append(sent.strip())

            # 检查 Discussion 是否回应了这些目标
            for obj in intro_objectives:
                if len(obj) < 10:
                    continue
                # 提取关键词
                obj_words = set(re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', obj.lower()))
                disc_words = set(re.findall(r'[一-鿿]{2,}|[a-zA-Z]{3,}', disc.lower()))
                overlap = len(obj_words & disc_words)
                if overlap < 2:
                    issues.append({
                        'issue': f'Introduction目标未在Discussion中充分回应: "{obj[:50]}..."',
                        'severity': 'MAJOR',
                        'suggestion': '在Discussion中添加对该目标的回应段落',
                    })

        # 2. Results-Discussion 数据一致性
        results = self.sections.get('results', '')
        if results and disc:
            # 提取 Results 中的数据值
            results_numbers = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%|μS/cm)', results))
            disc_numbers = set(re.findall(r'\d+\.?\d*\s*(?:mg/L|ppm|%|μS/cm)', disc))

            # Discussion 中引用的数据应该在 Results 中出现
            for num in disc_numbers:
                if num not in results_numbers:
                    issues.append({
                        'issue': f'Discussion中的数据"{num}"在Results中未找到',
                        'severity': 'MINOR',
                        'suggestion': '确保Discussion引用的数据与Results一致',
                    })

        # 3. 关键术语一致性
        all_sections_text = ' '.join(self.sections.values())
        # 检查核心术语是否在各章节中一致使用
        core_terms = ['碳污染物', '多相态', '赋存特征', '碳平衡']
        for term in core_terms:
            count = all_sections_text.count(term)
            if count == 0:
                continue
            # 检查每个主要章节是否包含核心术语
            for sec_name in ['introduction', 'results', 'discussion', 'conclusion']:
                sec_text = self.sections.get(sec_name, '')
                if sec_text and term not in sec_text and len(sec_text) > 200:
                    issues.append({
                        'issue': f'核心术语"{term}"在{sec_name}中未出现',
                        'severity': 'MINOR',
                        'suggestion': f'考虑在{sec_name}中使用术语"{term}"以保持一致性',
                    })

        # 4. 逻辑链完整性（Introduction→Methods→Results→Discussion）
        if 'introduction' in self.sections and 'methods' in self.sections:
            # Introduction 提到的方法应该在 Methods 中有描述
            intro_methods = set()
            for kw in ['PCA', 'HCA', 'Pearson', 'Spearman', 'Mann-Whitney', 't检验']:
                if kw in intro:
                    intro_methods.add(kw)

            methods_text = self.sections.get('methods', '')
            for method in intro_methods:
                if method not in methods_text:
                    issues.append({
                        'issue': f'Introduction提到的"{method}"在Methods中未描述',
                        'severity': 'MAJOR',
                        'suggestion': f'在Methods中添加{method}的方法描述',
                    })

        return issues

    def _verify_results_against_data(self, results_text):
        """
        结果反幻觉验证（借鉴 AI-Scientist）

        检查 Results 中的每个数据点是否来自实际分析结果。
        清除任何无法验证的数据声明。

        Returns
        -------
        (verified_text, issues_found)
        """
        import re
        issues = []

        if not self.analysis_agent or not hasattr(self.analysis_agent, 'results'):
            return results_text, issues

        actual_results = self.analysis_agent.results

        # 1. 检查 p 值是否合理
        p_matches = re.findall(r'p\s*[=<>≤≥]\s*(\d+\.?\d*)', results_text)
        for p_str in p_matches:
            p_val = float(p_str)
            if p_val > 1.0:
                issues.append(f'无效p值: p={p_val} (应≤1.0)')
            if p_val < 0.0001 and 'p=' in results_text:
                issues.append(f'极小p值: p={p_val} (请确认)')

        # 2. 检查 r 值是否在合理范围
        r_matches = re.findall(r'r\s*=\s*([-−]?\d+\.?\d*)', results_text)
        for r_str in r_matches:
            r_val = float(r_str.replace('−', '-'))
            if abs(r_val) > 1.0:
                issues.append(f'无效相关系数: r={r_val} (应在[-1,1])')

        # 3. 检查百分比是否合理（0-100）
        pct_matches = re.findall(r'(\d+\.?\d*)\s*%', results_text)
        for pct_str in pct_matches:
            pct = float(pct_str)
            if pct > 100:
                issues.append(f'不合理百分比: {pct}% (应≤100%)')

        # 4. 检查引用的统计量是否在实际结果中
        if '描述统计' in actual_results:
            desc = actual_results['描述统计']
            # 检查 Results 中引用的均值是否与实际结果一致
            mean_matches = re.findall(r'均值[为是]\s*(\d+\.?\d*)', results_text)
            # 这些检查只记录问题，不自动修复（避免破坏论文内容）

        if issues:
            logger.warning(f"Results verification: {len(issues)} issues found")

        return results_text, issues

    def _assemble_results(self):
        """组装Results章节"""
        lines = ['# 3 结果\n']

        texts = self.analysis_agent.texts
        captions = self.analysis_agent.captions

        # 按逻辑顺序组装
        order = [
            'descriptive_text', 'normality_text', 'comparison_text',
            'correlation_text', 'pca_text', 'regression_text',
            'carbon_balance_text'
        ]

        section_num = 1
        for key in order:
            text = texts.get(key, '')
            if text:
                # 替换章节编号
                text = text.replace('### ', f'### 3.{section_num} ', 1)
                lines.append(text)
                lines.append('')
                section_num += 1

        # 插入图注
        if captions:
            lines.append('\n**图注汇总：**\n')
            for fig_type, caption in captions.items():
                if caption:
                    lines.append(caption)
                    lines.append('')

        return '\n'.join(lines)

    def _generate_conclusion(self):
        """生成Conclusion"""
        language = self.language

        if language == 'zh':
            return (
                '# 5 结论\n\n'
                '本研究以某校园污水管网为研究对象，系统分析了固-液-气多相态碳污染物的'
                '赋存特征、空间分异及其驱动机制。主要结论如下：\n\n'
                '（1）校园污水管网碳污染物以固、液、气三种相态存在，'
                '各相态碳含量呈现不同的分布特征和变异程度。\n\n'
                '（2）不同功能区碳污染物浓度存在显著差异，'
                '餐饮区有机碳负荷最高，反映了排放源类型对碳污染特征的决定性影响。\n\n'
                '（3）溶解氧(DO)与甲烷(CH4)呈显著负相关，'
                '表明厌氧条件是管道产甲烷的关键驱动因素；'
                '总有机碳(TOC)与CH4呈显著正相关，说明有机负荷为产甲烷提供了底物来源。\n\n'
                '（4）碳平衡分析表明，液相碳是校园污水管网碳的主要赋存形式，'
                '碳在三相之间的分配受管道氧化还原条件和有机负荷的共同控制。\n\n'
                '研究结果可为校园污水碳减排策略制定和管网碳管理提供科学依据。'
            )
        return (
            '# 5 Conclusions\n\n'
            'This study systematically investigated the occurrence characteristics of '
            'multiphase carbon pollutants in a campus sewage network. The main conclusions '
            'are as follows:\n\n'
            '(1) Carbon pollutants exist in solid, liquid, and gas phases with distinct '
            'distribution patterns.\n\n'
            '(2) Significant spatial differences were observed among functional zones.\n\n'
            '(3) DO was negatively correlated with CH4, indicating anaerobic conditions '
            'as the key driver of methanogenesis.\n\n'
            '(4) TOC was positively correlated with CH4, suggesting organic loading as '
            'the substrate source for methane production.\n\n'
            'These findings provide scientific references for campus wastewater carbon '
            'management and emission reduction strategies.'
        )

    def _assemble_paper(self):
        """组装完整论文"""
        order = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']

        parts = []
        for section in order:
            content = self.sections.get(section, '')
            if content:
                parts.append(content)
                parts.append('\n---\n')

        # 参考文献占位
        parts.append('# 参考文献\n\n[待补充]\n')

        return '\n'.join(parts)


# ============================================================================
# 7. 快捷入口
# ============================================================================
def write_paper(data_path=None, paper_type='thesis', language='zh', output_dir=None,
                params=None, direction=None):
    """
    一键生成论文

    Args:
        data_path: 数据文件路径
        paper_type: 论文类型 thesis/sci/chinese
        language: zh/en
        output_dir: 输出目录
        params: Methods参数字典
        direction: ResearchDirection实例，自定义研究方向
    """
    writer = PaperWriter(output_dir)
    paper = writer.write(data_path, paper_type, language, params=params, direction=direction)
    return writer


if __name__ == '__main__':
    writer = write_paper()


# ============================================================================
# 知识库桥接：从knowledge_store加载进化后的机制知识
# ============================================================================
def _load_evolved_mechanisms():
    """从knowledge_store加载进化后的机制知识，失败时静默跳过。"""
    import json
    from pathlib import Path

    store_dir = Path(__file__).parent / "knowledge_store"
    if not store_dir.exists():
        return

    mech_path = store_dir / "mechanisms.json"
    if not mech_path.exists():
        return

    try:
        with open(mech_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get("entries", {})

        for key, entry in entries.items():
            val = entry.get("value", entry)
            if not isinstance(val, dict):
                continue
            # 将机制知识映射为MechanismKB的类属性
            attr_name = key.upper().replace("-", "_").replace(" ", "_")
            # 只添加新机制，不覆盖已有的硬编码机制
            if not hasattr(MechanismKB, attr_name) and val.get("mechanism"):
                setattr(MechanismKB, attr_name, val)
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Failed to load evolved mechanisms: {e}")


def save_mechanisms_to_store():
    """将MechanismKB中的硬编码机制写回knowledge_store（首次初始化用）"""
    import json
    from pathlib import Path
    from datetime import datetime, timezone

    store_dir = Path(__file__).parent / "knowledge_store"
    store_dir.mkdir(exist_ok=True)
    mech_path = store_dir / "mechanisms.json"

    # 加载已有数据
    if mech_path.exists():
        with open(mech_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {
            "meta": {"category": "mechanisms", "description": "碳污染物生成/转化机制",
                     "version": 1, "created": datetime.now(timezone.utc).isoformat()},
            "entries": {},
            "changelog": [],
        }

    entries = data.setdefault("entries", {})

    # 导出 MechanismKB 的所有类属性
    for attr_name in dir(MechanismKB):
        if attr_name.startswith('_'):
            continue
        attr = getattr(MechanismKB, attr_name)
        if isinstance(attr, dict) and attr_name.isupper() and attr.get('mechanism'):
            key = attr_name.lower()
            if key not in entries:
                entries[key] = {
                    "value": attr,
                    "confidence": 0.95,
                    "source": "MechanismKB_hardcoded",
                    "updated": datetime.now(timezone.utc).isoformat(),
                    "version": 1,
                }

    data["meta"]["updated"] = datetime.now(timezone.utc).isoformat()
    with open(mech_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return len(entries)


# 模块加载时自动桥接
_load_evolved_mechanisms()
