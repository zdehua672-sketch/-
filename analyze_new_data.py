import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from scipy.stats import mannwhitneyu
import re

def inspect_excel_structure(file_path, season_name):
    """详细检查Excel文件结构"""
    print(f"\n{'='*60}")
    print(f"📋 检查{season_name}数据结构")
    print(f"{'='*60}")
    
    df = pd.read_excel(file_path)
    print(f"文件路径: {file_path}")
    print(f"数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
    print(f"\n📊 所有列名:")
    for i, col in enumerate(df.columns):
        print(f"  {i+1:2d}. {col}")
    
    print(f"\n🔍 前3行数据:")
    print(df.head(3))
    
    # 检查采样点列
    sample_col = None
    for col in df.columns:
        if '采样点' in col or '检查井' in col:
            sample_col = col
            break
    
    if sample_col:
        print(f"\n📍 采样点信息 (列: {sample_col}):")
        print(f"  数量: {df[sample_col].nunique()}")
        print(f"  列表: {sorted([str(x) for x in df[sample_col].unique() if pd.notna(x)])}")
    
    # 检查数值列
    numeric_cols = []
    for col in df.columns:
        if any(x in str(col) for x in ['PPM', 'mg/L', 'us/cm', 'ppb', '%', 'pH', 'DO']):
            numeric_cols.append(col)
    
    print(f"\n📈 可能的数值指标列:")
    for col in numeric_cols:
        non_null_count = df[col].notna().sum()
        print(f"  - {col}: {non_null_count} 个非空值")
    
    return df, sample_col, numeric_cols

def standardize_column_names(df, season_name):
    """标准化列名格式"""
    print(f"\n🔧 标准化{season_name}列名...")
    
    # 清洗列名
    df.columns = [c.strip().replace('\r', '').replace('\n', '').replace('\t', '') for c in df.columns]
    
    # 列名映射表
    column_mapping = {
        # 氧化亚氮
        '氧化亚氮（PPM）': '氧化亚氮（PPM）',
        '氧化亚氮PPM': '氧化亚氮（PPM）',
        # 甲烷
        '甲烷(PPM)': '甲烷(PPM)',
        '甲烷PPM': '甲烷(PPM)',
        # CO2
        'CO2(PPM)': 'CO2(PPM)',
        'CO2PPM': 'CO2(PPM)',
        # DO
        'DO(mg/L)': 'DO(mg/L)',
        'DOmg/L': 'DO(mg/L)',
        # pH
        'pH': 'pH',
        # COD
        'COD（mg/L)': 'COD（mg/L)',
        'CODmg/L': 'COD（mg/L)',
    }
    
    # 应用列名映射
    renamed_cols = {}
    for old_name in df.columns:
        if old_name in column_mapping:
            new_name = column_mapping[old_name]
            if old_name != new_name:
                renamed_cols[old_name] = new_name
                print(f"  {old_name} → {new_name}")
    
    df.rename(columns=renamed_cols, inplace=True)
    
    # 统一采样点列名
    if '检查井编号' in df.columns and '采样点' not in df.columns:
        df.rename(columns={'检查井编号': '采样点'}, inplace=True)
        print(f"  检查井编号 → 采样点")
    
    return df

def clean_and_process_data(df, season_name):
    """清洗和处理数据"""
    print(f"\n🧹 清洗{season_name}数据...")
    
    # 清洗数值列
    def clean_numeric(series):
        s = series.astype(str).str.replace('g/L', '', regex=False).str.replace('mg/L', '', regex=False)
        return pd.to_numeric(s, errors='coerce')
    
    numeric_cols = df.select_dtypes(include=['object']).columns
    for col in numeric_cols:
        if any(x in str(col) for x in ['PPM', 'mg/L', 'us/cm', 'ppb', '%']):
            df[col] = clean_numeric(df[col])
            print(f"  清洗列: {col}")
    
    # 添加区域信息
    def get_point_num(p):
        if pd.isna(p):
            return 999
        res = re.findall(r'\d+', str(p))
        return int(res[0]) if res else 999
    
    if '采样点' in df.columns:
        df['采样点'] = df['采样点'].astype(str)
        df['point_num'] = df['采样点'].apply(get_point_num)
        df['Region'] = '教学与实验区 (R1-R12)'
        df.loc[df['point_num'] >= 13, 'Region'] = '食堂与生活区 (R13-R20)'
        print(f"  添加区域信息: {df['Region'].value_counts().to_dict()}")
    
    return df

def create_seasonal_comparison_chart(spring_data, winter_data):
    """创建冬春季对比图表"""
    print(f"\n{'='*60}")
    print("📊 创建冬春季对比图表")
    print(f"{'='*60}")
    
    # 字体配置
    plt.rcParams['font.sans-serif'] = ['SimHei']  
    plt.rcParams['axes.unicode_minus'] = False  
    
    # 配色方案
    season_colors = {'冬季': '#845a33', '春季': '#1661ab'}
    
    # 标准化指标列表
    standard_indicators = ['氧化亚氮（PPM）', '甲烷(PPM)', 'CO2(PPM)', 'DO(mg/L)', 'pH', 'COD（mg/L)']
    
    # 检查可用指标
    available_indicators = []
    indicator_info = {}
    
    print("\n🔍 检查可用指标:")
    for indicator in standard_indicators:
        info = {'春季': None, '冬季': None}
        
        if spring_data is not None and indicator in spring_data.columns:
            spring_vals = spring_data[indicator].dropna()
            if len(spring_vals) > 0:
                info['春季'] = {'count': len(spring_vals), 'mean': spring_vals.mean()}
        
        if winter_data is not None and indicator in winter_data.columns:
            winter_vals = winter_data[indicator].dropna()
            if len(winter_vals) > 0:
                info['冬季'] = {'count': len(winter_vals), 'mean': winter_vals.mean()}
        
        if info['春季'] or info['冬季']:
            available_indicators.append(indicator)
            indicator_info[indicator] = info
            
            status = []
            if info['春季']:
                status.append(f"春季{info['春季']['count']}个")
            if info['冬季']:
                status.append(f"冬季{info['冬季']['count']}个")
            print(f"  ✓ {indicator}: {' + '.join(status)}")
        else:
            print(f"  ❌ {indicator}: 无数据")
    
    if not available_indicators:
        print("\n❌ 没有找到可用的指标数据！")
        return
    
    # 创建对比图
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('冬春季主要指标对比分析', fontsize=20, fontname='SimHei', y=0.95)
    axes = axes.flatten()
    
    for i, indicator in enumerate(available_indicators[:6]):
        ax = axes[i]
        
        data_to_plot = []
        labels = []
        colors = []
        
        # 冬季数据
        if winter_data is not None and indicator in winter_data.columns:
            winter_vals = winter_data[indicator].dropna()
            if len(winter_vals) > 0:
                data_to_plot.append(winter_vals)
                labels.append(f'冬季\n(n={len(winter_vals)})')
                colors.append(season_colors['冬季'])
                print(f"    📊 {indicator} 冬季: {len(winter_vals)}个样本, 均值={winter_vals.mean():.3f}")
        
        # 春季数据
        if spring_data is not None and indicator in spring_data.columns:
            spring_vals = spring_data[indicator].dropna()
            if len(spring_vals) > 0:
                data_to_plot.append(spring_vals)
                labels.append(f'春季\n(n={len(spring_vals)})')
                colors.append(season_colors['春季'])
                print(f"    📊 {indicator} 春季: {len(spring_vals)}个样本, 均值={spring_vals.mean():.3f}")
        
        if data_to_plot:
            # 创建箱线图
            bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            # 添加统计显著性
            if len(data_to_plot) == 2:  # 有冬春两季数据
                try:
                    stat, p_value = mannwhitneyu(data_to_plot[0], data_to_plot[1], alternative='two-sided')
                    significance = ''
                    if p_value < 0.001: significance = '***'
                    elif p_value < 0.01: significance = '**'
                    elif p_value < 0.05: significance = '*'
                    
                    ax.text(0.5, 0.95, f'p={p_value:.3f}{significance}', 
                           transform=ax.transAxes, ha='center', va='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                    print(f"    🔬 {indicator} 统计检验: p={p_value:.3f}{significance}")
                except Exception as e:
                    print(f"    ⚠️ {indicator} 统计检验失败: {e}")
            
            # 格式化标签
            ylabel = indicator.replace('（PPM）', ' (ppm)').replace('（mg/L)', ' (mg/L)')
            ax.set_ylabel(ylabel, fontsize=12, fontname='SimHei')
            ax.set_title(f'{ylabel} 季节对比', fontsize=14, fontname='SimHei')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{indicator} 季节对比', fontsize=14, fontname='SimHei')
    
    # 隐藏多余子图
    for i in range(len(available_indicators), 6):
        axes[i].set_visible(False)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    
    # 保存PDF
    output_pdf = r"C:\Users\Administrator\Desktop\winter_spring_comparison.pdf"
    plt.savefig(output_pdf, format='pdf', bbox_inches='tight', dpi=300)
    print(f"\n✅ 冬春季对比图已保存: {output_pdf}")
    
    plt.close('all')

def create_comparison_charts(spring_data, winter_data):
    """创建对比图表"""
    # 字体配置
    plt.rcParams['font.sans-serif'] = ['SimHei']  
    plt.rcParams['axes.unicode_minus'] = False  
    
    # 配色方案
    season_colors = {'冬季': '#845a33', '春季': '#1661ab'}
    region_colors = {'教学与实验区 (R1-R12)': '#845a33', '食堂与生活区 (R13-R20)': '#1661ab'}
    
    # 主要指标列表及其可能的变体
    main_indicators = {
        '氧化亚氮（PPM）': ['氧化亚氮（PPM）', '氧化亚氮PPM'],
        '甲烷(PPM)': ['甲烷(PPM)', '甲烷PPM'],
        'CO2(PPM)': ['CO2(PPM)', 'CO2PPM'],
        'DO(mg/L)': ['DO(mg/L)', 'DOmg/L'],
        'pH': ['pH'],
        'COD（mg/L)': ['COD（mg/L)', 'CODmg/L']
    }
    
    # 检查可用指标
    available_indicators = []
    all_data = {'春季': spring_data, '冬季': winter_data}
    
    print("\n📊 指标匹配检查:")
    for standard_name, variants in main_indicators.items():
        found = False
        for season, df in all_data.items():
            if df is not None:
                for variant in variants:
                    if variant in df.columns:
                        available_indicators.append(standard_name)
                        print(f"  ✓ {standard_name} → 找到匹配: {variant} ({season})")
                        found = True
                        break
                if found:
                    break
        if not found:
            print(f"  ❌ {standard_name} → 未找到匹配")
    
    print(f"\n可用指标: {available_indicators}")
    
    if not available_indicators:
        print("⚠️  未找到匹配的指标列，请检查数据列名")
        return
    
    # 确定图表标题
    has_winter = winter_data is not None
    has_spring = spring_data is not None
    
    if has_winter and has_spring:
        title = '冬春季主要指标对比分析'
    elif has_winter:
        title = '冬季主要指标数据分析'
    elif has_spring:
        title = '春季主要指标数据分析'
    else:
        title = '主要指标数据分析'
    
    # 1. 季节对比图
    fig1, axes1 = plt.subplots(2, 3, figsize=(18, 12))
    fig1.suptitle(title, fontsize=20, fontname='SimHei', y=0.95)
    axes1 = axes1.flatten()
    
    for i, indicator in enumerate(available_indicators[:6]):
        ax = axes1[i]
        
        # 收集数据
        data_to_plot = []
        labels = []
        colors = []
        
        if has_winter and indicator in winter_data.columns:
            winter_values = winter_data[indicator].dropna()
            if len(winter_values) > 0:
                data_to_plot.append(winter_values)
                labels.append('冬季')
                colors.append(season_colors['冬季'])
                print(f"  ✓ 找到冬季数据: {indicator} ({len(winter_values)}个样本)")
        
        if has_spring and indicator in spring_data.columns:
            spring_values = spring_data[indicator].dropna()
            if len(spring_values) > 0:
                data_to_plot.append(spring_values)
                labels.append('春季')
                colors.append(season_colors['春季'])
                print(f"  ✓ 找到春季数据: {indicator} ({len(spring_values)}个样本)")
        
        if data_to_plot:
            # 创建箱线图
            bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            # 添加统计显著性
            if has_winter and has_spring:
                # 找到实际的列名
                winter_col = None
                spring_col = None
                
                for variant in main_indicators[indicator]:
                    if winter_col is None and variant in winter_data.columns:
                        winter_col = variant
                    if spring_col is None and variant in spring_data.columns:
                        spring_col = variant
                    if winter_col is not None and spring_col is not None:
                        break
                
                if winter_col is not None and spring_col is not None:
                    try:
                        winter_vals = winter_data[winter_col].dropna()
                        spring_vals = spring_data[spring_col].dropna()
                        if len(winter_vals) > 0 and len(spring_vals) > 0:
                            stat, p_value = mannwhitneyu(winter_vals, spring_vals, alternative='two-sided')
                            significance = ''
                            if p_value < 0.001: significance = '***'
                            elif p_value < 0.01: significance = '**'
                            elif p_value < 0.05: significance = '*'
                            
                            ax.text(0.5, 0.95, f'p={p_value:.3f}{significance}', 
                                   transform=ax.transAxes, ha='center', va='top',
                                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                    except:
                        pass
            
            # 格式化标签
            ylabel = indicator.replace('（PPM）', ' (ppm)').replace('（mg/L)', ' (mg/L)')
            ax.set_ylabel(ylabel, fontsize=12, fontname='SimHei')
            ax.set_title(f'{ylabel} 季节对比', fontsize=14, fontname='SimHei')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{indicator} 季节对比', fontsize=14, fontname='SimHei')
    
    # 隐藏多余子图
    for i in range(len(available_indicators), 6):
        axes1[i].set_visible(False)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    
    # 保存第一个PDF
    if has_winter and has_spring:
        output_pdf1 = r"C:\Users\Administrator\Desktop\winter_spring_comparison.pdf"
        save_msg = "冬春季对比图"
    elif has_winter:
        output_pdf1 = r"C:\Users\Administrator\Desktop\winter_data_analysis.pdf"
        save_msg = "冬季数据分析图"
    elif has_spring:
        output_pdf1 = r"C:\Users\Administrator\Desktop\spring_data_analysis.pdf"
        save_msg = "春季数据分析图"
    else:
        output_pdf1 = r"C:\Users\Administrator\Desktop\data_analysis.pdf"
        save_msg = "数据分析图"
    
    plt.savefig(output_pdf1, format='pdf', bbox_inches='tight', dpi=300)
    print(f"\n✓ {save_msg}已保存: {output_pdf1}")
    
    # 2. 区域差异分析图
    region_title = f'{title.replace("主要指标", "主要指标区域")}'
    fig2, axes2 = plt.subplots(2, 3, figsize=(18, 12))
    fig2.suptitle(region_title, fontsize=20, fontname='SimHei', y=0.95)
    axes2 = axes2.flatten()
    
    for i, indicator in enumerate(available_indicators[:6]):
        ax = axes2[i]
        
        # 收集各季节的区域数据
        all_data = []
        labels = []
        colors = []
        
        for season_name, df in [('春季', spring_data), ('冬季', winter_data)]:
            if df is not None and indicator in df.columns:
                for region in ['教学与实验区 (R1-R12)', '食堂与生活区 (R13-R20)']:
                    region_data = df[df['Region'] == region][indicator].dropna()
                    if len(region_data) > 0:
                        all_data.append(region_data)
                        labels.append(f'{season_name}\n{region}')
                        colors.append(region_colors[region])
        
        if all_data:
            bp = ax.boxplot(all_data, tick_labels=labels, patch_artist=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ylabel = indicator.replace('（PPM）', ' (ppm)').replace('（mg/L)', ' (mg/L)')
            ax.set_ylabel(ylabel, fontsize=12, fontname='SimHei')
            ax.set_title(f'{ylabel} 区域差异', fontsize=14, fontname='SimHei')
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{indicator} 区域差异', fontsize=14, fontname='SimHei')
    
    # 隐藏多余子图
    for i in range(len(available_indicators), 6):
        axes2[i].set_visible(False)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    
    # 保存第二个PDF
    output_pdf2 = r"C:\Users\Administrator\Desktop\regional_difference_analysis.pdf"
    plt.savefig(output_pdf2, format='pdf', bbox_inches='tight', dpi=300)
    print(f"✓ 区域差异分析图已保存: {output_pdf2}")
    
    plt.close('all')
    print("\n🎉 所有PDF图表已生成完成！")

# 主程序
def main():
    """主函数：分别读取两个文件，然后对比分析"""
    print("=== 冬春季数据对比分析 ===")
    
    # 文件路径
    spring_file = r"C:\Users\Administrator\Desktop\春季数据.xlsx"
    winter_file = r"C:\Users\Administrator\Desktop\冬季数据.xlsx"
    
    # 检查文件存在性
    spring_exists = os.path.exists(spring_file)
    winter_exists = os.path.exists(winter_file)
    
    print(f"春季数据文件: {'✓ 存在' if spring_exists else '❌ 不存在'} - {spring_file}")
    print(f"冬季数据文件: {'✓ 存在' if winter_exists else '❌ 不存在'} - {winter_file}")
    
    if not spring_exists and not winter_exists:
        print("\n❌ 没有找到任何数据文件！")
        return
    
    try:
        # 第一步：详细检查两个表格结构
        spring_df, spring_sample_col, spring_numeric_cols = inspect_excel_structure(spring_file, '春季') if spring_exists else (None, None, [])
        winter_df, winter_sample_col, winter_numeric_cols = inspect_excel_structure(winter_file, '冬季') if winter_exists else (None, None, [])
        
        # 第二步：标准化列名
        spring_data = standardize_column_names(spring_df, '春季') if spring_df is not None else None
        winter_data = standardize_column_names(winter_df, '冬季') if winter_df is not None else None
        
        # 第三步：清洗和处理数据
        spring_data = clean_and_process_data(spring_data, '春季') if spring_data is not None else None
        winter_data = clean_and_process_data(winter_data, '冬季') if winter_data is not None else None
        
        # 第四步：整合对比分析
        create_seasonal_comparison_chart(spring_data, winter_data)
        
        print(f"\n{'='*60}")
        print("🎉 分析完成！")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
