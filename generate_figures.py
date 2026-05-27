# -*- coding: utf-8 -*-
"""Generate 9 figures for Cr(VI)-chlorinated hydrocarbon review paper"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import os

# Global font settings
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'

OUT = os.path.expanduser('~/Desktop/论文插图')
os.makedirs(OUT, exist_ok=True)


def fig1_eh_ph():
    """图1: Cr在地下水Eh-pH条件下的主要赋存形态及迁移风险示意图"""
    fig, ax = plt.subplots(figsize=(10, 7))

    # Water stability lines
    pH = np.linspace(0, 14, 200)
    Eh_upper = 1.23 - 0.059 * pH  # O2/H2O line
    Eh_lower = -0.059 * pH         # H2/H2O line
    ax.plot(pH, Eh_upper, 'k--', linewidth=1, alpha=0.5, label='水稳定区边界')
    ax.plot(pH, Eh_lower, 'k--', linewidth=1, alpha=0.5)
    ax.fill_between(pH, Eh_lower, Eh_upper, alpha=0.05, color='blue')

    # Cr speciation regions
    # Cr(VI) region - high Eh
    cr6_vertices = np.array([
        [0, 0.9], [0, 1.5], [14, 0.6], [14, -0.1],
        [8, -0.1], [6, 0.2], [2, 0.6]
    ])
    cr6_patch = patches.Polygon(cr6_vertices, closed=True, alpha=0.25,
                                 facecolor='#FF4444', edgecolor='#CC0000', linewidth=2)
    ax.add_patch(cr6_patch)

    # Cr(III) region - low Eh, neutral pH
    cr3_vertices = np.array([
        [4, -0.5], [4, 0.1], [6, 0.2], [8, -0.1],
        [10, -0.3], [10, -0.8], [6, -0.8]
    ])
    cr3_patch = patches.Polygon(cr3_vertices, closed=True, alpha=0.25,
                                 facecolor='#44AA44', edgecolor='#228822', linewidth=2)
    ax.add_patch(cr3_patch)

    # Cr(OH)3 precipitation region
    cr_oh3_vertices = np.array([
        [7, -0.8], [6, -0.6], [6, 0.2], [8, -0.1],
        [10, -0.3], [10, -0.8]
    ])
    cr_oh3_patch = patches.Polygon(cr_oh3_vertices, closed=True, alpha=0.15,
                                    facecolor='#8B4513', edgecolor='#666666', linewidth=1, linestyle='--')
    ax.add_patch(cr_oh3_patch)

    # Labels for Cr(VI) species
    ax.text(1.5, 1.1, 'HCrO$_4$$^-$', fontsize=13, color='#CC0000', fontweight='bold',
            ha='center', style='italic')
    ax.text(3.5, 0.7, 'CrO$_4$$^{2-}$', fontsize=13, color='#CC0000', fontweight='bold',
            ha='center', style='italic')
    ax.text(6, 0.35, 'Cr$_2$O$_7$$^{2-}$', fontsize=12, color='#CC0000', fontweight='bold',
            ha='center', style='italic')

    # Labels for Cr(III) species
    ax.text(7, -0.2, 'Cr(OH)$_3$↓', fontsize=13, color='#228822', fontweight='bold',
            ha='center')
    ax.text(5, -0.5, 'Cr(OH)$_2$$^+$', fontsize=12, color='#228822', ha='center')
    ax.text(9, -0.5, 'Cr(OH)$_4$$^-$', fontsize=12, color='#228822', ha='center')

    # Migration risk annotation
    ax.annotate('高迁移/高毒性区\n（Cr(VI)阴离子形态）', xy=(3, 0.8), fontsize=11,
                color='#CC0000', fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFEEEE', edgecolor='#CC0000', alpha=0.8))

    ax.annotate('低迁移/低毒性区\n（Cr(III)沉淀或共沉淀）', xy=(7, -0.6), fontsize=11,
                color='#228822', fontweight='bold', ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#EEFFEE', edgecolor='#228822', alpha=0.8))

    # Fe-Cr co-precipitation
    ax.annotate('Fe-Cr共沉淀', xy=(9, -0.15), fontsize=10, color='#8B4513',
                xytext=(11, 0.2), ha='center',
                arrowprops=dict(arrowstyle='->', color='#8B4513', lw=1.5))

    # Typical groundwater range box
    gw_rect = patches.Rectangle((5.5, -0.3), 3.5, 0.8, linewidth=2,
                                  edgecolor='blue', facecolor='none', linestyle=':', alpha=0.6)
    ax.add_patch(gw_rect)
    ax.text(7.25, 0.55, '典型地下水\nEh-pH范围', fontsize=10, color='blue',
            ha='center', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='blue', alpha=0.8))

    # Reduction arrow
    ax.annotate('', xy=(5, -0.3), xytext=(5, 0.5),
                arrowprops=dict(arrowstyle='->', color='purple', lw=2.5))
    ax.text(4.3, 0.1, '还原', fontsize=12, color='purple', fontweight='bold', rotation=90)

    ax.set_xlabel('pH', fontsize=14)
    ax.set_ylabel('Eh (V vs SHE)', fontsize=14)
    ax.set_title('图1 Cr在地下水Eh-pH条件下的主要赋存形态及迁移风险示意图',
                 fontsize=15, fontweight='bold', pad=15)
    ax.set_xlim(0, 14)
    ax.set_ylim(-1.0, 1.5)
    ax.grid(True, alpha=0.2)
    ax.set_aspect(4)

    # Legend
    legend_elements = [
        patches.Patch(facecolor='#FF4444', alpha=0.4, label='Cr(VI)形态区（高迁移性）'),
        patches.Patch(facecolor='#44AA44', alpha=0.4, label='Cr(III)形态区（低迁移性）'),
        patches.Patch(facecolor='#8B4513', alpha=0.3, label='Cr(OH)₃/Fe-Cr共沉淀区'),
        plt.Line2D([0], [0], color='blue', linestyle=':', linewidth=2, label='典型地下水Eh-pH范围'),
        plt.Line2D([0], [0], color='black', linestyle='--', linewidth=1, label='水稳定区边界'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.9)

    plt.tight_layout()
    fig.savefig(os.path.join(OUT, '图1_Cr_Eh-pH_赋存形态图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图1_Cr_Eh-pH_赋存形态图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图1 done")


def fig2_source_migration():
    """图2: Cr(VI)-氯代烃复合污染地下水的典型来源、共存场景及迁移转化示意图"""
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Four layers from top to bottom
    # Layer 1: Surface industrial sources (y=7.5-10)
    ax.add_patch(patches.Rectangle((0.5, 7.5), 11, 2.5, facecolor='#FFF3E0', edgecolor='#E65100', linewidth=2, alpha=0.7))
    ax.text(6, 9.5, '地表工业源区', fontsize=16, fontweight='bold', ha='center', color='#E65100')

    # Industrial elements
    factories = [(1.5, 8.5, '电镀车间'), (4, 8.5, '金属表面处理'), (6.5, 8.5, '脱脂清洗区'), (9, 8.5, '储罐/废液池')]
    for x, y, label in factories:
        ax.add_patch(patches.FancyBboxPatch((x-0.8, y-0.5), 1.8, 1.2,
                     boxstyle="round,pad=0.1", facecolor='#FFE0B2', edgecolor='#E65100', linewidth=1.5))
        ax.text(x+0.1, y+0.1, label, fontsize=9, ha='center', fontweight='bold')

    # Cr(VI) source labels
    ax.text(2.5, 7.8, 'Cr(VI)来源：电镀废液、铬渣渗滤', fontsize=9, color='#1565C0', ha='center',
            bbox=dict(boxstyle='round', facecolor='#E3F2FD', alpha=0.8))
    # Chlorinated hydrocarbon source labels
    ax.text(8.5, 7.8, '氯代烃来源：脱脂清洗、有机溶剂', fontsize=9, color='#C62828', ha='center',
            bbox=dict(boxstyle='round', facecolor='#FFEBEE', alpha=0.8))

    # Arrows from sources down
    for x in [2.5, 8.5]:
        ax.annotate('', xy=(x, 7.5), xytext=(x, 7.0),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=2))

    # Layer 2: Vadose zone (y=5.5-7.5)
    ax.add_patch(patches.Rectangle((0.5, 5.5), 11, 2, facecolor='#FFF8E1', edgecolor='#F9A825', linewidth=2, alpha=0.7))
    ax.text(6, 7.2, '包气带', fontsize=16, fontweight='bold', ha='center', color='#F9A825')

    # Cr(VI) leaching
    ax.annotate('', xy=(2.5, 5.8), xytext=(2.5, 6.8),
                arrowprops=dict(arrowstyle='->', color='#1565C0', lw=2))
    ax.text(1.2, 6.3, 'Cr(VI)随渗滤液\n下移', fontsize=8, color='#1565C0', ha='center')

    # DNAPL percolation
    ax.annotate('', xy=(8.5, 5.8), xytext=(8.5, 6.8),
                arrowprops=dict(arrowstyle='->', color='#C62828', lw=2))
    ax.text(10, 6.3, 'DNAPL形式\n下渗', fontsize=8, color='#C62828', ha='center')

    # Layer 3: Saturated zone (y=2.5-5.5)
    ax.add_patch(patches.Rectangle((0.5, 2.5), 11, 3, facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2, alpha=0.5))
    ax.text(6, 5.2, '含水层', fontsize=16, fontweight='bold', ha='center', color='#1565C0')

    # Cr(VI) plume - blue/purple ellipse
    cr_plume = patches.Ellipse((3.5, 4), 4, 1.5, alpha=0.3, facecolor='#7B1FA2', edgecolor='#4A148C', linewidth=2)
    ax.add_patch(cr_plume)
    ax.text(3.5, 4.2, 'Cr(VI)污染羽', fontsize=10, ha='center', fontweight='bold', color='#4A148C')
    ax.text(3.5, 3.7, '(溶解相)', fontsize=9, ha='center', color='#4A148C')

    # TCE/PCE DNAPL residual - red/orange
    dnapl_patch = patches.Ellipse((7, 4.2), 2.5, 1, alpha=0.3, facecolor='#FF5722', edgecolor='#D84315', linewidth=2)
    ax.add_patch(dnapl_patch)
    ax.text(7, 4.4, 'TCE/PCE', fontsize=10, ha='center', fontweight='bold', color='#D84315')
    ax.text(7, 3.9, 'DNAPL残留', fontsize=9, ha='center', color='#D84315')

    # Dissolved plume for chlorinated HC
    dis_plume = patches.Ellipse((9, 3.5), 3, 1.2, alpha=0.2, facecolor='#FF8A65', edgecolor='#E64A19', linewidth=1.5, linestyle='--')
    ax.add_patch(dis_plume)
    ax.text(9, 3.5, '溶解相\n污染羽', fontsize=9, ha='center', color='#E64A19')

    # Co-contaminated zone
    overlap = patches.Ellipse((5.5, 4), 2.5, 1.2, alpha=0.4, facecolor='#FFD54F', edgecolor='#F57F17', linewidth=2.5)
    ax.add_patch(overlap)
    ax.text(5.5, 4.2, '复合', fontsize=11, ha='center', fontweight='bold', color='#E65100')
    ax.text(5.5, 3.7, '污染区', fontsize=11, ha='center', fontweight='bold', color='#E65100')

    # Groundwater flow arrow
    ax.annotate('', xy=(11, 4), xytext=(0.8, 4),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2.5, connectionstyle='arc3,rad=0'))
    ax.text(6, 2.7, '地下水流向 →', fontsize=11, color='blue', fontweight='bold', ha='center')

    # Interaction annotations
    ax.annotate('电子竞争\n微生物抑制', xy=(5.5, 3.2), fontsize=9, color='#6A1B9A',
                xytext=(3, 2.2), ha='center',
                arrowprops=dict(arrowstyle='->', color='#6A1B9A', lw=1.5))

    ax.annotate('耦合氧化还原\n环境', xy=(7, 3.2), fontsize=9, color='#6A1B9A',
                xytext=(9, 2.2), ha='center',
                arrowprops=dict(arrowstyle='->', color='#6A1B9A', lw=1.5))

    # Layer 4: Confining layer (y=1-2.5)
    ax.add_patch(patches.Rectangle((0.5, 1), 11, 1.5, facecolor='#EFEBE9', edgecolor='#795548', linewidth=2, alpha=0.7))
    ax.text(6, 2.2, '隔水层/低渗透层', fontsize=16, fontweight='bold', ha='center', color='#795548')
    ax.text(6, 1.5, 'DNAPL池化区 — 残余相长期释放', fontsize=11, ha='center', color='#795548',
            bbox=dict(boxstyle='round', facecolor='#FFF3E0', alpha=0.8))

    # DNAPL pooling arrows
    ax.annotate('', xy=(7, 2.0), xytext=(7, 2.5),
                arrowprops=dict(arrowstyle='->', color='#D84315', lw=2, linestyle='--'))
    ax.annotate('', xy=(8.5, 2.0), xytext=(8.5, 2.5),
                arrowprops=dict(arrowstyle='->', color='#D84315', lw=2, linestyle='--'))

    # Title
    ax.set_title('图2 Cr(VI)-氯代烃复合污染地下水的典型来源、共存场景及\n迁移转化示意图',
                 fontsize=15, fontweight='bold', pad=15)

    # Legend
    legend_elements = [
        patches.Patch(facecolor='#7B1FA2', alpha=0.4, label='Cr(VI)污染羽（蓝色/紫色）'),
        patches.Patch(facecolor='#FF5722', alpha=0.4, label='氯代烃污染羽（红色/橙色）'),
        patches.Patch(facecolor='#FFD54F', alpha=0.5, label='复合污染区（两者重叠）'),
        plt.Line2D([0], [0], color='blue', linewidth=2, label='地下水流向'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=9, framealpha=0.9)

    fig.savefig(os.path.join(OUT, '图2_复合污染来源与迁移转化图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图2_复合污染来源与迁移转化图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图2 done")


def fig3_interaction_mechanism():
    """图3: Cr(VI)-氯代烃复合污染地下水中关键相互作用及修复受限机制示意图"""
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Center circle
    center = plt.Circle((6, 5), 1.5, facecolor='#E8EAF6', edgecolor='#283593', linewidth=3)
    ax.add_patch(center)
    ax.text(6, 5.3, 'Cr(VI)-氯代烃', fontsize=12, ha='center', fontweight='bold', color='#283593')
    ax.text(6, 4.8, '复合污染修复体系', fontsize=12, ha='center', fontweight='bold', color='#283593')
    ax.text(6, 4.3, '(ZVI/nZVI + 微生物)', fontsize=9, ha='center', color='#5C6BC0')

    # Four quadrants
    # Top-left: Electron competition
    box1 = FancyBboxPatch((0.5, 6.5), 4, 3, boxstyle="round,pad=0.2",
                            facecolor='#FFF3E0', edgecolor='#E65100', linewidth=2)
    ax.add_patch(box1)
    ax.text(2.5, 9.1, '电子竞争', fontsize=14, ha='center', fontweight='bold', color='#E65100')
    items1 = ['Cr(VI)优先接受电子', 'Fe⁰/Fe(II)被优先消耗', '有机碳/H₂电子供体不足',
              'TCE/PCE脱氯电子匮乏']
    for i, item in enumerate(items1):
        ax.text(1, 8.5 - i*0.55, f'• {item}', fontsize=9, color='#BF360C')

    # Top-right: Surface passivation
    box2 = FancyBboxPatch((7.5, 6.5), 4, 3, boxstyle="round,pad=0.2",
                            facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(box2)
    ax.text(9.5, 9.1, '表面钝化', fontsize=14, ha='center', fontweight='bold', color='#2E7D32')
    items2 = ['Cr(VI)还原→Cr(III)', 'Cr(OH)₃、Fe(OH)₃沉淀', 'Cr-Fe共沉淀覆盖表面',
              '阻碍电子传递通道']
    for i, item in enumerate(items2):
        ax.text(8, 8.5 - i*0.55, f'• {item}', fontsize=9, color='#1B5E20')

    # Bottom-left: Microbial toxicity
    box3 = FancyBboxPatch((0.5, 0.5), 4, 3, boxstyle="round,pad=0.2",
                            facecolor='#FCE4EC', edgecolor='#C62828', linewidth=2)
    ax.add_patch(box3)
    ax.text(2.5, 3.1, '微生物毒性抑制', fontsize=14, ha='center', fontweight='bold', color='#C62828')
    items3 = ['Cr(VI)诱导ROS生成', '脱氯菌和产氢菌受损', 'VC→乙烯转化受阻',
              '微生物群落结构失衡']
    for i, item in enumerate(items3):
        ax.text(1, 2.5 - i*0.55, f'• {item}', fontsize=9, color='#B71C1C')

    # Bottom-right: Redox coupling
    box4 = FancyBboxPatch((7.5, 0.5), 4, 3, boxstyle="round,pad=0.2",
                            facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(box4)
    ax.text(9.5, 3.1, '氧化还原环境耦合', fontsize=14, ha='center', fontweight='bold', color='#1565C0')
    items4 = ['pH、Eh协同调控', 'Fe(II)浓度动态变化', '硫化物/有机质干扰',
              'Cr还原与脱氯路径耦合']
    for i, item in enumerate(items4):
        ax.text(8, 2.5 - i*0.55, f'• {item}', fontsize=9, color='#0D47A1')

    # Arrows from quadrants to center
    for (sx, sy, ex, ey) in [(4.3, 6.8, 5, 6), (7.7, 6.8, 7, 6),
                               (4.3, 3.2, 5, 4), (7.7, 3.2, 7, 4)]:
        ax.annotate('', xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=2))

    # Bottom output
    output_box = FancyBboxPatch((1.5, -0.2), 9, 0.9, boxstyle="round,pad=0.1",
                                  facecolor='#FFEBEE', edgecolor='#C62828', linewidth=2)
    ax.add_patch(output_box)
    outputs = '修复受限结果：  Cr(VI)优先还原  |  氯代烃深度脱氯受阻  |  材料活性下降  |  修复效率失衡'
    ax.text(6, 0.2, outputs, fontsize=10, ha='center', fontweight='bold', color='#C62828')

    # Strategy annotation
    ax.text(6, -0.8, '→ 需要协同修复策略', fontsize=12, ha='center', fontweight='bold',
            color='#1B5E20', style='italic',
            bbox=dict(boxstyle='round', facecolor='#E8F5E9', edgecolor='#2E7D32'))

    ax.set_title('图3 Cr(VI)-氯代烃复合污染地下水中关键相互作用及\n修复受限机制示意图',
                 fontsize=15, fontweight='bold', pad=20)

    fig.savefig(os.path.join(OUT, '图3_相互作用与修复受限机制图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图3_相互作用与修复受限机制图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图3 done")


def fig4_tech_framework():
    """图4: Cr(VI)-氯代烃复合污染地下水修复技术路径与工程定位框架图"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Left: demand
    demand_box = FancyBboxPatch((0.3, 1), 3, 7, boxstyle="round,pad=0.2",
                                  facecolor='#FFF3E0', edgecolor='#E65100', linewidth=2)
    ax.add_patch(demand_box)
    ax.text(1.8, 7.6, '复合污染治理需求', fontsize=13, ha='center', fontweight='bold', color='#E65100')
    demands = ['Cr(VI)快速降毒', '氯代烃持续脱氯', '污染羽拦截', '长期风险控制']
    colors_d = ['#C62828', '#1565C0', '#4A148C', '#2E7D32']
    for i, (d, c) in enumerate(zip(demands, colors_d)):
        ax.add_patch(patches.FancyBboxPatch((0.6, 6.3-i*1.2), 2.4, 0.8, boxstyle="round,pad=0.1",
                      facecolor='white', edgecolor=c, linewidth=1.5))
        ax.text(1.8, 6.7-i*1.2, d, fontsize=10, ha='center', fontweight='bold', color=c)

    # Center: five basic technologies
    tech_box = FancyBboxPatch((4, 0.5), 6, 8, boxstyle="round,pad=0.2",
                                facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(tech_box)
    ax.text(7, 8.1, '五类基础修复技术', fontsize=13, ha='center', fontweight='bold', color='#2E7D32')

    techs = [
        ('自然衰减/监测\n自然衰减(MNA)', '低浓度、长周期'),
        ('铁基还原修复\nZVI/nZVI', 'Cr(VI)快速还原固定'),
        ('铁基氧化–还原\n耦合(PS/PMS)', '同步氧化脱氯+还原降铬'),
        ('电化学/生物\n电化学(BES)', '电子精准调控'),
        ('微生物强化修复\n功能菌群', '深度脱氯、长效治理'),
    ]
    for i, (tech, desc) in enumerate(techs):
        y = 7.2 - i*1.4
        ax.add_patch(patches.FancyBboxPatch((4.3, y-0.5), 2.8, 1.1, boxstyle="round,pad=0.1",
                      facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=1.5))
        ax.text(5.7, y+0.15, tech, fontsize=9, ha='center', fontweight='bold', color='#1B5E20')
        ax.add_patch(patches.FancyBboxPatch((7.3, y-0.5), 2.5, 1.1, boxstyle="round,pad=0.1",
                      facecolor='#F1F8E9', edgecolor='#689F38', linewidth=1))
        ax.text(8.55, y, desc, fontsize=8, ha='center', color='#33691E')

    # Arrows from demand to tech
    for i in range(4):
        ax.annotate('', xy=(4.1, 7.2-i*1.4), xytext=(3.2, 6.7-i*1.2),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))

    # Right: engineering modes
    eng_box = FancyBboxPatch((10.7, 1), 3, 7, boxstyle="round,pad=0.2",
                               facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(eng_box)
    ax.text(12.2, 7.6, '工程化模式', fontsize=13, ha='center', fontweight='bold', color='#1565C0')
    eng_modes = ['PRB', '注入修复', '原位反应带', '多技术联合', '长期监测']
    for i, mode in enumerate(eng_modes):
        ax.add_patch(patches.FancyBboxPatch((11, 6.3-i*1.1), 2.4, 0.8, boxstyle="round,pad=0.1",
                      facecolor='#BBDEFB', edgecolor='#1565C0', linewidth=1.5))
        ax.text(12.2, 6.7-i*1.1, mode, fontsize=10, ha='center', fontweight='bold', color='#0D47A1')

    # Arrows from tech to engineering
    for i in range(5):
        ax.annotate('', xy=(10.8, 7.2-i*1.4), xytext=(10.2, 7.2-i*1.4),
                    arrowprops=dict(arrowstyle='->', color='blue', lw=1.5))

    # Bottom: phased configuration
    phases_box = FancyBboxPatch((4, -0.3), 6, 1.2, boxstyle="round,pad=0.1",
                                  facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(phases_box)
    ax.text(7, 0.5, '阶段化配置', fontsize=12, ha='center', fontweight='bold', color='#7B1FA2')
    phases = ['前端快速降毒', '中段强化转化', '后端长期维持']
    for i, phase in enumerate(phases):
        ax.text(5.5+i*1.8, 0.1, phase, fontsize=9, ha='center', color='#4A148C',
                bbox=dict(boxstyle='round', facecolor='#E1BEE7', alpha=0.7))

    # Arrows from tech to phases
    ax.annotate('', xy=(7, 0.7), xytext=(7, 0.9),
                arrowprops=dict(arrowstyle='->', color='#7B1FA2', lw=2))

    ax.set_title('图4 Cr(VI)-氯代烃复合污染地下水修复技术路径与工程定位框架图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图4_修复技术路径与工程定位框架图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图4_修复技术路径与工程定位框架图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图4 done")


def fig5_zvi_modification():
    """图5: 改性ZVI/nZVI修复Cr(VI)-氯代烃复合污染的作用机制示意图"""
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Center ZVI particle
    center = plt.Circle((6.5, 5), 1.2, facecolor='#B0BEC5', edgecolor='#37474F', linewidth=3)
    ax.add_patch(center)
    ax.text(6.5, 5.2, 'ZVI/nZVI', fontsize=14, ha='center', fontweight='bold', color='#263238')
    ax.text(6.5, 4.7, '颗粒', fontsize=12, ha='center', fontweight='bold', color='#263238')

    # Five modification types around the center
    modifications = [
        (2.5, 8.5, '双金属改性', 'Pd/Ni/Cu + Fe', '微电池效应\n促进电子转移\nH*生成', '#E8EAF6', '#283593'),
        (10.5, 8.5, '载体负载', '生物炭/活性炭\n膨润土', '增强分散\n吸附富集\n迁移性↑', '#E8F5E9', '#2E7D32'),
        (2.5, 2, '表面包覆', 'CMC/CMCS', '增强分散性\n输运性↑\n抗团聚', '#FFF3E0', '#E65100'),
        (10.5, 2, '硫化改性', 'FeSₓ壳层', '电子选择性↑\n疏水性↑\n抗钝化', '#FCE4EC', '#C62828'),
        (6.5, 9, '非金属掺杂', 'N/P/B', '调控电子结构\n活性位点\n催化效率↑', '#F3E5F5', '#7B1FA2'),
    ]

    for x, y, title, subtitle, effects, bg_color, edge_color in modifications:
        # Box
        box = FancyBboxPatch((x-1.5, y-0.8), 3, 1.6, boxstyle="round,pad=0.15",
                               facecolor=bg_color, edgecolor=edge_color, linewidth=2)
        ax.add_patch(box)
        ax.text(x, y+0.45, title, fontsize=11, ha='center', fontweight='bold', color=edge_color)
        ax.text(x, y-0.05, subtitle, fontsize=8, ha='center', color=edge_color)
        # Arrow to center
        angle = np.arctan2(5-y, 6.5-x)
        sx = x - 1.5*np.cos(angle) if x != 6.5 else x
        sy = y - 0.8*np.sin(angle) if y != 9 else y - 0.8
        ex = 6.5 + 1.2*np.cos(angle)
        ey = 5 + 1.2*np.sin(angle)
        ax.annotate('', xy=(ex, ey), xytext=(x, y-0.8),
                    arrowprops=dict(arrowstyle='->', color=edge_color, lw=2))

    # Right side: Output pathways
    # Cr(VI) reduction pathway
    cr_box = FancyBboxPatch((9.5, 4), 3.3, 1.8, boxstyle="round,pad=0.15",
                              facecolor='#FFEBEE', edgecolor='#C62828', linewidth=2)
    ax.add_patch(cr_box)
    ax.text(11.15, 5.4, 'Cr(VI)还原路径', fontsize=10, ha='center', fontweight='bold', color='#C62828')
    ax.text(11.15, 4.9, 'Cr(VI) → Cr(III)', fontsize=10, ha='center', color='#C62828')
    ax.text(11.15, 4.4, '→ Cr(OH)₃/Fe-Cr↓', fontsize=9, ha='center', color='#C62828')

    # Chlorinated HC dechlorination
    tc_box = FancyBboxPatch((0.2, 4), 3.3, 1.8, boxstyle="round,pad=0.15",
                              facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(tc_box)
    ax.text(1.85, 5.4, '氯代烃脱氯路径', fontsize=10, ha='center', fontweight='bold', color='#1565C0')
    ax.text(1.85, 4.9, 'PCE→TCE→DCE→VC', fontsize=8, ha='center', color='#1565C0')
    ax.text(1.85, 4.4, '→ 乙烯/乙烷', fontsize=10, ha='center', color='#1565C0')

    # Bottom: Limitations
    limit_box = FancyBboxPatch((2.5, 0.2), 8, 1.2, boxstyle="round,pad=0.15",
                                 facecolor='#FFF8E1', edgecolor='#F57F17', linewidth=2)
    ax.add_patch(limit_box)
    ax.text(6.5, 1.1, '主要限制', fontsize=12, ha='center', fontweight='bold', color='#E65100')
    limits = '电子竞争 | Cr-Fe沉淀覆盖 | 长期脱氯受限 | 材料钝化 | 微生物毒性'
    ax.text(6.5, 0.55, limits, fontsize=9, ha='center', color='#BF360C')

    ax.set_title('图5 改性ZVI/nZVI修复Cr(VI)-氯代烃复合污染的作用机制示意图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图5_改性ZVI_nZVI作用机制图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图5_改性ZVI_nZVI作用机制图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图5 done")


def fig6_redox_coupling():
    """图6: 铁基氧化–还原耦合体系同步去除Cr(VI)与氯代烃的机制示意图"""
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Title core reaction
    ax.add_patch(patches.FancyBboxPatch((4.5, 7.5), 4, 1, boxstyle="round,pad=0.15",
                  facecolor='#E8EAF6', edgecolor='#283593', linewidth=2.5))
    ax.text(6.5, 8, '核心反应体系：ZVI/nZVI + PS/PMS', fontsize=12, ha='center',
            fontweight='bold', color='#283593')

    # Left: Reduction pathway
    red_box = FancyBboxPatch((0.5, 1.5), 5.5, 5.5, boxstyle="round,pad=0.2",
                               facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(red_box)
    ax.text(3.25, 6.6, '还原路径', fontsize=14, ha='center', fontweight='bold', color='#1565C0')

    red_items = [
        'Fe⁰ → Fe²⁺ + 2e⁻',
        'Cr(VI) + 3e⁻ → Cr(III)',
        'Cr(III) + Fe(III) → 共沉淀↓',
    ]
    for i, item in enumerate(red_items):
        y = 5.8 - i*1.2
        ax.add_patch(patches.FancyBboxPatch((1, y-0.3), 4.5, 0.8, boxstyle="round,pad=0.1",
                      facecolor='#BBDEFB', edgecolor='#1565C0', linewidth=1))
        ax.text(3.25, y+0.1, item, fontsize=10, ha='center', fontweight='bold', color='#0D47A1')
        if i < 2:
            ax.annotate('', xy=(3.25, y-0.3), xytext=(3.25, y-0.3-0.1),
                        arrowprops=dict(arrowstyle='->', color='#1565C0', lw=2))

    # Right: Oxidation pathway
    ox_box = FancyBboxPatch((7, 1.5), 5.5, 5.5, boxstyle="round,pad=0.2",
                              facecolor='#FCE4EC', edgecolor='#C62828', linewidth=2)
    ax.add_patch(ox_box)
    ax.text(9.75, 6.6, '氧化路径', fontsize=14, ha='center', fontweight='bold', color='#C62828')

    ox_items = [
        'Fe⁰/Fe(II) 活化PS',
        '生成 SO₄·⁻ 、·OH',
        'TCE/PCE → CO₂ + Cl⁻',
    ]
    for i, item in enumerate(ox_items):
        y = 5.8 - i*1.2
        ax.add_patch(patches.FancyBboxPatch((7.5, y-0.3), 4.5, 0.8, boxstyle="round,pad=0.1",
                      facecolor='#F8BBD0', edgecolor='#C62828', linewidth=1))
        ax.text(9.75, y+0.1, item, fontsize=10, ha='center', fontweight='bold', color='#B71C1C')
        if i < 2:
            ax.annotate('', xy=(9.75, y-0.3), xytext=(9.75, y-0.3-0.1),
                        arrowprops=dict(arrowstyle='->', color='#C62828', lw=2))

    # Center: Regulation factors
    reg_box = FancyBboxPatch((4.5, 2), 4, 3.5, boxstyle="round,pad=0.2",
                               facecolor='#FFF8E1', edgecolor='#F57F17', linewidth=2)
    ax.add_patch(reg_box)
    ax.text(6.5, 5.2, '调控因素', fontsize=12, ha='center', fontweight='bold', color='#E65100')
    factors = ['Fe(II)释放速率', 'PS投加量', 'pH调控',
               'HCO₃⁻/Cl⁻猝灭', 'Fe(II)过量清除']
    for i, f in enumerate(factors):
        ax.text(6.5, 4.5-i*0.5, f'• {f}', fontsize=9, ha='center', color='#BF360C')

    # Bottom: Engineering limitations
    lim_box = FancyBboxPatch((2, 0.2), 9, 1, boxstyle="round,pad=0.15",
                               facecolor='#EFEBE9', edgecolor='#5D4037', linewidth=2)
    ax.add_patch(lim_box)
    ax.text(6.5, 0.9, '工程限制', fontsize=11, ha='center', fontweight='bold', color='#4E342E')
    ax.text(6.5, 0.45, '氧化剂输运 | 副反应 | 反应持续性 | 地下水基质干扰',
            fontsize=9, ha='center', color='#5D4037')

    ax.set_title('图6 铁基氧化–还原耦合体系同步去除Cr(VI)与氯代烃的机制示意图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图6_铁基氧化还原耦合机制图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图6_铁基氧化还原耦合机制图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图6 done")


def fig7_electrochemical():
    """图7: 电化学/生物电化学修复Cr(VI)-氯代烃复合污染的电子传递机制示意图"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Anode (left)
    anode_box = FancyBboxPatch((0.5, 2.5), 4, 5, boxstyle="round,pad=0.2",
                                 facecolor='#FFF3E0', edgecolor='#E65100', linewidth=2.5)
    ax.add_patch(anode_box)
    ax.text(2.5, 7, '阳极', fontsize=16, ha='center', fontweight='bold', color='#E65100')
    ax.add_patch(patches.Rectangle((1.2, 5.5), 2.6, 0.4, facecolor='#E65100', edgecolor='none', alpha=0.6))

    anode_items = ['有机底物氧化', '释放电子(e⁻)和H⁺', '调控微环境Eh/pH']
    for i, item in enumerate(anode_items):
        ax.text(2.5, 5-i*0.6, f'• {item}', fontsize=9, ha='center', color='#BF360C')

    # Cathode (right)
    cathode_box = FancyBboxPatch((9.5, 2.5), 4, 5, boxstyle="round,pad=0.2",
                                   facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2.5)
    ax.add_patch(cathode_box)
    ax.text(11.5, 7, '阴极', fontsize=16, ha='center', fontweight='bold', color='#1565C0')
    ax.add_patch(patches.Rectangle((10.2, 5.5), 2.6, 0.4, facecolor='#1565C0', edgecolor='none', alpha=0.6))

    cathode_items = ['Cr(VI) + e⁻ → Cr(III)', 'TCE/PCE + H* → 脱氯', '产H₂供给脱氯菌']
    for i, item in enumerate(cathode_items):
        ax.text(11.5, 5-i*0.6, f'• {item}', fontsize=9, ha='center', color='#0D47A1')

    # External circuit (center)
    ext_box = FancyBboxPatch((5, 5), 4, 2.5, boxstyle="round,pad=0.2",
                               facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(ext_box)
    ax.text(7, 6.8, '外电路', fontsize=14, ha='center', fontweight='bold', color='#7B1FA2')
    ax.text(7, 6.2, '电子 e⁻ →', fontsize=12, ha='center', color='#4A148C')
    ax.text(7, 5.6, '外加电压/电位控制', fontsize=9, ha='center', color='#4A148C')

    # Arrows: anode to external
    ax.annotate('', xy=(5.1, 6.2), xytext=(4.4, 6.2),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=3))
    # Arrows: external to cathode
    ax.annotate('', xy=(9.6, 6.2), xytext=(8.9, 6.2),
                arrowprops=dict(arrowstyle='->', color='#1565C0', lw=3))

    # Bioelectrochemical module (center-bottom)
    bio_box = FancyBboxPatch((4.5, 1), 5, 3.5, boxstyle="round,pad=0.2",
                               facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(bio_box)
    ax.text(7, 4.1, '生物电化学模块', fontsize=13, ha='center', fontweight='bold', color='#2E7D32')

    bio_items = ['Dehalococcoides 脱氯菌', 'Cr(VI)还原菌',
                 '电子穿梭体(MQ/HQ)', '导电材料/生物膜']
    for i, item in enumerate(bio_items):
        ax.text(7, 3.4-i*0.55, f'• {item}', fontsize=9, ha='center', color='#1B5E20')

    # Limitations (bottom)
    lim_box = FancyBboxPatch((2.5, 0.1), 9, 0.8, boxstyle="round,pad=0.1",
                               facecolor='#FFEBEE', edgecolor='#C62828', linewidth=1.5)
    ax.add_patch(lim_box)
    ax.text(7, 0.5, '限制：电子竞争 | 阴极钝化 | 析氢副反应 | NOM干扰 | 电极布设',
            fontsize=9, ha='center', fontweight='bold', color='#C62828')

    ax.set_title('图7 电化学/生物电化学修复Cr(VI)-氯代烃复合污染的电子传递机制示意图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图7_电化学_生物电化学电子传递机制图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图7_电化学_生物电化学电子传递机制图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图7 done")


def fig8_microbial():
    """图8: 微生物强化修复Cr(VI)-氯代烃复合污染的作用路径及受限机制示意图"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Left: Cr(VI) microbial reduction
    cr_box = FancyBboxPatch((0.5, 3.5), 5.5, 5.5, boxstyle="round,pad=0.2",
                              facecolor='#FFEBEE', edgecolor='#C62828', linewidth=2)
    ax.add_patch(cr_box)
    ax.text(3.25, 8.5, 'Cr(VI)微生物还原', fontsize=14, ha='center', fontweight='bold', color='#C62828')

    cr_items = [
        ('Cr(VI) → Cr(III)', 7.8),
        ('铬酸还原酶', 7.0),
        ('胞外聚合物(EPS)吸附', 6.2),
        ('细胞表面络合', 5.4),
        ('Cr(OH)₃沉淀固定', 4.6),
    ]
    for item, y in cr_items:
        ax.add_patch(patches.FancyBboxPatch((1, y-0.3), 4.5, 0.6, boxstyle="round,pad=0.1",
                      facecolor='#FFCDD2', edgecolor='#C62828', linewidth=1))
        ax.text(3.25, y, item, fontsize=10, ha='center', color='#B71C1C')

    # Arrows between items
    for i in range(len(cr_items)-1):
        ax.annotate('', xy=(3.25, cr_items[i+1][1]+0.3), xytext=(3.25, cr_items[i][1]-0.3),
                    arrowprops=dict(arrowstyle='->', color='#C62828', lw=1.5))

    # Right: Chlorinated HC anaerobic dechlorination
    tc_box = FancyBboxPatch((8, 3.5), 5.5, 5.5, boxstyle="round,pad=0.2",
                              facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    ax.add_patch(tc_box)
    ax.text(10.75, 8.5, '氯代烃厌氧脱氯', fontsize=14, ha='center', fontweight='bold', color='#1565C0')

    tc_items = [
        ('PCE → TCE', 7.8),
        ('TCE → cis-DCE', 7.0),
        ('cis-DCE → VC', 6.2),
        ('VC → 乙烯', 5.4),
        ('Dehalococcoides + tceA/vcrA/bvcA', 4.6),
    ]
    for item, y in tc_items:
        ax.add_patch(patches.FancyBboxPatch((8.5, y-0.3), 4.5, 0.6, boxstyle="round,pad=0.1",
                      facecolor='#BBDEFB', edgecolor='#1565C0', linewidth=1))
        ax.text(10.75, y, item, fontsize=10, ha='center', color='#0D47A1')

    for i in range(len(tc_items)-1):
        ax.annotate('', xy=(10.75, tc_items[i+1][1]+0.3), xytext=(10.75, tc_items[i][1]-0.3),
                    arrowprops=dict(arrowstyle='->', color='#1565C0', lw=1.5))

    # Center: Co-contamination limitations
    lim_box = FancyBboxPatch((5.2, 3.5), 3.6, 5.5, boxstyle="round,pad=0.2",
                               facecolor='#FFF8E1', edgecolor='#F57F17', linewidth=2)
    ax.add_patch(lim_box)
    ax.text(7, 8.5, '复合污染限制', fontsize=13, ha='center', fontweight='bold', color='#E65100')

    lim_items = [
        'Cr(VI)毒性抑制脱氯菌',
        '电子供体竞争',
        'VC阶段更敏感',
        '乙烯生成不足',
    ]
    for i, item in enumerate(lim_items):
        ax.text(7, 7.5-i*0.8, f'• {item}', fontsize=9, ha='center', color='#BF360C')

    # Bottom: Optimization strategies
    opt_box = FancyBboxPatch((1, 0.3), 12, 2.8, boxstyle="round,pad=0.2",
                               facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(opt_box)
    ax.text(7, 2.7, '优化策略', fontsize=14, ha='center', fontweight='bold', color='#2E7D32')

    strategies = [
        ('先化学降铬\n再生物脱氯', '#C62828'),
        ('耐毒菌群\n筛选', '#1565C0'),
        ('电子供体\n缓释', '#E65100'),
        ('生物电化学\n供电子', '#7B1FA2'),
        ('功能基因\n监测', '#2E7D32'),
    ]
    for i, (strategy, color) in enumerate(strategies):
        x = 1.8 + i*2.4
        ax.add_patch(patches.FancyBboxPatch((x-0.9, 0.6), 2, 1.6, boxstyle="round,pad=0.1",
                      facecolor='white', edgecolor=color, linewidth=1.5))
        ax.text(x, 1.4, strategy, fontsize=8, ha='center', fontweight='bold', color=color)

    ax.set_title('图8 微生物强化修复Cr(VI)-氯代烃复合污染的作用路径及受限机制示意图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图8_微生物强化修复机制图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图8_微生物强化修复机制图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图8 done")


def fig9_integrated_engineering():
    """图9: Cr(VI)-氯代烃复合污染地下水原位工程化集成修复模式示意图"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Geological layers
    # Surface (y=8.5-10)
    ax.add_patch(patches.Rectangle((0.2, 8.5), 13.6, 1.5, facecolor='#D7CCC8', edgecolor='#5D4037', linewidth=1.5))
    ax.text(7, 9.5, '地表', fontsize=12, ha='center', fontweight='bold', color='#4E342E')
    ax.text(2, 9, '源区(注入型铁基材料)', fontsize=9, color='#C62828', fontweight='bold')
    ax.text(10, 9, '监测井', fontsize=9, color='#1565C0',
            bbox=dict(boxstyle='round', facecolor='#BBDEFB', alpha=0.7))

    # Vadose zone (y=6.5-8.5)
    ax.add_patch(patches.Rectangle((0.2, 6.5), 13.6, 2, facecolor='#FFF8E1', edgecolor='#F9A825', linewidth=1.5))
    ax.text(7, 7.5, '包气带', fontsize=12, ha='center', fontweight='bold', color='#F57F17')

    # Water table line
    ax.plot([0.2, 13.8], [6.5, 6.5], 'b-', linewidth=2.5, alpha=0.7)
    ax.text(13.5, 6.7, '← 水位线', fontsize=9, color='blue', ha='right')

    # Saturated zone (y=3-6.5)
    ax.add_patch(patches.Rectangle((0.2, 3), 13.6, 3.5, facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=1.5, alpha=0.6))
    ax.text(7, 6, '含水层', fontsize=12, ha='center', fontweight='bold', color='#1565C0')

    # Groundwater flow arrow
    ax.annotate('', xy=(13.5, 4.8), xytext=(0.5, 4.8),
                arrowprops=dict(arrowstyle='->', color='blue', lw=3, connectionstyle='arc3,rad=0'))
    ax.text(7, 4.2, '地下水流向 →', fontsize=11, color='blue', fontweight='bold', ha='center')

    # Upstream/source zone
    source_zone = patches.Rectangle((0.5, 5), 3.5, 3, facecolor='#FFCDD2', edgecolor='#C62828', linewidth=2, alpha=0.5)
    ax.add_patch(source_zone)
    ax.text(2.25, 7.6, '上游/源区', fontsize=12, ha='center', fontweight='bold', color='#C62828')
    ax.text(2.25, 7.1, '注入型铁基材料', fontsize=9, ha='center', color='#B71C1C')
    ax.text(2.25, 6.6, '处理Cr(VI)高浓度区', fontsize=8, ha='center', color='#B71C1C')
    ax.text(2.25, 6.1, '和氯代烃热点', fontsize=8, ha='center', color='#B71C1C')
    ax.add_patch(patches.FancyBboxPatch((0.8, 5.2), 2.8, 0.6, boxstyle="round,pad=0.1",
                  facecolor='#C62828', edgecolor='none', alpha=0.2))
    ax.text(2.25, 5.5, '前端快速降毒', fontsize=9, ha='center', fontweight='bold', color='#C62828')

    # Midstream: PRB / reaction zone
    prb_zone = patches.Rectangle((4.5, 5), 4.5, 3, facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=2, alpha=0.5)
    ax.add_patch(prb_zone)
    ax.text(6.75, 7.6, '中游污染羽主通道', fontsize=12, ha='center', fontweight='bold', color='#2E7D32')
    ax.text(6.75, 7.1, 'PRB / 原位反应带', fontsize=9, ha='center', color='#1B5E20')
    ax.text(6.75, 6.6, 'ZVI/硫化ZVI/释碳材料', fontsize=8, ha='center', color='#1B5E20')
    ax.text(6.75, 6.1, '组合', fontsize=8, ha='center', color='#1B5E20')
    ax.add_patch(patches.FancyBboxPatch((5, 5.2), 3.4, 0.6, boxstyle="round,pad=0.1",
                  facecolor='#2E7D32', edgecolor='none', alpha=0.2))
    ax.text(6.75, 5.5, '污染羽拦截与强化转化', fontsize=9, ha='center', fontweight='bold', color='#2E7D32')

    # Downstream: long-term
    down_zone = patches.Rectangle((9.5, 5), 4, 3, facecolor='#BBDEFB', edgecolor='#1565C0', linewidth=2, alpha=0.5)
    ax.add_patch(down_zone)
    ax.text(11.5, 7.6, '下游', fontsize=12, ha='center', fontweight='bold', color='#1565C0')
    ax.text(11.5, 7.1, '释碳反应带', fontsize=9, ha='center', color='#0D47A1')
    ax.text(11.5, 6.6, '生物强化/BES', fontsize=9, ha='center', color='#0D47A1')
    ax.text(11.5, 6.1, '残余TCE/DCE/VC深度脱氯', fontsize=8, ha='center', color='#0D47A1')
    ax.add_patch(patches.FancyBboxPatch((9.8, 5.2), 3.4, 0.6, boxstyle="round,pad=0.1",
                  facecolor='#1565C0', edgecolor='none', alpha=0.2))
    ax.text(11.5, 5.5, '长期维持与风险控制', fontsize=9, ha='center', fontweight='bold', color='#1565C0')

    # Confining layer (y=1.5-3)
    ax.add_patch(patches.Rectangle((0.2, 1.5), 13.6, 1.5, facecolor='#EFEBE9', edgecolor='#795548', linewidth=1.5))
    ax.text(7, 2.2, '隔水层/低渗透层', fontsize=12, ha='center', fontweight='bold', color='#5D4037')

    # Low permeability annotation
    ax.add_patch(patches.FancyBboxPatch((10, 3.2), 3, 1.2, boxstyle="round,pad=0.1",
                  facecolor='#FFF3E0', edgecolor='#E65100', linewidth=1, linestyle='--'))
    ax.text(11.5, 3.8, '低渗透区\nEK-PRB/电场\n辅助注入', fontsize=8, ha='center', color='#E65100')

    # Monitoring wells
    for wx in [3, 6, 9, 12]:
        ax.plot([wx, wx], [5, 9], 'k-', linewidth=1.5, linestyle='--', alpha=0.5)
        ax.plot(wx, 9, 'kv', markersize=8)
        ax.text(wx, 4.6, '监测', fontsize=7, ha='center', color='#37474F')

    # Monitoring parameters box
    mon_box = FancyBboxPatch((0.5, 0.2), 13, 1.1, boxstyle="round,pad=0.15",
                               facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=2)
    ax.add_patch(mon_box)
    ax.text(7, 1, '监测参数：Eh | pH | Fe(II) | Cr(VI) | TCE | DCE | VC | 乙烯 | 功能基因 (tceA/vcrA/bvcA)',
            fontsize=9, ha='center', fontweight='bold', color='#4A148C')

    # Phase labels on bottom
    phases = [('前端快速降毒', '#C62828', 2.25), ('中段强化转化', '#2E7D32', 6.75), ('后端长期维持', '#1565C0', 11.5)]
    for label, color, x in phases:
        ax.text(x, 4.5, f'▼ {label}', fontsize=9, ha='center', fontweight='bold', color=color)

    ax.set_title('图9 Cr(VI)-氯代烃复合污染地下水原位工程化集成修复模式示意图',
                 fontsize=15, fontweight='bold', pad=10)

    fig.savefig(os.path.join(OUT, '图9_原位工程化集成修复模式图.png'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(OUT, '图9_原位工程化集成修复模式图.pdf'), bbox_inches='tight')
    plt.close(fig)
    print("图9 done")


if __name__ == '__main__':
    print("Starting figure generation...")
    fig1_eh_ph()
    fig2_source_migration()
    fig3_interaction_mechanism()
    fig4_tech_framework()
    fig5_zvi_modification()
    fig6_redox_coupling()
    fig7_electrochemical()
    fig8_microbial()
    fig9_integrated_engineering()
    print(f"\nAll 9 figures saved to: {OUT}")
    print("Formats: PNG (300dpi) + PDF (vector)")
