import os
import sys
import numpy as np
import pandas as pd

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from paper_context import PaperContext, _run_generate_figures

# 生成合成数据
np.random.seed(42)
N = 60
seasons = np.random.choice(['冬季', '春季', '夏季', '秋季'], size=N)
points = np.random.choice([f'P{i}' for i in range(1, 9)], size=N)

data = pd.DataFrame({
    '采样点': points,
    '季节': seasons,
    '甲烷(ppm)': np.random.gamma(2.0, 2.0, size=N) * 10,
    'CO2': np.random.normal(400, 50, size=N),
    'COD（mg/L)': np.abs(np.random.normal(50, 20, size=N)),
    'DO(mg/L)': np.random.uniform(0, 8, size=N),
    'TOC（mg/L)': np.random.normal(5, 2, size=N),
    'pH': np.random.normal(7, 0.3, size=N),
    'VOCs(ppb)': np.random.gamma(1.5, 10, size=N),
    '总氮（mg/L)': np.random.normal(10, 3, size=N),
    '铵态氮（mg/L)': np.random.normal(2, 1, size=N),
    'IC(mg/L)': np.random.normal(1, 0.5, size=N),
    'NaCl(mg/L)': np.random.normal(50, 10, size=N),
})

# 插入一些极端值
for _ in range(3):
    idx = np.random.randint(0, N)
    data.at[idx, '甲烷(ppm)'] *= 10

out_dir = os.path.join(os.path.dirname(__file__), 'test_output')
ctx = PaperContext(df=data, output_dir=out_dir, language='zh')

os.makedirs(out_dir, exist_ok=True)

print('Running figure generation...')
_run_generate_figures(ctx)
print('Done. Generated figures saved to:', os.path.join(out_dir, 'figures'))
print('Figures list:', list(ctx.figures.keys()))
