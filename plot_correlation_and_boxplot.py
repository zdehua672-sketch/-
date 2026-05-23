import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import os
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 字体与风格配置
# -----------------------------------------------------------------------------
plt.rcParams['font.sans-serif'] = ['SimHei']  
plt.rcParams['axes.unicode_minus'] = False  
plt.rcParams['font.family'] = 'sans-serif' 

# -----------------------------------------------------------------------------
# 2. 数据加载与预处理
# -----------------------------------------------------------------------------
# 支持单个或多个数据文件
data_file = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"
sheet_name = '春季' # 指定加载春季数据
# 使用自动找到的数据文件
file_paths = [data_file]

# 如果需要合并多个数据文件，请在此处添加其他文件路径
# file_paths.append(r"C:\Users\Administrator\Desktop\其他数据.xlsx")

df_list = []
for file_path in file_paths:
    try:
        df_temp = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"成功加载: {file_path} (Sheet: {sheet_name}, 数据量: {len(df_temp)})")
        df_list.append(df_temp)
    except Exception as e:
        print(f"读取失败: {file_path} - {e}")

if not df_list:
    print("错误：没有成功加载任何数据文件")
    exit()

# 合并数据
df = pd.concat(df_list, ignore_index=True)
print(f"合并后总数据量: {len(df)}")

# 2.1 基础清洗：去除列名空格换行、回车等不可见字符
df.columns = [c.strip().replace('\r', '').replace('\n', '').replace('\t', '') for c in df.columns]

# 统一采样点列名
if '检查井编号' in df.columns and '采样点' not in df.columns:
    df.rename(columns={'检查井编号': '采样点'}, inplace=True)

# 2.2 处理数值列 (关键：确保所有统计列都是 float 类型)
def clean_numeric(series):
    # 先转为字符串，去掉可能存在的单位如 'g/L' 或 'mg/L'
    s = series.astype(str).str.replace('g/L', '', regex=False).str.replace('mg/L', '', regex=False)
    # 转换为数值，非数值变 NaN
    return pd.to_numeric(s, errors='coerce')

# 气体指标列 (春季数据的列名略有不同，添加一些变体以适应)
gas_cols = ['氧化亚氮（PPM）', '甲烷(PPM)', 'CO2(PPM)', 'O2(%vol)', 'VOCs(ppb)']
# 液体指标列 (这里列出可能的所有变体，程序会自动筛选存在的列)
liquid_cols = [
    'DO(mg/L)', 'NaCl(mg/L)', '电导率(us/cm)', '液温', 'pH', 
    'TOC（mg/L)', '总氮（mg/L)', '总磷（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)', 'COD（mg/L)'
]

# 执行清洗
for col in gas_cols + liquid_cols:
    # 寻找是否存在列名或其相似变体
    actual_col = None
    if col in df.columns:
        actual_col = col
    else:
        # 尝试一些模糊匹配
        if '甲烷' in col:
            matches = [c for c in df.columns if '甲烷' in c and '平均值' not in c]
            if matches: actual_col = matches[0]
        elif '氧化亚氮' in col:
            matches = [c for c in df.columns if '氧化亚氮' in c and '平均值' not in c]
            if matches: actual_col = matches[0]
        elif 'COD' in col:
            matches = [c for c in df.columns if 'COD' in c]
            if matches: actual_col = matches[0]

    if actual_col:
        # 如果找到实际列名，但不是我们的标准名，则重命名
        if actual_col != col:
            df.rename(columns={actual_col: col}, inplace=True)
        df[col] = clean_numeric(df[col])

# 2.3 VOCs 换算 (ppb -> ppm)
if 'VOCs(ppb)' in df.columns:
    df['VOCs(ppm)'] = df['VOCs(ppb)'] / 1000
    gas_cols = [c if c != 'VOCs(ppb)' else 'VOCs(ppm)' for c in gas_cols]

# 检查实际可用的列
available_gas_cols = [c for c in gas_cols if c in df.columns]
available_liquid_cols = [c for c in liquid_cols if c in df.columns]

# -----------------------------------------------------------------------------
# 3. 相关性分析 (Spearman)
# -----------------------------------------------------------------------------
# 计算相关系数和 P 值
cross_corr = pd.DataFrame(index=available_liquid_cols, columns=available_gas_cols)
p_values = pd.DataFrame(index=available_liquid_cols, columns=available_gas_cols)

for l_col in available_liquid_cols:
    for g_col in available_gas_cols:
        # 仅针对同时具有气液数据的样本点计算
        valid_data = df[[l_col, g_col]].dropna()
        if len(valid_data) >= 3:
            corr, p = spearmanr(valid_data[l_col], valid_data[g_col])
            cross_corr.loc[l_col, g_col] = corr
            p_values.loc[l_col, g_col] = p
        else:
            cross_corr.loc[l_col, g_col] = np.nan
            p_values.loc[l_col, g_col] = np.nan

# 转换为浮点数矩阵
cross_corr = cross_corr.astype(float)
p_values = p_values.astype(float)

# 定义下标格式转换字典 (用于图表展示)
label_map = {
    '氧化亚氮（PPM）': r'$N_2O$ (ppm)',
    '甲烷(PPM)': r'$CH_4$ (ppm)',
    'CO2(PPM)': r'$CO_2$ (ppm)',
    'O2(%vol)': r'$O_2$ (%vol)',
    'VOCs(ppm)': 'VOCs (ppm)',
    'COD（mg/L)': 'COD (mg/L)',
    'NaCl(mg/L)': 'NaCl (mg/L)',
    '电导率(us/cm)': 'EC (us/cm)',
    '液温': 'Water Temp (°C)',
    'DO(mg/L)': 'DO (mg/L)'
}

# -----------------------------------------------------------------------------
# 4. 绘图：气-液相关性热图
# -----------------------------------------------------------------------------
plt.figure(figsize=(12, 10))

# 重命名 cross_corr 和 p_values 的行列以应用 LaTeX 格式
plot_corr = cross_corr.rename(index=label_map, columns=label_map)
plot_p = p_values.rename(index=label_map, columns=label_map)

ax = sns.heatmap(plot_corr, 
                 annot=True, 
                 fmt=".2f", 
                 cmap='RdBu_r', 
                 vmin=-1, vmax=1, 
                 center=0,
                 square=True, 
                 linewidths=0.8, 
                 linecolor='white',
                 cbar_kws={"shrink": .8, "label": "Spearman Correlation (ρ)"})

# 添加显著性星号
for i in range(plot_corr.shape[0]):
    for j in range(plot_corr.shape[1]):
        p_val = plot_p.iloc[i, j]
        if pd.notna(p_val):
            star = ""
            if p_val < 0.001: star = "***"
            elif p_val < 0.01: star = "**"
            elif p_val < 0.05: star = "*"
            if star:
                ax.text(j + 0.85, i + 0.3, star, ha='center', va='center', 
                        color='black', fontsize=14, fontweight='bold')

plt.title('春季气相指标与液相指标关联性热图', fontsize=18, fontname='SimHei', pad=25)
plt.xticks(rotation=45, ha='right', fontsize=11)
plt.yticks(fontsize=11)

# 添加外框
for _, spine in ax.spines.items():
    spine.set_visible(True)
    spine.set_linewidth(1.5)
    spine.set_edgecolor('black')

plt.tight_layout()

# 保存
output_png = r"C:\Users\Administrator\Desktop\spring_gas_liquid_correlation.png"
output_pdf = r"C:\Users\Administrator\Desktop\spring_gas_liquid_correlation.pdf"
plt.savefig(output_png, dpi=300, bbox_inches='tight')
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
print(f"Spring Heatmap saved to: {output_png}")
plt.close()

# -----------------------------------------------------------------------------
# 5. 液体指标区域分布图 (分面条形图)
# -----------------------------------------------------------------------------
# 定义区域 (春季点位可能包含非R开头的点，这里加个判断)
df['Region'] = '教学与实验区 (R1-R12)'
# 尝试提取R后面的数字
def get_point_num(p):
    import re
    res = re.findall(r'\d+', str(p))
    return int(res[0]) if res else 999

df['point_num'] = df['采样点'].apply(get_point_num)
df.loc[df['point_num'] >= 13, 'Region'] = '食堂与生活区 (R13-R20)'

# 选择4个关键液体指标
display_liquid = ['DO(mg/L)', 'pH', 'NaCl(mg/L)', 'COD（mg/L)']
display_liquid = [c for c in display_liquid if c in df.columns]

if display_liquid:
    fig, axes = plt.subplots(len(display_liquid), 1, figsize=(10, 4*len(display_liquid)), sharex=True)
    if len(display_liquid) == 1: axes = [axes] # 确保axes是列表
    chinese_palette = ['#845a33', '#1661ab']
    
    for i, (col, ax) in enumerate(zip(display_liquid, axes)):
        # 仅绘制有数据的点位
        valid_df = df[df[col].notna()]
        if not valid_df.empty:
            sns.barplot(x='采样点', y=col, hue='Region', data=valid_df, ax=ax, palette=chinese_palette, dodge=False)
            
            # 应用下标格式转换
            ylabel = label_map.get(col, col)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_xlabel('')
            ax.legend().set_visible(False)
            ax.grid(axis='y', linestyle='--', alpha=0.4)
            # 添加外框
            for _, spine in ax.spines.items():
                spine.set_visible(True)
                spine.set_linewidth(1)
                spine.set_edgecolor('black')

    if len(display_liquid) > 0:
        axes[0].legend(loc='upper right', frameon=True, prop={'family': 'SimHei'})
        axes[-1].set_xlabel('采样点位', fontsize=14, fontname='SimHei')
        plt.xticks(rotation=45)
    
    plt.suptitle('春季关键液体指标空间分布特征', fontsize=18, fontname='SimHei', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    output_box_png = r"C:\Users\Administrator\Desktop\spring_liquid_spatial_distribution.png"
    output_box_pdf = r"C:\Users\Administrator\Desktop\spring_liquid_spatial_distribution.pdf"
    plt.savefig(output_box_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_box_pdf, format='pdf', bbox_inches='tight')
    print(f"Spring Spatial plot saved to:\n- {output_box_png}\n- {output_box_pdf}")
    plt.close()
