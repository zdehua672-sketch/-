import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import seaborn as sns

# -----------------------------------------------------------------------------
# 1. 字体与风格配置
# -----------------------------------------------------------------------------
# 尝试使用 SimHei 字体来支持中文（如果系统中没有，可能需要替换为其他中文字体）
plt.rcParams['font.sans-serif'] = ['SimHei']  
plt.rcParams['axes.unicode_minus'] = False  
plt.rcParams['font.family'] = 'sans-serif' # 优先使用无衬线字体（通常包含SimHei）

# 设置英文字体为 Times New Roman
# 注意：Matplotlib 的 font.family 全局设置通常只能选一种主要字体族。
# 为了让中文和英文（Times New Roman）混排，通常需要更复杂的配置。
# 这里我们采用一种折衷方案：全局字体设为 SimHei 以显示中文，
# 但在绘图时对英文标签单独指定 Times New Roman（如果需要）。
# 或者，我们可以尝试设置 font.serif 为 Times New Roman，并设置 font.family = 'serif'，
# 但这可能会导致中文无法显示。
# 考虑到学术图表通常要求英文为 Times New Roman，我们可以手动设置刻度和标签的字体属性。

# 定义中国风配色 (参考：中国传统色)
# 赭石, 靛蓝, 豆绿, 妃色, 缃色
chinese_colors = ['#845a33', '#1661ab', '#9ed048', '#ed5736', '#f0c239']

# -----------------------------------------------------------------------------
# 2. 数据加载与预处理
# -----------------------------------------------------------------------------
file_path = r"C:\Users\Administrator\Desktop\硕士毕业论文\采样点和气体数据图.xlsx"

try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Error reading file: {e}")
    exit()

# 定义列名映射（方便后续引用）
columns = {
    'point': '采样点',
    'N2O': '氧化亚氮（PPM）',
    'CH4': '甲烷（PPM）',
    'CO2': 'CO2(mg/L)',
    'O2': 'O2(%vol)',
    'VOCs': 'VOCs(ppb)'
}

# 提取数据
points = df[columns['point']]
indicators = [columns['N2O'], columns['CH4'], columns['CO2'], columns['O2'], columns['VOCs']]
indicator_names_cn = ['氧化亚氮 (ppm)', '甲烷 (ppm)', '二氧化碳 (mg/L)', '氧气 (%vol)', '挥发性有机物 (ppb)'] # 用于图表显示的中文标签

# 分区定义
zone1_points = [f'R{i}' for i in range(1, 13)] # R1-R12
zone2_points = [f'R{i}' for i in range(13, 21)] # R13-R20

# -----------------------------------------------------------------------------
# 3. 绘图逻辑
# -----------------------------------------------------------------------------
# 创建画布：5个子图，垂直排列
fig, axes = plt.subplots(nrows=5, ncols=1, figsize=(10, 15), sharex=True)

# 设置整体标题
fig.suptitle('各采样点气体浓度空间变化特征', fontsize=18, fontname='SimHei', y=0.95)

# 遍历每个指标进行绘图
for i, (col_name, ax) in enumerate(zip(indicators, axes)):
    color = chinese_colors[i % len(chinese_colors)]
    
    # 绘制条形图
    bars = ax.bar(points, df[col_name], color=color, edgecolor='black', linewidth=0.8, alpha=0.8, width=0.6)
    
    # 设置Y轴标签
    ax.set_ylabel(indicator_names_cn[i], fontsize=12, fontname='SimHei')
    
    # 设置刻度字体
    for label in ax.get_yticklabels():
        label.set_fontname('Times New Roman')
        label.set_fontsize(10)
        
    # 添加网格线 (仅Y轴)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # 添加分区背景色或竖线分隔
    # 在 R12 和 R13 之间画一条虚线
    # R1-R12 是前12个点 (索引 0-11)，R13 是第13个点 (索引 12)
    # 在索引 11.5 处画线
    ax.axvline(x=11.5, color='gray', linestyle='--', linewidth=1.5)
    
    # 添加分区文本标注 (仅在第一个子图添加，避免重复)
    if i == 0:
        # 获取Y轴范围以确定文本位置
        y_min, y_max = ax.get_ylim()
        text_y = y_max * 0.9
        
        ax.text(5.5, text_y, '教学区与实验楼区 (R1-R12)', ha='center', va='center', 
                fontsize=12, fontname='SimHei', fontweight='bold', color='#333333',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=3))
        
        ax.text(15.5, text_y, '食堂区与生活区 (R13-R20)', ha='center', va='center', 
                fontsize=12, fontname='SimHei', fontweight='bold', color='#333333',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=3))

# 设置X轴标签 (仅在最后一个子图)
axes[-1].set_xlabel('采样点位', fontsize=14, fontname='SimHei')
axes[-1].set_xticklabels(points, rotation=45, ha='right')

# 设置X轴刻度字体
for label in axes[-1].get_xticklabels():
    label.set_fontname('Times New Roman')
    label.set_fontsize(10)

# 调整布局
plt.tight_layout(rect=[0, 0, 1, 0.95]) # 预留顶部标题空间
plt.subplots_adjust(hspace=0.2) # 调整子图间距

# 保存图片 (同时保存 PNG 和 PDF 矢量图)
output_path_png = r"C:\Users\Administrator\Desktop\gas_concentration_bar_chart.png"
output_path_pdf = r"C:\Users\Administrator\Desktop\gas_concentration_bar_chart.pdf"
output_path_svg = r"C:\Users\Administrator\Desktop\gas_concentration_bar_chart.svg"

plt.savefig(output_path_png, dpi=300, bbox_inches='tight')
plt.savefig(output_path_pdf, format='pdf', bbox_inches='tight')
plt.savefig(output_path_svg, format='svg', bbox_inches='tight')

print(f"Chart saved to:\n- {output_path_png}\n- {output_path_pdf}\n- {output_path_svg}")

plt.close()
