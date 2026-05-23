# -*- coding: utf-8 -*-
import pandas as pd, os, sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

fp = os.path.join(r'C:\Users\Administrator\Desktop\硕士毕业论文','冬春数据.xlsx')
w = pd.read_excel(fp, sheet_name='冬季')
s = pd.read_excel(fp, sheet_name='春季')

print('=== 冬季列名 ===')
for i, c in enumerate(w.columns):
    print(f'{i}: [{c}]')

print('\n=== 春季列名 ===')
for i, c in enumerate(s.columns):
    print(f'{i}: [{c}]')

print('\n=== 冬季独有 ===')
for c in w.columns:
    if c not in s.columns:
        print(f'  [{c}]')

print('\n=== 春季独有 ===')
for c in s.columns:
    if c not in w.columns:
        print(f'  [{c}]')
</write_to_file>
