"""
=============================================================================
数据加载与预处理模块 - Data Loader
自动读取采样数据表.xlsx和冬季数据汇总.xlsx，合并数据，识别变量类型
=============================================================================
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# ============================================================================
# 1. 变量分类定义
# ============================================================================
GAS_VARS = [
    '甲烷(ppm)', 'CH4平均值', '甲烷PPM', '甲烷（PPM）',
    '氧化亚氮(ppm)', '氧化亚氮（ppm）', '氧化亚氮PPM', '氧化亚氮（PPM）',
    'N2O平均值', 'CO2(ppm)', 'CO2(PPM)', 'CO2', 'CO2(mg/L)',
    'VOCs(ppb)', 'O2(%vol)', 'H2S',
]

LIQUID_VARS = [
    'DO(mg/L)', 'pH', '液温', '液温(℃）', '电导率(uS/cm)', '电导率(us/cm)',
    'TOC（mg/L)', 'TC(mg/L)', 'IC(mg/L)', 'COD（mg/L)', 'COD（锰）（mg/L)',
    '总氮（mg/L)', '总磷（mg/L)', '铵态氮（mg/L)', '硝态氮（mg/L)',
    'NaCl(mg/L)', 'NaCl(g/L)',
]

SOLID_VARS = [
    '固总碳（g/kg)', '有机碳（g/kg)', '无机碳（g/kg)',
    'DOC(mg/kg)', '全磷（g/kg)',
    '（固）铵态氮（mg/kg）', '（固）硝态氮（mg/kg）',
]

ENV_VARS = [
    '气温/℃', '气温℃', '气温（℃）', '泥水状况', '采样时间', '采样时段',
    '井深(m)', '管径（mm)', 'O2(%vol)', 'O2本底值',
    'CO2本底值', 'VOCs本底值',
]


# ============================================================================
# 2. 数据加载器
# ============================================================================
class DataLoader:
    """
    数据加载器：从多个数据源读取并合并冬春数据

    用法:
        # 方式1: 传入包含数据文件的目录
        loader = DataLoader(data_dir=r'C:\\Users\\xxx\\data')

        # 方式2: 传入主数据文件路径（自动推断同目录下的其他文件）
        loader = DataLoader(file_path=r'C:\\Users\\xxx\\data\\采样数据表.xlsx')

        # 方式3: 不传参数，使用当前目录
        loader = DataLoader()
    """

    def __init__(self, file_path=None, data_dir=None):
        # 优先使用 data_dir，其次从 file_path 推断，最后用当前目录
        if data_dir:
            self.base_dir = data_dir
        elif file_path and os.path.isfile(file_path):
            self.base_dir = os.path.dirname(os.path.abspath(file_path))
        else:
            self.base_dir = os.getcwd()

        # 自动查找数据文件
        self.sampling_file = self._find_file(
            ['采样数据表.xlsx', '采样数据表.xls', 'sampling_data.xlsx'],
            file_path if file_path and '采样' in str(file_path) else None,
        )
        self.winter_summary_file = self._find_file(
            ['冬季数据汇总.xlsx', '冬季数据汇总.xls', 'winter_summary.xlsx'],
            file_path if file_path and '冬季' in str(file_path) else None,
        )

        self.winter = None
        self.spring = None
        self.winter_summary = None
        self.df = None
        self.data_dict = {}
        self.quality_report = {}

    def _find_file(self, candidates, explicit_path=None):
        """在 base_dir 中查找候选文件名，返回完整路径或第一个候选"""
        if explicit_path and os.path.isfile(explicit_path):
            return explicit_path
        for name in candidates:
            path = os.path.join(self.base_dir, name)
            if os.path.isfile(path):
                return path
        # 返回第一个候选（后续 load_data 会报清晰的 FileNotFoundError）
        return os.path.join(self.base_dir, candidates[0])

    def load_data(self):
        """加载并合并所有数据源"""
        print("=" * 60)
        print("数据加载中...")
        print(f"数据目录: {self.base_dir}")
        print("=" * 60)

        # ========== 1. 加载采样数据表（气相数据） ==========
        print(f"\n[数据源1] {os.path.basename(self.sampling_file)} (气相数据)")
        if not os.path.isfile(self.sampling_file):
            raise FileNotFoundError(
                f"找不到采样数据表: {self.sampling_file}\n"
                f"请确认文件存在于: {self.base_dir}\n"
                f"或通过 DataLoader(file_path='...') / DataLoader(data_dir='...') 指定路径"
            )
        self.winter = pd.read_excel(self.sampling_file, sheet_name='冬季')
        self.spring = pd.read_excel(self.sampling_file, sheet_name='春季')
        
        print(f"  冬季: {self.winter.shape[0]} 行 x {self.winter.shape[1]} 列")
        print(f"  春季: {self.spring.shape[0]} 行 x {self.spring.shape[1]} 列")
        
        # 统一列名
        self._unify_columns()
        
        # 添加季节标签
        self.winter['季节'] = '冬季'
        self.spring['季节'] = '春季'
        
        # 统一采样点名称
        if '采样点' not in self.winter.columns:
            self.winter['采样点'] = [f'R{i}' for i in range(1, len(self.winter) + 1)]
        if '采样点' not in self.spring.columns:
            self.spring['采样点'] = [f'R{i}' for i in range(1, len(self.spring) + 1)]
        
        # 合并冬春数据
        df_gas = pd.concat([self.winter, self.spring], ignore_index=True)
        
        # 删除Unnamed列
        unnamed_cols = [c for c in df_gas.columns if 'Unnamed' in str(c)]
        if unnamed_cols:
            df_gas = df_gas.drop(columns=unnamed_cols)
            print(f"  已删除 {len(unnamed_cols)} 个Unnamed列")
        
        # ========== 2. 加载冬季数据汇总（液相数据） ==========
        print(f"\n[数据源2] {os.path.basename(self.winter_summary_file)} (液相数据)")
        if not os.path.isfile(self.winter_summary_file):
            raise FileNotFoundError(
                f"找不到冬季数据汇总: {self.winter_summary_file}\n"
                f"请确认文件存在于: {self.base_dir}"
            )
        self.winter_summary = pd.read_excel(self.winter_summary_file)
        print(f"  数据: {self.winter_summary.shape[0]} 行 x {self.winter_summary.shape[1]} 列")
        
        # 统一列名
        rename_summary = {
            'CO2(mg/L)': 'CO2',
            '液温(℃）': '液温',
            'NaCl(g/L)': 'NaCl(mg/L)',
            'COD（锰）（mg/L)': 'COD（mg/L)',
        }
        rename_summary = {k: v for k, v in rename_summary.items() if k in self.winter_summary.columns}
        self.winter_summary = self.winter_summary.rename(columns=rename_summary)
        
        # 添加季节标签
        self.winter_summary['季节'] = '冬季'
        
        # ========== 3. 合并数据 ==========
        print("\n[合并] 合并气相和液相数据...")
        
        # 清理冬季数据汇总：删除重复表头行和重复采样点
        ws = self.winter_summary.copy()
        # 删除包含'采样点'字符串的行（重复表头）
        ws = ws[ws['采样点'] != '采样点']
        # 删除第一行（NaN行）
        ws = ws.dropna(subset=['采样点'])
        # 删除重复的采样点，保留第一个
        ws = ws.drop_duplicates(subset=['采样点'], keep='first')
        # 转数值类型
        for col in ws.columns:
            if col not in ['采样点']:
                ws[col] = pd.to_numeric(ws[col], errors='coerce')
        
        print(f"  清理后冬季数据汇总: {ws.shape[0]} 行")
        
        # 清理采样数据表冬季数据：删除第一行（NaN采样点）
        df_gas = df_gas.dropna(subset=['采样点'])
        
        # 分离冬季和春季数据
        winter_gas = df_gas[df_gas['季节'] == '冬季'].copy()
        spring_gas = df_gas[df_gas['季节'] == '春季'].copy()
        
        # 冬季数据：用merge合并气相和液相数据
        winter_merged = winter_gas.merge(ws, on='采样点', how='left', suffixes=('', '_汇总'))
        # 删除重复列
        for col in list(winter_merged.columns):
            if col.endswith('_汇总'):
                base = col.replace('_汇总', '')
                if base in winter_merged.columns:
                    # 用汇总数据填充缺失值
                    winter_merged[base] = winter_merged[base].fillna(winter_merged[col])
                    winter_merged = winter_merged.drop(columns=[col])
        
        # 春季数据保持不变
        spring_merged = spring_gas.copy()
        
        # 合并冬春数据
        df_merged = pd.concat([winter_merged, spring_merged], ignore_index=True)
        
        # 转数值类型
        for col in df_merged.columns:
            if col not in ['采样点', '季节', '泥水状况', '采样时间', '采样时段']:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')
        
        self.df = df_merged
        
        print(f"\n合并后数据: {self.df.shape[0]} 行 x {self.df.shape[1]} 列")
        print(f"季节分布: {self.df['季节'].value_counts().to_dict()}")
        print(f"变量列表: {[c for c in self.df.columns if c not in ['采样点', '季节']]}")
        
        return self.df
    
    def _unify_columns(self):
        """统一冬季和春季的列名"""
        # 冬季列名统一
        rename_winter = {
            '平均值': 'N2O平均值',
            '平均值.1': 'CH4平均值',
            'CO2(ppm)': 'CO2',
            '氧化亚氮PPM': '氧化亚氮（PPM）',
            '甲烷PPM': '甲烷（PPM）',
            '气温/℃': '气温（℃）',
        }
        rename_winter = {k: v for k, v in rename_winter.items() if k in self.winter.columns}
        self.winter = self.winter.rename(columns=rename_winter)
        
        # 春季列名统一
        rename_spring = {
            '平均值': 'CH4平均值',
            '平均值.1': 'N2O平均值',
            'CO2(PPM)': 'CO2',
            '检查井编号': '采样点',
            '甲烷(PPM)': '甲烷（PPM）',
            '氧化亚氮（PPM）': '氧化亚氮（PPM）',
            '气温℃': '气温（℃）',
            '电导率(us/cm)': '电导率(uS/cm)',
        }
        rename_spring = {k: v for k, v in rename_spring.items() if k in self.spring.columns}
        self.spring = self.spring.rename(columns=rename_spring)
    
    def get_variable_categories(self):
        """自动识别变量类别"""
        categories = {
            '气相': [],
            '液相': [],
            '固相': [],
            '环境因子': [],
            '其他': [],
        }
        
        for col in self.df.columns:
            if col in ['采样点', '季节']:
                continue
            if col in GAS_VARS:
                categories['气相'].append(col)
            elif col in LIQUID_VARS:
                categories['液相'].append(col)
            elif col in SOLID_VARS:
                categories['固相'].append(col)
            elif col in ENV_VARS:
                categories['环境因子'].append(col)
            else:
                categories['其他'].append(col)
        
        return categories
    
    def check_data_quality(self):
        """检查数据质量：缺失值、异常值、重复值"""
        print("\n" + "=" * 60)
        print("数据质量检查")
        print("=" * 60)
        
        report = {}
        
        # 1. 缺失值检查
        missing = self.df.isnull().sum()
        missing_pct = (missing / len(self.df)) * 100
        missing_df = pd.DataFrame({
            '缺失数': missing,
            '缺失率(%)': missing_pct.round(2)
        })
        missing_df = missing_df[missing_df['缺失数'] > 0].sort_values('缺失率(%)', ascending=False)
        
        report['缺失值'] = missing_df
        print(f"\n[缺失值] 共有 {len(missing_df)} 列存在缺失值")
        if len(missing_df) > 0:
            print(missing_df.to_string())
        
        # 2. 异常值检查 (IQR方法)
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        outlier_info = {}
        for col in numeric_cols:
            data = self.df[col].dropna()
            if len(data) > 5:
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                outliers = data[(data < lower) | (data > upper)]
                if len(outliers) > 0:
                    outlier_info[col] = {
                        '异常值个数': len(outliers),
                        '异常值比例(%)': round(len(outliers) / len(data) * 100, 2),
                        '下限': round(lower, 2),
                        '上限': round(upper, 2),
                    }
        
        report['异常值'] = outlier_info
        print(f"\n[异常值] 共有 {len(outlier_info)} 列存在异常值")
        
        # 3. 重复值检查
        dup_rows = self.df.duplicated().sum()
        report['重复行'] = dup_rows
        print(f"\n[重复值] 重复行数: {dup_rows}")
        
        self.quality_report = report
        return report
    
    def generate_data_dictionary(self):
        """生成数据字典"""
        print("\n" + "=" * 60)
        print("生成数据字典")
        print("=" * 60)
        
        categories = self.get_variable_categories()
        
        rows = []
        for category, vars_list in categories.items():
            for col in vars_list:
                if col in self.df.columns:
                    dtype = self.df[col].dtype
                    n_missing = self.df[col].isnull().sum()
                    n_unique = self.df[col].nunique()
                    try:
                        is_numeric = np.issubdtype(dtype, np.number)
                    except TypeError:
                        is_numeric = False
                    if is_numeric:
                        mean_val = self.df[col].mean()
                        std_val = self.df[col].std()
                        min_val = self.df[col].min()
                        max_val = self.df[col].max()
                    else:
                        mean_val = std_val = min_val = max_val = None
                    
                    rows.append({
                        '变量名': col,
                        '类别': category,
                        '数据类型': dtype,
                        '非空数': len(self.df) - n_missing,
                        '缺失数': n_missing,
                        '唯一值数': n_unique,
                        '均值': round(mean_val, 4) if mean_val is not None else '',
                        '标准差': round(std_val, 4) if std_val is not None else '',
                        '最小值': round(min_val, 4) if min_val is not None else '',
                        '最大值': round(max_val, 4) if max_val is not None else '',
                    })
        
        data_dict = pd.DataFrame(rows)
        self.data_dict = data_dict
        
        print(f"数据字典共 {len(data_dict)} 个变量")
        print(data_dict[['变量名', '类别', '数据类型', '非空数', '缺失数']].to_string())
        
        return data_dict
    
    def save_data_dictionary(self, output_dir):
        """保存数据字典到Excel"""
        if self.data_dict is None or len(self.data_dict) == 0:
            self.generate_data_dictionary()
        
        filepath = os.path.join(output_dir, '数据字典.xlsx')
        self.data_dict.to_excel(filepath, index=False)
        print(f"\n数据字典已保存: {filepath}")
        return filepath
    
    def save_quality_report(self, output_dir):
        """保存数据质量报告到Markdown"""
        if not self.quality_report:
            self.check_data_quality()
        
        lines = []
        lines.append("# 数据质量报告\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"数据文件: {self.sampling_file}, {self.winter_summary_file}\n")
        lines.append(f"数据维度: {self.df.shape[0]} 行 x {self.df.shape[1]} 列\n")
        
        lines.append("## 1. 缺失值统计\n")
        missing_df = self.quality_report.get('缺失值', pd.DataFrame())
        if len(missing_df) > 0:
            lines.append("| 变量名 | 缺失数 | 缺失率(%) |")
            lines.append("|--------|--------|-----------|")
            for col, row in missing_df.iterrows():
                lines.append(f"| {col} | {row['缺失数']} | {row['缺失率(%)']} |")
        else:
            lines.append("无缺失值。\n")
        
        lines.append("\n## 2. 异常值统计\n")
        outlier_info = self.quality_report.get('异常值', {})
        if outlier_info:
            lines.append("| 变量名 | 异常值个数 | 异常值比例(%) | 下限 | 上限 |")
            lines.append("|--------|------------|---------------|------|------|")
            for col, info in outlier_info.items():
                lines.append(f"| {col} | {info['异常值个数']} | {info['异常值比例(%)']} | {info['下限']} | {info['上限']} |")
        else:
            lines.append("无异常值。\n")
        
        lines.append(f"\n## 3. 重复值\n")
        lines.append(f"重复行数: {self.quality_report.get('重复行', 0)}\n")
        
        lines.append("\n## 4. 变量分类\n")
        categories = self.get_variable_categories()
        for cat, vars_list in categories.items():
            if vars_list:
                lines.append(f"- **{cat}** ({len(vars_list)}个): {', '.join(vars_list)}")
        
        report_text = '\n'.join(lines)
        
        filepath = os.path.join(output_dir, '数据质量报告.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"\n数据质量报告已保存: {filepath}")
        return filepath
    
    def validate_data(self):
        """
        数据验证：检查数据是否满足分析要求

        Returns
        -------
        dict: {valid: bool, errors: list, warnings: list}
        """
        errors = []
        warnings = []

        if self.df is None:
            self.load_data()

        df = self.df

        # 1. 空数据检查
        if len(df) == 0:
            errors.append("数据为空（0行）")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # 2. 关键列存在性检查
        has_season = '季节' in df.columns
        has_sampling = '采样点' in df.columns
        if not has_season:
            warnings.append("缺少'季节'列，无法进行组间比较分析")
        if not has_sampling:
            warnings.append("缺少'采样点'列，无法进行空间分布分析")

        # 3. 数值列检查
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 3:
            errors.append(f"数值列不足（仅{len(numeric_cols)}个），至少需要3个数值变量")
        else:
            # 4. 每列有效数据量检查
            for col in numeric_cols:
                valid_count = df[col].notna().sum()
                if valid_count < 3:
                    warnings.append(f"列'{col}'有效数据仅{valid_count}个，可能无法进行统计分析")
                elif valid_count < len(df) * 0.5:
                    warnings.append(f"列'{col}'缺失率>{(1-valid_count/len(df))*100:.0f}%")

        # 5. 样本量检查
        if has_season:
            groups = df['季节'].value_counts()
            for group, count in groups.items():
                if count < 3:
                    errors.append(f"季节'{group}'仅{count}个样本，无法进行组间比较")
        if len(df) < 5:
            warnings.append(f"总样本量仅{len(df)}个，PCA/HCA等分析可能不可靠")

        # 6. 全NA列检查
        all_na_cols = [c for c in df.columns if df[c].isna().all()]
        if all_na_cols:
            warnings.append(f"以下列全为空值: {', '.join(all_na_cols[:5])}")

        valid = len(errors) == 0
        if errors:
            print(f"\n⚠ 数据验证失败 ({len(errors)}个错误):")
            for e in errors:
                print(f"  ✗ {e}")
        if warnings:
            print(f"\n⚠ 数据验证警告 ({len(warnings)}个):")
            for w in warnings:
                print(f"  △ {w}")
        if valid and not warnings:
            print("\n✓ 数据验证通过")

        return {"valid": valid, "errors": errors, "warnings": warnings}

    def get_analysis_ready_data(self):
        """返回分析就绪的数据（自动验证）"""
        if self.df is None:
            self.load_data()

        # 自动验证
        validation = self.validate_data()
        if not validation["valid"]:
            raise ValueError(
                f"数据验证失败:\n" + "\n".join(f"  - {e}" for e in validation["errors"])
            )
        
        df = self.df.copy()
        
        # 计算衍生变量
        # 1. 气相碳 (CH4 + CO2)
        ch4_col = None
        for c in ['CH4平均值', '甲烷（PPM）', '甲烷PPM', '甲烷(ppm)']:
            if c in df.columns:
                ch4_col = c
                break
        
        co2_col = None
        for c in ['CO2', 'CO2(mg/L)', 'CO2(ppm)', 'CO2(PPM)']:
            if c in df.columns:
                co2_col = c
                break
        
        if ch4_col and co2_col:
            df['CH4_ppm'] = df[ch4_col]
            df['CO2_ppm'] = df[co2_col]
            df['气相碳'] = df[ch4_col] + df[co2_col]
        
        # 2. 液相碳 (TOC作为液相碳指标)
        if 'TOC（mg/L)' in df.columns:
            df['液相碳'] = df['TOC（mg/L)']
        
        # 3. 气液碳比
        if '气相碳' in df.columns and '液相碳' in df.columns:
            df['气液碳比'] = df['气相碳'] / df['液相碳'].replace(0, np.nan)
        
        # 4. CH4/TOC比
        if ch4_col and 'TOC（mg/L)' in df.columns:
            df['CH4_TOC比'] = df[ch4_col] / df['TOC（mg/L)'].replace(0, np.nan)
        
        # 5. 总氮磷比
        if '总氮（mg/L)' in df.columns and '总磷（mg/L)' in df.columns:
            df['N_P比'] = df['总氮（mg/L)'] / df['总磷（mg/L)'].replace(0, np.nan)
        
        return df


# ============================================================================
# 3. 测试代码
# ============================================================================
if __name__ == '__main__':
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    loader = DataLoader(data_dir=data_dir)
    df = loader.load_data()
    categories = loader.get_variable_categories()
    print("\n变量分类:")
    for cat, vars_list in categories.items():
        print(f"  {cat}: {vars_list}")
    loader.check_data_quality()
    loader.generate_data_dictionary()

    output_dir = os.path.join(loader.base_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    loader.save_data_dictionary(output_dir)
    loader.save_quality_report(output_dir)
