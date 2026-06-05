# -*- coding: utf-8 -*-
"""
PaperContext 架构全流程测试
中央上下文 + 灵活编排 + 知识库打通 + 图文对应
"""
import os
import sys
import shutil
from datetime import datetime

# ============================================================
# 配置
# ============================================================
DATA_FILE = r'C:\Users\Administrator\Desktop\冬春数据.xlsx'
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_output')
ANALYSIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis_output')
DESKTOP = r'C:\Users\Administrator\Desktop'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# ============================================================
# 创建上下文 + 编排器
# ============================================================
from paper_context import PaperContext, PaperOrchestrator

ctx = PaperContext(
    data_path=DATA_FILE,
    output_dir=OUTPUT_DIR,
    language='zh',
    paper_type='chinese',
    title='污水管网中碳污染物的冬春季节变化特征',
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
from plotting_functions import ThesisPlotter

loader = DataLoader(DATA_FILE)
df = loader.load_data()

plotter = ThesisPlotter(df, ANALYSIS_DIR)

# 基础图
plotter.plot_phase_composition()
plotter.plot_gas_boxplot()
plotter.plot_liquid_boxplot()
plotter.plot_correlation_heatmap()
plotter.plot_all_regressions()

# 新增图
plotter.plot_pca_biplot()
plotter.plot_hca_dendrogram()
plotter.plot_spatial_distribution()
plotter.plot_gas_liquid_ratio()
plotter.plot_carbon_balance()

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
# 后处理：复制到桌面 + 推理链报告 + 审稿报告
# ============================================================
print("\n[后处理] 输出到桌面...")

# 复制 DOCX 到桌面
if ctx.has('docx_path') and os.path.exists(ctx.docx_path):
    desktop_docx = os.path.join(DESKTOP, '冬春数据论文_PaperContext版.docx')
    shutil.copy2(ctx.docx_path, desktop_docx)
    print(f"  DOCX: {desktop_docx}")

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
    complete = sum(1 for r in ctx.rationale_rows if r.get('completeness', 0) >= 0.8)
    partial = sum(1 for r in ctx.rationale_rows if 0.3 <= r.get('completeness', 0) < 0.8)
    print(f"\n推理链: {len(ctx.rationale_rows)}条 (完整:{complete} 部分:{partial})")

# 审稿统计
if ctx.has('review_summary'):
    s = ctx.review_summary
    print(f"\n审稿: {s.get('total', 0)}个问题 "
          f"(CRITICAL:{s.get('by_severity', {}).get('CRITICAL', 0)} "
          f"MAJOR:{s.get('by_severity', {}).get('MAJOR', 0)})")

print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
