# -*- coding: utf-8 -*-
import pandas as pd, os, sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

fp = r'C:\Users\Administrator\Desktop\硕士毕业论文\冬春数据.xlsx'
s = pd.read_excel(fp, sheet_name='春季')
print('春季列名:', list(s.columns))
print('前2行:')
print(s.head(2).to_string())
</write_to_file>
