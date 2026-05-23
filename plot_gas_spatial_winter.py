import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# -----------------------------------------------------------------------------
# 1. 字体与风格配置
# -----------------------------------------------------------------------------
plt.rcParams['font.sans-serif'] = ['SimHei']  
plt.rcParams['axes.unicode_minus'] = False  

# 定义中国风配色 (赭石, 靛蓝, 豆绿, 妃色, 缃色)
chinese_colors = ['#845a33', '#1661ab', '#9ed048', '#ed5736', '#f0c239']

# -----------------------------------------------------------------------------
# 2. 数据加载与预处理
# -----------------------------------------------------------------------------
# 使用冬季数据汇总文件，因为该文件数据最完整（包含CO2, O2, VOCs等）
data_file = r"C:\Users\Administrator\Desktop\硕士毕业论文\冬季数据汇总.xlsx"

try:
    df = pd.read_excel(data_file)
    print(f"成功加载: {data_file}")
except Exception as e:
    print(f"读取失败: {e}")
    exit()

# 清洗列名
df.columns = [c.strip().replace('\r', '').replace('\n', '').replace('\t', '') for c in df.columns]

# 定义气体指标及其 LaTeX 标签
gas_indicators = {
    '氧化亚氮（PPM）': r'$N_2O$ (ppm)',
    '甲烷（PPM）': r'$CH_4$ (ppm)',
    'CO2(mg/L)': r'$CO_2$ (mg/L)',
    'O2(%vol)': r'$O_2$ (%vol)',
    'VOCs(ppb)': 'VOCs (ppb)'
}

# 提取并清洗数据
plot_data = pd.DataFrame({'采样点': df['采样点']})
available_indicators = []

def clean_numeric(series):
    return pd.to_numeric(series.astype(str).str.replace('mg/L', '', regex=False).str.replace('g/L', '', regex=False), errors='coerce')

for col, label in gas_indicators.items():
    if col in df.columns:
        plot_data[label] = clean_numeric(df[col])
        available_indicators.append(label)

# VOCs 换算 (ppb -> ppm) 保持与春季一致
if 'VOCs (ppb)' in available_indicators:
    plot_data['VOCs (ppm)'] = plot_data['VOCs (ppb)'] / 1000
    available_indicators = [i if i != 'VOCs (ppb)' else 'VOCs (ppm)' for i in available_indicators]

# -----------------------------------------------------------------------------
# 3. 绘图：冬季气体浓度空间分布
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(len(available_indicators), 1, figsize=(12, 3 * len(available_indicators)), sharex=True)

# 采样点分区逻辑
def get_point_num(p):
    res = re.findall(r'\d+', str(p))
    return int(res[0]) if res else 999

plot_data['point_num'] = plot_data['采样点'].apply(get_point_num)
plot_data['Region'] = '教学区 (R1-R12)'
plot_data.loc[plot_data['point_num'] >= 13, 'Region'] = '生活区 (R13-R20)'

for i, (indicator, ax) in enumerate(zip(available_indicators, axes)):
    color = chinese_colors[i % len(chinese_colors)]
    
    # 绘制条形图
    sns.barplot(x='采样点', y=indicator, hue='Region', data=plot_data, 
                ax=ax, palette=[color, color], dodge=False, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel(indicator, fontsize=12, fontweight='bold')
    ax.set_xlabel('')
    ax.legend().set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # 添加分区线
    ax.axvline(x=11.5, color='gray', linestyle='--', linewidth=1.5)
    
    # 标注分区文本
    if i == 0:
        y_max = plot_data[indicator].max() * 1.1
        ax.text(5.5, y_max * 0.9, '教学与实验楼区 (R1-R12)', ha='center', fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))
        ax.text(15.5, y_max * 0.9, '食堂与生活区 (R13-R20)', ha='center', fontsize=12, fontname='SimHei', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7))

# 设置底部 X 轴
axes[-1].set_xlabel('采样点位', fontsize=14, fontname='SimHei')
plt.xticks(rotation=45, ha='right', fontname='Times New Roman')

# 整体美化
plt.suptitle('冬季各采样点气体浓度空间变化特征', fontsize=18, fontname='SimHei', y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.97])

# 保存
output_png = r"C:\Users\Administrator\Desktop\winter_gas_spatial_distribution.png"
output_pdf = r"C:\Users\Administrator\Desktop\winter_gas_spatial_distribution.pdf"
plt.savefig(output_png, dpi=300, bbox_inches='tight')
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')

print(f"Winter Gas Spatial plot saved to:\n- {output_png}\n- {output_pdf}")
plt.close()
