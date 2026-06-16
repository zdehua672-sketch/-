# -*- coding: utf-8 -*-
"""
MCP 学术写作服务器 — 将系统功能暴露为 AI Agent 可调用的工具

启动:
    python mcp_academic_writer.py

对外暴露的工具:
    - explore_data          — 数据探索，发现模式
    - analyze_all           — 全部分析（基础+科学+高级）
    - generate_figures      — 生成论文图表
    - write_section         — 写特定论文章节
    - review_paper          — 审稿检查
    - pipeline_full         — 全流程管线
    - pipeline_quick        — 快速离线流程
    - check_status          — 系统状态检查
"""

import os
import sys
import json
import logging

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('mcp_server')

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool, TextContent, Prompt, PromptMessage, PromptArgument,
        GetPromptResult,
    )
    from pydantic import BaseModel, Field
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.error("mcp 包未安装。运行: pip install mcp")


# ============================================================
# 工具函数（与 cli.py 共享）
# ============================================================

def _find_data_file():
    """查找数据文件"""
    DATA_FILE = os.environ.get('PAPER_DATA_FILE', '')
    if DATA_FILE and os.path.exists(DATA_FILE):
        return DATA_FILE
    candidates = [
        os.path.join(_HERE, 'data', 'sample_data.xlsx'),
        os.path.join(os.path.expanduser('~'), 'Desktop', '冬春数据.xlsx'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _ensure_data(data_path=None):
    """确保数据可用，返回 (df, data_path)"""
    from data_loader import DataLoader
    path = data_path or _find_data_file()
    if not path:
        raise FileNotFoundError("未找到数据文件。运行 python scripts/generate_sample_data.py 生成示例数据")
    loader = DataLoader(path)
    df = loader.load_data()
    return df, path


# ============================================================
# 工具实现函数
# ============================================================

async def tool_explore_data(data_path: str = None) -> str:
    """数据探索 — 发现数据中的模式"""
    df, path = _ensure_data(data_path)
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    findings = explorer.explore()
    
    # 按重要性分组
    critical = [f for f in findings if f.get('importance') == 'critical']
    high = [f for f in findings if f.get('importance') == 'high']
    medium = [f for f in findings if f.get('importance') == 'medium']
    
    summary = [
        f"数据文件: {path}",
        f"样本数: {len(df)}行 x {len(df.columns)}列",
        f"共发现 {len(findings)} 个模式",
        f"  CRITICAL: {len(critical)} 个",
        f"  HIGH: {len(high)} 个",
        f"  MEDIUM: {len(medium)} 个",
    ]
    
    # 列出关键发现
    for f in (critical + high)[:10]:
        ftype = f.get('type', '')
        var = f.get('variable', '') or str(f.get('variables', ''))
        data = f.get('data', {})
        if ftype == 'correlation':
            v1, v2 = f.get('variables', ('', ''))
            r, p = data.get('r', 0), data.get('p', 1)
            summary.append(f"  [相关] {v1} vs {v2}: r={r:.3f}, p={p:.4f}")
        elif ftype == 'group_difference':
            pv = data.get('p_value', 1)
            summary.append(f"  [差异] {var}: p={pv:.4f}")
        elif ftype == 'distribution':
            skew = data.get('skew', 0)
            summary.append(f"  [分布] {var}: skew={skew:.2f}")
        else:
            summary.append(f"  [{ftype}] {var}")
    
    # 返回 JSON + 可读文本
    result = {
        'summary': '\n'.join(summary),
        'findings_count': len(findings),
        'findings': findings[:20],
        'data_shape': list(df.shape),
        'columns': list(df.columns),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


async def tool_analyze_all(data_path: str = None) -> str:
    """全部分析：基础探索 + 科学分析 + 高级分析"""
    df, path = _ensure_data(data_path)
    results = {}
    
    # 1. 基础探索
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    findings = explorer.explore()
    results['基础探索'] = f"{len(findings)} 个发现"
    
    # 2. 科学分析
    try:
        from scientific_analysis_agent import ScientificAnalysisAgent
        output_dir = os.path.join(_HERE, 'paper_output')
        agent = ScientificAnalysisAgent(data_path=path, output_dir=output_dir)
        agent.load_data()
        sci_results = agent.run()
        results['科学分析'] = '完成' if sci_results else '跳过'
    except Exception as e:
        results['科学分析'] = f'跳过 ({str(e)[:50]})'
    
    # 3. 高级分析
    try:
        from advanced_analysis import CrossAnalyzer
        cross = CrossAnalyzer(df)
        cross_results = cross.analyze_all()
        count = len(cross_results) if isinstance(cross_results, list) else 0
        results['交叉分析'] = f'{count} 项'
    except Exception as e:
        results['交叉分析'] = f'跳过 ({str(e)[:50]})'
    
    # 4. 关键发现摘要
    critical = [f for f in findings if f.get('importance') == 'critical']
    high = [f for f in findings if f.get('importance') == 'high']
    
    return json.dumps({
        'summary': results,
        'total_findings': len(findings),
        'critical_findings': len(critical),
        'high_findings': len(high),
        'top_findings': (critical + high)[:5],
    }, ensure_ascii=False, indent=2)


async def tool_generate_figures(data_path: str = None, output_dir: str = None) -> str:
    """生成论文图表"""
    df, path = _ensure_data(data_path)
    output_dir = output_dir or os.path.join(_HERE, 'paper_output')
    analysis_dir = os.path.join(output_dir, 'figures')
    os.makedirs(analysis_dir, exist_ok=True)
    
    # 使用 PaperContext 的图表生成逻辑
    from paper_context import PaperContext, _run_generate_figures, _run_memory_init
    ctx = PaperContext(data_path=path, output_dir=output_dir)
    ctx.df = df
    _run_memory_init(ctx)
    
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    ctx.findings = explorer.explore()
    
    fig_keys = _run_generate_figures(ctx)
    
    result = {
        'figure_count': len(fig_keys) if fig_keys else 0,
        'figures': {},
        'output_dir': analysis_dir,
    }
    
    if ctx.figures:
        for key, info in ctx.figures.items():
            result['figures'][key] = {
                'path': info.get('path', ''),
                'caption': info.get('caption', ''),
                'section': info.get('section', ''),
            }
        # 保存索引
        idx_path = os.path.join(analysis_dir, 'figure_index.json')
        with open(idx_path, 'w', encoding='utf-8') as f:
            json.dump(ctx.figures, f, ensure_ascii=False, indent=2)
        result['index_path'] = idx_path
    
    return json.dumps(result, ensure_ascii=False, indent=2)


async def tool_write_section(section: str, data_path: str = None, output_dir: str = None) -> str:
    """写作论文章节
    
    Parameters
    ----------
    section : str, 章节名: results/discussion/introduction/methods/conclusion/abstract/all
    """
    df, path = _ensure_data(data_path)
    output_dir = output_dir or os.path.join(_HERE, 'paper_output')
    os.makedirs(output_dir, exist_ok=True)
    
    from paper_context import PaperContext, _run_memory_init
    ctx = PaperContext(data_path=path, output_dir=output_dir, language='zh')
    ctx.df = df
    _run_memory_init(ctx)
    
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    ctx.findings = explorer.explore()
    
    from claude_writer import ClaudeWriter
    writer = ClaudeWriter(timeout=180)
    
    writers = {
        'results': lambda: _write_results_mcp(ctx, writer),
        'discussion': lambda: _write_discussion_mcp(ctx, writer),
        'introduction': lambda: _write_intro_mcp(ctx, writer),
        'methods': lambda: _write_methods_mcp(ctx, writer),
        'conclusion': lambda: _write_conclusion_mcp(ctx, writer),
        'abstract': lambda: _write_abstract_mcp(ctx, writer),
    }
    
    sections_map = {
        'abstract': 'abstract', 'introduction': 'introduction', 'methods': 'methods',
        'results': 'results', 'discussion': 'discussion', 'conclusion': 'conclusion',
    }
    
    if section == 'all':
        results = {}
        for name, fn in writers.items():
            try:
                text = fn()
                results[name] = {'status': 'ok', 'length': len(text), 'preview': text[:200]}
            except Exception as e:
                results[name] = {'status': 'error', 'error': str(e)[:100]}
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif section in writers:
        text = writers[section]()
        result = {
            'section': section,
            'status': 'ok',
            'length': len(text),
            'content': text,
            'saved_to': os.path.join(output_dir, f'section_{section}.md'),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"未知章节: {section}")


def _write_results_mcp(ctx, writer):
    text = writer.write_results(ctx.findings, ctx.figures, learned_patterns=ctx.learned_patterns)
    if not text:
        from data_driven_pipeline import DataDrivenWriter
        tpl = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
        text = tpl.write_results()
    ctx.sections['results'] = text
    path = os.path.join(ctx.output_dir, 'section_results.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def _write_discussion_mcp(ctx, writer):
    mechanisms = {}
    if ctx.has('memory'):
        for f in ctx.findings:
            if f.get('type') == 'correlation':
                v1, v2 = f.get('variables', ('', ''))
                mechs = ctx.memory.recall(f'{v1} {v2}', category='mechanisms', top_k=1)
                if mechs:
                    mechanisms[f'{v1}_vs_{v2}'] = mechs[0].get('value', {}).get('mechanism', '')
    text = writer.write_discussion(ctx.findings, mechanisms, language='zh')
    if not text:
        from data_driven_pipeline import DataDrivenWriter
        tpl = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
        text = tpl.write_discussion()
    ctx.sections['discussion'] = text
    path = os.path.join(ctx.output_dir, 'section_discussion.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def _write_intro_mcp(ctx, writer):
    text = writer.write_introduction(ctx.findings, language='zh')
    if not text:
        from paper_writing_agent import IntroductionGenerator
        gen = IntroductionGenerator()
        text = gen.generate(language='zh')
    ctx.sections['introduction'] = text
    path = os.path.join(ctx.output_dir, 'section_introduction.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def _write_methods_mcp(ctx, writer):
    data_info = {
        'n_samples': len(ctx.df),
        'n_variables': len(ctx.df.columns),
        'variables': list(ctx.df.columns),
        'groups': list(ctx.df.select_dtypes(include=['object', 'category']).columns),
    }
    text = writer.write_methods(data_info=data_info, language='zh')
    if not text:
        from paper_writing_agent import MethodsGenerator
        gen = MethodsGenerator()
        text = gen.generate(language='zh')
    ctx.sections['methods'] = text
    path = os.path.join(ctx.output_dir, 'section_methods.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def _write_conclusion_mcp(ctx, writer):
    import numpy as np
    text = writer.write_conclusion(ctx.findings, language='zh')
    if not text:
        critical = [f for f in ctx.findings if f['importance'] in ['critical', 'high']]
        group_f = [f for f in critical if f['type'] == 'group_difference']
        corr_f = [f for f in critical if f['type'] == 'correlation']
        lines = ['# 5 结论\n', '本研究以校园污水管网为对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。主要结论如下：\n']
        i = 1
        if group_f:
            lines.append(f'({i}) 碳污染物呈现显著的季节分异。')
            top = group_f[0]
            d = top['data']
            higher = d['groups'][np.argmax(d['means'])]
            lines.append(f'{top["variable"]}等指标在{higher}显著偏高。\n')
            i += 1
        if corr_f:
            lines.append(f'({i}) 变量间存在多组显著关联。')
            top = corr_f[0]
            v1, v2 = top['variables']
            lines.append(f'{v1}与{v2}的相关性最强(r={top["data"]["r"]:.3f})。\n')
            i += 1
        lines.append(f'({i}) 上述发现为碳排放核算和碳管理策略制定提供了数据支撑。')
        text = '\n'.join(lines)
    ctx.sections['conclusion'] = text
    path = os.path.join(ctx.output_dir, 'section_conclusion.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


def _write_abstract_mcp(ctx, writer):
    text = writer.write_abstract(sections=ctx.sections, language='zh') if ctx.sections else None
    if not text:
        from paper_writing_agent import AbstractGenerator
        gen = AbstractGenerator(
            ctx.sections.get('introduction', ''),
            ctx.sections.get('methods', ''),
            ctx.sections.get('results', ''),
            ctx.sections.get('discussion', ''),
        )
        text = gen.generate(language='zh')
    ctx.sections['abstract'] = text
    path = os.path.join(ctx.output_dir, 'section_abstract.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return text


async def tool_review_paper(paper_path: str = None, output_dir: str = None) -> str:
    """审稿检查"""
    if not paper_path or not os.path.exists(paper_path):
        # 默认路径
        default_path = os.path.join(output_dir or _HERE, 'paper_output', 'paper.md')
        if not os.path.exists(default_path):
            raise FileNotFoundError(f"论文文件不存在: {default_path}")
        paper_path = default_path
    
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_text = f.read()
    
    from academic_review_agent import AcademicReviewAgent
    reviewer = AcademicReviewAgent(paper_type='chinese_journal', language='zh')
    report = reviewer.review(paper_text)
    summary = report.summary()
    
    issues_list = []
    if hasattr(report, 'issues'):
        for issue in report.issues:
            issues_list.append({
                'severity': str(getattr(issue, 'severity', '')),
                'category': getattr(issue, 'category', ''),
                'section': getattr(issue, 'section', ''),
                'problem': getattr(issue, 'problem', ''),
                'suggestion': getattr(issue, 'suggestion', ''),
            })
    
    result = {
        'total_issues': summary.get('total', 0),
        'by_severity': {
            'CRITICAL': summary.get('by_severity', {}).get('CRITICAL', 0),
            'MAJOR': summary.get('by_severity', {}).get('MAJOR', 0),
            'MINOR': summary.get('by_severity', {}).get('MINOR', 0),
        },
        'issues': issues_list,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


async def tool_pipeline_full(data_path: str = None, output_dir: str = None) -> str:
    """全流程管线"""
    from paper_context import PaperContext, PaperOrchestrator
    path = data_path or _find_data_file()
    if not path:
        raise FileNotFoundError("未找到数据文件")
    output_dir = output_dir or os.path.join(_HERE, 'paper_output')
    
    ctx = PaperContext(
        data_path=path, output_dir=output_dir, language='zh',
        paper_type='chinese', title='污水管网中碳污染物的冬春季节变化特征',
    )
    orch = PaperOrchestrator()
    orch.run(ctx)
    
    sections_info = {}
    for name in ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']:
        if ctx.has_section(name):
            sections_info[name] = len(ctx.sections[name])
    
    return json.dumps({
        'status': 'completed',
        'output_dir': output_dir,
        'sections': sections_info,
        'docx_path': ctx.docx_path,
        'paper_md_path': ctx.paper_md_path,
        'execution_log': orch.get_log(),
    }, ensure_ascii=False, indent=2)


async def tool_pipeline_quick(data_path: str = None) -> str:
    """快速离线流程（无需Claude）"""
    path = data_path or _find_data_file()
    if not path:
        raise FileNotFoundError("未找到数据文件")
    
    # 执行 run_local_pipeline.py
    output_dir = os.path.join(_HERE, 'paper_output')
    exec_globals = {'__file__': os.path.join(_HERE, 'run_local_pipeline.py')}
    exec(open(os.path.join(_HERE, 'run_local_pipeline.py')).read(), exec_globals)
    
    return json.dumps({
        'status': 'completed',
        'output_dir': output_dir,
        'files': ['paper.md', 'paper.docx', 'review_report.md', 'rationale_report.md'],
    }, ensure_ascii=False, indent=2)


async def tool_check_status() -> str:
    """系统状态检查"""
    import shutil
    import pkg_resources
    
    info = {}
    
    # 数据文件
    data_file = _find_data_file()
    info['data_file'] = {'found': data_file is not None, 'path': data_file}
    
    # Claude CLI
    claude_npm = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm', 'claude.cmd')
    has_claude = shutil.which('claude') is not None or os.path.exists(claude_npm)
    info['claude_cli'] = {'available': has_claude}
    
    # 模块
    try:
        from paper_context import MODULE_REGISTRY
        info['modules'] = {
            'total': len(MODULE_REGISTRY),
            'names': list(MODULE_REGISTRY.keys()),
        }
    except Exception as e:
        info['modules'] = {'error': str(e)}
    
    # 知识库
    kb_dir = os.path.join(_HERE, 'knowledge_store')
    if os.path.exists(kb_dir):
        json_files = [f for f in os.listdir(kb_dir) if f.endswith('.json')]
        info['knowledge_base'] = {
            'json_files': len(json_files),
            'files': sorted(json_files),
        }
    
    # 输出目录
    out_dir = os.path.join(_HERE, 'paper_output')
    if os.path.exists(out_dir):
        files = os.listdir(out_dir)
        info['output'] = {
            'total_files': len(files),
            'files': sorted(files)[:20],
        }
    
    # 依赖
    required = ['pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'python-docx', 'openpyxl']
    deps = {}
    for pkg in required:
        try:
            pkg_resources.get_distribution(pkg)
            deps[pkg] = 'installed'
        except pkg_resources.DistributionNotFound:
            deps[pkg] = 'missing'
    info['dependencies'] = deps
    
    return json.dumps(info, ensure_ascii=False, indent=2)


# ============================================================
# MCP Server 主程序
# ============================================================

if MCP_AVAILABLE:
    
    app = Server('academic-writer')
    
    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name='explore_data',
                description='数据探索 — 自动发现数据中的统计模式（分布/相关性/差异/异常值等）',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'data_path': {'type': 'string', 'description': '数据文件路径（可选，自动查找）'},
                    },
                },
            ),
            Tool(
                name='analyze_all',
                description='全部分析 — 基础探索 + 科学分析 + 高级分析（交叉/异常/阈值）',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'data_path': {'type': 'string', 'description': '数据文件路径'},
                    },
                },
            ),
            Tool(
                name='generate_figures',
                description='生成论文图表 — 季节对比箱线图/相关散点图/热图/空间分布图等',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'data_path': {'type': 'string', 'description': '数据文件路径'},
                        'output_dir': {'type': 'string', 'description': '输出目录'},
                    },
                },
            ),
            Tool(
                name='write_section',
                description='写作论文章节 — 支持 results/discussion/introduction/methods/conclusion/abstract/all',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'section': {
                            'type': 'string',
                            'enum': ['results', 'discussion', 'introduction', 'methods', 'conclusion', 'abstract', 'all'],
                            'description': '章节名',
                        },
                        'data_path': {'type': 'string', 'description': '数据文件路径'},
                        'output_dir': {'type': 'string', 'description': '输出目录'},
                    },
                    'required': ['section'],
                },
            ),
            Tool(
                name='review_paper',
                description='审稿检查 — 12类检查，返回问题列表',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'paper_path': {'type': 'string', 'description': '论文文件路径（如 paper.md）'},
                        'output_dir': {'type': 'string', 'description': '输出目录'},
                    },
                },
            ),
            Tool(
                name='pipeline_full',
                description='全流程管线 — 数据分析→图表→写作→审稿→修订→DOCX排版（需Claude CLI）',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'data_path': {'type': 'string', 'description': '数据文件路径'},
                        'output_dir': {'type': 'string', 'description': '输出目录'},
                    },
                },
            ),
            Tool(
                name='pipeline_quick',
                description='快速离线流程 — 数据分析→模板写作→审稿→DOCX（无需Claude CLI）',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'data_path': {'type': 'string', 'description': '数据文件路径'},
                    },
                },
            ),
            Tool(
                name='check_status',
                description='系统状态检查 — 数据文件/Claude CLI/模块/知识库/依赖',
                inputSchema={
                    'type': 'object',
                    'properties': {},
                },
            ),
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        try:
            tool_map = {
                'explore_data': tool_explore_data,
                'analyze_all': tool_analyze_all,
                'generate_figures': tool_generate_figures,
                'write_section': tool_write_section,
                'review_paper': tool_review_paper,
                'pipeline_full': tool_pipeline_full,
                'pipeline_quick': tool_pipeline_quick,
                'check_status': tool_check_status,
            }
            
            handler = tool_map.get(name)
            if not handler:
                raise ValueError(f"未知工具: {name}")
            
            result = await handler(**arguments)
            return [TextContent(type='text', text=result)]
            
        except FileNotFoundError as e:
            return [TextContent(type='text', text=json.dumps({'error': str(e)}, ensure_ascii=False))]
        except Exception as e:
            logger.error(f"工具 {name} 执行失败: {e}")
            return [TextContent(type='text', text=json.dumps({'error': str(e)[:500]}, ensure_ascii=False))]
    
    @app.list_prompts()
    async def list_prompts():
        return [
            Prompt(
                name='write_paper',
                description='按标准流程完成一篇论文：分析→写作→审稿→输出',
                arguments=[
                    PromptArgument(name='data_path', description='数据文件路径', required=False),
                    PromptArgument(name='language', description='语言（zh/en）', required=False),
                ],
            ),
        ]
    
    @app.get_prompt()
    async def get_prompt(name: str, arguments: dict | None = None):
        if name == 'write_paper':
            data_path = (arguments or {}).get('data_path', _find_data_file() or '')
            language = (arguments or {}).get('language', 'zh')
            
            messages = [
                PromptMessage(
                    role='user',
                    content=TextContent(
                        type='text',
                        text=f"""请按以下步骤完成论文写作：

1. 使用 explore_data 工具探索数据
2. 使用 generate_figures 生成图表
3. 使用 write_section 逐一写作所有章节
4. 使用 review_paper 审稿检查
5. 最后汇总输出

数据路径: {data_path}
语言: {language}"""
                    ),
                ),
            ]
            return GetPromptResult(messages=messages)
        
        raise ValueError(f"未知提示模板: {name}")


# ============================================================
# 入口
# ============================================================

def main():
    if not MCP_AVAILABLE:
        print("ERROR: mcp 包未安装。请运行: pip install mcp")
        sys.exit(1)
    
    import asyncio
    asyncio.run(stdio_server(app))


if __name__ == '__main__':
    main()