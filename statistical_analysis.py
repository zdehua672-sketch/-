"""
=============================================================================
统计分析模块 - Statistical Analysis (No sklearn dependency)
描述统计、正态性检验、t检验/Mann-Whitney U、ANOVA/Kruskal-Wallis、
Pearson/Spearman相关、PCA、HCA、多元回归
=============================================================================
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster
import warnings
warnings.filterwarnings('ignore')

from variable_registry import DERIVED_VARS, get_analysis_cols, get_regression_pairs


class StandardScaler:
    """手动实现StandardScaler，避免sklearn依赖"""
    def __init__(self):
        self.mean_ = None
        self.std_ = None
    
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        self.std_ = np.std(X, axis=0, ddof=0)
        self.std_[self.std_ == 0] = 1.0
        return self
    
    def transform(self, X):
        return (X - self.mean_) / self.std_
    
    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)


class PCA:
    """手动实现PCA，避免sklearn依赖"""
    def __init__(self, n_components=2):
        self.n_components = n_components
        self.components_ = None
        self.explained_variance_ratio_ = None
        self.mean_ = None
    
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        X_centered = X - self.mean_
        n_samples = X_centered.shape[0]
        cov_matrix = np.dot(X_centered.T, X_centered) / (n_samples - 1)
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        self.components_ = eigenvectors[:, :self.n_components].T
        total_var = np.sum(eigenvalues)
        self.explained_variance_ratio_ = eigenvalues[:self.n_components] / total_var
        return self
    
    def transform(self, X):
        X_centered = X - self.mean_
        return np.dot(X_centered, self.components_.T)
    
    def fit_transform(self, X):
        self.fit(X)
        return self.transform(X)


class LinearRegression:
    """手动实现线性回归，避免sklearn依赖"""
    def __init__(self):
        self.coef_ = None
        self.intercept_ = None
    
    def fit(self, X, y):
        X = np.asarray(X)
        y = np.asarray(y).flatten()
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        X_with_intercept = np.column_stack([np.ones(X.shape[0]), X])
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        self.intercept_ = beta[0]
        self.coef_ = beta[1:]
        return self
    
    def predict(self, X):
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return np.dot(X, self.coef_) + self.intercept_


def r2_score(y_true, y_pred):
    """计算R²分数"""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - (ss_res / ss_tot)


class StatisticalAnalyzer:
    """统计分析器：对冬春数据进行全面的统计分析"""
    
    def __init__(self, df):
        self.df = df
        self.results = {}
    
    def descriptive_statistics(self, group_col='季节'):
        """描述性统计：按季节分组计算均值、标准差、中位数等"""
        print("\n" + "=" * 60)
        print("描述性统计分析")
        print("=" * 60)
        
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        numeric_cols = [c for c in numeric_cols if c not in DERIVED_VARS]
        
        desc_all = self.df[numeric_cols].describe()
        
        if group_col in self.df.columns:
            grouped = self.df.groupby(group_col)[numeric_cols]
            desc_grouped = grouped.describe(percentiles=[.25, .5, .75])
        
        self.results['描述统计'] = {
            '总体': desc_all,
            '分组': desc_grouped if group_col in self.df.columns else None
        }
        
        print("\n总体描述统计:")
        print(desc_all.round(2).to_string())
        
        return self.results['描述统计']
    
    def normality_test(self, cols=None):
        """正态性检验 (Shapiro-Wilk)"""
        print("\n" + "=" * 60)
        print("正态性检验 (Shapiro-Wilk)")
        print("=" * 60)
        
        if cols is None:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            exclude_cols = ['气相碳', '液相碳', '固相碳', 'TOC比例', 'IC比例', '气液碳比', 'CH4_TOCT比']
            cols = [c for c in numeric_cols if c not in exclude_cols]
        
        results = []
        for col in cols:
            data = self.df[col].dropna()
            if len(data) >= 3:
                stat, p_value = stats.shapiro(data)
                is_normal = p_value > 0.05
                results.append({
                    '变量': col,
                    '样本量': len(data),
                    'W统计量': round(stat, 4),
                    'p值': round(p_value, 4),
                    '正态性': '是' if is_normal else '否'
                })
        
        result_df = pd.DataFrame(results)
        self.results['正态性检验'] = result_df
        
        print(result_df.to_string())
        return result_df
    
    def compare_groups(self, group_col='季节', cols=None):
        """两组比较：正态数据用t检验，非正态用Mann-Whitney U"""
        print("\n" + "=" * 60)
        print("两组比较分析 (冬季 vs 春季)")
        print("=" * 60)
        
        if cols is None:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns
            exclude_cols = ['气相碳', '液相碳', '固相碳', 'TOC比例', 'IC比例', '气液碳比', 'CH4_TOCT比']
            cols = [c for c in numeric_cols if c not in exclude_cols]
        
        if group_col not in self.df.columns:
            print("错误: 找不到分组列")
            return None
        
        groups = self.df[group_col].unique()
        if len(groups) != 2:
            print(f"警告: 期望2组，实际有 {len(groups)} 组")
        
        results = []
        for col in cols:
            group_data = {}
            for g in groups:
                data = self.df[self.df[group_col] == g][col].dropna()
                group_data[g] = data
            
            if len(group_data) >= 2:
                g1, g2 = list(group_data.keys())[:2]
                data1, data2 = group_data[g1], group_data[g2]
                
                if len(data1) > 1 and len(data2) > 1:
                    _, p1 = stats.shapiro(data1) if len(data1) >= 3 else (0, 0)
                    _, p2 = stats.shapiro(data2) if len(data2) >= 3 else (0, 0)
                    
                    both_normal = (len(data1) >= 3 and p1 > 0.05 and 
                                   len(data2) >= 3 and p2 > 0.05)
                    
                    if both_normal:
                        stat, p_value = stats.ttest_ind(data1, data2)
                        method = 't检验'
                    else:
                        stat, p_value = stats.mannwhitneyu(data1, data2, alternative='two-sided')
                        method = 'Mann-Whitney U'
                    
                    mean1, std1 = data1.mean(), data1.std()
                    mean2, std2 = data2.mean(), data2.std()
                    
                    results.append({
                        '变量': col,
                        '方法': method,
                        f'{g1}_均值': round(mean1, 4),
                        f'{g1}_标准差': round(std1, 4),
                        f'{g2}_均值': round(mean2, 4),
                        f'{g2}_标准差': round(std2, 4),
                        '统计量': round(stat, 4),
                        'p值': round(p_value, 4),
                        '显著性': '***' if p_value <= 0.001 else (
                                  '**' if p_value <= 0.01 else (
                                  '*' if p_value <= 0.05 else 'n.s.'))
                    })
        
        result_df = pd.DataFrame(results)
        self.results['组间比较'] = result_df
        
        print(result_df.to_string())
        return result_df
    
    def correlation_analysis(self, method='pearson', cols=None):
        """相关性分析 (Pearson/Spearman)"""
        print(f"\n" + "=" * 60)
        print(f"相关性分析 ({method.capitalize()})")
        print("=" * 60)
        
        if cols is None:
            cols = get_analysis_cols(self.df)
        
        corr_df = self.df[cols].copy()
        corr_matrix = corr_df.corr(method=method)
        
        p_matrix = pd.DataFrame(np.ones_like(corr_matrix), 
                                index=corr_matrix.index, 
                                columns=corr_matrix.columns)
        for i in range(len(cols)):
            for j in range(len(cols)):
                if i != j:
                    data_i = corr_df[cols[i]].dropna()
                    data_j = corr_df[cols[j]].dropna()
                    common_idx = data_i.index.intersection(data_j.index)
                    if len(common_idx) > 3:
                        if method == 'pearson':
                            _, p = stats.pearsonr(data_i[common_idx], data_j[common_idx])
                        else:
                            _, p = stats.spearmanr(data_i[common_idx], data_j[common_idx])
                        p_matrix.iloc[i, j] = p
        
        self.results[f'{method}相关'] = {
            '相关系数': corr_matrix,
            'p值': p_matrix
        }
        
        print(f"\n相关系数矩阵 ({corr_matrix.shape[0]}x{corr_matrix.shape[1]})")
        print(corr_matrix.round(2).to_string())
        
        return corr_matrix, p_matrix
    
    def pca_analysis(self, n_components=2, cols=None):
        """PCA主成分分析 (使用手动实现，无sklearn依赖)"""
        print("\n" + "=" * 60)
        print("PCA主成分分析")
        print("=" * 60)
        
        if cols is None:
            cols = get_analysis_cols(self.df)

        pca_df = self.df[cols].copy()
        pca_df = pca_df.dropna()
        
        if len(pca_df) < 5:
            print("错误: 有效样本不足")
            return None
        
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(pca_df.values)
        
        pca = PCA(n_components=n_components)
        principal_components = pca.fit_transform(scaled_data)
        
        explained_variance = pca.explained_variance_ratio_
        loadings = pd.DataFrame(
            pca.components_.T,
            columns=[f'PC{i+1}' for i in range(n_components)],
            index=cols
        )
        
        scores = pd.DataFrame(
            principal_components,
            columns=[f'PC{i+1}' for i in range(n_components)]
        )
        if '季节' in self.df.columns:
            scores['季节'] = self.df.loc[pca_df.index, '季节'].values
        if '采样点' in self.df.columns:
            scores['采样点'] = self.df.loc[pca_df.index, '采样点'].values
        
        result = {
            'explained_variance_ratio': explained_variance,
            'loadings': loadings,
            'scores': scores,
            'scaler': scaler,
            'pca_model': pca,
            'n_samples': len(pca_df),
            'n_features': len(cols),
        }
        
        self.results['PCA'] = result
        
        print(f"\n样本数: {len(pca_df)}, 变量数: {len(cols)}")
        print(f"PC1 方差解释率: {explained_variance[0]*100:.2f}%")
        print(f"PC2 方差解释率: {explained_variance[1]*100:.2f}%")
        print(f"累计方差解释率: {sum(explained_variance)*100:.2f}%")
        print("\n载荷矩阵:")
        print(loadings.round(3).to_string())
        
        return result
    
    def hca_analysis(self, cols=None, n_clusters=3):
        """层次聚类分析 (HCA)"""
        print("\n" + "=" * 60)
        print("层次聚类分析 (HCA)")
        print("=" * 60)
        
        if cols is None:
            cols = get_analysis_cols(self.df)

        hca_df = self.df[cols].copy()
        hca_df = hca_df.dropna()
        
        if len(hca_df) < 5:
            print("错误: 有效样本不足")
            return None
        
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(hca_df.values)
        
        linked = linkage(scaled_data, method='ward')
        
        cluster_labels = fcluster(linked, n_clusters, criterion='maxclust')
        
        result = {
            'linked': linked,
            'cluster_labels': cluster_labels,
            'n_clusters': n_clusters,
            'data': hca_df,
            'scaled_data': scaled_data,
            'sample_indices': hca_df.index.tolist(),
        }
        
        self.results['HCA'] = result
        
        print(f"\n样本数: {len(hca_df)}, 聚类数: {n_clusters}")
        print(f"各类样本数: {pd.Series(cluster_labels).value_counts().sort_index().to_dict()}")
        
        return result
    
    def regression_analysis(self, x_col, y_col):
        """一元线性回归分析 (使用手动实现，无sklearn依赖)"""
        print(f"\n" + "=" * 60)
        print(f"回归分析: {x_col} -> {y_col}")
        print("=" * 60)
        
        x_data = pd.to_numeric(self.df[x_col], errors='coerce').dropna()
        y_data = pd.to_numeric(self.df[y_col], errors='coerce').dropna()
        
        common_idx = x_data.index.intersection(y_data.index)
        x = x_data[common_idx].values.reshape(-1, 1)
        y = y_data[common_idx].values
        
        if len(x) < 5:
            print("错误: 有效样本不足")
            return None
        
        model = LinearRegression()
        model.fit(x, y)
        y_pred = model.predict(x)
        
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y, y_pred)
        
        r, p_value = stats.pearsonr(x.flatten(), y)
        
        result = {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r2,
            'r': r,
            'p_value': p_value,
            'n': len(x),
            'x': x.flatten(),
            'y': y,
            'y_pred': y_pred,
            'x_col': x_col,
            'y_col': y_col,
        }
        
        key = f'回归_{x_col}_vs_{y_col}'
        self.results[key] = result
        
        print(f"\n样本量: {len(x)}")
        print(f"斜率: {slope:.4f}")
        print(f"截距: {intercept:.4f}")
        print(f"R²: {r2:.4f}")
        print(f"r: {r:.4f}")
        print(f"p值: {p_value:.4e}")
        print(f"显著性: {'***' if p_value <= 0.001 else '**' if p_value <= 0.01 else '*' if p_value <= 0.05 else 'n.s.'}")
        
        return result
    
    def run_all_analyses(self):
        """运行所有统计分析"""
        print("\n" + "=" * 60)
        print("开始全面统计分析")
        print("=" * 60)
        
        self.descriptive_statistics()
        self.normality_test()
        self.compare_groups()
        self.correlation_analysis(method='pearson')
        self.correlation_analysis(method='spearman')
        
        try:
            self.pca_analysis()
        except Exception as e:
            print(f"PCA分析出错: {e}")
        
        try:
            self.hca_analysis()
        except Exception as e:
            print(f"HCA分析出错: {e}")
        
        pairs = get_regression_pairs(self.df)
        for pair in pairs:
            x_col, y_col = pair['x'], pair['y']
            if x_col in self.df.columns and y_col in self.df.columns:
                try:
                    self.regression_analysis(x_col, y_col)
                except Exception as e:
                    print(f"回归分析 {x_col}->{y_col} 出错: {e}")
        
        print("\n" + "=" * 60)
        print("统计分析完成")
        print("=" * 60)
        
        return self.results
