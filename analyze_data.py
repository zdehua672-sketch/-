# 简单的Excel文件结构检查
try:
    import pandas as pd
    print("pandas已安装，开始检查文件结构...")
except ImportError:
    print("需要先安装pandas，请运行: pip install pandas")
    exit()

import os
import numpy as np

def analyze_data(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return
    
    try:
        df = pd.read_excel(file_path)
        print("Columns in the file:")
        print(df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df.head())
        print("\nData summary:")
        print(df.info())
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    # 分析冬春数据.xlsx文件
    file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
    else:
        print("=== 分析冬春数据.xlsx文件 ===")
        
        try:
            # 首先查看所有sheet
            excel_file = pd.ExcelFile(file_path)
            print(f"\n文件包含的Sheet: {excel_file.sheet_names}")
            
            # 分析每个sheet
            for sheet_name in excel_file.sheet_names:
                print(f"\n{'='*50}")
                print(f"Sheet: {sheet_name}")
                print(f"{'='*50}")
                
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                print(f"\n数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
                
                print(f"\n列名:")
                for i, col in enumerate(df.columns, 1):
                    print(f"  {i:2d}. {col}")
                
                print(f"\n前3行数据:")
                print(df.head(3))
                
                print(f"\n数据类型:")
                print(df.dtypes)
                
                # 检查采样点信息
                if '采样点' in df.columns:
                    print(f"\n采样点数量: {df['采样点'].nunique()}")
                    print(f"采样点: {sorted(df['采样点'].unique())}")
                elif '检查井编号' in df.columns:
                    print(f"\n采样点数量: {df['检查井编号'].nunique()}")
                    print(f"采样点: {sorted(df['检查井编号'].unique())}")
                
                # 检查数值列的基本统计
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    print(f"\n数值列基本统计:")
                    print(df[numeric_cols].describe())
                
        except Exception as e:
            print(f"Error reading file: {e}")
