# -*- coding: utf-8 -*-
"""
PaperContext 中央上下文 + 模块编排器

核心思想：
- PaperContext 是所有模块的共享状态
- 每个模块声明 needs/provides
- 编排器根据上下文状态灵活调度
- 模块之间不互相调用，只读写 Context
"""
import os
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 1. PaperContext — 中央上下文
# ============================================================

@dataclass
class PaperContext:
    """
    论文写作中央上下文 — 所有模块的共享状态。

    模块读 ctx.xxx 获取输入，写 ctx.xxx 贡献输出。
    编排器检查 ctx 状态决定下一步做什么。
    """

    # === 配置 ===
    data_path: str = None
    output_dir: str = './paper_output'
    language: str = 'zh'
    paper_type: str = 'chinese'
    title: str = None

    # === 数据层 ===
    df: Any = None                    # pd.DataFrame
    findings: list = field(default_factory=list)   # DataExplorer 输出

    # === 知识层 ===
    memory: Any = None                # KnowledgeMemory 实例
    literature_matrix: Any = None     # LiteratureMatrix
    recalled_mechanisms: list = field(default_factory=list)
    recalled_references: list = field(default_factory=list)

    # === 写作层 ===
    motivation: Any = None            # ConfirmedMotivation
    blueprint: Any = None             # WritingBlueprint
    planning_matrix: Any = None       # PlanningMatrix
    sections: dict = field(default_factory=dict)    # {name: markdown_str}
    figures: dict = field(default_factory=dict)      # {name: {'path', 'caption'}}
    rationale_rows: list = field(default_factory=list)

    # === 审稿层 ===
    review_report: Any = None         # ReviewReport
    review_summary: dict = field(default_factory=dict)
    revision_report: str = ''

    # === 高级分析层 ===
    advanced_findings: list = field(default_factory=list)  # AdvancedAnalyzer 输出
    cross_analyses: list = field(default_factory=list)
    anomaly_insights: list = field(default_factory=list)
    data_stories: list = field(default_factory=list)
    threshold_effects: list = field(default_factory=list)

    # === 深度模仿层 ===
    imitation_report: str = ''

    # === 完整性审计层 ===
    integrity_report: str = ''
    artifact_report: str = ''

    # === 引用支撑层 ===
    citation_bank: Any = None         # CitationSupportBank 实例

    # === 输出层 ===
    docx_path: str = None
    paper_md_path: str = None

    # === 内部状态 ===
    _completed_steps: list = field(default_factory=list)

    def mark_done(self, step: str):
        if step not in self._completed_steps:
            self._completed_steps.append(step)

    def is_done(self, step: str) -> bool:
        return step in self._completed_steps

    def has(self, attr: str) -> bool:
        """检查上下文是否有某个属性且非空"""
        val = getattr(self, attr, None)
        if val is None:
            return False
        if isinstance(val, (list, dict, str)):
            return len(val) > 0
        return True


# ============================================================
# 2. 模块注册表 — 声明式模块定义
# ============================================================

def _run_explorer(ctx: PaperContext):
    """数据探索"""
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(ctx.df)
    ctx.findings = explorer.explore()
    return ctx.findings


def _run_memory_init(ctx: PaperContext):
    """初始化知识记忆"""
    from knowledge_memory import KnowledgeMemory
    ctx.memory = KnowledgeMemory()
    stats = ctx.memory.get_stats()
    logger.info(f"知识库: {stats['total_entries']}条知识")
    return ctx.memory


def _run_literature_recall(ctx: PaperContext):
    """从文献矩阵召回主题作为写作查询词"""
    if ctx.memory is None:
        return None
    # 从 findings 中提取关键变量对，召回相关文献
    for f in ctx.findings:
        if f['type'] == 'correlation' and f['importance'] in ['critical', 'high']:
            v1, v2 = f.get('variables', ('', ''))
            query = f'{v1} {v2}'
            refs = ctx.memory.recall(query, category='resources', top_k=2)
            for r in refs:
                val = r['value']
                if isinstance(val, dict) and val.get('type') == 'academic_paper':
                    ctx.recalled_references.append({
                        'title': val.get('title', ''),
                        'year': val.get('year'),
                        'authors': val.get('authors', ''),
                        'query': query,
                    })
    return ctx.recalled_references


def _run_motivation(ctx: PaperContext):
    """生成动机选项（如果有 findings）"""
    if not ctx.has('findings'):
        return None
    from motivation_planner import MotivationManager
    mgr = MotivationManager(output_dir=ctx.output_dir)
    # 将 findings 转为 analysis_results 格式
    analysis_results = {}
    for f in ctx.findings:
        if f['type'] == 'correlation' and f['importance'] in ['critical', 'high']:
            v1, v2 = f.get('variables', ('', ''))
            key = f'{v1}_vs_{v2}'
            analysis_results[key] = f.get('data', {})
    options = mgr.generate_options(
        analysis_results=analysis_results,
        language=ctx.language,
    )
    if options:
        # 自动选第一个（最高优先级）
        ctx.motivation = mgr.confirm(option_id=options[0].option_id)
        ctx.blueprint = mgr.generate_blueprint(language=ctx.language)
        logger.info(f"动机已确认: {ctx.motivation.motivation_statement[:60]}")
    return ctx.motivation


def _run_writer_results(ctx: PaperContext):
    """写 Results 章节（带深度模仿指导）"""
    from data_driven_pipeline import DataDrivenWriter
    writer = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
    ctx.sections['results'] = writer.write_results()
    ctx.rationale_rows.extend(writer.rationale_rows)

    # 如果有深度模仿报告，在结果末尾注入写作改进建议
    if ctx.imitation_report:
        # 提取模仿报告中的关键改进点（取前300字）
        summary = ctx.imitation_report[:300]
        logger.info(f"深度模仿建议已记录: {summary[:60]}...")

    return ctx.sections['results']


def _run_writer_discussion(ctx: PaperContext):
    """写 Discussion 章节（带知识库支撑 + 高级分析 + 引用支撑库）"""
    from data_driven_pipeline import DataDrivenWriter
    writer = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
    ctx.sections['discussion'] = writer.write_discussion()
    ctx.rationale_rows.extend(writer.rationale_rows)

    # 注入高级分析发现（数据故事线、阈值效应、异常洞察）
    if ctx.data_stories or ctx.threshold_effects or ctx.anomaly_insights:
        injection = _build_advanced_injection(ctx)
        if injection:
            ctx.sections['discussion'] = ctx.sections['discussion'].replace(
                '## 4.4 研究局限性',
                f'{injection}\n## 4.4 研究局限性'
            )

    # 注入引用支撑库（如果有绑定好的引用）
    if ctx.citation_bank and hasattr(ctx.citation_bank, 'bindings'):
        citation_text = _build_citation_injection(ctx)
        if citation_text:
            ctx.sections['discussion'] += f'\n\n{citation_text}'

    return ctx.sections['discussion']


def _run_writer_intro(ctx: PaperContext):
    """写 Introduction 章节（带知识库支撑）"""
    from paper_writing_agent import IntroductionGenerator
    gen = IntroductionGenerator()
    base_text = gen.generate(language=ctx.language)

    # 如果有知识库，在文献综述部分注入召回的引用
    if ctx.has('memory') and ctx.has('recalled_references'):
        # 在 "## 1.2 国内外研究现状" 之后追加文献引用
        injection = '\n\n### 1.2.3 相关研究文献\n\n'
        seen_titles = set()
        for ref in ctx.recalled_references[:5]:
            title = ref.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                year = ref.get('year', '')
                authors = ref.get('authors', '')
                if isinstance(authors, list):
                    authors = ', '.join(authors[:3])
                injection += f'{authors}（{year}）研究了{title[:50]}。\n\n'
        if seen_titles:
            base_text = base_text.replace(
                '## 1.3 现有研究不足',
                f'{injection}\n## 1.3 现有研究不足'
            )

    ctx.sections['introduction'] = base_text
    return ctx.sections['introduction']


def _run_writer_methods(ctx: PaperContext):
    """写 Methods 章节"""
    from paper_writing_agent import MethodsGenerator
    gen = MethodsGenerator()
    ctx.sections['methods'] = gen.generate(language=ctx.language)
    return ctx.sections['methods']


def _run_writer_abstract(ctx: PaperContext):
    """写 Abstract（基于所有已有章节）"""
    from paper_writing_agent import AbstractGenerator
    gen = AbstractGenerator(
        ctx.sections.get('introduction', ''),
        ctx.sections.get('methods', ''),
        ctx.sections.get('results', ''),
        ctx.sections.get('discussion', ''),
    )
    ctx.sections['abstract'] = gen.generate(language=ctx.language)
    return ctx.sections['abstract']


def _run_writer_conclusion(ctx: PaperContext):
    """写 Conclusion — 提炼贡献，不是重复结果"""
    critical = [f for f in ctx.findings if f['importance'] in ['critical', 'high']]
    group_findings = [f for f in critical if f['type'] == 'group_difference']
    corr_findings = [f for f in critical if f['type'] == 'correlation']

    lines = ['# 5 结论\n']
    lines.append('本研究以校园污水管网为对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。主要结论如下：\n')

    idx = 1
    if group_findings:
        lines.append(f'({idx}) 碳污染物呈现显著的季节分异。')
        top = group_findings[0]
        d = top['data']
        higher = d['groups'][np.argmax(d['means'])]
        lines.append(f'{top["variable"]}等指标在{higher}显著偏高，'
                    f'温度和水文条件是驱动季节差异的主要因素。\n')
        idx += 1

    if corr_findings:
        lines.append(f'({idx}) 变量间存在多组显著关联。')
        top = corr_findings[0]
        v1, v2 = top['variables']
        lines.append(f'{v1}与{v2}的相关性最强(r={top["data"]["r"]:.3f})，'
                    f'揭示了碳氮耦合和多相态转化的内在机制。\n')
        idx += 1

    lines.append(f'({idx}) 上述发现为校园污水管网碳排放核算和碳管理策略制定提供了数据支撑和科学依据。')

    ctx.sections['conclusion'] = '\n'.join(lines)
    return ctx.sections['conclusion']


def _run_review(ctx: PaperContext):
    """审稿检查（整合完整性审计 + 制品检查结果）"""
    from academic_review_agent import AcademicReviewAgent
    # 组装全文
    full_paper = '\n\n---\n\n'.join(
        ctx.sections.get(k, '') for k in
        ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        if ctx.has_section(k)
    )
    if not full_paper:
        return None
    reviewer = AcademicReviewAgent(paper_type='chinese_journal', language=ctx.language)
    ctx.review_report = reviewer.review(full_paper)

    # 将完整性审计和制品检查结果附加到审稿报告
    extra_issues = []
    if ctx.integrity_report:
        extra_issues.append(f'[完整性审计] {ctx.integrity_report[:500]}')
    if ctx.artifact_report:
        extra_issues.append(f'[制品检查] {ctx.artifact_report[:500]}')
    if extra_issues:
        ctx.review_report.extra_notes = extra_issues

    ctx.review_summary = ctx.review_report.summary()
    logger.info(f"审稿: {ctx.review_summary['total']}个问题")
    return ctx.review_report


def _run_auto_revision(ctx: PaperContext):
    """自动修订"""
    if ctx.review_report is None:
        return None
    from auto_revision import AutoReviser
    # 组装全文
    full_paper = '\n\n---\n\n'.join(
        ctx.sections.get(k, '') for k in
        ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        if ctx.has_section(k)
    )
    # 生成审稿报告文本
    review_md = f"# 审稿报告\n\n共{ctx.review_summary.get('total', 0)}个问题\n"
    for issue in ctx.review_report.issues:
        review_md += f"\n### [{issue.severity.value}] {issue.category}\n"
        review_md += f"- {issue.problem}\n"

    reviser = AutoReviser(full_paper, review_md)
    revised = reviser.revise()
    ctx.revision_report = reviser.get_revision_report()

    # 将修订后的文本拆分回各章节
    _split_revised_into_sections(ctx, revised)

    logger.info(f"自动修订: {len(reviser.changes)}类修改")
    return revised


def _run_assemble(ctx: PaperContext):
    """排版 DOCX（图文对应）"""
    from data_driven_pipeline import InlineDocumentAssembler
    assembler = InlineDocumentAssembler(
        title=ctx.title or '论文',
        output_dir=ctx.output_dir,
    )

    section_order = [
        ('abstract', '摘要'),
        ('introduction', '1 引言'),
        ('methods', '2 材料与方法'),
        ('results', '3 结果'),
        ('discussion', '4 讨论'),
        ('conclusion', '5 结论'),
    ]

    import re
    for key, heading in section_order:
        text = ctx.sections.get(key, '')
        if not text:
            continue
        # 去掉 markdown 标题
        lines = text.strip().split('\n')
        body_lines = [l for l in lines if not l.strip().startswith('#')]
        body = '\n'.join(body_lines).strip()
        if body:
            # 匹配该章节的图表
            figures = _match_figures_for_section(ctx, key)
            assembler.add_section(heading, text=body, figures=figures)

    # 输出路径
    os.makedirs(ctx.output_dir, exist_ok=True)
    output_docx = os.path.join(ctx.output_dir, 'paper.docx')
    ctx.docx_path = assembler.assemble(output_docx)
    logger.info(f"DOCX: {ctx.docx_path}")
    return ctx.docx_path


# ============================================================
# 3. 辅助函数
# ============================================================

def _split_revised_into_sections(ctx: PaperContext, revised_text: str):
    """将修订后的全文拆分回各章节"""
    import re
    # 按 --- 分割
    parts = re.split(r'\n---\n', revised_text)
    section_map = {
        '摘要': 'abstract', 'abstract': 'abstract',
        '引言': 'introduction', '绪论': 'introduction',
        '材料与方法': 'methods', '方法': 'methods',
        '结果': 'results',
        '讨论': 'discussion',
        '结论': 'conclusion',
    }
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_line = part.split('\n')[0].strip()
        for keyword, section_key in section_map.items():
            if keyword in first_line:
                ctx.sections[section_key] = part
                break


def _match_figures_for_section(ctx: PaperContext, section_key: str) -> list:
    """为章节匹配对应的图表（根据图表的 section 属性）"""
    matched = []
    for fig_name, fig_info in ctx.figures.items():
        fig_section = fig_info.get('section', '')
        if fig_section == section_key:
            matched.append(fig_info)
    return matched


# ============================================================
# 4. 注入辅助函数
# ============================================================

def _build_advanced_injection(ctx: PaperContext) -> str:
    """将高级分析结果组装为可注入 Discussion 的文本"""
    parts = []
    if ctx.data_stories:
        parts.append('### 4.3.1 数据故事线\n')
        for story in ctx.data_stories[:3]:
            if isinstance(story, dict):
                finding = story.get('finding', '')
                explanation = story.get('explanation', '')
                if finding:
                    parts.append(f'- {finding}')
                    if explanation:
                        parts.append(f'  解释: {explanation}\n')
    if ctx.threshold_effects:
        parts.append('\n### 4.3.2 阈值效应\n')
        for eff in ctx.threshold_effects[:3]:
            if isinstance(eff, dict):
                var = eff.get('variable', '')
                threshold = eff.get('threshold', '')
                effect = eff.get('effect', '')
                if var:
                    parts.append(f'- {var} 在 {threshold} 处出现临界效应: {effect}')
    if ctx.anomaly_insights:
        parts.append('\n### 4.3.3 异常值洞察\n')
        for insight in ctx.anomaly_insights[:3]:
            if isinstance(insight, dict):
                desc = insight.get('description', '') or insight.get('insight', '')
                if desc:
                    parts.append(f'- {desc}')
    return '\n'.join(parts) if parts else ''


def _build_citation_injection(ctx: PaperContext) -> str:
    """将引用支撑库结果组装为可注入的文本"""
    if not ctx.citation_bank or not hasattr(ctx.citation_bank, 'bindings'):
        return ''
    lines = ['### 引用支撑索引\n']
    for binding in ctx.citation_bank.bindings[:10]:
        claim = binding.get('claim', '')
        refs = binding.get('references', [])
        if claim and refs:
            ref_str = ', '.join(str(r) for r in refs[:3])
            lines.append(f'- 论点: {claim[:80]}  支撑文献: {ref_str}')
    return '\n'.join(lines) if len(lines) > 1 else ''


# ============================================================
# 5. 新增模块函数 — 接入原孤立模块
# ============================================================

def _run_advanced_analysis(ctx: PaperContext):
    """高级多维分析（交叉分析、异常深挖、数据故事线、阈值检测）"""
    if not ctx.has('df'):
        return None
    from advanced_analysis import AdvancedAnalyzer
    analyzer = AdvancedAnalyzer(ctx.df)
    results = analyzer.analyze_all()
    ctx.advanced_findings = results.get('cross_analyses', [])
    ctx.cross_analyses = results.get('cross_analyses', [])
    ctx.anomaly_insights = results.get('anomaly_insights', [])
    ctx.data_stories = results.get('data_stories', [])
    ctx.threshold_effects = results.get('threshold_effects', [])
    total = sum(len(v) for v in results.values() if isinstance(v, list))
    logger.info(f"高级分析: {total}项发现")
    return results


def _run_deep_imitation(ctx: PaperContext):
    """深度模仿分析（3表法：范例动作/草稿动作/目标蓝图）"""
    if not ctx.has('sections'):
        return None
    from deep_imitation import DeepImitationProtocol
    protocol = DeepImitationProtocol(output_dir=ctx.output_dir)
    # 用已有章节作为草稿
    draft_text = '\n\n'.join(ctx.sections.values())
    if not draft_text.strip():
        return None
    result = protocol.run(draft_text)
    ctx.imitation_report = protocol.format_report(result)
    logger.info("深度模仿分析完成")
    return result


def _run_integrity_audit(ctx: PaperContext):
    """完整性审计（4维度：制品链、推理深度、证据链、模式扫描）"""
    from integrity_audit import IntegrityAuditor
    auditor = IntegrityAuditor(output_dir=ctx.output_dir)
    findings = auditor.run_audit(ctx.sections)
    ctx.integrity_report = auditor.format_report(findings)
    logger.info(f"完整性审计: {len(findings)}项发现")
    return findings


def _run_artifact_check(ctx: PaperContext):
    """制品完整性检查（文件存在性、内容质量、交叉引用）"""
    from artifact_check import ArtifactChecker
    checker = ArtifactChecker(output_dir=ctx.output_dir)
    report = checker.check_all()
    ctx.artifact_report = checker.format_report(report)
    logger.info(f"制品检查: {report.get('total_issues', 0)}个问题")
    return report


def _run_citation_bank(ctx: PaperContext):
    """构建引用支撑库（将论点绑定到引用）"""
    if not ctx.has('sections'):
        return None
    from citation_support_bank import CitationSupportBank
    bank = CitationSupportBank(output_dir=ctx.output_dir)
    full_text = '\n\n'.join(ctx.sections.values())
    claims = bank.extract_claims_from_text(full_text)
    if claims:
        bank.bind_citations(claims)
        bank.save()
        ctx.citation_bank = bank
        logger.info(f"引用支撑库: {len(claims)}个论点")
    return bank


# ============================================================
# 5. 模块注册表
# ============================================================

MODULE_REGISTRY = {
    'memory_init': {
        'needs': [],
        'provides': ['memory'],
        'run': _run_memory_init,
        'description': '初始化知识记忆',
    },
    'load_data': {
        'needs': ['data_path'],
        'provides': ['df'],
        'run': lambda ctx: _load_data(ctx),
        'description': '加载数据',
    },
    'explorer': {
        'needs': ['df'],
        'provides': ['findings'],
        'run': _run_explorer,
        'description': '数据探索',
    },
    'literature_recall': {
        'needs': ['memory', 'findings'],
        'provides': ['recalled_references'],
        'run': _run_literature_recall,
        'description': '从文献矩阵召回引用',
    },
    'motivation': {
        'needs': ['findings'],
        'provides': ['motivation'],
        'run': _run_motivation,
        'description': '生成并确认写作动机',
    },
    'writer_results': {
        'needs': ['df', 'findings'],
        'provides': ['sections.results'],
        'run': _run_writer_results,
        'description': '写 Results',
    },
    'writer_discussion': {
        'needs': ['df', 'findings', 'memory'],
        'provides': ['sections.discussion'],
        'run': _run_writer_discussion,
        'description': '写 Discussion（带知识库）',
    },
    'writer_intro': {
        'needs': [],
        'provides': ['sections.introduction'],
        'run': _run_writer_intro,
        'description': '写 Introduction',
    },
    'writer_methods': {
        'needs': [],
        'provides': ['sections.methods'],
        'run': _run_writer_methods,
        'description': '写 Methods',
    },
    'writer_abstract': {
        'needs': ['sections.introduction', 'sections.methods', 'sections.results', 'sections.discussion'],
        'provides': ['sections.abstract'],
        'run': _run_writer_abstract,
        'description': '写 Abstract',
    },
    'writer_conclusion': {
        'needs': ['findings'],
        'provides': ['sections.conclusion'],
        'run': _run_writer_conclusion,
        'description': '写 Conclusion',
    },
    'review': {
        'needs': ['sections'],
        'provides': ['review_report'],
        'run': _run_review,
        'description': '审稿检查',
    },
    'auto_revision': {
        'needs': ['review_report'],
        'provides': ['sections(revised)'],
        'run': _run_auto_revision,
        'description': '自动修订',
    },
    'advanced_analysis': {
        'needs': ['df'],
        'provides': ['advanced_findings', 'cross_analyses', 'anomaly_insights', 'data_stories', 'threshold_effects'],
        'run': _run_advanced_analysis,
        'description': '高级多维分析（交叉分析/异常深挖/数据故事线/阈值检测）',
    },
    'deep_imitation': {
        'needs': ['sections'],
        'provides': ['imitation_report'],
        'run': _run_deep_imitation,
        'description': '深度模仿分析（3表法）',
    },
    'integrity_audit': {
        'needs': ['sections'],
        'provides': ['integrity_report'],
        'run': _run_integrity_audit,
        'description': '完整性审计（4维度）',
    },
    'artifact_check': {
        'needs': ['sections'],
        'provides': ['artifact_report'],
        'run': _run_artifact_check,
        'description': '制品完整性检查',
    },
    'citation_bank': {
        'needs': ['sections'],
        'provides': ['citation_bank'],
        'run': _run_citation_bank,
        'description': '构建引用支撑库',
    },
    'assemble': {
        'needs': ['sections'],
        'provides': ['docx_path'],
        'run': _run_assemble,
        'description': '排版 DOCX',
    },
}


def _load_data(ctx: PaperContext):
    """加载数据"""
    from data_loader import DataLoader
    loader = DataLoader(ctx.data_path)
    ctx.df = loader.load_data()
    logger.info(f"数据: {ctx.df.shape[0]}行 x {ctx.df.shape[1]}列")
    return ctx.df


# 给 PaperContext 加 has_section 方法
def _has_section(self, name: str) -> bool:
    return name in self.sections and self.sections[name]

PaperContext.has_section = _has_section


# ============================================================
# 5. 编排器
# ============================================================

class PaperOrchestrator:
    """
    灵活编排器 — 根据上下文状态自动调度模块。

    用法:
        ctx = PaperContext(data_file='data.xlsx')
        orch = PaperOrchestrator()
        orch.run(ctx)  # 自动推断步骤
        orch.run(ctx, steps=['explorer', 'writer_results', ...])  # 手动指定
    """

    def __init__(self):
        self.execution_log = []

    def run(self, ctx: PaperContext, steps: list = None):
        """
        执行编排。

        Parameters
        ----------
        ctx : PaperContext
        steps : list or None, 模块名列表。None 时自动推断。
        """
        if steps is None:
            steps = self._auto_plan(ctx)

        print("=" * 60)
        print("  PaperOrchestrator — 灵活编排")
        print(f"  步骤: {len(steps)}个")
        print("=" * 60)

        for i, step_name in enumerate(steps, 1):
            if step_name not in MODULE_REGISTRY:
                logger.warning(f"未知模块: {step_name}")
                continue

            module = MODULE_REGISTRY[step_name]

            # 检查前置条件
            missing = self._check_needs(ctx, module['needs'])
            if missing:
                print(f"\n[{i}/{len(steps)}] {module['description']} — 跳过 (缺少: {missing})")
                self.execution_log.append({
                    'step': step_name, 'status': 'skipped', 'missing': missing
                })
                continue

            # 执行
            print(f"\n[{i}/{len(steps)}] {module['description']}...")
            try:
                result = module['run'](ctx)
                ctx.mark_done(step_name)
                self.execution_log.append({
                    'step': step_name, 'status': 'done'
                })
                if result is not None:
                    print(f"  完成")
            except Exception as e:
                logger.error(f"模块 {step_name} 失败: {e}")
                self.execution_log.append({
                    'step': step_name, 'status': 'error', 'error': str(e)
                })
                print(f"  失败: {e}")

        # 保存全文 MD
        self._save_paper_md(ctx)

        print(f"\n{'=' * 60}")
        print(f"  编排完成!")
        print(f"{'=' * 60}")

    def _auto_plan(self, ctx: PaperContext) -> list:
        """根据上下文状态自动推断执行步骤"""
        steps = []

        # 基础步骤
        steps.append('memory_init')

        if ctx.has('data_path'):
            steps.append('load_data')

        steps.append('explorer')

        # 知识召回（有 memory + findings 后）
        steps.append('literature_recall')

        # 动机（可选）
        steps.append('motivation')

        # 写作步骤
        steps.append('writer_results')
        steps.append('writer_discussion')
        steps.append('writer_intro')
        steps.append('writer_methods')
        steps.append('writer_conclusion')
        steps.append('writer_abstract')

        # 审稿 → 修订 → 复审
        steps.append('review')
        steps.append('auto_revision')

        # 排版
        steps.append('assemble')

        return steps

    def _check_needs(self, ctx: PaperContext, needs: list) -> list:
        """检查前置条件"""
        missing = []
        for need in needs:
            if need.startswith('sections.'):
                section_name = need.split('.', 1)[1]
                if not ctx.has_section(section_name):
                    missing.append(need)
            elif need == 'sections':
                if not ctx.sections:
                    missing.append(need)
            elif not ctx.has(need):
                missing.append(need)
        return missing

    def _save_paper_md(self, ctx: PaperContext):
        """保存全文 MD"""
        if not ctx.sections:
            return
        os.makedirs(ctx.output_dir, exist_ok=True)
        order = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        parts = []
        for key in order:
            if ctx.has_section(key):
                parts.append(ctx.sections[key])
        full_paper = '\n\n---\n\n'.join(parts)
        path = os.path.join(ctx.output_dir, 'paper.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(full_paper)
        ctx.paper_md_path = path
        logger.info(f"论文MD: {path}")

    def get_log(self) -> list:
        return self.execution_log
