# -*- coding: utf-8 -*-
"""
生成示例数据文件
================
用于测试管线是否正常工作。生成的 data/sample_data.xlsx 包含:
  - 冬季 sheet: 18行采样数据
  - 春季 sheet: 18行采样数据
  - 变量: 气相(CH4/N2O/CO2) + 液相(TOC/DO/COD/pH等) + 固相(固总碳等) + 环境(气温/泥水)

用法:
    python scripts/generate_sample_data.py
"""

import os
import sys
import numpy as np
import pandas as pd

np.random.seed(42)

# 采样点
SAMPLING_POINTS = [
    '管口', '管中', '末端',
    '管口-进水', '管口-出水', '管中-进水', '管中-出水', '末端-进水', '末端-出水',
]
N_POINTS = len(SAMPLING_POINTS)

def generate_season_data(season, n_points):
    """生成一个季节的数据"""
    data = {
        '采样点': SAMPLING_POINTS[:n_points],
        '季节': [season] * n_points,
        '泥水状况': np.random.choice(['有泥', '无泥', '少量泥'], n_points),
    }

    # 气相变量
    if season == '冬季':
        data['CH4平均值'] = np.random.uniform(0.5, 5.0, n_points).round(2)
        data['N2O平均值'] = np.random.uniform(0.01, 0.15, n_points).round(4)
        data['CO2'] = np.random.uniform(200, 1500, n_points).round(1)
        data['VOCs(ppb)'] = np.random.uniform(10, 200, n_points).round(1)
        data['O2(%vol)'] = np.random.uniform(0.5, 8.0, n_points).round(2)
        data['H2S'] = np.random.uniform(0, 5, n_points).round(2)
    else:
        data['CH4平均值'] = np.random.uniform(0.2, 3.0, n_points).round(2)
        data['N2O平均值'] = np.random.uniform(0.005, 0.1, n_points).round(4)
        data['CO2'] = np.random.uniform(150, 1000, n_points).round(1)
        data['VOCs(ppb)'] = np.random.uniform(5, 150, n_points).round(1)
        data['O2(%vol)'] = np.random.uniform(1.0, 10.0, n_points).round(2)
        data['H2S'] = np.random.uniform(0, 3, n_points).round(2)

    # 液相变量
    data['DO(mg/L)'] = np.random.uniform(0.5, 6.0, n_points).round(2)
    data['pH'] = np.random.uniform(6.5, 8.0, n_points).round(2)
    data['液温'] = np.random.uniform(8, 25, n_points).round(1)
    data['电导率(uS/cm)'] = np.random.uniform(200, 1500, n_points).round(0)
    data['TOC（mg/L)'] = np.random.uniform(10, 80, n_points).round(1)
    data['TC(mg/L)'] = np.random.uniform(15, 100, n_points).round(1)
    data['IC(mg/L)'] = np.random.uniform(5, 40, n_points).round(1)
    data['COD（mg/L)'] = np.random.uniform(20, 150, n_points).round(1)
    data['总氮（mg/L)'] = np.random.uniform(5, 50, n_points).round(1)
    data['总磷（mg/L)'] = np.random.uniform(0.5, 5.0, n_points).round(2)
    data['铵态氮（mg/L)'] = np.random.uniform(1, 30, n_points).round(1)
    data['硝态氮（mg/L)'] = np.random.uniform(0.5, 10, n_points).round(1)
    data['NaCl(mg/L)'] = np.random.uniform(100, 800, n_points).round(0)

    # 固相变量
    data['固总碳（g/kg)'] = np.random.uniform(5, 30, n_points).round(1)
    data['有机碳（g/kg)'] = np.random.uniform(3, 20, n_points).round(1)
    data['无机碳（g/kg)'] = np.random.uniform(1, 10, n_points).round(1)
    data['DOC(mg/kg)'] = np.random.uniform(50, 300, n_points).round(0)
    data['全磷（g/kg)'] = np.random.uniform(0.5, 3.0, n_points).round(2)

    # 环境变量
    if season == '冬季':
        data['气温/℃'] = np.random.uniform(2, 10, n_points).round(1)
    else:
        data['气温/℃'] = np.random.uniform(15, 28, n_points).round(1)

    return pd.DataFrame(data)


def main():
    # 创建 data 目录
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)

    # 生成冬季和春季数据
    winter_df = generate_season_data('冬季', N_POINTS)
    spring_df = generate_season_data('春季', N_POINTS)

    # 写入 Excel（两个 sheet）
    output_path = os.path.join(data_dir, 'sample_data.xlsx')
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        winter_df.to_excel(writer, sheet_name='冬季', index=False)
        spring_df.to_excel(writer, sheet_name='春季', index=False)

    print(f"示例数据已生成: {output_path}")
    print(f"  冬季: {len(winter_df)} 行 x {len(winter_df.columns)} 列")
    print(f"  春季: {len(spring_df)} 行 x {len(spring_df.columns)} 列")
    print(f"  列名: {list(winter_df.columns)}")
    return output_path


if __name__ == '__main__':
    main()
