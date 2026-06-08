# 自动科研工作流知识库

## 一、推荐架构：混合式科研AI系统

基于对20+个GitHub项目的分析，推荐以下混合架构：

### 架构原则
1. **Skills-first + Code hybrid** - Markdown定义工作流，Python实现工具
2. **CrewAI角色模型** - 自然映射科研团队
3. **LangGraph状态管理** - 长时运行+故障恢复
4. **NORA评审系统** - 对抗式多轮质量保证
5. **HalfSeed PI-LOCK** - 保护用户编辑

### 核心组件

```
┌─────────────────────────────────────────────────┐
│                  用户界面层                       │
│         CLI / Streamlit / Web UI                │
├─────────────────────────────────────────────────┤
│                  编排引擎层                       │
│     CrewAI (角色协作) + LangGraph (状态管理)      │
├─────────────────────────────────────────────────┤
│                  Agent层                         │
│  ┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────┐ │
│  │文献 │ │分析  │ │写作  │ │评审  │ │格式化 │ │
│  │Agent│ │Agent │ │Agent │ │Agent │ │Agent  │ │
│  └─────┘ └──────┘ └──────┘ └──────┘ └───────┘ │
├─────────────────────────────────────────────────┤
│                  工具层                           │
│  arXiv API │ Semantic Scholar │ CNKI │ LaTeX   │
├─────────────────────────────────────────────────┤
│                  记忆层                           │
│  短期(上下文) │ 中期(会话) │ 长期(知识库+Git)    │
├─────────────────────────────────────────────────┤
│                  LLM层                           │
│  DeepSeek │ Claude │ GPT │ Ollama(本地)         │
└─────────────────────────────────────────────────┘
```

---

## 二、Agent定义

### Agent 1: Literature Scout（文献侦察兵）
```yaml
role: 文献搜索专家
goal: 搜索、筛选、整理高质量学术文献
backstory: 精通中英文学术数据库，擅长快速定位核心文献
tools:
  - arxiv_search
  - semantic_scholar_search
  - cnki_search
  - pdf_parser
output: 文献列表 + 综述草稿
```

### Agent 2: Data Analyst（数据分析专家）
```yaml
role: 数据分析专家
goal: 执行统计分析，生成可视化图表
backstory: 精通Python数据分析，熟悉环境科学统计方法
tools:
  - python_executor
  - statistical_analysis
  - figure_generator
  - pca_analysis
output: 分析结果 + 图表文件
```

### Agent 3: Paper Writer（论文撰写者）
```yaml
role: 学术论文撰写者
goal: 基于文献和数据撰写高质量论文
backstory: 发表过10+篇SCI论文，精通中英文学术写作
tools:
  - latex_compiler
  - citation_manager
  - template_engine
output: paper.tex / paper.md
```

### Agent 4: Peer Reviewer（同行评审）
```yaml
role: 严格评审专家
goal: 从多个维度评审论文质量，给出具体修改建议
backstory: 资深审稿人，审过100+篇论文
output: 评分 + 修改建议
评分维度:
  - 科学性 (30%, 门槛>=7.0)
  - 创新性 (25%, 门槛>=6.5)
  - 文献支撑 (20%, 门槛>=6.5)
  - 逻辑性 (15%, 门槛>=6.0)
  - 可读性 (10%, 门槛>=6.0)
接受条件: 均分>=7.5 且所有门槛达标
```

### Agent 5: Formatter（格式化专家）
```yaml
role: 论文格式化专家
goal: 将论文格式化为目标期刊/学位论文要求
backstory: 熟悉各种期刊模板和学位论文格式要求
tools:
  - latex_compiler
  - template_selector
  - bibtex_manager
output: 最终PDF
```

---

## 三、工作流设计

### 主流程：论文生成管线

```
/启动论文
    │
    ▼
[阶段1: 选题] ─────────────────────────────────
    │ Literature Scout 搜索文献
    │ → 生成文献综述 + 研究空白
    │ → 人工确认选题
    │
    ▼
[阶段2: 数据分析] ────────────────────────────
    │ Data Analyst 执行分析
    │ → PCA/HCA/相关性/回归
    │ → 生成图表
    │ → 人工确认结果
    │
    ▼
[阶段3: 论文写作] ────────────────────────────
    │ Paper Writer 逐章撰写
    │ → Introduction
    │ → Materials & Methods
    │ → Results
    │ → Discussion
    │ → Conclusion
    │ → Abstract
    │
    ▼
[阶段4: 评审迭代] ────────────────────────────
    │ Peer Reviewer 评审
    │ → 评分 + 修改建议
    │ → Paper Writer 修改
    │ → 循环直到通过 (最多4轮)
    │
    ▼
[阶段5: 格式化] ──────────────────────────────
    │ Formatter 格式化
    │ → 选择模板（SCI/中文核心/硕论）
    │ → 编译LaTeX
    │ → 生成PDF
    │
    ▼
  最终论文.pdf
```

### 控制标志（借鉴NORA）
- `AUTO_PROCEED`: 自动继续下一阶段
- `HUMAN_CHECKPOINT`: 每阶段后暂停等人工确认
- `COMPACT_MODE`: 压缩上下文，节省token
- `REVIEWER_DIFFICULTY`: 评审严格度 (easy/normal/hard)
- `MAX_REVIEW_ROUNDS`: 最大评审轮数 (默认4)
- `SCORE_THRESHOLD`: 接受阈值 (默认7.5)

---

## 四、记忆系统设计

### 三层记忆架构

```
┌─────────────────────────────────────┐
│  长期记忆（持久化）                   │
│  - academic-writing/ 知识库          │
│  - MEMORY.md 项目记忆                │
│  - Git历史 版本记忆                   │
├─────────────────────────────────────┤
│  中期记忆（会话级）                   │
│  - handoff.json 跨会话状态           │
│  - TELEMETRY.jsonl 性能追踪          │
│  - project-state.json 项目状态       │
├─────────────────────────────────────┤
│  短期记忆（上下文）                   │
│  - Agent对话历史                      │
│  - Task输出                           │
│  - 当前阶段状态                       │
└─────────────────────────────────────┘
```

### 知识库结构
```
academic-writing/
├── knowledge-base/         # GitHub项目知识库（本次新增）
│   ├── 01-github-project-analysis.md
│   ├── 02-agent-architecture.md
│   ├── 03-prompt-engineering.md
│   └── 04-workflow-design.md
├── 00-index.md            # 学术写作知识索引
├── 01-sci-rules.md        # SCI写作规则
├── 02-chinese-rules.md    # 中文论文规则
├── 03-sentence-bank.md    # 句式库
├── 04-discussion-library.md
├── 05-figure-design.md    # 图表设计
├── 06-data-analysis-logic.md
├── 07-reviewer-comments.md
├── 08-common-mistakes.md
├── 09-structure-templates.md
└── 10-domain-knowledge.md # 领域知识
```

---

## 五、技术栈推荐

| 组件 | 推荐方案 | 备选 |
|------|---------|------|
| Agent编排 | CrewAI + LangGraph | AG2 |
| LLM | DeepSeek (中文) + Claude (英文) | GPT-4, Ollama本地 |
| 文献搜索 | arXiv API + Semantic Scholar | CNKI, Wanfang |
| 文献管理 | Zotero + pyzotero | 自建数据库 |
| PDF解析 | Docling | PyMuPDF, TextIN |
| 向量存储 | ChromaDB | FAISS, Qdrant |
| LaTeX | latexmk + xelatex | Overleaf API |
| 数据分析 | Python (pandas, scipy, sklearn) | - |
| 可视化 | matplotlib + seaborn | plotly |
| 前端 | Streamlit | React + FastAPI |
| 持久化 | SQLite + Git | PostgreSQL |
| MCP工具 | arxiv_mcp, filesystem, fetch | 自建MCP |
