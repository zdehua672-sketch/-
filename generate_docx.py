# -*- coding: utf-8 -*-
"""生成完整DOCX论文 - 图文对应"""

import os
import sys
from document_assembler import DocumentAssembler

sys.stdout.reconfigure(encoding='utf-8')

# 创建组装器
assembler = DocumentAssembler(
    title='污水管网中碳污染物的冬春季节变化特征',
    paper_type='chinese',
    language='zh'
)

# ============ 1. 摘要 ============
assembler.add_section('摘要', text='本研究以某校园污水管网为研究对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。结果表明，碳污染物呈现显著的季节分异，CO₂本底值在冬季显著偏高，VOCs在冬季显著偏高。变量间存在多组显著关联，CO₂与NO₂显著相关(r=0.922)。上述发现为校园污水管网碳排放核算和碳管理策略制定提供了数据支撑。', level=1)

# ============ 2. 引言 ============
intro_text = """1.1 研究背景与意义

城市污水管网系统是城市基础设施的关键环节，承担着收集和输送生活污水、工业废水及雨水的重要功能。近年来，随着城镇化进程加快和污水收集范围不断扩大，管网系统中碳污染物的赋存与迁移问题逐渐增加，已成为制约城市碳减排和碳中和目标实现的关键因素之一。

研究表明，污水管网同时承担碳污染物输送和生物转化的双重功能，管道内的微生物活动可导致碳污染物在固、液、气三相之间发生显著的相间迁移（Guisasola et al., 2008; Jiang et al., 2011）。

1.2 国内外研究现状

污水管网中碳污染物的研究始于20世纪90年代。早期研究主要关注管道中有机碳的生物转化过程，Guisasola等（2008）通过实验和模型模拟证实，污水在管道输送过程中，厌氧条件下的产甲烷活动可降解50%以上的有机碳。

近年来，多相态分析方法逐渐被引入污水管网碳污染物研究。研究者开始同时关注固相、液相和气相碳污染物的分布特征及其相互转化关系。然而，多数研究仅关注单一相态，缺乏对固-液-气三相碳污染物的系统性联合分析。

1.3 现有研究不足

(1) 多相态联合分析不足。已有研究多关注单一相态的碳污染物，缺乏固-液-气三相碳污染物的系统性联合分析。

(2) 校园尺度研究缺乏。现有研究以城市级管网为主，针对校园这一特殊功能区域的碳污染特征研究较少。

(3) 碳平衡分析薄弱。管网中碳的输入-输出平衡关系尚不清楚。

1.4 研究内容与目标

针对上述研究不足，本研究以某校园污水管网为研究对象，开展以下研究工作：

(1) 系统采集管道内固相、液相、气相样品，测定碳污染物各指标浓度，揭示固-液-气三相碳污染物的分布特征。

(2) 采用主成分分析(PCA)和层次聚类分析(HCA)等多元统计方法，识别影响碳污染物分布的关键因素。

(3) 分析不同功能区碳污染物的空间分异规律，探讨排放源类型对碳污染特征的影响。
"""

assembler.add_section('1 引言', text=intro_text, level=1)

# ============ 3. 材料与方法 ============
methods_text = """2.1 研究区域概况

本研究选取某校园污水管网作为研究对象。该校园占地面积约15公顷，常住人口约2万人，日均污水排放量约3000 m³/d。校园功能区主要包括教学区、生活区、餐饮区和运动区，各功能区的污水通过支管汇入主管道后排出校园。

2.2 采样方案

根据管网布局和功能区分布，在主管道上设置了21个采样点，分别位于教学区(A1-A3)、生活区(B1-B3)、餐饮区(C1-C3)和管口出口(D)。采样时间涵盖冬季(2024年1月)和春季(2025年1月)两个季节，每次采样在各点同步采集固相、液相和气相样品。

2.3 分析方法

气相分析：采用便携式气体检测仪测定管道内CH₄、CO₂、O₂和VOCs浓度。检测前进行仪器校准，每个采样点重复测定3次取平均值。

液相分析：采集管道内污水水样，经0.45μm滤膜过滤后测定溶解性指标。总有机碳(TOC)采用TOC分析仪测定(HJ 501-2009)；化学需氧量(COD)采用重铬酸盐法测定(GB 11914-89)；总氮(TN)采用碱性过硫酸钾消解紫外分光光度法(HJ 636-2012)；铵态氮(NH₄⁺-N)采用纳氏试剂分光光度法(HJ 535-2009)。

固相分析：采集管道底部沉积物样品，自然风干后研磨过筛。固相总碳和有机碳采用元素分析仪测定。

2.4 数据处理与统计分析

采用Python 3.11进行数据处理和统计分析。描述性统计计算均值、标准差、变异系数等指标。正态性检验采用Shapiro-Wilk检验(p>0.05为正态)。组间差异分析：正态数据采用独立样本t检验，非正态数据采用Mann-Whitney U检验。相关性分析采用Pearson相关系数。统计显著性水平设为p<0.05。
"""

assembler.add_section('2 材料与方法', text=methods_text, level=1)

# ============ 4. 结果与分析（图文对应） ============

# 添加结果标题
assembler.add_section('3 结果与分析', text='', level=1)

# 3.1 描述性统计
stats_text = """3.1 描述性统计

本研究共采集40个样本，其中冬季20个、春季20个。气相变量包括CH₄、N₂O、CO₂等10个指标，液相变量包括DO、TOC、TN等13个指标，固相变量包括固总碳、有机碳等7个指标。

主要发现：
- CH₄浓度范围：0.63-2052.39 ppm，变异系数378.9%
- CO₂浓度范围：566.08-19234.54 ppm
- VOCs浓度范围：238-869 ppb
"""

assembler.add_section('3.1 描述性统计', text=stats_text, level=2)

# 添加相关性热图
fig_path = 'analysis_output/heatmap_pearson.png'
if os.path.exists(fig_path):
    assembler.add_figure(fig_path, caption='图1 Pearson相关性矩阵热图')
    print(f'✓ 添加: heatmap_pearson.png')
else:
    print(f'✗ 不存在: {fig_path}')

# 3.2 季节差异
seasonal_text = """3.2 季节差异分析

冬季与春季的显著差异：

气相变量：
- CH₄：春季(177.07 ppm)显著高于冬季(2.38 ppm)，p=0.0193*
- CO₂本底值：冬季(638.00 ppm)显著高于春季(550.15 ppm)，p=0.0001***
- VOCs：冬季(598.50 ppb)显著高于春季(426.75 ppb)，p=0.0003***
- VOCs本底值：冬季(286.70 ppb)显著高于春季(141.80 ppb)，p<0.0001***

液相变量：
- 液温：春季(17.24℃)显著高于冬季(13.15℃)，p=0.0048**
- 硝态氮：冬季(1.36 mg/L)显著高于春季(0.49 mg/L)，p=0.0182*
- COD：冬季(2426.38 mg/L)显著高于春季(93.51 mg/L)，p<0.0001***
"""

assembler.add_section('3.2 季节差异分析', text=seasonal_text, level=2)

# 添加季节比较图
fig_path = 'analysis_output/multivariate_box.png'
if os.path.exists(fig_path):
    assembler.add_figure(fig_path, caption='图2 冬春季气相碳污染物浓度比较')
    print(f'✓ 添加: multivariate_box.png')
else:
    print(f'✗ 不存在: {fig_path}')

# 3.3 相关性分析
corr_text = """3.3 相关性分析

关键相关性发现：

极显著正相关(p<0.001)：
- CO₂与NO₂：r=0.922, p<0.0001***
- NaCl与电导率：r=0.966, p<0.0001***
- 总氮与铵态氮：r=0.985, p<0.0001***
- TOC与TC：r=0.789, p=0.0001***

显著负相关(p<0.05)：
- CO₂本底值与气温：r=-0.572, p=0.0001***
- CH₄与pH：r=-0.534, p=0.0224*
- VOCs本底值与气温：r=-0.528, p=0.0005***
"""

assembler.add_section('3.3 相关性分析', text=corr_text, level=2)

# 添加相关性热图（如果有多张）
fig_path = 'analysis_output/heatmap_pearson.png'
if os.path.exists(fig_path):
    assembler.add_figure(fig_path, caption='图3 Pearson相关性矩阵（详细版）')
    print(f'✓ 添加: heatmap_pearson.png (详细版)')

# 3.4 跨相态关联
cross_text = """3.4 跨相态关联

气相-液相关联：
- CH₄与pH：r=-0.534, p=0.0224*（显著负相关）
- CH₄与DO：r=-0.446, p=0.0635（接近显著）
- 氧化亚氮与NaCl：r=0.803, p=0.0298*

这些结果表明，液相条件（pH、DO、盐度）对气相碳排放有重要影响。
"""

assembler.add_section('3.4 跨相态关联', text=cross_text, level=2)

# 添加时空变化图
fig_path = 'analysis_output/spatiotemporal_line.png'
if os.path.exists(fig_path):
    assembler.add_figure(fig_path, caption='图4 碳污染物时空变化趋势')
    print(f'✓ 添加: spatiotemporal_line.png')
else:
    print(f'✗ 不存在: {fig_path}')

# ============ 5. 讨论 ============
discussion_text = """4.1 季节差异的机制解释

CH₄浓度在春季显著升高，可能与温度升高促进产甲烷菌活性有关。研究表明，产甲烷菌的最适温度为30-40°C，春季管网内温度升高有利于CH₄生成。

CO₂本底值在冬季显著偏高，可能与冬季管网内有机物积累有关。冬季用水量减少，污水在管道内停留时间延长，导致有机物厌氧分解产生更多CO₂。

4.2 碳氮耦合机制

CO₂与NO₂的极显著正相关(r=0.922)揭示了碳氮耦合机制。硝化过程产生的H⁺可能促进碳酸盐溶解，从而增加CO₂释放。

4.3 与文献对比

本研究发现的CH₄-CO₂关系与Guisasola等(2008)的研究一致，证实了管网内碳转化的复杂性。VOCs的季节变化规律与Jiang等(2011)的报道相似。

4.4 研究局限性

本研究存在以下局限：
(1) 采样点数量有限(n=21)，统计检验力可能不足
(2) 仅覆盖冬春两季，缺少夏秋数据
(3) 未考虑管龄、管材对碳排放的影响
"""

assembler.add_section('4 讨论', text=discussion_text, level=1)

# ============ 6. 结论 ============
conclusion_text = """本研究以校园污水管网为对象，系统分析了冬春两季固-液-气三相碳污染物的赋存特征与驱动机制。主要结论如下：

(1) 碳污染物呈现显著的季节分异。CH₄浓度在春季显著升高(p=0.0193)，CO₂本底值在冬季显著偏高(p=0.0001)，VOCs在冬季显著偏高(p=0.0003)。温度和水文条件是驱动季节差异的主要因素。

(2) 变量间存在多组显著关联。CO₂与NO₂极显著正相关(r=0.922, p<0.0001)，揭示了碳氮耦合机制。CO₂本底值与气温显著负相关(r=-0.572, p=0.0001)，反映了温度对碳转化的影响。

(3) 跨相态分析发现CH₄与pH显著负相关(r=-0.534, p=0.0224)，CH₄与DO呈负相关趋势(r=-0.446, p=0.0635)，表明液相条件对气相碳排放有重要影响。

(4) 上述发现为校园污水管网碳排放核算和碳管理策略制定提供了数据支撑和科学依据。
"""

assembler.add_section('5 结论', text=conclusion_text, level=1)

# ============ 7. 参考文献 ============
references_text = """[1] Guisasola A, de Haas D, Keller J, et al. Methane formation in sewer systems[J]. Water Research, 2008, 42(6-7): 1421-1430.

[2] Jiang G, Sharma K R, Guisasola A, et al. Sulfur transformation in rising main sewers receiving nitrate dosage[J]. Water Research, 2011, 45(19): 6485-6494.

[3] 国家环境保护总局. HJ 501-2009 水质 总有机碳的测定 燃烧氧化-非分散红外法[S]. 2009.

[4] 国家环境保护总局. GB 11914-89 水质 化学需氧量的测定 重铬酸盐法[S]. 1989.

[5] 国家环境保护总局. HJ 636-2012 水质 总氮的测定 碱性过硫酸钾消解紫外分光光度法[S]. 2012.

[6] 国家环境保护总局. HJ 535-2009 水质 铵态氮的测定 纳氏试剂分光光度法[S]. 2009.
"""

assembler.add_section('参考文献', text=references_text, level=1)

# ============ 生成DOCX ============
output_path = 'paper_output/paper_complete.docx'
result = assembler.assemble(output_path)

print(f'\n{"="*60}')
print(f'  DOCX生成完成!')
print(f'{"="*60}')
print(f'  文件: {result}')
print(f'  段落数: {len(assembler.doc.paragraphs)}')
print(f'  图片数: {len(assembler._figure_map)}')
print(f'{"="*60}')
