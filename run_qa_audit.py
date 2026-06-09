# -*- coding: utf-8 -*-
"""对所有现有图表运行QA审核"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

from chart_qa import check_chart_quality, print_qa_report

OUT = os.path.expanduser('~/Desktop/数据分析图表')

# 列出所有PNG
charts = sorted([f for f in os.listdir(OUT) if f.endswith('.png') and f.startswith('图')])

print("=" * 55)
print(f"QA Audit: {len(charts)} charts in {OUT}")
print("=" * 55)

results = []
for fname in charts:
    fpath = os.path.join(OUT, fname)
    try:
        img = plt.imread(fpath)
        # 用原始比例渲染
        h, w = img.shape[:2]
        fig, ax = plt.subplots(figsize=(w/100, h/100), dpi=100)
        ax.imshow(img)
        ax.axis('off')
        r = check_chart_quality(fig, auto_fix=False)
        results.append((fname, r))
        print_qa_report(r, fname)
        plt.close(fig)
    except Exception as e:
        print(f"  [SKIP] {fname}: {e}")

# 汇总
print("\n" + "=" * 55)
n_pass = sum(1 for _, r in results if r['status'] == 'PASS')
n_warn = sum(1 for _, r in results if r['status'] == 'WARN')
n_fail = sum(1 for _, r in results if r['status'] == 'FAIL')
print(f"Summary: {len(results)} charts | PASS:{n_pass} WARN:{n_warn} FAIL:{n_fail}")

if n_fail > 0:
    print("\n需要修复:")
    for name, r in results:
        if r['status'] == 'FAIL':
            print(f"  [XX] {name}")
            for typ, sev, detail in r['issues']:
                if sev == 'HIGH':
                    print(f"       - {typ}: {detail}")
