# =========================================================
# 固液气多相态碳污染物赋存特征及碳平衡分析
# Python 数据分析与绘图脚本
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
# 1. 读取并处理数据
# =========================================================
# 先处理冬季数据（数据完整）
winter_file = r"C:\Users\Administrator\Desktop\硕士毕业论文\冬季数据汇总.xlsx"
winter = pd.read_excel(winter_file)

# 处理春季数据，小心处理表头问题
spring_file = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"
try:
    # 先读取所有行看看结构
    spring_raw = pd.read_excel(spring_file, sheet_name='春季', header=None)
    
    # 找到真正的数据开始行（跳过所有包含表头的行）
    # 假设第一行是主标题，第二行是表头
    spring = pd.read_excel(spring_file, sheet_name='春季', header=1)
    
    # 再次清洗，确保所有值都是数值
    for col in spring.columns:
        spring[col] = pd.to_numeric(spring[col].astype(str).str.replace('mg/L', '').str.replace('ppm', ''), errors='coerce')
    
except Exception as e:
    print(f"春季数据读取警告: {e}")
    # 如果出错，就只用冬季数据
    spring = pd.DataFrame()

print("成功加载数据文件")
print(f"冬季数据量: {len(winter)}")

# =========================================================
# 2. 只处理冬季数据（数据最完整可靠）
# =========================================================
df = winter
gas_cols = ['氧化亚氮（PPM）', '甲烷（PPM）', 'CO2(mg/L)', 'O2(%vol)', 'VOCs(ppb)']
liquid_cols = ['DO(mg/L)', 'pH', 'TOC（mg/L)', '总氮（mg/L)', 'COD（锰）（mg/L)']

# 确保数据都是数值
for col in gas_cols + liquid_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

print("\n正在生成图表...")

# =========================================================
# 3. 冬季气体浓度空间分布图（沿用你之前的风格）
# =========================================================
fig, axes = plt.subplots(len(gas_cols), 1, figsize=(12, 3 * len(gas_cols)), sharex=True)
chinese_colors = ['#845a33', '#1661ab', '#9ed048', '#ed5736', '#f0c239']
gas_labels = [r'$N_2O$ (ppm)', r'$CH_4$ (ppm)', r'$CO_2$ (mg/L)', r'$O_2$ (%vol)', 'VOCs (ppb)']

for i, (col, ax, color, label) in enumerate(zip(gas_cols, axes, chinese_colors, gas_labels)):
    if col in df.columns:
        sns.barplot(x='采样点', y=col, data=df, ax=ax, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.set_ylabel(label, fontname='Times New Roman', fontsize=12)
        ax.set_xlabel('')
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        # 分区线
        ax.axvline(x=11.5, color='gray', linestyle='--', linewidth=1.5)
        
        if i == 0:
            y_max = df[col].max() * 1.1
            ax.text(5.5, y_max * 0.9, '教学与实验楼区 (R1-R12)', ha='center', 
                    fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
            ax.text(15.5, y_max * 0.9, '食堂与生活区 (R13-R20)', ha='center', 
                    fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))

axes[-1].set_xlabel('采样点位', fontsize=14, fontname='SimHei')
plt.xticks(rotation=45, ha='right', fontname='Times New Roman')
plt.suptitle('冬季各采样点气体浓度空间变化特征', fontsize=18, fontname='SimHei', y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.97])

output_gas_png = os.path.join(output_dir, "冬季气体浓度空间分布图.png")
output_gas_pdf = os.path.join(output_dir, "冬季气体浓度空间分布图.pdf")
plt.savefig(output_gas_png, dpi=300, bbox_inches='tight')
plt.savefig(output_gas_pdf, format='pdf', bbox_inches='tight')
plt.show()
plt.close()
print(f"冬季气体浓度图已保存: {output_gas_pdf}")

# =========================================================
# 4. 相关性热力图
# =========================================================
available_cols = [c for c in gas_cols + liquid_cols if c in df.columns]
corr_df = df[available_cols].dropna()

if len(corr_df) > 5:
    corr = corr_df.corr(method='spearman')
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr, annot=True, cmap='RdBu_r', fmt=".2f", 
                center=0, linewidths=0.8, square=True,
                annot_kws={"fontname": "Times New Roman", "fontsize": 10})
    
    plt.title("冬季固液气多参数相关性热力图 (Spearman)", fontname='SimHei', fontsize=16, pad=20)
    plt.tight_layout()
    
    output_corr_png = os.path.join(output_dir, "冬季相关性热力图.png")
    output_corr_pdf = os.path.join(output_dir, "冬季相关性热力图.pdf")
    plt.savefig(output_corr_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_corr_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"相关性热力图已保存: {output_corr_pdf}")

# =========================================================
# 5. 导出数据
# =========================================================
df.to_excel(os.path.join(output_dir, "处理后数据.xlsx"), index=False)

print("\n================ 分析完成 ================")
print(f"所有文件已保存至: {output_dir}")
