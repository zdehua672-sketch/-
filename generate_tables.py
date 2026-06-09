# -*- coding: utf-8 -*-
"""Generate 4 tables for Cr(VI)-chlorinated hydrocarbon review paper"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.expanduser('~/Desktop/论文插图')
os.makedirs(OUT, exist_ok=True)


def table1_cr_speciation():
    """表1: Cr(III)/Cr(VI)赋存形态及环境条件"""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('off')

    headers = ['价态', '主要形态', '存在条件', '溶解性', '迁移性', '毒性', '典型浓度范围']
    data = [
        ['Cr(VI)', 'HCrO₄⁻', 'pH<6.5, 高Eh', '高', '高', '强致癌', '0.01-500 mg/L'],
        ['Cr(VI)', 'CrO₄⁻⁸', 'pH>6.5, 高Eh', '高', '高', '强致癌', '0.01-3400 mg/L'],
        ['Cr(VI)', 'Cr₂O₇⁻⁸', 'pH<3, 高浓度', '高', '高', '强致癌', '局部>1000 mg/L'],
        ['Cr(III)', 'Cr³⁺', 'pH<4, 低Eh', '中', '中', '低', '0.1-50 mg/L'],
        ['Cr(III)', 'Cr(OH)²⁺', 'pH 4-6', '低', '低', '低', '-'],
        ['Cr(III)', 'Cr(OH)₃↓', 'pH 5.5-12, 低Eh', '极低', '极低', '极低', '-'],
        ['Cr(III)', 'Cr(OH)₄⁻', 'pH>10', '低', '低', '低', '-'],
        ['Cr(III)', 'Cr-Fe共沉淀', 'Fe(III)共存', '极低', '极低', '极低', '-'],
    ]

    col_widths = [0.08, 0.13, 0.17, 0.09, 0.09, 0.1, 0.17]
    table = ax.table(cellText=data, colLabels=headers, loc='center',
                     cellLoc='center', colWidths=col_widths)

    # Style
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.0)

    # Header style
    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor('#1565C0')
        cell.set_text_props(color='white', fontweight='bold', fontsize=11)

    # Color rows by Cr(VI) vs Cr(III)
    for i in range(1, len(data)+1):
        for j in range(len(headers)):
            cell = table[i, j]
            if data[i-1][0] == 'Cr(VI)':
                cell.set_facecolor('#FFEBEE')
            else:
                cell.set_facecolor('#E8F5E9')

    ax.set_title('表1 Cr(III)/Cr(VI)赋存形态及环境条件', fontsize=16,
                 fontweight='bold', pad=20)

    fig.savefig(os.path.join(OUT, '表1_Cr赋存形态及环境条件.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '表1_Cr赋存形态及环境条件.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("表1 done")


def table2_site_sources():
    """表2: Cr(VI)-氯代烃复合污染典型场地来源与污染特征"""
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.axis('off')

    headers = ['场地类型', 'Cr(VI)来源', '氯代烃来源', 'Cr(VI)浓度\n(mg/L)', 'TCE/PCE浓度\n(mg/L)',
               '污染深度\n(m)', '修复难度']

    data = [
        ['电镀厂', '镀铬废液\n铬酸雾排放', '脱脂清洗\nTCE/PCE', '10-500', '5-200', '3-15', '高'],
        ['铬盐制造', '铬渣渗滤\n废水排放', '设备清洗\n脱脂溶剂', '100-3400', '1-50', '5-20', '极高'],
        ['金属表面\n处理厂', '钝化液\n铬酸盐处理', '脱脂/清洗\n三氯乙烯', '5-200', '10-500', '2-10', '高'],
        ['印染/制革', '铬鞣剂\n含铬染料', '干洗溶剂\n脱脂剂', '1-100', '0.5-50', '2-8', '中-高'],
        ['化工厂', '催化剂\n含铬废物', '有机合成\n溶剂残留', '50-1000', '50-2000', '5-30', '极高'],
        ['矿山/冶炼', '矿渣堆存\n尾矿渗滤', '选矿药剂\n设备清洗', '20-500', '1-100', '3-25', '高'],
    ]

    col_widths = [0.11, 0.14, 0.14, 0.11, 0.12, 0.1, 0.09]
    table = ax.table(cellText=data, colLabels=headers, loc='center',
                     cellLoc='center', colWidths=col_widths)

    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 2.2)

    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor('#E65100')
        cell.set_text_props(color='white', fontweight='bold', fontsize=10)

    # Alternate row colors
    for i in range(1, len(data)+1):
        for j in range(len(headers)):
            cell = table[i, j]
            if i % 2 == 0:
                cell.set_facecolor('#FFF3E0')
            else:
                cell.set_facecolor('#FFF8E1')

    ax.set_title('表2 Cr(VI)-氯代烃复合污染典型场地来源与污染特征', fontsize=16,
                 fontweight='bold', pad=20)

    fig.savefig(os.path.join(OUT, '表2_典型场地来源与污染特征.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '表2_典型场地来源与污染特征.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("表2 done")


def table3_tech_comparison():
    """表3: 不同修复技术在Cr(VI)-氯代烃复合污染中的适用性比较"""
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.axis('off')

    headers = ['技术类型', '主要作用目标', '核心机制', '适用条件', '主要限制',
               '研究/应用阶段', '工程定位']

    data = [
        ['MNA/\n监测自然衰减', '低浓度复合\n污染羽', '自然降解\n稀释/吸附', '低浓度、\n非敏感区', '周期长\n不可控', '工程应用', '后端长期\n监控'],
        ['铁基还原\n(ZVI/nZVI)', 'Cr(VI)快速\n还原固定', 'Fe⁰提供电子\nCr(VI)→Cr(III)', '中高浓度\nCr(VI)优先', '材料钝化\n脱氯受限', '研究充分\n大量应用', '前端快速\n降铬'],
        ['铁基氧化-\n还原耦合', 'Cr(VI)+TCE\n同步去除', 'Fe活化PS/PMS\n氧化+还原', '复合污染\n中高浓度', '氧化剂输运\n副反应', '研究活跃\n中试阶段', '中段强化\n转化'],
        ['电化学/\n生物电化学', '复合污染\n深度处理', '电子定向转移\n微生物协同', '导电性较好\n场地', '电极布设\n能耗高', '实验室-\n中试', '重点污染\n区强化'],
        ['微生物强化\n修复', '氯代烃\n深度脱氯', '功能菌降解\n共代谢', '厌氧环境\n营养充足', 'Cr毒性抑制\nVC积累', '研究活跃\n部分应用', '中后段\n深度脱氯'],
        ['PRB', '污染羽\n拦截处理', '反应墙拦截\n原位反应', '水力梯度\n明确', '渗透性变化\n寿命有限', '工程应用', '中游拦截'],
        ['注入修复', '源区高浓度\n快速处理', '注入反应材料\n原位修复', '源区可及\n地层渗透', '分布不均\n二次污染', '工程应用', '前端源区'],
        ['多技术联合', '复杂场地\n全流程处理', '分阶段组合\n协同增效', '大型复杂\n污染场地', '成本高\n管理复杂', '研究示范', '全流程\n覆盖'],
    ]

    col_widths = [0.11, 0.11, 0.13, 0.11, 0.11, 0.11, 0.11]
    table = ax.table(cellText=data, colLabels=headers, loc='center',
                     cellLoc='center', colWidths=col_widths)

    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 2.4)

    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor('#2E7D32')
        cell.set_text_props(color='white', fontweight='bold', fontsize=9.5)

    for i in range(1, len(data)+1):
        for j in range(len(headers)):
            cell = table[i, j]
            if i % 2 == 0:
                cell.set_facecolor('#E8F5E9')
            else:
                cell.set_facecolor('#F1F8E9')

    ax.set_title('表3 不同修复技术在Cr(VI)-氯代烃复合污染中的适用性比较', fontsize=16,
                 fontweight='bold', pad=20)

    fig.savefig(os.path.join(OUT, '表3_修复技术适用性比较.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '表3_修复技术适用性比较.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("表3 done")


def table4_zvi_modifications():
    """表4: 改性ZVI/nZVI材料作用机制与局限比较"""
    fig, ax = plt.subplots(figsize=(15, 8))
    ax.axis('off')

    headers = ['改性类型', '代表材料/方法', '核心机制', '对Cr(VI)的作用', '对氯代烃的作用',
               '复合污染中的限制', '工程适用性']

    data = [
        ['双金属改性', 'Pd/Fe, Ni/Fe\nCu/Fe', '微电池效应\n促进H*生成\n降低活化能', '加速Cr(VI)\n还原', '促进加氢脱氯\n提高脱氯速率', 'Pd中毒\nCr沉淀覆盖\n成本高', '中-高\n实验室/中试'],
        ['载体负载', '生物炭/Fe\n活性炭/Fe\n膨润土/Fe', '分散ZVI\n吸附富集\n增加接触', '协同吸附+\n还原固定', '改善接触\n间接促进', '长期吸附饱和\n载体堵塞', '高\n工程应用多'],
        ['表面包覆', 'CMC-nZVI\nCMCS-nZVI', '增强分散性\n抗团聚\n改善输运', '提高反应\n活性面积', '改善迁移\n到达污染区', '地下水中\n稳定性不足', '中\n中试阶段'],
        ['硫化改性', 'FeS/ZVI\nS-nZVI', 'FeSₓ壳层\n电子选择性↑\n抗钝化', '选择性还原\nCr(VI)优先', '抑制析氢\n电子定向', '过度硫化失活\n长期稳定性', '高\n研究活跃'],
        ['非金属掺杂', 'N-ZVI\nB-ZVI\nP-ZVI', '调控电子结构\n活性位点↑\n催化效率↑', '提高还原\n活性', '协同促进\n脱氯', '掺杂均匀性\n规模化困难', '中\n实验室阶段'],
    ]

    col_widths = [0.1, 0.12, 0.14, 0.13, 0.13, 0.16, 0.1]
    table = ax.table(cellText=data, colLabels=headers, loc='center',
                     cellLoc='center', colWidths=col_widths)

    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 2.8)

    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor('#C62828')
        cell.set_text_props(color='white', fontweight='bold', fontsize=9.5)

    for i in range(1, len(data)+1):
        for j in range(len(headers)):
            cell = table[i, j]
            if i % 2 == 0:
                cell.set_facecolor('#FFEBEE')
            else:
                cell.set_facecolor('#FFCDD2')

    ax.set_title('表4 改性ZVI/nZVI材料作用机制与局限比较', fontsize=16,
                 fontweight='bold', pad=20)

    fig.savefig(os.path.join(OUT, '表4_改性ZVI_nZVI材料比较.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '表4_改性ZVI_nZVI材料比较.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("表4 done")


if __name__ == '__main__':
    print("Generating tables...")
    table1_cr_speciation()
    table2_site_sources()
    table3_tech_comparison()
    table4_zvi_modifications()
    print(f"\nAll 4 tables saved to: {OUT}")
