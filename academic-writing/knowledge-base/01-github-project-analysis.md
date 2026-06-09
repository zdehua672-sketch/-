# GitHub科研项目知识库

## 一、项目总览

### A. 论文写作/生成系统

| 项目 | Stars | 核心功能 | 成熟度 |
|------|-------|---------|--------|
| Future-House/paper-qa (PaperQA2) | 高 | 科学RAG问答，超人表现 | 生产级 |
| Agnuxo1/CAJAL | 中 | 本地论文生成，Tribunal评分 | 早期 |
| yanqiangmiffy/Agentic-PaperQA | 低 | OCR+LLM论文问答Demo | Demo |
| lejacobroy/paperqa-zotero | 低 | Zotero+论文QA脚本 | PoC |

### B. 多Agent科研系统

| 项目 | Stars | Agent数 | 核心功能 | 成熟度 |
|------|-------|---------|---------|--------|
| NORA (night_owl) | 85 | 9+23技能 | 完整论文生成管线 | Alpha |
| HalfSeed | 1 | 7 | LaTeX论文生成，PI-LOCK | Alpha |
| HeShen-1/科研助手 | 3 | 3 | 中文研究报告生成 | 早期 |
| OpenCLAW | 10 | Swarm | 去中心化科研网络 | Alpha |
| crewai-research | 8 | 2-3 | 研究报告生成 | Working |

### C. 核心框架

| 框架 | Stars | 定位 | 科研适合度 |
|------|-------|------|-----------|
| LangGraph | 极高 | 低层编排，图执行 | 高（复杂管线） |
| CrewAI | 极高 | 高层角色协作 | 高（快速原型） |
| AG2 (AutoGen) | 极高 | 对话式多Agent | 高（RAG内置） |
| Microsoft AutoGen | 极高 | 多Agent框架 | 中（维护模式） |
| OpenHands | 极高 | 代码Agent | 低（SWE聚焦） |

---

## 二、关键项目深度分析

### PaperQA2 - 科学RAG金标准

**架构：** 三阶段Agent RAG
```
Paper Search → Gather Evidence → Generate Answer
```

**可提取模块：**
1. Contextual Summarization (RCS) - 按查询上下文摘要每个chunk
2. LLM重评分机制 - 对证据进行二次筛选
3. 元数据自动丰富 - 引用数、撤稿检查、期刊质量
4. 全文搜索引擎 - 本地论文库索引
5. 多模态支持 - 表格、图片、公式解析

**技术栈：** LiteLLM, Tantivy, OpenAI Embeddings, Semantic Scholar, CrossRef, Docling

**Prompt模式：**
- ToolSelector agent模式
- 配置型Prompt（可插拔）
- 多轮迭代细化

---

### NORA - 最完整的论文生成管线

**架构：** Skills-first + 9 Sub-agents + 23 Skills
```
full-pipeline
├── idea-discovery-pipeline
│   ├── lit-review
│   ├── generate-idea
│   ├── novelty-check
│   └── idea-review
├── deploy-experiment
│   ├── Track A (GPU ML)
│   ├── Track B (CPU spatial)
│   └── Mixed
├── auto-review-loop (最多4轮，>=7.5分)
├── generate-report
└── paper-writing-pipeline
    ├── paper-plan
    ├── paper-figure-generate
    ├── paper-draft
    ├── paper-review-loop
    └── paper-covert (MD→LaTeX→PDF)
```

**可提取模块：**
1. Skills-first架构 - Markdown定义工作流
2. 评审评分系统 - 5维度加权+硬门槛
3. Generator-evaluator分离 - 写作和评审用不同上下文
4. Harness hooks - PreToolUse/PostToolUse自动化
5. Journal模板系统 - 7个地学期刊模板
6. 控制标志 - AUTO_PROCEED, HUMAN_CHECKPOINT, COMPACT_MODE

**评分系统：**
| 维度 | 权重 | 硬门槛 |
|------|------|--------|
| Novelty | 30% | >=6.5 |
| Rigor | 25% | >=7.0 |
| Literature | 20% | >=6.5 |
| Clarity | 15% | >=6.0 |
| Impact | 10% | >=6.0 |
| **接受条件** | 均分>=7.5 | 所有门槛达标 |

---

### HalfSeed - LaTeX论文+PI-LOCK

**架构：** 7 Agent有向工作流
```
Director → [Analytical + Numerical + Literature] → Skeptic → Curator → Writer → Referee
```

**可提取模块：**
1. PI-LOCK机制 - paper.tex中保护手写段落不被覆盖
2. 对抗评审 - Skeptic质疑所有主张
3. SQLite+git持久化 - 每次编辑都git commit
4. 架构图可编辑 - 拖拽Agent修改工作流
5. Provider-neutral - 支持Claude/DeepSeek/OpenAI/Ollama

---

### HeShen-1 - 中文科研助手

**架构：** CrewAI 3 Agent层级
```
Research Manager → [Senior Researcher ×2 (并行)] → Research Analyst
```

**可提取模块：**
1. 中文原生支持 - DeepSeek优化
2. 并行搜索 - Web + arXiv同时搜索
3. 低成本 - 约0.3元/次
4. Streamlit双界面 - CLI + Web

---

### CAJAL - 本地论文生成

**架构：** 模板化生成 + Tribunal评审
```
Topic → Generator → Citations → Paper → Tribunal (8-10 judges) → Score
```

**可提取模块：**
1. Tribunal评审系统 - 8-10个LLM法官评分
2. 10维度评分 - 新颖性、方法论、引用质量、论证强度等
3. arXiv/CrossRef引用集成 - 真实引用非幻觉
4. 多格式输出 - Markdown/LaTeX/PDF
5. 100%本地运行 - 无API依赖

---

## 三、框架对比与推荐

### 科研Agent框架排名

| 排名 | 框架 | 推荐理由 | 适用场景 |
|------|------|---------|---------|
| 1 | LangGraph | 状态持久化、长时运行、图执行 | 复杂科研管线 |
| 2 | CrewAI | 快速原型、角色映射、YAML配置 | 中等复杂度 |
| 3 | AG2 | RAG内置、9种编排模式、学术渊源 | RAG密集型 |
| 4 | Claude Code Skills | 无需服务器、Markdown工作流 | CLI工作流 |
| 5 | AutoGen | 维护模式，不推荐新项目 | - |

### 框架选型决策树

```
需要长时运行/持久化?
├── 是 → LangGraph
└── 否 → 需要快速原型?
    ├── 是 → CrewAI
    └── 否 → RAG是核心需求?
        ├── 是 → AG2
        └── 否 → Claude Code Skills
```
