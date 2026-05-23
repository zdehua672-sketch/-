# 检查文件结构
import pandas as pd

file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"

# 读取所有工作表名称
excel_file = pd.ExcelFile(file_path)
print("工作表名称:", excel_file.sheet_names)

# 查看冬季工作表结构
print("\n--- 冬季工作表 ---")
winter_header0 = pd.read_excel(file_path, sheet_name='冬季', header=None, nrows=5)
print(winter_header0)

# 查看春季工作表结构
print("\n--- 春季工作表 ---")
spring_header0 = pd.read_excel(file_path, sheet_name='春季', header=None, nrows=5)
print(spring_header0)
