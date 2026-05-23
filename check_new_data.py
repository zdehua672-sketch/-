# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import os, sys

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

base = r'C:\Users\Administrator\Desktop\硕士毕业论文'
filepath = os.path.join(base, '冬春数据.xlsx')

print('='*70)
print('冬春数据.xlsx 全面检查')
print('='*70)

xl = pd.ExcelFile(filepath)
print(f'\nSheet数量: {len(xl.sheet_names)}')
print(f'Sheet名称: {xl.sheet_names}')

for s in xl.sheet_names:
    df = pd.read_excel(filepath, sheet_name=s)
    print(f'\n{"="*60}')
    print(f'【Sheet: {s}】')
    print(f'  形状: {df.shape[0]}行 x {df.shape[1]}列')
    print(f'  列名: {list(df.columns)}')
    print(f'  前5行:')
    print(df.head(5).to_string())
    print(f'  后3行:')
    print(df.tail(3).to_string())
    print(f'  数据类型:')
    print(df.dtypes.to_string())
</write_to_file>
