# =========================================================
# 固液气多相态碳污染物赋存特征及碳平衡分析
# Python 数据分析与绘图脚本 - 最终修正版
# =========================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

# 中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 图像风格
sns.set(style="whitegrid", font='SimHei')

# 定义输出路径
output_dir = r"C:\Users\Administrator\Desktop\分析结果"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# ======================
# 化学式标签映射（恢复LaTeX下标）
# ======================
label_map = {
    'CH4平均值': r'$CH_4$ (ppm)',
    'N2O平均值': r'$N_2O$ (ppm)',
    'CO2': r'$CO_2$',
    'VOCs(ppb)': 'VOCs (ppb)',
    'O2(%vol)': r'$O_2$ (%vol)',
    '甲烷': r'$CH_4$ (ppm)',
    '氧化亚氮': r'$N_2O$ (ppm)',
    'CO2(ppm)': r'$CO_2$ (ppm)',
    'CO2(PPM)': r'$CO_2$ (ppm)',
    'DO(mg/L)': 'DO (mg/L)',
    'pH': 'pH',
    '液温': '液温',
    '电导率(uS/cm)': '电导率 (uS/cm)',
    '电导率(us/cm)': '电导率 (uS/cm)',
    'TOC（mg/L)': 'TOC (mg/L)',
    'TC(mg/L)': 'TC (mg/L)',
    'IC(mg/L)': 'IC (mg/L)',
    'COD（mg/L)': 'COD (mg/L)',
    '固总碳（g/kg)': '固总碳 (g/kg)',
    '有机碳（g/kg)': '有机碳 (g/kg)',
    '无机碳（g/kg)': '无机碳 (g/kg)',
}

def get_label(col):
    return label_map.get(col, col)

# ======================
# 1. 读取数据
# ======================
file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"

winter = pd.read_excel(file_path, sheet_name='冬季')
spring = pd.read_excel(file_path, sheet_name='春季')

# ======================
# 2. 数据整理
# ======================

# ---- 冬季列名统一 ----
winter = winter.rename(columns={
    '平均值': 'N2O平均值',
    '平均值.1': 'CH4平均值',
    'CO2(ppm)': 'CO2',
    '氧化亚氮(ppm)': '氧化亚氮',
    '甲烷(ppm)': '甲烷'
})

# ---- 春季列名统一 ----
spring = spring.rename(columns={
    '平均值': 'CH4平均值',
    '平均值.1': 'N2O平均值',
    'CO2(PPM)': 'CO2',
    '检查井编号': '采样点'
})

# 添加季节标签
winter['季节'] = '冬季'
spring['季节'] = '春季'

# 统一采样点名称
if '采样点' not in winter.columns:
    winter['采样点'] = [f'R{i}' for i in range(1, len(winter)+1)]

# 合并数据
df = pd.concat([winter, spring], ignore_index=True)

# ======================
# 3. 选择分析参数 - 修正重复电导率
# ======================

gas_cols = [
    'CH4平均值',
    'N2O平均值',
    'CO2',
    'VOCs(ppb)',
    'O2(%vol)'
]

# 补充可能的列名变体
available_gas_cols = []
for col in gas_cols:
    if col in df.columns:
        available_gas_cols.append(col)

# 如果没有找到平均值列，查找原始数据列
if 'CH4平均值' not in available_gas_cols and '甲烷' in df.columns:
    available_gas_cols.append('甲烷')
if 'N2O平均值' not in available_gas_cols and '氧化亚氮' in df.columns:
    available_gas_cols.append('氧化亚氮')

# 修正重复的电导率列
liquid_cols = [
    'DO(mg/L)',
    'pH',
    '液温',
    '电导率(uS/cm)',  # 只保留大写版本
    'TOC（mg/L)',
    'TC(mg/L)',
    'IC(mg/L)',
    'COD（mg/L)'
]

# 如果大写版本不存在，尝试小写版本
if '电导率(uS/cm)' not in df.columns and '电导率(us/cm)' in df.columns:
    # 重命名为统一的列名
    df.rename(columns={'电导率(us/cm)': '电导率(uS/cm)'}, inplace=True)

# 筛选实际存在的列
available_liquid_cols = [c for c in liquid_cols if c in df.columns]

solid_cols = [
    '固总碳（g/kg)',
    '有机碳（g/kg)',
    '无机碳（g/kg)'
]

available_solid_cols = [c for c in solid_cols if c in df.columns]

print(f"\n可用气体指标: {available_gas_cols}")
print(f"可用液体指标: {available_liquid_cols}")
print(f"可用固体指标: {available_solid_cols}")

# ======================
# 4. 描述性统计
# ======================
print("\n================ 描述性统计 ================\n")

all_cols = available_gas_cols + available_liquid_cols + available_solid_cols
if all_cols:
    desc = df[all_cols].describe()
    print(desc)
    desc.to_excel(os.path.join(output_dir, "描述性统计.xlsx"))

# ======================
# 5. 箱线图（不同季节气体浓度）
# ======================
if available_gas_cols:
    plt.figure(figsize=(14, 8))
    
    n_cols = min(4, len(available_gas_cols))
    n_rows = 1 if len(available_gas_cols) <=4 else 2
    
    for i, col in enumerate(available_gas_cols[:4]):
        plt.subplot(n_rows, n_cols, i+1)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        sns.boxplot(data=df, x='季节', y=col, hue='季节', palette=['#1661ab', '#ed5736'], legend=False)
        plt.title(f"冬春季{get_label(col)}浓度分布", fontname='SimHei', fontsize=12)
        plt.ylabel(get_label(col), fontname='Times New Roman', fontsize=10)
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(os.path.join(output_dir, f"气体浓度箱线图_{timestamp}.png"), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, f"气体浓度箱线图_{timestamp}.pdf"), format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("箱线图已保存")

# ======================
# 6. 采样点气体分布图
# ======================
if available_gas_cols and '采样点' in df.columns:
    plt.figure(figsize=(14, 10))
    
    n_cols = min(2, len(available_gas_cols))
    n_rows = min(2, (len(available_gas_cols) + 1) // n_cols)
    
    for i, col in enumerate(available_gas_cols[:4]):
        plt.subplot(n_rows, n_cols, i+1)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        sns.lineplot(data=df, x='采样点', y=col, hue='季节', marker='o', linewidth=2)
        plt.title(f"不同采样点{get_label(col)}变化", fontname='SimHei', fontsize=12)
        plt.ylabel(get_label(col), fontname='Times New Roman', fontsize=10)
        plt.xticks(rotation=45)
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(os.path.join(output_dir, f"采样点气体变化_{timestamp}.png"), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, f"采样点气体变化_{timestamp}.pdf"), format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("采样点分布图已保存")

# ======================
# 7. 多参数相关性热力图（保持原列名，避免LaTeX乱码）
# ======================
corr_cols = available_gas_cols + available_liquid_cols

if len(corr_cols) >= 5:
    corr_df = df[corr_cols].copy()
    
    # 转数值
    corr_df = corr_df.apply(pd.to_numeric, errors='coerce')
    
    # 相关矩阵
    corr = corr_df.corr(method='pearson')
    
    # 创建标签列表（不修改DataFrame的列名）
    xtick_labels = [get_label(col) for col in corr.columns]
    ytick_labels = [get_label(col) for col in corr.index]
    
    plt.figure(figsize=(14, 10))
    
    # 绘制热图，使用原始列名但显示格式化标签
    ax = sns.heatmap(
        corr,
        annot=True,
        cmap='RdBu_r',
        fmt=".2f",
        annot_kws={"fontname": "Times New Roman", "fontsize": 9},
        center=0,
        linewidths=0.5,
        xticklabels=xtick_labels,
        yticklabels=ytick_labels
    )
    
    plt.title("固液气多参数相关性热力图", fontname='SimHei', fontsize=16, pad=20)
    
    # 设置X轴和Y轴标签的字体
    for text in ax.get_xticklabels():
        text.set_fontname('SimHei')
        text.set_fontsize(10)
        text.set_rotation(45)
    
    for text in ax.get_yticklabels():
        text.set_fontname('SimHei')
        text.set_fontsize(10)
        text.set_rotation(0)
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(os.path.join(output_dir, f"相关性热力图_{timestamp}.png"), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, f"相关性热力图_{timestamp}.pdf"), format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("相关性热力图已保存")

# ======================
# 8. 散点图分析
# ======================
if 'DO(mg/L)' in df.columns and len(available_gas_cols) > 0:
    plt.figure(figsize=(16, 5))
    
    plot_cols = available_gas_cols[:3]
    for i, col in enumerate(plot_cols):
        plt.subplot(1, len(plot_cols), i+1)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df['DO(mg/L)'] = pd.to_numeric(df['DO(mg/L)'], errors='coerce')
        
        sns.scatterplot(data=df, x='DO(mg/L)', y=col, hue='季节', s=100, alpha=0.7, edgecolor='black')
        
        plt.title(f"DO 与 {get_label(col)} 的关系", fontname='SimHei')
        plt.xlabel("DO (mg/L)", fontname='Times New Roman')
        plt.ylabel(get_label(col), fontname='Times New Roman')
    
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(os.path.join(output_dir, f"DO_关系图_{timestamp}.png"), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, f"DO_关系图_{timestamp}.pdf"), format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("散点图已保存")

# ======================
# 9. 导出处理后数据
# ======================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
df.to_excel(os.path.join(output_dir, f"处理后数据_{timestamp}.xlsx"), index=False)

print("\n================ 分析完成 ================")
print(f"所有文件已保存至: {output_dir}")
