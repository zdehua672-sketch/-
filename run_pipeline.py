# -*- coding: utf-8 -*-
"""
运行完整管线 - 使用冬春数据
"""
import os
import sys
import shutil
from datetime import datetime

# 设置标准输出编码为UTF-8（解决Windows中文显示问题）
if sys.platform == 'win32':
    import io
    # 保存原始的 stdout 和 stderr
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    # 创建 UTF-8 编码的 wrapper
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置数据文件路径
DATA_FILE = 'data/winter_spring_data.xlsx'
if not os.path.exists(DATA_FILE):
    print(f"错误: 数据文件不存在: {DATA_FILE}")
    sys.exit(1)

OUTPUT_DIR = 'paper_output'
ANALYSIS_DIR = 'analysis_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# ============================================================
# 创建上下文 + 编排器
# ============================================================
from paper_context import PaperContext, PaperOrchestrator

# 设置元数据（用于填充占位符）
metadata = {
    'campus_area': '15',  # 校园面积（公顷）
    'population': '2',  # 常住人口（万人）
    'daily_sewage': '800',  # 日均污水排放量（m³/d）
    'n_sampling_points': 20,  # 采样点数量
    'winter_months': '1',  # 冬季采样月份
    'spring_months': '4',  # 春季采样月份
}

ctx = PaperContext(
    data_path=DATA_FILE,
    output_dir=OUTPUT_DIR,
    language='zh',
    paper_type='chinese',
    title='污水管网中碳污染物的冬春季节变化特征',
    metadata=metadata,
)

orch = PaperOrchestrator()

# ============================================================
# 自动编排执行
# ============================================================
print("=" * 60)
print("  PaperContext 架构全流程")
print("=" * 60)

# 先生成图表（需要在编排前，因为图表是独立的）
print("\n[预处理] 生成图表...")
from data_loader import DataLoader
from scientific_visualization_agent import VisualizationAgent

loader = DataLoader(DATA_FILE)
df = loader.load_data()

plotter = VisualizationAgent(df, ANALYSIS_DIR, style='chinese')

# 基础图
plotter.plot_phase_composition()
gas_vars = [c for c in ['CH4平均值', 'N2O平均值', 'CO2', 'VOCs(ppb)'] if c in df.columns]
if gas_vars:
    plotter.plot_multivariate(variables=gas_vars, kind='box')
liquid_vars = [c for c in ['TOC（mg/L)', 'IC(mg/L)', 'DO(mg/L)', 'pH'] if c in df.columns]
if liquid_vars:
    plotter.plot_multivariate(variables=liquid_vars, kind='box')
plotter.plot_heatmap()
plotter.plot_batch_regressions()

# 新增图
plotter.plot_pca_hca()
plotter.plot_hca_dendrogram()
plotter.plot_spatiotemporal()
plotter.plot_phase_composition()
plotter.plot_carbon_flow()

# 注册图表到上下文（按章节分组）
ctx.figures = {
    # Results 3.1 描述统计
    'phase_pie': {'path': os.path.join(ANALYSIS_DIR, '图1_三相碳组成.png'), 'caption': '图1 固液气三相碳污染物组成比例', 'type': 'descriptive', 'section': 'results'},
    # Results 3.2 季节差异
    'gas_box': {'path': os.path.join(ANALYSIS_DIR, '图4_气体浓度箱线图.png'), 'caption': '图2 冬春季气相碳污染物浓度比较', 'type': 'group_difference', 'section': 'results'},
    'liquid_box': {'path': os.path.join(ANALYSIS_DIR, '图5_液相指标箱线图.png'), 'caption': '图3 冬春季液相指标比较', 'type': 'group_difference', 'section': 'results'},
    # Results 3.3 相关性
    'heatmap': {'path': os.path.join(ANALYSIS_DIR, '图6_相关性热图.png'), 'caption': '图4 Pearson相关性矩阵', 'type': 'correlation', 'section': 'results'},
    # Results 3.4 多元分析
    'pca': {'path': os.path.join(ANALYSIS_DIR, '图7_PCA双标图.png'), 'caption': '图5 主成分分析双标图', 'type': 'pca', 'section': 'results'},
    'hca': {'path': os.path.join(ANALYSIS_DIR, '图8_HCA聚类图.png'), 'caption': '图6 层次聚类分析树状图', 'type': 'hca', 'section': 'results'},
    # Results 3.5 回归
    'reg_toc_co2': {'path': os.path.join(ANALYSIS_DIR, '图10_TOC_CO2回归.png'), 'caption': '图7 TOC与CO₂回归分析', 'type': 'regression', 'section': 'results'},
    'reg_tn_toc': {'path': os.path.join(ANALYSIS_DIR, '图13_TN_TOC回归.png'), 'caption': '图8 总氮与TOC回归分析', 'type': 'regression', 'section': 'results'},
    # Results 3.6 空间分布
    'spatial': {'path': os.path.join(ANALYSIS_DIR, '图15_空间分布图.png'), 'caption': '图9 冬春季气体浓度沿程空间分布', 'type': 'spatial', 'section': 'results'},
    # Discussion 碳平衡
    'gas_liquid_ratio': {'path': os.path.join(ANALYSIS_DIR, '图16_气液碳比分布.png'), 'caption': '图10 气液碳比分布', 'type': 'ratio', 'section': 'discussion'},
    'carbon_balance': {'path': os.path.join(ANALYSIS_DIR, '图17_碳平衡.png'), 'caption': '图11 碳平衡分析', 'type': 'balance', 'section': 'discussion'},
}
print(f"  图表: {len(ctx.figures)}张")

# 运行编排器
orch.run(ctx)

# ============================================================
# 后处理：推理链报告 + 审稿报告
# ============================================================
print("\n[后处理] 生成报告...")

# DOCX 已在 paper_output 目录
if ctx.has('docx_path') and os.path.exists(ctx.docx_path):
    print(f"  DOCX: {ctx.docx_path}")

# 推理链报告
if ctx.rationale_rows:
    from data_driven_pipeline import DataDrivenWriter
    # 临时 writer 只用于生成报告
    tmp_writer = DataDrivenWriter.__new__(DataDrivenWriter)
    tmp_writer.rationale_rows = ctx.rationale_rows
    rationale_report = tmp_writer.get_rationale_report()
    rationale_path = os.path.join(OUTPUT_DIR, 'rationale_report.md')
    with open(rationale_path, 'w', encoding='utf-8') as f:
        f.write(rationale_report)
    print(f"  推理链: {rationale_path}")

# 审稿报告
if ctx.has('review_report'):
    review_path = os.path.join(OUTPUT_DIR, 'review_report.md')
    with open(review_path, 'w', encoding='utf-8') as f:
        f.write(f"# 审稿报告\n\n")
        f.write(f"**总计**: {ctx.review_summary.get('total', 0)}个问题\n\n")
        for issue in ctx.review_report.issues:
            f.write(f"### [{issue.severity.value}] {issue.category}\n")
            f.write(f"- 位置: {issue.section} / {issue.location}\n")
            f.write(f"- 问题: {issue.problem}\n")
            f.write(f"- 建议: {issue.suggestion}\n\n")
    print(f"  审稿报告: {review_path}")

# 修订报告
if ctx.revision_report:
    rev_path = os.path.join(OUTPUT_DIR, 'revision_report.md')
    with open(rev_path, 'w', encoding='utf-8') as f:
        f.write(ctx.revision_report)
    print(f"  修订报告: {rev_path}")

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 60)
print("  全流程完成！")
print("=" * 60)

# 执行日志
print(f"\n执行日志:")
for entry in orch.get_log():
    status_icon = {'done': 'OK', 'skipped': 'SKIP', 'error': 'ERR'}.get(entry['status'], '?')
    print(f"  [{status_icon}] {entry['step']}")

# 章节统计
print(f"\n章节:")
for name in ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']:
    if ctx.has_section(name):
        print(f"  {name}: {len(ctx.sections[name])}字")

# 推理链统计
if ctx.rationale_rows:
    # 过滤出字典类型的元素
    valid_rows = [r for r in ctx.rationale_rows if isinstance(r, dict)]
    if valid_rows:
        complete = sum(1 for r in valid_rows if r.get('completeness', 0) >= 0.8)
        partial = sum(1 for r in valid_rows if 0.3 <= r.get('completeness', 0) < 0.8)
        print(f"\n推理链: {len(ctx.rationale_rows)}条 (完整:{complete} 部分:{partial})")
    else:
        print(f"\n推理链: {len(ctx.rationale_rows)}条 (均为字符串格式)")

# 审稿统计
if ctx.has('review_summary'):
    s = ctx.review_summary
    print(f"\n审稿: {s.get('total', 0)}个问题 "
          f"(CRITICAL:{s.get('by_severity', {}).get('CRITICAL', 0)} "
          f"MAJOR:{s.get('by_severity', {}).get('MAJOR', 0)})")

print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")