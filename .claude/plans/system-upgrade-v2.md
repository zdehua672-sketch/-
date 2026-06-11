# 系统升级 v2 — 逐文件逐函数实施方案

---

## 阶段B：图表补全 + 字体修复（最优先）

### B1. 新增8种基础图表
**文件**：`scientific_visualization_agent.py`
**位置**：在 `VisualizationAgent` 类内，`plot_distribution` 方法之后（约L2397后）插入

```python
# 新增方法 1：plot_bar — 分组/堆叠条形图
def plot_bar(self, x, y, group_col=None, kind='grouped', title=None, **kwargs):
    """
    条形图
    kind: 'grouped'(分组) | 'stacked'(堆叠) | 'horizontal'(水平)
    """
    # 1. 数据准备：按 group_col 分组聚合（mean±std）
    # 2. 绘图：sns.barplot 或 ax.bar
    # 3. 样式：调用 StylePresets.apply(self._current_style)
    # 4. 字体：所有 ax.set_xlabel/set_ylabel/set_title 使用 fontproperties=CN_FONT_PROP
    # 5. 保存：调用 save_figure()
    # 6. 返回路径

# 新增方法 2：plot_line — 折线图（带置信区间）
def plot_line(self, x, y, group_col=None, ci=True, title=None, **kwargs):
    """
    折线图
    ci: True=显示95%置信区间, False=只显示均值线
    """
    # sns.lineplot(x=x, y=y, hue=group_col, ci=ci)
    # 误差带用 fill_between

# 新增方法 3：plot_scatter — 散点图（带回归线）
def plot_scatter(self, x, y, group_col=None, regression=True, title=None, **kwargs):
    """散点图，可选拟合回归线"""
    # sns.scatterplot + sns.regplot(regression=True时)

# 新增方法 4：plot_box — 箱线图
def plot_box(self, x, y, group_col=None, title=None, **kwargs):
    """箱线图，x为分类变量，y为连续变量"""
    # sns.boxplot + sns.stripplot(叠加散点)

# 新增方法 5：plot_violin — 小提琴图
def plot_violin(self, x, y, group_col=None, title=None, **kwargs):
    """小提琴图"""
    # sns.violinplot + 内嵌箱线图

# 新增方法 6：plot_pie — 饼图
def plot_pie(self, values, labels, title=None, **kwargs):
    """饼图/环形图，用于占比分析"""
    # ax.pie + autopct

# 新增方法 7：plot_radar — 雷达图
def plot_radar(self, categories, values_dict, title=None, **kwargs):
    """雷达图，多维对比"""
    # polar subplot + fill

# 新增方法 8：plot_waterfall — 瀑布图
def plot_waterfall(self, categories, values, title=None, **kwargs):
    """瀑布图，展示增减分解"""
    # ax.bar + 底部偏移计算
```

**每个方法的共同规范**：
- 开头调用 `StylePresets.apply(self._current_style)` 应用字体
- 所有文字元素使用 `fontproperties=CN_FONT_PROP`（从 `academic_plot_style` 导入）
- 图例 `prop=CN_FONT_PROP`
- 保存调用 `save_figure(fig, filename, self.output_dir, formats=['png','pdf','svg'])`
- 返回 `{'path': filepath, 'caption': caption}`

### B2. 字体乱码彻底修复
**文件**：`academic_plot_style.py`

**改动1**：`setup_fonts()` 函数（L59-123）
```python
# 当前问题：CN_FONT_PROP 是局部变量，返回后作为全局变量
# 但部分绑图函数可能未导入/未使用这个变量

# 修复：新增 ensure_chinese_text() 函数
def ensure_chinese_text(ax, title=None, xlabel=None, ylabel=None):
    """确保 Axes 上的所有文本使用中文字体"""
    if title:
        ax.set_title(title, fontproperties=CN_FONT_PROP)
    if xlabel:
        ax.set_xlabel(xlabel, fontproperties=CN_FONT_PROP)
    if ylabel:
        ax.set_ylabel(ylabel, fontproperties=CN_FONT_PROP)
    # 刻度标签也要设置
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(CN_FONT_PROP)
```

**改动2**：`save_figure()` 函数（约L276）
```python
# 在保存前验证：生成一个包含中文的测试文本，检查是否能正确渲染
# 如果检测到方块，自动切换字体并重新保存
```

**文件**：`scientific_visualization_agent.py`

**改动3**：在 `VisualizationAgent.__init__()` 中（约L975）：
```python
def __init__(self, df=None, output_dir='./figures', style='chinese', ...):
    # 强制调用 setup_fonts() 确保字体已初始化
    from academic_plot_style import setup_fonts, CN_FONT_PROP
    setup_fonts()
    self._cn_font = CN_FONT_PROP
```

**改动4**：在所有现有 `plot_*` 方法中，找到 `ax.set_xlabel`/`ax.set_ylabel`/`ax.set_title` 调用，统一加上 `fontproperties=self._cn_font`

### B3. 图表自动推荐增强
**文件**：`scientific_visualization_agent.py` → `AutoRecommender` 类（约L275）

**改动**：在 `recommend()` 方法中增加基础图表推荐逻辑：
```python
# 当前：只推荐 multivariate/pca/heatmap/sankey 等专业图
# 修改后：根据变量类型推荐基础图

def recommend(self, df, analysis_results=None):
    recs = []
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # 分类变量 → 条形图、箱线图
    for cat in cat_cols:
        for num in num_cols[:3]:
            recs.append({'method': 'plot_bar', 'args': {'x': cat, 'y': num}, 'priority': 8})
            recs.append({'method': 'plot_box', 'args': {'x': cat, 'y': num}, 'priority': 7})

    # 连续变量对 → 散点图、折线图
    for i, x in enumerate(num_cols[:5]):
        for y in num_cols[i+1:5]:
            recs.append({'method': 'plot_scatter', 'args': {'x': x, 'y': y}, 'priority': 9})

    # 分类变量占比 → 饼图
    for cat in cat_cols:
        recs.append({'method': 'plot_pie', 'args': {'col': cat}, 'priority': 5})

    # 加上原有的专业图推荐
    # ...
    return sorted(recs, key=lambda r: -r['priority'])
```

### B4. 批量生成基础图表入口
**文件**：`scientific_visualization_agent.py`

**新增函数**（模块级，在 `visualize()` 函数附近）：
```python
def plot_all_essentials(df, output_dir='./figures', style='chinese'):
    """一键生成所有基础图表，返回路径字典"""
    agent = VisualizationAgent(df=df, output_dir=output_dir, style=style)
    paths = {}

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    # 1. 每个数值变量的分布图
    for col in num_cols[:6]:
        paths[f'dist_{col}'] = agent.plot_distribution(col=col)

    # 2. 分类变量的条形图
    for cat in cat_cols[:3]:
        for num in num_cols[:3]:
            paths[f'bar_{cat}_{num}'] = agent.plot_bar(x=cat, y=num)

    # 3. 数值变量对的散点图
    for i, x in enumerate(num_cols[:4]):
        for y in num_cols[i+1:4]:
            paths[f'scatter_{x}_{y}'] = agent.plot_scatter(x=x, y=y)

    # 4. 相关性热力图
    if len(num_cols) >= 3:
        paths['heatmap'] = agent.plot_heatmap()

    # 5. 箱线图（按季节/分组）
    for cat in cat_cols[:2]:
        for num in num_cols[:4]:
            paths[f'box_{cat}_{num}'] = agent.plot_box(x=cat, y=num)

    return paths
```

---

## 阶段A：数据分析增强

### A1. DataExplorer 扩展
**文件**：`data_driven_pipeline.py` → `DataExplorer` 类

**改动1**：新增 `_explore_effect_size()` 方法
```python
def _explore_effect_size(self):
    """计算效应量（Cohen's d, eta-squared）"""
    findings = []
    numeric_cols = self.df.select_dtypes(include=[np.number]).columns
    cat_cols = self.df.select_dtypes(include=['object', 'category']).columns

    for cat in cat_cols:
        groups = [g[1].values for g in self.df.groupby(cat)]
        if len(groups) == 2:
            # Cohen's d
            n1, n2 = len(groups[0]), len(groups[1])
            pooled_std = np.sqrt(((n1-1)*groups[0].std()**2 + (n2-1)*groups[1].std()**2) / (n1+n2-2))
            for col in numeric_cols:
                d = (groups[0].mean() - groups[1].mean()) / pooled_std if pooled_std > 0 else 0
                if abs(d) > 0.5:  # 中等以上效应
                    findings.append({
                        'type': 'effect_size',
                        'variable': col,
                        'group_var': cat,
                        'effect_size': round(d, 3),
                        'magnitude': 'large' if abs(d) > 0.8 else 'medium',
                        'importance': 'high' if abs(d) > 0.8 else 'medium',
                    })
    return findings
```

**改动2**：新增 `_explore_distribution_fit()` 方法
```python
def _explore_distribution_fit(self):
    """分布拟合检验（Shapiro-Wilk 正态性检验）"""
    findings = []
    for col in self.df.select_dtypes(include=[np.number]).columns:
        data = self.df[col].dropna()
        if len(data) >= 3 and len(data) <= 5000:
            stat, p = scipy_stats.shapiro(data)
            if p < 0.05:
                findings.append({
                    'type': 'distribution',
                    'variable': col,
                    'test': 'shapiro_wilk',
                    'statistic': round(stat, 4),
                    'p_value': round(p, 4),
                    'is_normal': False,
                    'importance': 'medium',
                })
    return findings
```

**改动3**：在 `explore()` 方法末尾调用新方法
```python
def explore(self):
    # ... 现有代码 ...
    findings.extend(self._explore_effect_size())
    findings.extend(self._explore_distribution_fit())
    return findings
```

### A2. 统计分析增强
**文件**：`statistical_analysis.py`

**新增类**：
```python
class ANOVA:
    """单因素方差分析"""
    @staticmethod
    def one_way(*groups):
        stat, p = scipy_stats.f_oneway(*groups)
        return {'f_stat': stat, 'p_value': p, 'significant': p < 0.05}

class NonParametricTests:
    """非参数检验"""
    @staticmethod
    def mann_whitney(group1, group2):
        stat, p = scipy_stats.mannwhitneyu(group1, group2)
        return {'u_stat': stat, 'p_value': p}

    @staticmethod
    def kruskal_wallis(*groups):
        stat, p = scipy_stats.kruskal(*groups)
        return {'h_stat': stat, 'p_value': p}
```

---

## 阶段E：写作+排版完善

### E1. Discussion 段落逻辑增强
**文件**：`paper_writing_agent.py` → `DiscussionGenerator`

**改动**：在 `_generate_zh()` 方法中，替换 `_discuss_findings_zh()` 的实现

```python
# 当前：每个 finding 独立一段，无衔接
# 修改后：增加过渡句 + 文献对比 + 机制解释

def _discuss_findings_zh(self):
    """逐发现讨论，带衔接和文献对比"""
    parts = []
    findings = sorted(self.analysis_results.items(), key=lambda x: -len(str(x[1])))

    for i, (key, data) in enumerate(findings[:5]):
        # 1. 描述发现
        desc = self._describe_finding(key, data)
        # 2. 与文献对比
        comparison = self._search_literature(key, max_results=2)
        lit_text = self._format_comparison(comparison) if comparison else ''
        # 3. 机制解释
        mechanism = MechanismKB.find_mechanism_for_correlation(*key.split('_vs_')[:2])
        mech_text = f"这可能与{mechanism}有关。" if mechanism else ''
        # 4. 过渡句（如果不是最后一段）
        transition = self._transition_sentence(i, len(findings)) if i < len(findings)-1 else ''

        part = f'{desc}\n{lit_text}{mech_text}\n{transition}'
        parts.append(part)

    return '\n\n'.join(parts)

def _transition_sentence(self, current, total):
    """生成段落间过渡句"""
    transitions = [
        '除上述发现外，',
        '此外，',
        '与此同时，',
        '值得注意的是，',  # 这个要替换为更自然的
    ]
    # 用更学术的过渡词
    academic_transitions = [
        '进一步分析表明，',
        '此外，本研究还发现，',
        '与此相关的是，',
        '从多相耦合的角度看，',
    ]
    return academic_transitions[current % len(academic_transitions)]
```

### E2. 排版文本清理
**文件**：`document_assembler.py`

**新增方法** `_clean_markdown()`（在 `_render_text` 之前）：
```python
def _clean_markdown(self, text: str) -> str:
    """清理 markdown 符号，保留纯文本"""
    import re

    # 1. 去掉标题符号 # ## ###（保留文字）
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 2. **bold** → bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # 3. *italic* → italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # 4. `code` → code
    text = re.sub(r'`(.+?)`', r'\1', text)

    # 5. ```code block``` → 去掉
    text = re.sub(r'```[\s\S]*?```', '', text)

    # 6. --- 分隔线 → 去掉
    text = re.sub(r'^-{3,}\s*$', '', text, flags=re.MULTILINE)

    # 7. [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # 8. ![alt](img) → 去掉
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)

    # 9. HTML 标签 → 去掉
    text = re.sub(r'<[^>]+>', '', text)

    # 10. 连续空行 → 最多2个空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # 11. 行首多余空格
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)

    return text.strip()
```

**在 `_render_text()` 开头调用**：
```python
def _render_text(self, data):
    text = data.get('text', '')
    if not text:
        return
    text = self._clean_markdown(text)  # ← 新增
    # ... 后续逻辑不变
```

**同样在 `_render_section()` 中调用**：
```python
def _render_section(self, data):
    heading = data['heading']
    text = data.get('text')
    self.doc.add_heading(heading, level=level)
    if text:
        text = self._clean_markdown(text)  # ← 新增
        self._render_text({'text': text, ...})
```

### E3. DOCX 排版样式增强
**文件**：`document_assembler.py` → `_setup_document()`

**改动**：
```python
def _setup_document(self):
    # 页边距（当前可能没设置）
    for section in self.doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)

    # 默认段落样式
    style = self.doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5  # 1.5倍行距
    style.paragraph_format.space_after = Pt(6)  # 段后6pt
```

### E4. 写作完整性检查
**文件**：`paper_context.py` → 各 `_run_writer_*` 函数

**改动**：在每个 writer 函数末尾增加检查
```python
def _run_writer_results(ctx):
    # ... 现有写作逻辑 ...
    result = ctx.sections.get('results', '')

    # 完整性检查
    if result:
        checks = []
        if len(result) < 800:
            checks.append(f'Reults 字数不足({len(result)}/800)')
        if '图' not in result and '表' not in result and 'Fig' not in result:
            checks.append('Results 缺少图表引用')
        if not any(kw in result for kw in ['r=', 'p<', 'p=', 't=', 'F=', 'χ']):
            checks.append('Results 缺少统计数值')
        if checks:
            logger.warning(f'Reults 检查: {"; ".join(checks)}')
```

---

## 阶段C：文献搜索扩展

### C1. Google Scholar 镜像接入
**文件**：`auto_paper_finder.py`

**新增类** `GoogleScholarSearcher`：
```python
class GoogleScholarSearcher(RateLimitedClient):
    """Google Scholar 镜像搜索"""

    MIRRORS = [
        'https://xs.xasa.top',
        'https://scholar.google.com',
    ]

    def __init__(self, delay_range=(4, 8)):
        super().__init__(delay_range)
        self._working_mirror = None

    def _find_working_mirror(self):
        """测试镜像可用性"""
        for mirror in self.MIRRORS:
            try:
                resp = self.session.get(mirror, timeout=10)
                if resp.status_code == 200:
                    self._working_mirror = mirror
                    return mirror
            except:
                continue
        return None

    def search(self, query, max_results=10):
        """搜索 Google Scholar"""
        if not self._working_mirror:
            self._find_working_mirror()
        if not self._working_mirror:
            return []  # 所有镜像不可用，降级

        # 使用 scholarly 库或直接请求
        # scholarly: from scholarly import scholarly
        # results = scholarly.search_pubs(query)
        # 或直接爬取镜像页面解析
```

### C2. Connected Papers 接入
**文件**：`auto_paper_finder.py`

**新增类** `ConnectedPapersSearcher`：
```python
class ConnectedPapersSearcher(RateLimitedClient):
    """Connected Papers 相关论文图谱"""

    BASE_URL = 'https://www.connectedpapers.com'

    def get_related_papers(self, paper_id, max_results=20):
        """获取与指定论文相关的论文图谱"""
        # Connected Papers 的 API 或页面解析
        # 返回相关论文列表（包含引用关系）
```

### C3. 统一搜索调度器改造
**文件**：`auto_paper_finder.py` → `AutoPaperFinder`

**改动**：在 `__init__` 中注册新搜索器
```python
def __init__(self, ...):
    self.searchers = {
        'semantic_scholar': SemanticScholarSearcher(),
        'arxiv': ArxivSearcher(),
        'google_scholar': GoogleScholarSearcher(),  # ← 新增
        'connected_papers': ConnectedPapersSearcher(),  # ← 新增
    }
```

**改动**：`search()` 方法改为多源搜索 + 去重
```python
def search(self, query, max_results=20):
    all_results = []
    for name, searcher in self.searchers.items():
        try:
            results = searcher.search(query, max_results=max_results)
            all_results.extend(results)
        except Exception as e:
            logger.warning(f'{name} 搜索失败: {e}')

    # 去重（按标题相似度 > 0.85）
    deduplicated = self._deduplicate(all_results)
    return deduplicated[:max_results]
```

---

## 阶段D：文献学习深化

### D1. 方法论学习
**文件**：`pattern_learner.py`

**新增类** `MethodologyLearner`：
```python
class MethodologyLearner:
    """从论文 Methods 章节学习实验方法论"""

    # 方法论关键词字典
    METHOD_KEYWORDS = {
        'sampling': ['采样', 'sampling', '样品采集'],
        'analysis': ['GC-MS', 'IC', 'TOC', '同位素', '色谱', '光谱'],
        'statistics': ['ANOVA', 'PCA', '回归', '聚类', 't检验'],
        'experiment': ['对照', 'control', '实验组', '处理组'],
    }

    def learn_from_text(self, text, source=''):
        """从 Methods 文本中提取方法论知识"""
        methods = []
        for category, keywords in self.METHOD_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    # 提取关键词所在的句子作为上下文
                    context = self._extract_context(text, kw)
                    methods.append({
                        'category': category,
                        'keyword': kw,
                        'context': context,
                        'source': source,
                    })
        return methods

    def to_knowledge_store_format(self):
        """转为 KnowledgeMemory 可存储的格式"""
        # ...
```

---

## 文件变更清单

| 文件 | 变更类型 | 改动量估算 |
|------|---------|-----------|
| `scientific_visualization_agent.py` | 新增8个方法 + 修改现有方法字体 | +500行 |
| `academic_plot_style.py` | 新增 `ensure_chinese_text()` + 修改 `setup_fonts()` | +30行 |
| `data_driven_pipeline.py` | 新增3个分析方法 + 修改 `explore()` | +100行 |
| `statistical_analysis.py` | 新增2个类 | +60行 |
| `paper_writing_agent.py` | 修改 DiscussionGenerator | +80行 |
| `document_assembler.py` | 新增 `_clean_markdown()` + 修改排版 | +60行 |
| `paper_context.py` | 各 writer 函数增加完整性检查 | +30行 |
| `auto_paper_finder.py` | 新增2个搜索器 + 改造调度器 | +200行 |
| `pattern_learner.py` | 新增 `MethodologyLearner` | +100行 |

**总计**：约 +1160 行改动

---

## 执行顺序

```
B2(字体修复) → B1(基础图表) → B3+B4(推荐+批量)
    → A1+A2(数据分析) → E2(排版清理) → E3(排版样式)
    → E1(写作逻辑) → E4(完整性检查)
    → C1+C2+C3(文献搜索) → D1(文献学习)
```

每完成一个任务，运行 `python check_orphans.py` 验证。
