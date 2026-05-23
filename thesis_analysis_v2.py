# =========================================================
# 污水管网固-液-气多相态碳污染物赋存特征及碳平衡分析
# 毕业论文完整Python分析代码（适合直接运行）- 字体修复版
# =========================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from datetime import datetime

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from scipy.cluster.hierarchy import linkage, dendrogram
    has_sklearn = True
except:
    has_sklearn = False
    print("警告：sklearn 或 scipy 未安装，将跳过 PCA 和聚类分析")

# =========================
# 强制设置字体配置
# =========================
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'STHeiti']  # 中文字体优先级
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'  # 优先使用无衬线字体（含中文）

sns.set(style='whitegrid', font='SimHei', font_scale=1.1)

# 定义输出路径
output_dir = r"C:\Users\Administrator\Desktop\分析结果"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 时间戳
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# =========================
# 化学式标签映射（简化版本，避免LaTeX问题）
# =========================
label_map = {
    'CH4平均值': 'CH4 (ppm)',
    'N2O平均值': 'N2O (ppm)',
    'CO2': 'CO2',
    'VOCs(ppb)': 'VOCs (ppb)',
    'O2(%vol)': 'O2 (%vol)',
    '甲烷': 'CH4 (ppm)',
    '氧化亚氮': 'N2O (ppm)',
    'CO2(ppm)': 'CO2 (ppm)',
    'CO2(PPM)': 'CO2 (ppm)',
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
    'DOC(mg/kg)': 'DOC (mg/kg)',
    '总氮（mg/L)': 'TN (mg/L)',
    '铵态氮（mg/L)': 'NH4+ (mg/L)',
    '硝态氮（mg/L)': 'NO3- (mg/L)',
}

def get_label(col):
    return label_map.get(col, col)

def draw_academic_pie(labels, sizes, colors, title, output_png, output_pdf):
    fig, ax = plt.subplots(figsize=(9, 9), facecolor='white')
    ax.set_facecolor('white')
    fig.patch.set_edgecolor('#d9d9d9')
    fig.patch.set_linewidth(1.5)

    explode = [0.04] * len(labels)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colors,
        autopct='%1.1f%%',
        pctdistance=0.76,
        startangle=90,
        explode=explode,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.8},
        textprops={'fontname': 'SimHei', 'fontsize': 12, 'color': '#333333'}
    )
    for text in texts + autotexts:
        text.set_fontname('SimHei')
        text.set_fontsize(12)
        text.set_color('#333333')

    centre_circle = plt.Circle((0, 0), 0.42, fc='white', linewidth=0)
    ax.add_artist(centre_circle)
    ax.set_title(title, fontname='SimHei', fontsize=18, pad=16, color='#222222')
    ax.axis('equal')
    legend = ax.legend(
        wedges,
        labels,
        title='组成',
        loc='center left',
        bbox_to_anchor=(1.05, 0.5),
        prop={'family': 'SimHei', 'size': 12},
        frameon=True,
        edgecolor='#bbbbbb',
        facecolor='white'
    )
    legend.get_title().set_fontsize(12)
    legend.get_title().set_fontname('SimHei')
    plt.tight_layout()
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()

def set_chinese_font():
    """确保中文显示的辅助函数"""
    pass  # rcParams 已经设置

# =========================
# 1. 读取数据
# =========================

file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"

winter = pd.read_excel(file_path, sheet_name='冬季')
spring = pd.read_excel(file_path, sheet_name='春季')

# =========================
# 2. 统一列名
# =========================

winter = winter.rename(columns={
    '平均值':'N2O平均值',
    '平均值.1':'CH4平均值',
    'CO2(ppm)':'CO2',
})

spring = spring.rename(columns={
    '平均值':'CH4平均值',
    '平均值.1':'N2O平均值',
    'CO2(PPM)':'CO2',
    '检查井编号':'采样点'
})

winter['季节'] = '冬季'
spring['季节'] = '春季'

# 统一采样点名称
if '采样点' not in winter.columns:
    winter['采样点'] = [f'R{i}' for i in range(1, len(winter)+1)]
if '采样点' not in spring.columns:
    spring['采样点'] = [f'R{i}' for i in range(1, len(spring)+1)]

# 合并数据
df = pd.concat([winter, spring], ignore_index=True)

# =========================
# 3. 数据预处理（修正重复电导率）
# =========================

# 转数值
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 修正重复电导率列
if '电导率(uS/cm)' not in df.columns and '电导率(us/cm)' in df.columns:
    df.rename(columns={'电导率(us/cm)': '电导率(uS/cm)'}, inplace=True)

# 缺失值查看
print("缺失值统计：")
print(df.isnull().sum())

# =========================
# 4. 描述性统计
# =========================

desc = df.describe()

print("\n描述性统计：")
print(desc)

desc.to_excel(os.path.join(output_dir, f"描述性统计_{timestamp}.xlsx"))

# =========================================================
# 第一部分：三相碳组成分析
# =========================================================

# =========================
# 5. 固液气三相碳组成
# =========================

# 气相碳
df['CH4平均值'] = pd.to_numeric(df['CH4平均值'], errors='coerce')
df['CO2'] = pd.to_numeric(df['CO2'], errors='coerce')
df['气相碳'] = df['CH4平均值'] + df['CO2']

# 液相碳
df['TC(mg/L)'] = pd.to_numeric(df['TC(mg/L)'], errors='coerce')
df['液相碳'] = df['TC(mg/L)']

# 固相碳
df['固总碳（g/kg)'] = pd.to_numeric(df['固总碳（g/kg)'], errors='coerce')
df['固相碳'] = df['固总碳（g/kg)']

# 求均值
gas_mean = df['气相碳'].mean()
liquid_mean = df['液相碳'].mean()
solid_mean = df['固相碳'].mean()

phase_df = pd.DataFrame({
    '相态':['气相','液相','固相'],
    '碳含量':[gas_mean, liquid_mean, solid_mean]
})

# 绘图
labels = phase_df['相态'].tolist()
sizes = phase_df['碳含量'].tolist()
colors = ['#4E79A7', '#F28E2B', '#E15759']
output_png = os.path.join(output_dir, f"图1_三相碳组成_{timestamp}.png")
output_pdf = os.path.join(output_dir, f"图1_三相碳组成_{timestamp}.pdf")
draw_academic_pie(labels, sizes, colors, '固液气三相碳组成', output_png, output_pdf)
print("图1已保存")

# =========================
# 6. 液相 TOC-IC-TC 组成
# =========================

if 'TOC（mg/L)' in df.columns and 'IC(mg/L)' in df.columns:
    liquid_carbon = pd.DataFrame({
        'TOC': [df['TOC（mg/L)'].mean()],
        'IC': [df['IC(mg/L)'].mean()]
    })

    labels = liquid_carbon.columns.tolist()
    sizes = liquid_carbon.iloc[0].tolist()
    colors = ['#59A14F', '#B07AA1']
    output_png = os.path.join(output_dir, f"图2_液相碳组成_{timestamp}.png")
    output_pdf = os.path.join(output_dir, f"图2_液相碳组成_{timestamp}.pdf")
    draw_academic_pie(labels, sizes, colors, '液相碳组成', output_png, output_pdf)
    print("图2已保存")

# =========================
# 7. 固相碳组成
# =========================

solid_cols = ['有机碳（g/kg)', '无机碳（g/kg)']
if 'DOC(mg/kg)' in df.columns:
    solid_cols.append('DOC(mg/kg)')

if all(col in df.columns for col in ['有机碳（g/kg)', '无机碳（g/kg)']):
    solid_data = {}
    for col in solid_cols:
        solid_data[get_label(col)] = [df[col].mean()]
    
    solid_df = pd.DataFrame(solid_data)

    labels = solid_df.columns.tolist()
    sizes = solid_df.iloc[0].tolist()
    colors = ['#76B7B2', '#EDC948', '#FF9DA7']
    output_png = os.path.join(output_dir, f"图3_固相碳组成_{timestamp}.png")
    output_pdf = os.path.join(output_dir, f"图3_固相碳组成_{timestamp}.pdf")
    draw_academic_pie(labels, sizes, colors, '固相碳组成', output_png, output_pdf)
    print("图3已保存")
    sys.exit(0)

# =========================================================
# 第二部分：碳迁移转化分析
# =========================================================

# =========================
# 8. DOC vs TOC
# =========================

if 'DOC(mg/kg)' in df.columns and 'TOC（mg/L)' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['DOC(mg/kg)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['TOC（mg/L)'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#1661ab')
        
        plt.xlabel('DOC', fontname='SimHei')
        plt.ylabel('TOC', fontname='SimHei')
        plt.title('DOC 与 TOC 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图4_DOC_TOC_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图4_DOC_TOC_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图4已保存")

# =========================
# 9. TOC vs CH4
# =========================

if 'TOC（mg/L)' in df.columns and 'CH4平均值' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['TOC（mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['CH4平均值'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#ed5736')
        
        plt.xlabel('TOC', fontname='SimHei')
        plt.ylabel('CH4', fontname='SimHei')
        plt.title('TOC 与 CH4 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图5_TOC_CH4_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图5_TOC_CH4_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图5已保存")

# =========================
# 10. TOC vs CO2
# =========================

if 'TOC（mg/L)' in df.columns and 'CO2' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['TOC（mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['CO2'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#f0c239')
        
        plt.xlabel('TOC', fontname='SimHei')
        plt.ylabel('CO2', fontname='SimHei')
        plt.title('TOC 与 CO2 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图6_TOC_CO2_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图6_TOC_CO2_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图6已保存")

# =========================
# 11. DO vs CH4
# =========================

if 'DO(mg/L)' in df.columns and 'CH4平均值' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['DO(mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['CH4平均值'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#845a33')
        
        plt.xlabel('DO', fontname='SimHei')
        plt.ylabel('CH4', fontname='SimHei')
        plt.title('DO 与 CH4 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图7_DO_CH4_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图7_DO_CH4_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图7已保存")

# =========================
# 12. COD vs CH4
# =========================

if 'COD（mg/L)' in df.columns and 'CH4平均值' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['COD（mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['CH4平均值'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#1661ab')
        
        plt.xlabel('COD', fontname='SimHei')
        plt.ylabel('CH4', fontname='SimHei')
        plt.title('COD 与 CH4 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图8_COD_CH4_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图8_COD_CH4_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图8已保存")

# =========================================================
# 第三部分：碳氮耦合分析
# =========================================================

# =========================
# 13. TOC vs TN
# =========================

if '总氮（mg/L)' in df.columns and 'TOC（mg/L)' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['总氮（mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['TOC（mg/L)'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#9ed048')
        
        plt.xlabel('TN', fontname='SimHei')
        plt.ylabel('TOC', fontname='SimHei')
        plt.title('TOC 与 TN 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图9_TOC_TN_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图9_TOC_TN_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图9已保存")

# =========================
# 14. NH4 vs CH4
# =========================

if '铵态氮（mg/L)' in df.columns and 'CH4平均值' in df.columns:
    plt.figure(figsize=(8,6))
    
    x_data = pd.to_numeric(df['铵态氮（mg/L)'], errors='coerce').dropna()
    y_data = pd.to_numeric(df['CH4平均值'], errors='coerce').dropna()
    
    valid_idx = x_data.index.intersection(y_data.index)
    x_data = x_data[valid_idx]
    y_data = y_data[valid_idx]
    
    if len(x_data) > 5:
        sns.regplot(x=x_data, y=y_data, color='#ed5736')
        
        plt.xlabel('NH4+', fontname='SimHei')
        plt.ylabel('CH4', fontname='SimHei')
        plt.title('NH4+ 与 CH4 的关系', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图10_NH4_CH4_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图10_NH4_CH4_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图10已保存")

# =========================================================
# 第四部分：相关性热图
# =========================================================

corr_cols = [
    'CH4平均值',
    'N2O平均值',
    'CO2',
    'VOCs(ppb)',
    'TOC（mg/L)',
    'IC(mg/L)',
    'TC(mg/L)',
    'DO(mg/L)',
    'COD（mg/L)',
    '总氮（mg/L)',
    '铵态氮（mg/L)',
    '硝态氮（mg/L)'
]

# 添加可选的列
for col in ['DOC(mg/kg)', '固总碳（g/kg)', '有机碳（g/kg)', '无机碳（g/kg)']:
    if col in df.columns:
        corr_cols.append(col)

# 筛选实际存在的列
corr_cols = [c for c in corr_cols if c in df.columns]

if len(corr_cols) >= 5:
    corr_df = df[corr_cols].copy()
    corr_df = corr_df.apply(pd.to_numeric, errors='coerce')
    corr = corr_df.corr(method='pearson')
    
    # 创建标签列表
    xtick_labels = [get_label(col) for col in corr.columns]
    ytick_labels = [get_label(col) for col in corr.index]
    
    plt.figure(figsize=(14,12))
    
    ax = sns.heatmap(
        corr,
        annot=True,
        cmap='RdBu_r',
        fmt='.2f',
        annot_kws={"fontname": "SimHei", "fontsize": 9},
        center=0,
        linewidths=0.5,
        xticklabels=xtick_labels,
        yticklabels=ytick_labels
    )
    
    plt.title('参数相关性热图', fontname='SimHei', fontsize=16)
    
    # 设置字体
    for text in ax.get_xticklabels():
        text.set_fontname('SimHei')
        text.set_fontsize(10)
        text.set_rotation(45)
    
    for text in ax.get_yticklabels():
        text.set_fontname('SimHei')
        text.set_fontsize(10)
        text.set_rotation(0)
    
    output_png = os.path.join(output_dir, f"图11_相关性热图_{timestamp}.png")
    output_pdf = os.path.join(output_dir, f"图11_相关性热图_{timestamp}.pdf")
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("图11已保存")

# =========================================================
# 第五部分：PCA主成分分析 (如果可用)
# =========================================================

# (省略，保持不变)

# =========================================================
# 第七部分：碳平衡分析
# =========================================================

# =========================
# 15. 液相碳比例
# =========================

if 'TOC（mg/L)' in df.columns and 'TC(mg/L)' in df.columns:
    df['TOC比例'] = df['TOC（mg/L)'] / df['TC(mg/L)']
    df['IC比例'] = df['IC(mg/L)'] / df['TC(mg/L)']

# =========================
# 16. 固相碳比例
# =========================

if '有机碳（g/kg)' in df.columns and '固总碳（g/kg)' in df.columns:
    df['固有机碳比例'] = (
        df['有机碳（g/kg)'] / 
        df['固总碳（g/kg)']
    )
    
    df['固无机碳比例'] = (
        df['无机碳（g/kg)'] / 
        df['固总碳（g/kg)']
    )

# =========================
# 17. 碳释放效率
# =========================

if 'CH4平均值' in df.columns and 'TOC（mg/L)' in df.columns:
    df['CH4_TOCT比'] = (
        df['CH4平均值'] / 
        df['TOC（mg/L)']
    )

# =========================
# 18. 气液碳比
# =========================

if '气相碳' in df.columns and '液相碳' in df.columns:
    df['气液碳比'] = (
        df['气相碳'] / 
        df['液相碳']
    )
    
    # =========================
    # 19. 气液碳比分布图
    # =========================
    
    plt.figure(figsize=(8,6))
    
    valid_data = df['气液碳比'].dropna()
    if len(valid_data) > 5:
        sns.histplot(valid_data, kde=True, color='#1661ab')
        
        plt.title('气液碳比分布', fontname='SimHei', fontsize=14)
        plt.xticks(fontname='SimHei')
        plt.yticks(fontname='SimHei')
        
        output_png = os.path.join(output_dir, f"图14_气液碳比_{timestamp}.png")
        output_pdf = os.path.join(output_dir, f"图14_气液碳比_{timestamp}.pdf")
        plt.savefig(output_png, dpi=300, bbox_inches='tight')
        plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        print("图14已保存")

# =========================================================
# 第八部分：结果导出
# =========================================================

df.to_excel(os.path.join(output_dir, f"最终分析结果_{timestamp}.xlsx"), index=False)

print('==============================')
print('所有分析完成')
print('图片已保存至:')
print(output_dir)
print('Excel结果已导出')
print('==============================')
