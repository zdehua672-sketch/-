# 🎓 Academic AI Agent — 科研论文全流程AI助手

面向环境科学（碳污染物多相态分析）方向的学术写作AI Agent系统，覆盖从数据分析到论文生成的完整链路。

## ✨ 核心功能

- **📊 数据分析** — 自动检测变量类型，运行描述统计/正态性检验/组间比较/PCA/HCA/回归
- **📝 论文写作** — 一键生成 Introduction/Methods/Results/Discussion/Abstract/Conclusion
- **🔍 论文检查** — 13类检查器（SCI格式/AI痕迹/引用质量/推理链完整性...）
- **📈 自动绘图** — 17种论文级图表，支持SCI/Nature/中文三种风格
- **🧠 自我进化** — 反馈驱动参数调优，知识库自动增长
- **📚 文献管理** — 论文阅读器 + RAG检索 + 引用质量审计

## 🏗️ 系统架构

```
数据 → 分析 → 写作 → 检查 → 修改
         ↑                    ↓
         └── 进化引擎（反馈驱动）──┘
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `paper_writing_agent.py` | 论文自动写作（一键生成完整论文） |
| `academic_review_agent.py` | 13类论文质量检查 + 模拟审稿意见 |
| `scientific_analysis_agent.py` | 数据分析编排器（智能决策该做什么分析） |
| `scientific_visualization_agent.py` | 高级自动绘图（10种图表类型） |
| `self_evolving_engine.py` | 自我进化引擎（知识库+反馈+GitHub监控） |
| `paper_reader.py` | 论文阅读器（arxiv/本地PDF/MD） |
| `rag_system/` | RAG检索增强生成系统 |

### 知识库

| 文件 | 内容 |
|------|------|
| `academic-writing/01-sci-rules.md` | SCI英文论文写作规则 |
| `academic-writing/02-chinese-rules.md` | 中文论文写作规则 |
| `academic-writing/03-sentence-bank.md` | 学术句式库（可直接套用） |
| `academic-writing/04-discussion-library.md` | Discussion写作模板 |
| `academic-writing/09-structure-templates.md` | 论文结构模板 |
| `knowledge_store/` | JSON结构化知识库（10个分类） |

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy scipy matplotlib seaborn openpyxl
```

可选依赖（增强功能）：
```bash
pip install scienceplots adjustText plotly kaleido sentence-transformers
```

### 一键生成论文

```python
from paper_writing_agent import write_paper

# 使用默认数据
writer = write_paper()

# 指定数据文件
writer = write_paper(
    data_path='your_data.xlsx',
    paper_type='thesis',      # thesis / sci / chinese
    language='zh',            # zh / en
    params={
        'area': 50,           # 校园面积（公顷）
        'population': 3,      # 常住人口（万人）
        'sampling_points': 10,
    }
)
```

### 自定义研究方向

```python
from paper_writing_agent import write_paper, ResearchDirection

direction = ResearchDirection(
    field="环境科学",
    topic="城市河流碳污染物迁移",
    object_name="某城市河流",
)

writer = write_paper(direction=direction)
```

### 论文质量检查

```python
from academic_review_agent import review_paper

report, text = review_paper('your_paper.md', paper_type='sci')
print(text)
```

### 自动绘图

```python
from scientific_visualization_agent import visualize

agent, results = visualize(
    data_path='your_data.xlsx',
    output_dir='./figures',
    style='sci',    # sci / nature / chinese
    language='zh',
)
```

### 运行进化引擎

```bash
python self_evolving_engine.py init     # 初始化知识库
python self_evolving_engine.py evolve   # 运行一次进化周期
python self_evolving_engine.py status   # 查看系统状态
python self_evolving_engine.py scan     # 扫描GitHub项目
```

## 📂 项目结构

```
.
├── paper_writing_agent.py          # 论文自动写作
├── academic_review_agent.py        # 论文质量检查
├── scientific_analysis_agent.py    # 数据分析编排
├── scientific_visualization_agent.py # 高级自动绘图
├── self_evolving_engine.py         # 自我进化引擎
├── paper_reader.py                 # 论文阅读器
├── data_loader.py                  # 数据加载与预处理
├── statistical_analysis.py         # 统计分析（零sklearn依赖）
├── plotting_functions.py           # 基础图表生成
├── academic_plot_style.py          # 学术绘图风格
├── citation_audit.py               # 引用质量审计
├── revision_audit.py               # 修订审计
├── motivation_thread.py            # 七句话血统测试
├── writing_rationale.py            # 写作推理矩阵
├── rag_system/                     # RAG检索系统
│   ├── retrieval/rag_engine.py     # 检索引擎
│   ├── index/                      # 索引（关键词+向量+引用图谱）
│   └── ingestion/                  # 文档解析
├── academic-writing/               # 知识库（10个Markdown模块）
│   ├── 00-index.md                 # 索引
│   ├── 01-sci-rules.md             # SCI写作规则
│   ├── mechanism-kb.md             # 领域机制知识库
│   └── knowledge-base/             # 外部知识库
└── knowledge_store/                # JSON结构化知识库
    ├── mechanisms.json
    ├── review_rules.json
    ├── writing_templates.json
    └── ...
```

## 🔧 技术特点

- **零重型依赖** — 核心功能仅需 pandas + numpy + scipy + matplotlib
- **手写PCA/回归** — 不依赖 sklearn，算法透明可控
- **知识可进化** — JSON知识库 + 反馈驱动 + 版本追踪
- **中英双语** — 所有生成器支持 zh/en 双语输出
- **色盲友好** — Okabe-Ito + Tableau 10 配色方案

## 📄 License

MIT
