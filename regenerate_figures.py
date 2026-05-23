import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

# 字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False
sns.set(style='whitegrid', font='SimHei', font_scale=1.1)

# 输出路径
output_dir = r"C:\Users\Administrator\Desktop\分析结果"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# 标签映射
label_map = {
    '有机碳（g/kg)': '有机碳 (g/kg)',
    '无机碳（g/kg)': '无机碳 (g/kg)',
    'DOC(mg/kg)': 'DOC (mg/kg)',
}

def get_label(col):
    return label_map.get(col, col)

# 读取数据
file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"
winter = pd.read_excel(file_path, sheet_name='冬季')
spring = pd.read_excel(file_path, sheet_name='春季')

# 统一列名
winter = winter.rename(columns={'平均值':'N2O平均值', '平均值.1':'CH4平均值', 'CO2(ppm)':'CO2'})
spring = spring.rename(columns={'平均值':'CH4平均值', '平均值.1':'N2O平均值', 'CO2(PPM)':'CO2', '检查井编号':'采样点'})

winter['季节'] = '冬季'
spring['季节'] = '春季'

df = pd.concat([winter, spring], ignore_index=True)

# =========================
# 重新生成图2_液相碳组成
# =========================
if 'TOC（mg/L)' in df.columns and 'IC(mg/L)' in df.columns:
    liquid_carbon = pd.DataFrame({
        'TOC': [pd.to_numeric(df['TOC（mg/L)'], errors='coerce').mean()],
        'IC': [pd.to_numeric(df['IC(mg/L)'], errors='coerce').mean()]
    })

    liquid_carbon.plot(
        kind='bar',
        stacked=True,
        figsize=(10,6),
        color=['#1661ab', '#ed5736']
    )

    plt.title('液相碳组成', fontname='SimHei', fontsize=14)
    plt.ylabel('mg/L', fontname='SimHei', fontsize=12)
    plt.xlabel('', fontname='SimHei')
    plt.xticks(fontname='SimHei')
    plt.yticks(fontname='SimHei')
    plt.legend(
        prop={'family': 'SimHei'},
        bbox_to_anchor=(1.05, 1),
        loc='upper left',
        borderaxespad=0
    )

    output_png = os.path.join(output_dir, f"图2_液相碳组成_{timestamp}.png")
    output_pdf = os.path.join(output_dir, f"图2_液相碳组成_{timestamp}.pdf")
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("图2已重新生成")

# =========================
# 重新生成图3_固相碳组成
# =========================
solid_cols = ['有机碳（g/kg)', '无机碳（g/kg)']
if 'DOC(mg/kg)' in df.columns:
    solid_cols.append('DOC(mg/kg)')

if all(col in df.columns for col in ['有机碳（g/kg)', '无机碳（g/kg)']):
    solid_data = {}
    for col in solid_cols:
        solid_data[get_label(col)] = [pd.to_numeric(df[col], errors='coerce').mean()]
    
    solid_df = pd.DataFrame(solid_data)

    solid_df.plot(
        kind='bar',
        stacked=True,
        figsize=(10,6),
        color=['#9ed048', '#f0c239', '#ed5736']
    )

    plt.title('固相碳组成', fontname='SimHei', fontsize=14)
    plt.ylabel('g/kg', fontname='SimHei', fontsize=12)
    plt.xlabel('', fontname='SimHei')
    plt.xticks(fontname='SimHei')
    plt.yticks(fontname='SimHei')
    plt.legend(
        prop={'family': 'SimHei'},
        bbox_to_anchor=(1.05, 1),
        loc='upper left',
        borderaxespad=0
    )

    output_png = os.path.join(output_dir, f"图3_固相碳组成_{timestamp}.png")
    output_pdf = os.path.join(output_dir, f"图3_固相碳组成_{timestamp}.pdf")
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
    plt.show()
    plt.close()
    print("图3已重新生成")

print("\n完成！图2和图3已重新生成并保存。")
