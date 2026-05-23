# =========================================================
# 固液气多相态碳污染物赋存特征及碳平衡分析
# Python 数据分析与绘图脚本 - 冬春数据对比版
# =========================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 中文显示与风格配置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set(style="whitegrid", font='SimHei', font_scale=1.2)

# 定义输出路径
output_dir = r"C:\Users\Administrator\Desktop\分析结果"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# =========================================================
# 1. 读取并处理冬春数据.xlsx
# =========================================================
file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"

print("正在读取文件...")

# 读取冬季数据（第0行是表头）
winter = pd.read_excel(file_path, sheet_name='冬季', header=0)
winter['季节'] = '冬季'

# 读取春季数据（第0行是表头）
spring = pd.read_excel(file_path, sheet_name='春季', header=0)
spring['季节'] = '春季'

# 统一列名
if '检查井编号' in spring.columns and '采样点' not in spring.columns:
    spring = spring.rename(columns={'检查井编号': '采样点'})

# 合并数据
df = pd.concat([winter, spring], ignore_index=True)

print(f"数据加载完成！")
print(f"冬季数据: {len(winter)} 行")
print(f"春季数据: {len(spring)} 行")
print(f"可用列: {df.columns.tolist()}")

# =========================================================
# 2. 气体浓度对比箱线图（冬春对比）
# =========================================================
print("\n正在生成图表...")

# 定义要分析的气体指标
gas_indicators = []
# 找甲烷、氧化亚氮、CO2
ch4_col = [c for c in df.columns if '甲烷' in c]
n2o_col = [c for c in df.columns if '氧化亚氮' in c]
co2_col = [c for c in df.columns if 'CO2' in c]

if ch4_col: gas_indicators.append( (ch4_col[0], r'$CH_4$ (ppm)') )
if n2o_col: gas_indicators.append( (n2o_col[0], r'$N_2O$ (ppm)') )
if co2_col: gas_indicators.append( (co2_col[0], r'$CO_2$') )

if gas_indicators:
    fig, axes = plt.subplots(1, len(gas_indicators), figsize=(6*len(gas_indicators), 5))
    if len(gas_indicators) == 1: axes = [axes]
    
    for i, (col, label) in enumerate(gas_indicators):
        # 确保列是数值类型
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        sns.boxplot(data=df, x='季节', y=col, ax=axes[i], 
                    hue='季节', palette=['#1661ab', '#ed5736'], legend=False)
        axes[i].set_title(f"冬春季{label}浓度分布", fontname='SimHei', fontsize=14)
        axes[i].set_xlabel('', fontname='SimHei')
        axes[i].set_ylabel(label, fontname='Times New Roman')
    
    plt.tight_layout()
    output_png = os.path.join(output_dir, "冬春气体浓度对比箱线图.png")
    output_pdf = os.path.join(output_dir, "冬春气体浓度对比箱线图.pdf")
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"箱线图已保存: {output_pdf}")

# =========================================================
# 3. 冬季各采样点气体浓度空间分布图
# =========================================================
winter_gas_cols = [c for c in winter.columns if '甲烷' in c or '氧化亚氮' in c or 'CO2' in c or 'O2' in c or 'VOCs' in c]

if len(winter_gas_cols) >= 4 and '采样点' in winter.columns:
    fig, axes = plt.subplots(len(winter_gas_cols), 1, figsize=(12, 3 * len(winter_gas_cols)), sharex=True)
    chinese_colors = ['#845a33', '#1661ab', '#9ed048', '#ed5736', '#f0c239']
    
    # 简单的标签映射
    def get_label(col):
        if '甲烷' in col: return r'$CH_4$ (ppm)'
        if '氧化亚氮' in col: return r'$N_2O$ (ppm)'
        if 'CO2' in col: return r'$CO_2$'
        if 'O2' in col: return r'$O_2$'
        if 'VOCs' in col: return 'VOCs'
        return col
    
    for i, (col, ax) in enumerate(zip(winter_gas_cols, axes)):
        color = chinese_colors[i % len(chinese_colors)]
        winter[col] = pd.to_numeric(winter[col], errors='coerce')
        
        sns.barplot(x='采样点', y=col, data=winter, ax=ax, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.set_ylabel(get_label(col), fontname='Times New Roman', fontsize=12)
        ax.set_xlabel('')
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.axvline(x=11.5, color='gray', linestyle='--', linewidth=1.5)
        
        if i == 0:
            y_max = winter[col].max() * 1.1 if pd.notna(winter[col].max()) else 1
            ax.text(5.5, y_max * 0.9, '教学与实验楼区 (R1-R12)', ha='center', 
                    fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
            ax.text(15.5, y_max * 0.9, '食堂与生活区 (R13-R20)', ha='center', 
                    fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
    
    axes[-1].set_xlabel('采样点位', fontsize=14, fontname='SimHei')
    plt.xticks(rotation=45, ha='right', fontname='Times New Roman')
    plt.suptitle('冬季各采样点气体浓度空间变化特征', fontsize=18, fontname='SimHei', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    output_winter_png = os.path.join(output_dir, "冬季气体浓度空间分布图.png")
    output_winter_pdf = os.path.join(output_dir, "冬季气体浓度空间分布图.pdf")
    plt.savefig(output_winter_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_winter_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"冬季气体浓度空间分布图已保存: {output_winter_pdf}")

# =========================================================
# 4. 导出数据
# =========================================================
df.to_excel(os.path.join(output_dir, "处理后冬春数据.xlsx"), index=False)

print("\n================ 分析完成 ================")
print(f"所有文件已保存至: {output_dir}")
