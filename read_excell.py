import subprocess
import sys
import os

def install_package(package):
    """安装单个包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ {package} 安装失败")
        return False

def main():
    """主安装函数"""
    print("=== 开始安装数据分析所需包 ===")
    
    # 需要安装的包列表
    packages = [
        "pandas>=1.5.0",
        "numpy>=1.21.0", 
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "scipy>=1.9.0",
        "openpyxl>=3.0.0"
    ]
    
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()
    
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        package_name = package.split('>=')[0].split('==')[0]
        print(f"正在安装 {package_name}...")
        if install_package(package):
            success_count += 1
        print()
    
    print("=== 安装完成 ===")
    print(f"成功安装: {success_count}/{total_count} 个包")
    
    if success_count == total_count:
        print("\n🎉 所有包安装成功！现在可以运行数据分析脚本了。")
        print("\n运行命令:")
        print("python c:/Users/Administrator/python-sdk/analyze_new_data.py")
    else:
        print("\n⚠️  部分包安装失败，请检查网络连接或手动安装失败的包。")
        print("\n手动安装命令:")
        for package in packages:
            print(f"pip install {package}")

def check_excel_structure():
    """检查Excel文件结构"""
    file_path = r"C:\Users\Administrator\Desktop\冬春数据.xlsx"
    
    try:
        import pandas as pd
        print("\n" + "="*60)
        print("=== 检查Excel文件结构 ===")
        
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
            
        excel_file = pd.ExcelFile(file_path)
        print(f"\n📁 文件: {file_path}")
        print(f"📋 包含的Sheet: {excel_file.sheet_names}")
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n" + "-"*40)
            print(f"📊 Sheet: {sheet_name}")
            print("-"*40)
            
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"📏 维度: {df.shape[0]}行 × {df.shape[1]}列")
            
            print(f"\n📝 列名:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i:2d}. {col}")
            
            print(f"\n👀 前3行数据:")
            print(df.head(3).to_string())
            
            # 检查采样点信息
            if '采样点' in df.columns:
                print(f"\n📍 采样点数量: {df['采样点'].nunique()}")
                print(f"📍 采样点: {sorted(df['采样点'].unique())}")
            elif '检查井编号' in df.columns:
                print(f"\n📍 采样点数量: {df['检查井编号'].nunique()}")
                print(f"📍 采样点: {sorted(df['检查井编号'].unique())}")
                
        print(f"\n" + "="*60)
        print("✅ Excel文件结构检查完成！")
        
        # 检查是否包含冬春数据
        sheet_names = excel_file.sheet_names
        if '冬季' in sheet_names and '春季' in sheet_names:
            print("\n🎉 检测到冬季和春季数据，可以生成对比图表！")
            print("\n📈 运行以下命令生成PDF图表:")
            print("python c:/Users/Administrator/python-sdk/analyze_new_data.py")
        elif any('冬' in name or '春' in name for name in sheet_names):
            print("\n🔍 检测到可能包含季节数据的Sheet")
        else:
            print("\n⚠️  未明确检测到冬春数据，可能需要调整脚本")
            
        return True
        
    except Exception as e:
        print(f"❌ 读取Excel文件出错: {e}")
        return False

if __name__ == "__main__":
    main()
    
    # 安装完成后检查Excel文件结构
    print("\n" + "="*60)
    print("=== 准备检查Excel文件结构 ===")
    check_excel_structure()