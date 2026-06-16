# -*- coding: utf-8 -*-
"""
学术写作系统 CLI 脚手架 — 让外部 AI (xiaomiMIMO/Claude) 能精确调用每个模块

用法:
    python cli.py explore                          # 数据探索
    python cli.py analyze                          # 全部数据分析
    python cli.py figures                          # 生成图表
    python cli.py write results                    # 写 Results
    python cli.py write discussion                 # 写 Discussion
    python cli.py write introduction               # 写 Introduction
    python cli.py write methods                    # 写 Methods
    python cli.py write conclusion                 # 写 Conclusion
    python cli.py write abstract                   # 写 Abstract
    python cli.py review                           # 审稿检查
    python cli.py revise                           # 自动修订
    python cli.py assemble                         # DOCX排版
    python cli.py latex                            # LaTeX导出
    python cli.py pipeline full                    # 全流程
    python cli.py pipeline quick                   # 快速流程（无Claude）
    python cli.py status                           # 查看模块状态
    python cli.py knowledge inject                 # 注入知识库
"""
import os
import sys
import json
import logging
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('cli')


# ============================================================
# 工具函数
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


def _load_df(data_path=None):
    """加载 DataFrame"""
    from data_loader import DataLoader
    path = data_path or _find_data_file()
    if not path:
        print("ERROR: 未找到数据文件。运行 python scripts/generate_sample_data.py 生成示例数据")
        sys.exit(1)
    print(f"  数据文件: {path}")
    loader = DataLoader(path)
    df = loader.load_data()
    print(f"  样本: {len(df)}行, 变量: {len(df.columns)}列")
    return df, path


def _print_json(obj):
    """打印 JSON 格式结果"""
    if isinstance(obj, (list, dict)):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(str(obj))


# ============================================================
# CLI 命令实现
# ============================================================

def cmd_explore(args):
    """数据探索 — 发现数据中的模式"""
    df, _ = _load_df(args.data)
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    findings = explorer.explore()
    print(f"\n共发现 {len(findings)} 个模式")
    if args.json:
        _print_json(findings)
    return findings


def cmd_analyze(args):
    """全部分析：基础探索 + 科学分析 + 高级分析"""
    df, data_path = _load_df(args.data)
    
    # 1. 基础探索
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    findings = explorer.explore()
    print(f"  基础探索: {len(findings)} 个发现")
    
    # 2. 科学分析
    try:
        from scientific_analysis_agent import ScientificAnalysisAgent
        output_dir = args.output or os.path.join(_HERE, 'paper_output')
        agent = ScientificAnalysisAgent(data_path=data_path, output_dir=output_dir)
        agent.load_data()
        sci_results = agent.run()
        print(f"  科学分析: {'完成' if sci_results else '跳过'}")
    except Exception as e:
        print(f"  科学分析: 跳过 ({e})")
    
    # 3. 高级分析
    try:
        from advanced_analysis import CrossAnalyzer, AnomalyDeepDiver, DataStoryExtractor, ThresholdDetector
        cross = CrossAnalyzer(df)
        cross_results = cross.analyze_all()
        print(f"  交叉分析: {len(cross_results) if isinstance(cross_results, list) else 0} 项")
    except Exception as e:
        print(f"  高级分析: 跳过 ({e})")
    
    print("\n分析完成！")
    return findings


def cmd_figures(args):
    """生成图表"""
    df, data_path = _load_df(args.data)
    output_dir = args.output or os.path.join(_HERE, 'paper_output')
    analysis_dir = os.path.join(output_dir, 'figures')
    os.makedirs(analysis_dir, exist_ok=True)
    
    # 使用 PaperContext 的图表生成逻辑
    from paper_context import PaperContext, _run_generate_figures, _run_memory_init
    ctx = PaperContext(data_path=data_path, output_dir=output_dir)
    ctx.df = df
    _run_memory_init(ctx)
    
    # 先运行探索获取 findings
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    ctx.findings = explorer.explore()
    
    # 生成图表
    fig_keys = _run_generate_figures(ctx)
    if fig_keys:
        print(f"\n生成 {len(fig_keys)} 张图表:")
        for key in fig_keys:
            info = ctx.figures.get(key, {})
            print(f"  - {key}: {info.get('caption', '')}")
    else:
        print("\n图表生成完成")
    
    # 保存图表信息
    if ctx.figures:
        info_path = os.path.join(analysis_dir, 'figure_index.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(ctx.figures, f, ensure_ascii=False, indent=2)
        print(f"  图表索引: {info_path}")
    
    return ctx.figures


def cmd_write(args):
    """写论文章节"""
    section = args.section
    
    df, data_path = _load_df(args.data)
    output_dir = args.output or os.path.join(_HERE, 'paper_output')
    os.makedirs(output_dir, exist_ok=True)
    
    from paper_context import PaperContext, _run_memory_init
    ctx = PaperContext(data_path=data_path, output_dir=output_dir, language='zh')
    ctx.df = df
    _run_memory_init(ctx)
    
    # 探索数据
    from data_driven_pipeline import DataExplorer
    explorer = DataExplorer(df)
    ctx.findings = explorer.explore()
    
    # 获取 ClaudeWriter
    from claude_writer import ClaudeWriter
    writer = ClaudeWriter(timeout=180)
    
    writers = {
        'results': lambda: _write_results(ctx, writer),
        'discussion': lambda: _write_discussion(ctx, writer),
        'introduction': lambda: _write_introduction(ctx, writer),
        'methods': lambda: _write_methods(ctx, writer),
        'conclusion': lambda: _write_conclusion(ctx, writer),
        'abstract': lambda: _write_abstract(ctx, writer),
    }
    
    if section == 'all':
        results = {}
        for name, fn in writers.items():
            print(f"\n[{name}]")
            results[name] = fn()
        print("\n所有章节写作完成！")
        # 保存全文
        _save_full_paper(ctx, output_dir)
        return results
    elif section in writers:
        return writers[section]()
    else:
        print(f"未知章节: {section}")
        print(f"可用章节: {list(writers.keys())}")
        sys.exit(1)


def _write_results(ctx, writer):
    """写 Results"""
    result = writer.write_results(ctx.findings, ctx.figures, learned_patterns=ctx.learned_patterns)
    if not result:
        from data_driven_pipeline import DataDrivenWriter
        tpl = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
        result = tpl.write_results()
    ctx.sections['results'] = result
    print(f"  Results: {len(result)} 字")
    _save_section(ctx.output_dir, 'results', result)
    return result


def _write_discussion(ctx, writer):
    """写 Discussion"""
    mechanisms = {}
    if ctx.has('memory'):
        for f in ctx.findings:
            if f.get('type') == 'correlation':
                v1, v2 = f.get('variables', ('', ''))
                mechs = ctx.memory.recall(f'{v1} {v2}', category='mechanisms', top_k=1)
                if mechs:
                    mechanisms[f'{v1}_vs_{v2}'] = mechs[0].get('value', {}).get('mechanism', '')
    result = writer.write_discussion(ctx.findings, mechanisms, language='zh')
    if not result:
        from data_driven_pipeline import DataDrivenWriter
        tpl = DataDrivenWriter(ctx.df, ctx.findings, ctx.output_dir, memory=ctx.memory)
        result = tpl.write_discussion()
    ctx.sections['discussion'] = result
    print(f"  Discussion: {len(result)} 字")
    _save_section(ctx.output_dir, 'discussion', result)
    return result


def _write_introduction(ctx, writer):
    """写 Introduction"""
    result = writer.write_introduction(ctx.findings, language='zh')
    if not result:
        from paper_writing_agent import IntroductionGenerator
        gen = IntroductionGenerator()
        result = gen.generate(language='zh')
    ctx.sections['introduction'] = result
    print(f"  Introduction: {len(result)} 字")
    _save_section(ctx.output_dir, 'introduction', result)
    return result


def _write_methods(ctx, writer):
    """写 Methods"""
    data_info = {
        'n_samples': len(ctx.df),
        'n_variables': len(ctx.df.columns),
        'variables': list(ctx.df.columns),
        'groups': list(ctx.df.select_dtypes(include=['object', 'category']).columns),
    }
    result = writer.write_methods(data_info=data_info, language='zh')
    if not result:
        from paper_writing_agent import MethodsGenerator
        gen = MethodsGenerator()
        result = gen.generate(language='zh')
    ctx.sections['methods'] = result
    print(f"  Methods: {len(result)} 字")
    _save_section(ctx.output_dir, 'methods', result)
    return result


def _write_conclusion(ctx, writer):
    """写 Conclusion"""
    result = writer.write_conclusion(ctx.findings, language='zh')
    if not result:
        import numpy as np
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
            lines.append(f'{top["variable"]}等指标在{higher}显著偏高，温度和水文条件是驱动季节差异的主要因素。\n')
            i += 1
        if corr_f:
            lines.append(f'({i}) 变量间存在多组显著关联。')
            top = corr_f[0]
            v1, v2 = top['variables']
            lines.append(f'{v1}与{v2}的相关性最强(r={top["data"]["r"]:.3f})，揭示了碳氮耦合和多相态转化的内在机制。\n')
            i += 1
        lines.append(f'({i}) 上述发现为校园污水管网碳排放核算和碳管理策略制定提供了数据支撑和科学依据。')
        result = '\n'.join(lines)
    ctx.sections['conclusion'] = result
    print(f"  Conclusion: {len(result)} 字")
    _save_section(ctx.output_dir, 'conclusion', result)
    return result


def _write_abstract(ctx, writer):
    """写 Abstract"""
    if ctx.sections:
        result = writer.write_abstract(sections=ctx.sections, language='zh')
    else:
        result = None
    if not result:
        from paper_writing_agent import AbstractGenerator
        gen = AbstractGenerator(
            ctx.sections.get('introduction', ''),
            ctx.sections.get('methods', ''),
            ctx.sections.get('results', ''),
            ctx.sections.get('discussion', ''),
        )
        result = gen.generate(language='zh')
    ctx.sections['abstract'] = result
    print(f"  Abstract: {len(result)} 字")
    _save_section(ctx.output_dir, 'abstract', result)
    return result


def _save_section(output_dir, name, text):
    """保存单个章节"""
    path = os.path.join(output_dir, f'section_{name}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"  已保存: {path}")


def _save_full_paper(ctx, output_dir):
    """保存全文 MD"""
    order = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
    parts = []
    for key in order:
        text = ctx.sections.get(key, '')
        if text:
            parts.append(text)
    if parts:
        full = '\n\n---\n\n'.join(parts)
        path = os.path.join(output_dir, 'paper.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(full)
        print(f"  全文已保存: {path}")
    return ctx.sections


def cmd_review(args):
    """审稿检查"""
    paper_path = args.paper or os.path.join(args.output or _HERE, 'paper_output', 'paper.md')
    if not os.path.exists(paper_path):
        print(f"ERROR: 论文文件不存在: {paper_path}")
        print("请先运行 python cli.py write all")
        sys.exit(1)
    
    with open(paper_path, 'r', encoding='utf-8') as f:
        paper_text = f.read()
    
    from academic_review_agent import AcademicReviewAgent
    reviewer = AcademicReviewAgent(paper_type='chinese_journal', language='zh')
    report = reviewer.review(paper_text)
    summary = report.summary()
    
    print(f"\n审稿结果: {summary.get('total', 0)} 个问题")
    print(f"  CRITICAL: {summary.get('by_severity', {}).get('CRITICAL', 0)}")
    print(f"  MAJOR: {summary.get('by_severity', {}).get('MAJOR', 0)}")
    print(f"  MINOR: {summary.get('by_severity', {}).get('MINOR', 0)}")
    
    if hasattr(report, 'issues'):
        print(f"\n问题列表:")
        for issue in report.issues[:10]:
            sev = getattr(issue, 'severity', '')
            cat = getattr(issue, 'category', '')
            prob = getattr(issue, 'problem', '')[:100]
            print(f"  [{sev}] {cat}: {prob}")
    
    # 保存报告
    output_dir = args.output or os.path.join(_HERE, 'paper_output')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'review_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 审稿报告\n\n**总计**: {summary.get('total', 0)}个问题\n\n")
        if hasattr(report, 'issues'):
            for issue in report.issues:
                sev = getattr(issue, 'severity', '')
                cat = getattr(issue, 'category', '')
                prob = getattr(issue, 'problem', '')
                sug = getattr(issue, 'suggestion', '')
                sec = getattr(issue, 'section', '')
                f.write(f"### [{sev}] {cat}\n- 位置: {sec}\n- 问题: {prob}\n- 建议: {sug}\n\n")
    print(f"  审稿报告: {report_path}")
    
    return report


def cmd_pipeline(args):
    """管线执行"""
    mode = args.mode
    
    if mode == 'full':
        print("=" * 60)
        print("  全流程管线")
        print("=" * 60)
        from paper_context import PaperContext, PaperOrchestrator
        data_path = args.data or _find_data_file()
        if not data_path:
            print("ERROR: 未找到数据文件")
            sys.exit(1)
        output_dir = args.output or os.path.join(_HERE, 'paper_output')
        ctx = PaperContext(data_path=data_path, output_dir=output_dir, language='zh', 
                          paper_type='chinese', title='污水管网中碳污染物的冬春季节变化特征')
        orch = PaperOrchestrator()
        orch.run(ctx)
        print(f"\n全流程完成！输出目录: {output_dir}")
        
    elif mode == 'quick':
        print("=" * 60)
        print("  快速流程（离线模式，无需Claude）")
        print("=" * 60)
        exec(open(os.path.join(_HERE, 'run_local_pipeline.py')).read())
        
    else:
        print(f"未知模式: {mode}，可选: full, quick")


def cmd_status(args):
    """查看系统状态"""
    print("=" * 60)
    print("  学术写作系统状态检查")
    print("=" * 60)
    
    # 1. 检查数据文件
    data_file = _find_data_file()
    print(f"\n[数据文件] {'OK' if data_file else 'NO'}")
    if data_file:
        print(f"  {data_file}")
    else:
        print("  未找到，运行: python scripts/generate_sample_data.py")
    
    # 2. 检查 Claude CLI
    import shutil
    claude_cmd = shutil.which('claude')
    claude_npm = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm', 'claude.cmd')
    has_claude = claude_cmd is not None or os.path.exists(claude_npm)
    print(f"\n[Claude CLI] {'OK' if has_claude else 'NO'}")
    if not has_claude:
        print("  未安装，写作将使用模板回退")
    
    # 3. 检查模块注册
    try:
        from paper_context import MODULE_REGISTRY
        print(f"\n[模块注册表] {len(MODULE_REGISTRY)} 个模块")
        for name, info in MODULE_REGISTRY.items():
            needs = ', '.join(info['needs']) if info['needs'] else '无'
            provides = ', '.join(info['provides']) if info['provides'] else '无'
            print(f"  {name}: needs=[{needs}] → provides=[{provides}]")
    except Exception as e:
        print(f"\n[模块注册表] ✗ {e}")
    
    # 4. 检查孤立模块
    try:
        from check_orphans import check_orphans
        orphans = check_orphans()
        print(f"\n[孤立模块] {'OK 无孤立模块' if orphans == 0 else f'NO {orphans} 个孤立模块'}")
    except Exception:
        pass
    
    # 5. 检查知识库
    kb_dir = os.path.join(_HERE, 'knowledge_store')
    if os.path.exists(kb_dir):
        json_files = [f for f in os.listdir(kb_dir) if f.endswith('.json')]
        print(f"\n[知识库] {len(json_files)} 个 JSON 文件")
        for f in sorted(json_files):
            fsize = os.path.getsize(os.path.join(kb_dir, f))
            print(f"  {f} ({fsize/1024:.1f}KB)")
    
    # 6. 检查输出目录
    output_dir = os.path.join(_HERE, 'paper_output')
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print(f"\n[输出目录] {len(files)} 个文件")
        for f in sorted(files)[:10]:
            fsize = os.path.getsize(os.path.join(output_dir, f))
            print(f"  {f} ({fsize/1024:.1f}KB)")
    
    # 7. 检查依赖
    print(f"\n[Python 环境]")
    required = ['pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'python-docx', 'openpyxl']
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  OK {pkg}")
        except ImportError:
            print(f"  NO {pkg}")
    
    print(f"\n{'='*60}")
    print("  检查完成")
    print(f"{'='*60}")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='学术写作系统 CLI')
    parser.add_argument('--data', '-d', help='数据文件路径')
    parser.add_argument('--output', '-o', help='输出目录')
    parser.add_argument('--json', '-j', action='store_true', help='JSON 格式输出')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # explore
    p_explore = subparsers.add_parser('explore', help='数据探索')
    p_explore.set_defaults(func=cmd_explore)
    
    # analyze
    p_analyze = subparsers.add_parser('analyze', help='全部分析')
    p_analyze.set_defaults(func=cmd_analyze)
    
    # figures
    p_figures = subparsers.add_parser('figures', help='生成图表')
    p_figures.set_defaults(func=cmd_figures)
    
    # write
    p_write = subparsers.add_parser('write', help='写论文章节')
    p_write.add_argument('section', choices=['results', 'discussion', 'introduction', 'methods', 'conclusion', 'abstract', 'all'])
    p_write.set_defaults(func=cmd_write)
    
    # review
    p_review = subparsers.add_parser('review', help='审稿检查')
    p_review.add_argument('--paper', help='论文文件路径')
    p_review.set_defaults(func=cmd_review)
    
    # pipeline
    p_pipe = subparsers.add_parser('pipeline', help='管线执行')
    p_pipe.add_argument('mode', choices=['full', 'quick'])
    p_pipe.set_defaults(func=cmd_pipeline)
    
    # status
    p_status = subparsers.add_parser('status', help='系统状态检查')
    p_status.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)
    
    args.data = args.data or _find_data_file()
    result = args.func(args)
    
    return result


if __name__ == '__main__':
    main()