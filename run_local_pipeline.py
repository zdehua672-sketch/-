# -*- coding: utf-8 -*-
"""
本地全自动管线 — 无需Claude API，完全离线运行
加载桌面冬春数据 → 数据探索 → 图表生成 → 论文写作 → DOCX输出
"""
import os
import sys
import shutil
import matplotlib
matplotlib.use('Agg')

from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
OUTPUT_DIR = os.path.join(_HERE, 'paper_output')
ANALYSIS_DIR = os.path.join(_HERE, 'analysis_output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# ============================================================
# 1. 数据加载 — 使用桌面冬春数据
# ============================================================
print("=" * 60)
print("  学术论文全自动生成系统 (离线模式)")
print("=" * 60)

DATA_FILE = os.path.join(DESKTOP, '冬春数据.xlsx')
if not os.path.exists(DATA_FILE):
    DATA_FILE = os.path.join(_HERE, 'data', 'sample_data.xlsx')
print(f"\n[1] 数据文件: {DATA_FILE}")

from data_loader import DataLoader
loader = DataLoader(DATA_FILE)
df = loader.load_data()
print(f"    样本: {len(df)}行, 变量: {len(df.columns)}列")

# ============================================================
# 2. 数据探索 — 发现模式
# ============================================================
print("\n[2] 数据探索...")
from data_driven_pipeline import DataExplorer
explorer = DataExplorer(df)
findings = explorer.explore()
print(f"    发现 {len(findings)} 个模式")

# ============================================================
# 3. 初始化知识记忆
# ============================================================
print("\n[3] 初始化知识记忆...")
from knowledge_memory import KnowledgeMemory
memory = KnowledgeMemory()
stats = memory.get_stats()
print(f"    知识库: {stats.get('total_entries', 0)}条")

# ============================================================
# 4. 生成图表
# ============================================================
print("\n[4] 生成图表...")
from scientific_visualization_agent import VisualizationAgent

plotter = VisualizationAgent(df, ANALYSIS_DIR, style='chinese')

# 基础图
plotter.plot_phase_composition()
plotter.plot_multivariate(variables=['CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)'], kind='box')
plotter.plot_multivariate(variables=['TOC（mg/L)', 'IC(mg/L)', 'DO(mg/L)', 'pH'], kind='box')
plotter.plot_heatmap()
plotter.plot_batch_regressions()
plotter.plot_pca_hca(mode='biplot')
plotter.plot_hca_dendrogram()
plotter.plot_spatiotemporal(mode='line')
plotter.plot_multiphase_coupling()

# 列出全部图表
fig_list = sorted(os.listdir(ANALYSIS_DIR))
png_files = [f for f in fig_list if f.endswith('.png')]
print(f"    生成 {len(png_files)} 张图表")

# ============================================================
# 5. 自动注册图表
# ============================================================
print("\n[5] 注册图表到上下文...")
figures = {}
fig_names = {
    'descriptive': ['pie', '饼', 'phase', '相'],
    'group_gas': ['box', '箱线', 'CH4', 'gas', '气体'],
    'group_liquid': ['box', '箱线', 'TOC', 'liquid', '液相'],
    'correlation': ['heatmap', '热图', 'corr', '相关'],
    'pca': ['pca', 'PCA', 'biplot', '双标'],
    'hca': ['hca', 'HCA', 'dendro', '聚类', '树状'],
    'regression': ['regression', '回归', 'TOC_CO2'],
    'spatial': ['spatial', 'spatiotemporal', '空间'],
    'multiphase': ['multiphase', 'carbon_flow', '碳平衡', '耦合'],
}

idx = 1
for f in png_files:
    fpath = os.path.join(ANALYSIS_DIR, f)

    # 自动匹配类型
    if any(k in f.lower() for k in ['pie', 'phase', '饼', '相']):
        figures['phase_pie'] = {'path': fpath, 'caption': f'图{idx} 固液气三相碳污染物组成比例', 'type': 'descriptive', 'section': 'results'}
        print(f"    图{idx}: {f} → 描述统计")
    elif any(k in f.lower() for k in ['box', '箱线']) and any(k in f.lower() for k in ['ch4', 'gas', '气体']):
        figures['gas_box'] = {'path': fpath, 'caption': f'图{idx} 冬春季气相碳污染物浓度比较', 'type': 'group_difference', 'section': 'results'}
        print(f"    图{idx}: {f} → 季节差异(气相)")
    elif any(k in f.lower() for k in ['box', '箱线']):
        figures['liquid_box'] = {'path': fpath, 'caption': f'图{idx} 冬春季液相指标比较', 'type': 'group_difference', 'section': 'results'}
        print(f"    图{idx}: {f} → 季节差异(液相)")
    elif any(k in f.lower() for k in ['heatmap', '热图', 'corr', '相关']):
        figures['heatmap'] = {'path': fpath, 'caption': f'图{idx} Pearson相关性矩阵', 'type': 'correlation', 'section': 'results'}
        print(f"    图{idx}: {f} → 相关性热图")
    elif any(k in f.lower() for k in ['pca', 'biplot', '双标']):
        figures['pca'] = {'path': fpath, 'caption': f'图{idx} 主成分分析双标图', 'type': 'pca', 'section': 'results'}
        print(f"    图{idx}: {f} → PCA")
    elif any(k in f.lower() for k in ['hca', 'dendro', '聚类', '树状']):
        figures['hca'] = {'path': fpath, 'caption': f'图{idx} 层次聚类分析树状图', 'type': 'hca', 'section': 'results'}
        print(f"    图{idx}: {f} → HCA")
    elif any(k in f.lower() for k in ['regression', '回归']):
        if 'toc' in f.lower() and 'co2' in f.lower():
            figures['reg_toc_co2'] = {'path': fpath, 'caption': f'图{idx} TOC与CO₂回归分析', 'type': 'regression', 'section': 'results'}
            print(f"    图{idx}: {f} → TOC-CO2回归")
        else:
            figures['reg_tn_toc'] = {'path': fpath, 'caption': f'图{idx} 总氮与TOC回归分析', 'type': 'regression', 'section': 'results'}
            print(f"    图{idx}: {f} → 回归分析")
    elif any(k in f.lower() for k in ['spatial', 'spatiotemporal', '空间']):
        figures['spatial'] = {'path': fpath, 'caption': f'图{idx} 冬春季气体浓度沿程空间分布', 'type': 'spatial', 'section': 'results'}
        print(f"    图{idx}: {f} → 空间分布")
    elif any(k in f.lower() for k in ['multiphase', 'carbon_flow', '耦合']):
        figures['carbon_balance'] = {'path': fpath, 'caption': f'图{idx} 碳平衡与多相态耦合分析', 'type': 'balance', 'section': 'discussion'}
        print(f"    图{idx}: {f} → 碳平衡")
    else:
        print(f"    图{idx}: {f} → 未匹配")
    idx += 1

# ============================================================
# 6. 论文写作 — 使用本地模板引擎（无Claude API依赖）
# ============================================================
print("\n[6] 论文写作...")

# 6.1 Results - 使用DataDrivenWriter模板
from data_driven_pipeline import DataDrivenWriter
writer = DataDrivenWriter(df, findings, OUTPUT_DIR, memory=memory)
results_text = writer.write_results()
discussion_text = writer.write_discussion()
rationale_report = writer.get_rationale_report()
rationale_rows = writer.rationale_rows
print(f"    ✓ Results: {len(results_text)}字")
print(f"    ✓ Discussion: {len(discussion_text)}字")
print(f"    ✓ 推理链: {len(rationale_rows)}条")

# 6.2 Introduction - 使用模板
from paper_writing_agent import IntroductionGenerator
intro_gen = IntroductionGenerator()
intro_text = intro_gen.generate(language='zh')
print(f"    ✓ Introduction: {len(intro_text)}字")

# 6.3 Methods - 使用模板
from paper_writing_agent import MethodsGenerator
methods_gen = MethodsGenerator()
methods_text = methods_gen.generate(language='zh')
print(f"    ✓ Methods: {len(methods_text)}字")

# 6.4 Conclusion - 模板
critical = [f for f in findings if f['importance'] in ['critical', 'high']]
group_f = [f for f in critical if f['type'] == 'group_difference']
corr_f = [f for f in critical if f['type'] == 'correlation']

import numpy as np
lines = ['# 5 结论\n']
lines.append('本研究以校园污水管网为对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。主要结论如下：\n')
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
conclusion_text = '\n'.join(lines)
print(f"    ✓ Conclusion: {len(conclusion_text)}字")

# 6.5 Abstract - 使用模板
from paper_writing_agent import AbstractGenerator
abstract_gen = AbstractGenerator(intro_text, methods_text, results_text, discussion_text)
abstract_text = abstract_gen.generate(language='zh')
print(f"    ✓ Abstract: {len(abstract_text)}字")

# 6.6 保存各章节
sections = {
    'abstract': abstract_text,
    'introduction': intro_text,
    'methods': methods_text,
    'results': results_text,
    'discussion': discussion_text,
    'conclusion': conclusion_text,
}

# 保存MD论文
full_paper_md = []
for key, heading in [('abstract', '# 摘要'), ('introduction', '# 1 引言'),
                       ('methods', '# 2 材料与方法'), ('results', '# 3 结果'),
                       ('discussion', '# 4 讨论'), ('conclusion', '# 5 结论')]:
    if key in sections and sections[key]:
        full_paper_md.append(f"{heading}\n\n{sections[key]}")
        # 去掉章节内自带的标题
        lines_clean = [l for l in sections[key].split('\n') if not l.strip().startswith('#')]
        full_paper_md.append('\n'.join(lines_clean))

paper_md = '\n\n---\n\n'.join(full_paper_md)
paper_md_path = os.path.join(OUTPUT_DIR, 'paper.md')
with open(paper_md_path, 'w', encoding='utf-8') as f:
    f.write(paper_md)
print(f"    ✓ 论文MD: {paper_md_path}")

# 复制到桌面
desktop_md = os.path.join(DESKTOP, '冬春数据论文_离线版.md')
shutil.copy2(paper_md_path, desktop_md)
print(f"    ✓ 已复制到桌面: {desktop_md}")

# ============================================================
# 7. 审稿
# ============================================================
print("\n[7] 审稿检查...")
try:
    from academic_review_agent import AcademicReviewAgent
    reviewer = AcademicReviewAgent(paper_type='chinese_journal', language='zh')
    review_report = reviewer.review(paper_md)
    review_summary = review_report.summary()
    print(f"    发现 {review_summary.get('total', 0)} 个问题")

    # 保存审稿报告
    review_path = os.path.join(OUTPUT_DIR, 'review_report.md')
    with open(review_path, 'w', encoding='utf-8') as f:
        f.write(f"# 审稿报告\n\n")
        s = review_summary
        f.write(f"**总计**: {s.get('total', 0)}个问题\n\n")
        if hasattr(review_report, 'issues'):
            for issue in review_report.issues:
                severity = getattr(issue, 'severity', '')
                category = getattr(issue, 'category', '')
                problem = getattr(issue, 'problem', '')
                suggestion = getattr(issue, 'suggestion', '')
                section = getattr(issue, 'section', '')
                location = getattr(issue, 'location', '')
                f.write(f"### [{severity}] {category}\n")
                f.write(f"- 位置: {section} / {location}\n")
                f.write(f"- 问题: {problem}\n")
                f.write(f"- 建议: {suggestion}\n\n")
    print(f"    审稿报告: {review_path}")
except Exception as e:
    print(f"    审稿跳过: {e}")

# ============================================================
# 8. 推理链报告
# ============================================================
print("\n[8] 推理链报告...")
if rationale_rows:
    rationale_path = os.path.join(OUTPUT_DIR, 'rationale_report.md')
    with open(rationale_path, 'w', encoding='utf-8') as f:
        f.write(rationale_report)
    print(f"    推理链: {rationale_path}")
else:
    print("    无推理链记录")

# ============================================================
# 9. DOCX排版
# ============================================================
print("\n[9] 排版DOCX...")
try:
    from data_driven_pipeline import InlineDocumentAssembler
    assembler = InlineDocumentAssembler(
        title='污水管网中碳污染物的冬春季节变化特征',
        output_dir=OUTPUT_DIR,
    )

    section_order = [
        ('abstract', '摘要'),
        ('introduction', '1 引言'),
        ('methods', '2 材料与方法'),
        ('results', '3 结果'),
        ('discussion', '4 讨论'),
        ('conclusion', '5 结论'),
    ]

    for key, heading in section_order:
        text = sections.get(key, '')
        if not text:
            continue
        lines = text.strip().split('\n')
        body_lines = [l for l in lines if not l.strip().startswith('#')]
        body = '\n'.join(body_lines).strip()
        if body:
            # 匹配该章节的图表
            matched_figs = []
            section_map = {'results': ['gas_box', 'liquid_box', 'heatmap', 'pca', 'hca', 'reg_toc_co2', 'reg_tn_toc', 'spatial', 'phase_pie'],
                          'discussion': ['carbon_balance']}
            for fig_key in section_map.get(key, []):
                if fig_key in figures:
                    matched_figs.append(figures[fig_key])
            assembler.add_section(heading, text=body, figures=matched_figs)

    docx_path = assembler.assemble(os.path.join(OUTPUT_DIR, 'paper.docx'))
    print(f"    DOCX: {docx_path}")

    # 复制到桌面
    desktop_docx = os.path.join(DESKTOP, '冬春数据论文_离线版.docx')
    if os.path.exists(docx_path):
        shutil.copy2(docx_path, desktop_docx)
        print(f"    已复制到桌面: {desktop_docx}")
except Exception as e:
    print(f"    DOCX排版失败: {e}")

# ============================================================
# 10. 汇总
# ============================================================
print("\n" + "=" * 60)
print("  论文生成完成！")
print("=" * 60)
print(f"\n论文目录: {OUTPUT_DIR}")
print(f"桌面文件:")
print(f"  - {desktop_md}")
if os.path.exists(docx_path if 'docx_path' in dir() else ''):
    print(f"  - {desktop_docx}")
print(f"\n生成文件:")
print(f"  - paper.md (Markdown论文)")
print(f"  - paper.docx (Word文档)")
print(f"  - review_report.md (审稿报告)")
print(f"  - rationale_report.md (推理链报告)")
print(f"  - analysis_output/ ({len(png_files)}张图表)")
print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")