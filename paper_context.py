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

# Claude 写作引擎（通过 CLI 调用）
_claude_writer = None

def _get_claude_writer():
    global _claude_writer
    if _claude_writer is None:
        try:
            from claude_writer import ClaudeWriter
            _claude_writer = ClaudeWriter(timeout=180)
        except Exception as e:
            logger.warning(f"ClaudeWriter init failed: {e}")
    return _claude_writer


def _get_domain_config(ctx):
    """从 ctx 获取领域配置，延迟初始化"""
    if ctx.domain_config:
        return ctx.domain_config
    if ctx.domain:
        from domain_config import get_config
        ctx.domain_config = get_config(ctx.domain)
        return ctx.domain_config
    return None
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
    domain: str = None           # 领域名称，如 'sewer_carbon', 'water_quality'
    domain_config: Any = None    # DomainConfig 实例

    # === 数据层 ===
    df: Any = None                    # pd.DataFrame
    findings: list = field(default_factory=list)   # DataExplorer 输出

    # === 知识层 ===
    memory: Any = None                # KnowledgeMemory 实例
    literature_matrix: Any = None     # LiteratureMatrix
    recalled_mechanisms: list = field(default_factory=list)

    # === 文献学习层 ===
    papers_dir: str = None            # 论文目录路径
    papers_read: list = field(default_factory=list)    # 已读论文列表
    learned_patterns: dict = field(default_factory=dict)  # 学到的写作模式
    learned_mechanisms: list = field(default_factory=list)  # 学到的机制知识
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
    # 优先用 Claude 生成 Results
    claude = _get_claude_writer()
    if claude and ctx.has('findings'):
        result = claude.write_results(
            findings=ctx.findings,
            figures=ctx.figures if ctx.figures else None,
            learned_patterns=ctx.learned_patterns if ctx.learned_patterns else None,
        )
        if result:
            ctx.sections['results'] = result
            return result

    # 回退：模板
    tpl_writer = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
    ctx.sections['results'] = tpl_writer.write_results()
    ctx.rationale_rows.extend(tpl_writer.rationale_rows)
    return ctx.sections['results']


def _run_writer_discussion(ctx: PaperContext):
    """写 Discussion 章节（优先 Claude 生成，回退模板）"""
    # 检查是否有预生成的 Discussion 文件
    prebuilt_path = os.path.join(ctx.output_dir, 'discussion_claude.md')
    if os.path.exists(prebuilt_path):
        with open(prebuilt_path, encoding='utf-8') as f:
            prebuilt = f.read()
        if len(prebuilt) > 500:
            ctx.sections['discussion'] = prebuilt
            logger.info(f"Discussion: 使用预生成文件 ({len(prebuilt)} 字)")
            return prebuilt

    writer = _get_claude_writer()
    if writer and ctx.has('findings'):
        # 收集机制知识
        mechanisms = {}
        if ctx.has('memory'):
            for f in ctx.findings:
                if f.get('type') == 'correlation':
                    v1, v2 = f.get('variables', ('', ''))
                    query = f'{v1} {v2}'
                    mechs = ctx.memory.recall(query, category='mechanisms', top_k=1)
                    if mechs:
                        mechanisms[f'{v1}_vs_{v2}'] = mechs[0].get('value', {}).get('mechanism', '')

        # 合并学到的机制（从 pattern_learning 模块）
        if ctx.learned_mechanisms:
            for m in ctx.learned_mechanisms[:10]:
                var1 = m.get('var1', '')
                var2 = m.get('var2', '')
                evidence = m.get('evidence', '') or m.get('mechanism', '')
                if var1 and var2 and evidence:
                    mechanisms[f'{var1}_vs_{var2}'] = evidence

        result = writer.write_discussion(
            findings=ctx.findings,
            mechanisms=mechanisms,
            language=ctx.language,
            recalled_refs=ctx.recalled_references if ctx.has('recalled_references') else None,
            learned_patterns=ctx.learned_patterns if ctx.learned_patterns else None,
        )
        if result:
            ctx.sections['discussion'] = result
            return result

    # 回退：使用模板
    from data_driven_pipeline import DataDrivenWriter
    tpl_writer = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
    ctx.sections['discussion'] = tpl_writer.write_discussion()
    ctx.rationale_rows.extend(tpl_writer.rationale_rows)
    return ctx.sections['discussion']


def _run_writer_intro(ctx: PaperContext):
    """写 Introduction 章节（优先 Claude 生成，回退模板）"""
    writer = _get_claude_writer()
    if writer and ctx.has('findings'):
        result = writer.write_introduction(
            findings=ctx.findings,
            language=ctx.language,
            recalled_refs=ctx.recalled_references if ctx.has('recalled_references') else None,
            learned_patterns=ctx.learned_patterns if ctx.learned_patterns else None,
        )
        if result:
            ctx.sections['introduction'] = result
            return result

    # 回退：使用模板
    from paper_writing_agent import IntroductionGenerator
    gen = IntroductionGenerator()
    base_text = gen.generate(language=ctx.language)
    ctx.sections['introduction'] = base_text
    return ctx.sections['introduction']


def _run_writer_methods(ctx: PaperContext):
    """写 Methods 章节（优先 Claude 生成，回退模板）"""
    writer = _get_claude_writer()
    if writer and ctx.has('df'):
        data_info = {
            'n_samples': len(ctx.df),
            'n_variables': len(ctx.df.columns),
            'variables': list(ctx.df.columns),
            'groups': list(ctx.df.select_dtypes(include=['object', 'category']).columns),
        }
        # 注入领域标准
        dc = _get_domain_config(ctx)
        if dc and dc.standards:
            data_info['standards'] = dc.standards
        result = writer.write_methods(data_info=data_info, language=ctx.language)
        if result:
            ctx.sections['methods'] = result
            return result

    # 回退：使用模板
    from paper_writing_agent import MethodsGenerator
    gen = MethodsGenerator()
    ctx.sections['methods'] = gen.generate(language=ctx.language)
    return ctx.sections['methods']


def _run_writer_abstract(ctx: PaperContext):
    """写 Abstract（优先 Claude 基于实际章节生成，回退模板）"""
    writer = _get_claude_writer()
    if writer and ctx.sections:
        result = writer.write_abstract(
            sections=ctx.sections,
            language=ctx.language,
        )
        if result:
            ctx.sections['abstract'] = result
            return result

    # 回退：使用模板
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
    """写 Conclusion（优先 Claude 生成，回退模板）"""
    writer = _get_claude_writer()
    if writer and ctx.has('findings'):
        result = writer.write_conclusion(
            findings=ctx.findings,
            language=ctx.language,
        )
        if result:
            ctx.sections['conclusion'] = result
            return result

    # 回退：使用模板
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


def _run_polish(ctx: PaperContext):
    """用文献学到的模式润色各章节文本"""
    if not ctx.has('sections') or not ctx.learned_patterns:
        return None

    writer = _get_claude_writer()
    if not writer:
        return None

    polished_count = 0
    for section_name in ['results', 'discussion', 'introduction']:
        text = ctx.sections.get(section_name, '')
        if not text or len(text) < 200:
            continue
        try:
            polished = writer.polish_text(
                text[:3000],  # 限制长度避免超时
                learned_patterns=ctx.learned_patterns,
            )
            if polished and len(polished) > len(text) * 0.5:  # 防止返回垃圾
                ctx.sections[section_name] = polished
                polished_count += 1
                logger.info(f"润色 {section_name}: {len(text)} -> {len(polished)} 字")
        except Exception as e:
            logger.debug(f"润色 {section_name} 跳过: {e}")

    if polished_count:
        logger.info(f"润色完成: {polished_count} 个章节")
    return polished_count


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

    # 中文核心期刊投稿检查
    if ctx.language == 'zh':
        try:
            from cn_core_rules import SubmissionChecklist
            checklist = SubmissionChecklist()
            checklist_result = checklist.run_check(full_paper)
            report_text = checklist.generate_report(checklist_result)
            extra_issues.append(f'[投稿检查] {report_text[:500]}')
        except Exception as e:
            logger.debug(f"cn_core_rules check skipped: {e}")

    # 引用安全检查（防幻觉）
    try:
        from citation_guard import CitationGuard
        guard = CitationGuard()
        # 检查文中引用是否有幻觉风险
        import re
        citation_patterns = re.findall(r'\[(\d+(?:[-,]\d+)*)\]', full_paper)
        if citation_patterns:
            extra_issues.append(f'[引用安全] 检测到 {len(citation_patterns)} 处引用，建议核实DOI')
    except Exception as e:
        logger.debug(f"citation_guard check skipped: {e}")

    # 文本质量检查（使用 text_utils）
    try:
        from text_utils import split_sentences
        all_sentences = split_sentences(full_paper)
        long_sentences = [s for s in all_sentences if len(s) > 100]
        if long_sentences:
            extra_issues.append(f'[文本质量] 发现 {len(long_sentences)} 个超长句子(>100字)，建议拆分')
    except Exception as e:
        logger.debug(f"text_utils check skipped: {e}")

    # 文献质量验证（使用 literature_memory 的引用验证功能）
    if ctx.has('memory'):
        try:
            from literature_memory import LiteratureMemory
            lit_mem = LiteratureMemory()
            # 从 recalled_references 中验证引用质量
            if ctx.has('recalled_references'):
                verified = 0
                questionable = 0
                for ref in ctx.recalled_references[:10]:
                    title = ref.get('title', '')
                    if title:
                        assessment = lit_mem.assess_paper(title)
                        if assessment and assessment.get('credibility', 0) < 0.5:
                            questionable += 1
                        else:
                            verified += 1
                if questionable:
                    extra_issues.append(f'[文献质量] {questionable}/{verified+questionable} 篇引用可信度较低，建议核实')
        except Exception as e:
            logger.debug(f"literature_memory check skipped: {e}")

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


def _run_final_check(ctx: PaperContext):
    """修订后二次审稿：检查修订是否引入新问题"""
    if not ctx.has('sections'):
        return None

    from academic_review_agent import AcademicReviewAgent
    full_paper = '\n\n---\n\n'.join(
        ctx.sections.get(k, '') for k in
        ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        if ctx.has_section(k)
    )
    if not full_paper:
        return None

    reviewer = AcademicReviewAgent(paper_type='chinese_journal', language=ctx.language)
    final_report = reviewer.review(full_paper)
    final_summary = final_report.summary()

    # 对比修订前后
    prev_count = ctx.review_summary.get('total', 0)
    new_count = final_summary.get('total', 0)
    improvement = prev_count - new_count

    ctx.review_summary['final_total'] = new_count
    ctx.review_summary['improvement'] = improvement

    if improvement > 0:
        logger.info(f"二次审稿: {prev_count} -> {new_count} 个问题 (减少 {improvement} 个)")
    elif improvement < 0:
        logger.warning(f"二次审稿: 问题增加 {abs(improvement)} 个，建议人工检查")
    else:
        logger.info(f"二次审稿: 问题数不变 ({new_count} 个)")

    return final_report


def _run_latex_export(ctx: PaperContext):
    """导出 LaTeX 格式论文"""
    if not ctx.has('sections'):
        return None
    try:
        from latex_exporter import LatexExporter
        exporter = LatexExporter()
        # 构造 sections dict
        sections = {}
        for key in ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']:
            if ctx.has_section(key):
                sections[key] = ctx.sections[key]
        result = exporter.export(
            sections=sections,
            output_dir=ctx.output_dir,
            title=ctx.title or '',
            abstract_text=ctx.sections.get('abstract', ''),
        )
        logger.info(f"LaTeX: {ctx.output_dir}")
        return result
    except Exception as e:
        logger.warning(f"LaTeX export failed: {e}")
        return None


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
# 5. 文献深度学习模块
# ============================================================

def _run_paper_reading(ctx: PaperContext):
    """读论文：优先本地目录，无文献时自动在线搜索"""
    from paper_reader import PaperReader
    reader = PaperReader()

    papers_found = []

    # 1. 尝试从本地目录读取
    if ctx.papers_dir and os.path.isdir(ctx.papers_dir):
        import glob
        for ext in ['*.pdf', '*.txt', '*.md']:
            papers_found.extend(glob.glob(os.path.join(ctx.papers_dir, ext)))

    # 2. 本地无文献时，自动在线搜索
    if not papers_found:
        logger.info("本地无文献，尝试自动在线搜索...")
        try:
            from auto_paper_finder import AutoPaperFinder
            finder = AutoPaperFinder()
            # 从 findings 中提取关键词搜索
            keywords = []
            for f in ctx.findings[:5]:
                vars_ = f.get('variables', ('', ''))
                if isinstance(vars_, (list, tuple)):
                    keywords.extend([v for v in vars_ if v])
            if not keywords:
                keywords = ['sewage', 'greenhouse gas', 'methane', 'carbon']
            search_query = ' '.join(keywords[:5])
            found_papers = finder.find_papers(search_query)
            if found_papers:
                logger.info(f"在线搜索到 {len(found_papers)} 篇论文")
                for p in found_papers[:10]:
                    ctx.papers_read.append({
                        'title': p.get('title', ''),
                        'authors': p.get('authors', []),
                        'abstract': p.get('abstract', ''),
                        'source': 'online_search',
                    })
                return ctx.papers_read
        except Exception as e:
            logger.warning(f"在线搜索失败: {e}")
        logger.info("未找到任何文献")
        return None

    logger.info(f"发现 {len(papers_found)} 篇文献，开始阅读...")
    for paper_path in papers_found[:20]:  # 最多读20篇
        try:
            content = reader.read(paper_path, fetch_metadata=False)
            if content and content.metadata:
                ctx.papers_read.append({
                    'path': paper_path,
                    'title': content.metadata.title,
                    'authors': content.metadata.authors,
                    'abstract': content.metadata.abstract,
                    'sections': len(content.sections),
                    'references': len(content.references),
                })
        except Exception as e:
            logger.warning(f"读取失败 {paper_path}: {e}")

    logger.info(f"成功读取 {len(ctx.papers_read)} 篇文献")
    return ctx.papers_read


def _run_pattern_learning(ctx: PaperContext):
    """从已读论文中学习写作模式，持久化到知识库"""
    if not ctx.papers_read:
        logger.info("无已读论文，跳过模式学习")
        return None

    from pattern_learner import SentencePatternLearner, DiscussionLearner, MechanismLearner
    from paper_reader import PaperReader

    reader = PaperReader()
    sentence_learner = SentencePatternLearner()
    discussion_learner = DiscussionLearner()
    mechanism_learner = MechanismLearner()

    all_patterns = []
    all_structures = []

    for paper_info in ctx.papers_read[:10]:
        path = paper_info.get('path', '')
        if not path or not os.path.exists(path):
            continue
        try:
            content = reader.read(path, fetch_metadata=False)
            if not content:
                continue

            for sec in content.sections:
                if not sec.text:
                    continue
                # 学习句式模式
                patterns = sentence_learner.learn_from_text(sec.text, sec.section_type or 'unknown')
                all_patterns.extend(patterns)

                # 学习讨论结构
                if sec.section_type == 'discussion':
                    structure = discussion_learner.learn_structure(sec.text)
                    all_structures.append(structure)

            # 学习机制知识
            full_text = '\n\n'.join(sec.text for sec in content.sections if sec.text)
            mechanisms = mechanism_learner.learn_from_text(full_text, source=paper_info.get('title', ''))

        except Exception as e:
            logger.warning(f"学习失败 {path}: {e}")

    # 持久化：将学到的机制存入 KnowledgeStore
    if ctx.has('memory') and mechanism_learner.mechanisms:
        ks_format = mechanism_learner.to_knowledge_store_format()
        for key, entry in ks_format.items():
            ctx.memory.remember(key, entry, category='mechanisms')
        logger.info(f"已将 {len(ks_format)} 个学到的机制存入知识库")

    # 存储到 ctx（完整数据，不只是计数）
    ctx.learned_patterns = {
        'sentence_patterns': sentence_learner.get_patterns() if hasattr(sentence_learner, 'get_patterns') else {},
        'discussion_structures': all_structures,
        'mechanisms': mechanism_learner.get_mechanisms() if hasattr(mechanism_learner, 'get_mechanisms') else [],
        'patterns_count': len(all_patterns),
        'mechanisms_count': len(mechanism_learner.mechanisms) if hasattr(mechanism_learner, 'mechanisms') else 0,
        'papers_learned': len(ctx.papers_read),
    }

    # 同时存储到 learned_mechanisms 供写作模块使用
    ctx.learned_mechanisms = mechanism_learner.get_mechanisms() if hasattr(mechanism_learner, 'get_mechanisms') else []

    # 触发 auto_learn：用学到的变量对自动搜索更多文献和机制
    try:
        from self_evolving_engine import EvolutionEngine
        engine = EvolutionEngine(base_dir=ctx.output_dir)
        engine.initialize()
        # 从 findings 中提取变量对，自动学习
        var_pairs = []
        for f in ctx.findings:
            if f.get('type') == 'correlation' and f.get('importance') in ['critical', 'high']:
                v1, v2 = f.get('variables', ('', ''))
                if v1 and v2:
                    var_pairs.append((v1, v2))
        if var_pairs:
            learn_report = engine.auto_learn(var_pairs[:5], ctx.findings)
            logger.info(f"自动学习: {learn_report.get('total_learned', 0)} 条新知识")
    except Exception as e:
        logger.debug(f"auto_learn skipped: {e}")

    logger.info(f"模式学习: {ctx.learned_patterns['patterns_count']} 个句式, "
               f"{ctx.learned_patterns['mechanisms_count']} 个机制")
    return ctx.learned_patterns


# ============================================================
# 6. 新增模块函数 — 接入原孤立模块
# ============================================================

def _run_advanced_analysis(ctx: PaperContext):
    """高级多维分析（交叉分析、异常深挖、数据故事线、阈值检测）"""
    if not ctx.has('df'):
        return None
    try:
        from advanced_analysis import CrossAnalyzer, AnomalyDeepDiver, DataStoryExtractor, ThresholdDetector
        all_results = {}

        # 交叉分析
        cross = CrossAnalyzer(ctx.df)
        cross_results = cross.analyze_all()
        all_results['cross_analyses'] = cross_results if isinstance(cross_results, list) else []

        # 异常深挖
        try:
            diver = AnomalyDeepDiver(ctx.df)
            anomaly_results = diver.analyze_all() if hasattr(diver, 'analyze_all') else []
            all_results['anomaly_insights'] = anomaly_results if isinstance(anomaly_results, list) else []
        except Exception:
            all_results['anomaly_insights'] = []

        # 数据故事线
        try:
            extractor = DataStoryExtractor(ctx.df)
            story_results = extractor.extract_all() if hasattr(extractor, 'extract_all') else []
            all_results['data_stories'] = story_results if isinstance(story_results, list) else []
        except Exception:
            all_results['data_stories'] = []

        # 阈值检测
        try:
            detector = ThresholdDetector(ctx.df)
            threshold_results = detector.detect_all() if hasattr(detector, 'detect_all') else []
            all_results['threshold_effects'] = threshold_results if isinstance(threshold_results, list) else []
        except Exception:
            all_results['threshold_effects'] = []

        ctx.advanced_findings = all_results.get('cross_analyses', [])
        ctx.cross_analyses = all_results.get('cross_analyses', [])
        ctx.anomaly_insights = all_results.get('anomaly_insights', [])
        ctx.data_stories = all_results.get('data_stories', [])
        ctx.threshold_effects = all_results.get('threshold_effects', [])
        total = sum(len(v) for v in all_results.values() if isinstance(v, list))
        logger.info(f"高级分析: {total}项发现")
        return all_results
    except Exception as e:
        logger.warning(f"高级分析失败: {e}")
        return None


def _run_deep_imitation(ctx: PaperContext):
    """深度模仿分析（3表法：范例动作/草稿动作/目标蓝图）"""
    if not ctx.has('sections'):
        return None
    from deep_imitation import DeepImitationManager
    manager = DeepImitationManager(output_dir=ctx.output_dir)
    # 用已有章节作为草稿
    draft_text = '\n\n'.join(ctx.sections.values())
    if not draft_text.strip():
        return None
    manager.analyze_draft(draft_text)
    manager.generate_blueprint()
    report = manager.generate_report()
    ctx.imitation_report = report if isinstance(report, str) else str(report)
    logger.info("深度模仿分析完成")
    return report


def _run_integrity_audit(ctx: PaperContext):
    """完整性审计（4维度：制品链、推理深度、证据链、模式扫描）"""
    from integrity_audit import IntegrityAuditManager
    auditor = IntegrityAuditManager(output_dir=ctx.output_dir)
    report = auditor.run_audit()
    ctx.integrity_report = auditor.format_report(report)
    issue_count = len(report.findings) if hasattr(report, 'findings') else 0
    logger.info(f"完整性审计: {issue_count}项发现")
    return report


def _run_artifact_check(ctx: PaperContext):
    """制品完整性检查（文件存在性、内容质量、交叉引用）"""
    from artifact_check import ArtifactChecker
    checker = ArtifactChecker(output_dir=ctx.output_dir)
    report = checker.check_all()
    ctx.artifact_report = checker.format_report(report)
    issue_count = len(report.findings) if hasattr(report, 'findings') else 0
    logger.info(f"制品检查: {issue_count}个问题")
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
        bank.bind_citations()
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
    'paper_reading': {
        'needs': [],
        'provides': ['papers_read'],
        'run': _run_paper_reading,
        'description': '文献深度阅读（读论文→存入知识库）',
    },
    'pattern_learning': {
        'needs': ['papers_read'],
        'provides': ['learned_patterns', 'learned_mechanisms'],
        'run': _run_pattern_learning,
        'description': '写作模式学习（从论文中提取句式/讨论结构/机制）',
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
    'polish': {
        'needs': ['sections', 'learned_patterns'],
        'provides': ['sections(polished)'],
        'run': _run_polish,
        'description': '用文献学到的模式润色各章节',
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
    'final_check': {
        'needs': ['sections(revised)'],
        'provides': ['review_summary'],
        'run': _run_final_check,
        'description': '修订后二次审稿（检查修订是否引入新问题）',
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
    'latex_export': {
        'needs': ['sections'],
        'provides': ['latex_path'],
        'run': _run_latex_export,
        'description': '导出 LaTeX 格式论文',
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

        # 检测可并行的写作步骤
        parallel_groups = self._find_parallel_groups(steps)

        step_idx = 0
        for group in parallel_groups:
            if len(group) == 1:
                # 单步执行
                step_name = group[0]
                step_idx += 1
                self._execute_step(ctx, step_name, step_idx, len(steps))
            else:
                # 并行执行
                self._execute_parallel(ctx, group, step_idx + 1, len(steps))
                step_idx += len(group)

        # 保存全文 MD
        self._save_paper_md(ctx)

        print(f"\n{'=' * 60}")
        print(f"  编排完成!")
        print(f"{'=' * 60}")

    def _execute_step(self, ctx, step_name, idx, total):
        """执行单个步骤"""
        if step_name not in MODULE_REGISTRY:
            logger.warning(f"未知模块: {step_name}")
            return

        module = MODULE_REGISTRY[step_name]
        missing = self._check_needs(ctx, module['needs'])
        if missing:
            print(f"\n[{idx}/{total}] {module['description']} — 跳过 (缺少: {missing})")
            self.execution_log.append({'step': step_name, 'status': 'skipped', 'missing': missing})
            return

        print(f"\n[{idx}/{total}] {module['description']}...")
        try:
            result = module['run'](ctx)
            ctx.mark_done(step_name)
            self.execution_log.append({'step': step_name, 'status': 'done'})
            if result is not None:
                if isinstance(result, str) and len(result) > 50:
                    print(f"  完成 ({len(result)} 字)")
                elif isinstance(result, list):
                    print(f"  完成 ({len(result)} 项)")
                elif isinstance(result, dict):
                    print(f"  完成 ({len(result)} 个条目)")
                else:
                    print(f"  完成")
            self._save_checkpoint(ctx, step_name)
        except Exception as e:
            logger.error(f"模块 {step_name} 失败: {e}")
            self.execution_log.append({'step': step_name, 'status': 'failed', 'error': str(e)})

    def _execute_parallel(self, ctx, steps, idx_start, total):
        """并行执行多个步骤（使用线程池）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"\n[{idx_start}/{total}] 并行执行 {len(steps)} 个步骤: {steps}")
        with ThreadPoolExecutor(max_workers=len(steps)) as executor:
            futures = {}
            for step_name in steps:
                if step_name in MODULE_REGISTRY:
                    module = MODULE_REGISTRY[step_name]
                    missing = self._check_needs(ctx, module['needs'])
                    if not missing:
                        futures[executor.submit(module['run'], ctx)] = step_name
                    else:
                        print(f"  {step_name} — 跳过 (缺少: {missing})")

            for future in as_completed(futures):
                step_name = futures[future]
                try:
                    result = future.result()
                    ctx.mark_done(step_name)
                    self.execution_log.append({'step': step_name, 'status': 'done'})
                    if isinstance(result, str) and result:
                        print(f"  {step_name} 完成 ({len(result)} 字)")
                    else:
                        print(f"  {step_name} 完成")
                except Exception as e:
                    logger.error(f"模块 {step_name} 失败: {e}")
                    self.execution_log.append({'step': step_name, 'status': 'failed', 'error': str(e)})

    def _find_parallel_groups(self, steps):
        """
        将步骤分组，同组内可并行执行。
        规则：
        - Introduction + Methods 可并行（互不依赖，且不依赖数据）
        - Results + Discussion 可并行（共享 findings）
        - 其他步骤串行
        """
        # 只有 writer_intro 和 writer_methods 可以并行（都不依赖 df/findings）
        # writer_results 和 writer_discussion 都依赖 df/findings，需要串行保证
        parallel_sets = [
            {'writer_intro', 'writer_methods'},           # 批次1: 互不依赖
        ]

        groups = []
        remaining = list(steps)

        for pset in parallel_sets:
            batch = [s for s in remaining if s in pset]
            if len(batch) > 1:
                groups.append(batch)
                for s in batch:
                    remaining.remove(s)

        # 剩余步骤全部串行
        for s in remaining:
            groups.append([s])

        return groups

    def _auto_plan(self, ctx: PaperContext) -> list:
        """根据上下文状态自动推断执行步骤"""
        steps = []

        # 第1阶段：知识初始化 + 文献学习
        steps.append('memory_init')
        steps.append('paper_reading')
        steps.append('pattern_learning')

        # 第2阶段：数据处理
        if ctx.has('data_path'):
            steps.append('load_data')
        steps.append('explorer')
        steps.append('advanced_analysis')

        # 第3阶段：知识支撑
        steps.append('literature_recall')
        steps.append('motivation')

        # 第4阶段：AI写作
        steps.append('writer_results')
        steps.append('writer_discussion')
        steps.append('writer_intro')
        steps.append('writer_methods')
        steps.append('writer_conclusion')
        steps.append('writer_abstract')

        # 第5阶段：润色 + 迭代审改
        steps.append('polish')
        # 迭代审改循环（写→审→改→审，最多2轮）
        for _iteration in range(2):
            steps.append('review')
            steps.append('auto_revision')
        steps.append('final_check')

        # 第6阶段：补充检查
        steps.append('deep_imitation')
        steps.append('integrity_audit')
        steps.append('artifact_check')
        steps.append('citation_bank')

        # 第7阶段：排版 + LaTeX
        steps.append('assemble')
        steps.append('latex_export')

        return steps

    def _save_checkpoint(self, ctx: PaperContext, step_name: str):
        """保存中间结果检查点"""
        import json
        checkpoint_dir = os.path.join(ctx.output_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_file = os.path.join(checkpoint_dir, f'{step_name}.json')
        try:
            data = {
                'step': step_name,
                'sections': {k: v[:200] + '...' if isinstance(v, str) and len(v) > 200 else v
                            for k, v in ctx.sections.items()},
                'findings_count': len(ctx.findings),
                'papers_read_count': len(ctx.papers_read),
            }
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Checkpoint save failed: {e}")

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
