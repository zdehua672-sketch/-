# Clawboat AI 学术系统 — 全面审查报告与修复计划

## 项目概况

Clawboat 是一个 AI 学术写作工具集，包含 20+ Python 模块，覆盖论文阅读、数据分析、统计分析、可视化、论文写作、审稿、自我进化等 8 步流水线。项目在 10 天内快速开发完成（2026.5.23-5.30）。

---

## 一、关键发现总览

| 等级 | 数量 | 说明 |
|------|------|------|
| **致命 Bug** | 15 | 运行时崩溃（NameError/TypeError/AttributeError） |
| **中等 Bug** | 9 | 逻辑错误、死代码、缺失功能 |
| **轻微问题** | 15 | 未使用 import、风格、可移植性 |
| **架构问题** | 8 | 测试为零、LLM 缺失、知识存储双重写入等 |

---

## 二、致命 Bug 清单（会导致运行时崩溃）

### 必须立即修复

| # | 文件:行号 | 问题 | 修复方案 |
|---|-----------|------|----------|
| 1 | `orchestrator.py:36` | 引用未定义的 `DEFAULT_CONFIG` | 改为 `DEFAULT_ANALYSIS_CONFIG` |
| 2 | `plotting_functions.py:254` | 同上，`DEFAULT_CONFIG` 未定义 | 改为 `DEFAULT_ANALYSIS_CONFIG` |
| 3 | `motivation_thread.py:332` | `self.linking_map` 声明为 `set()` 但用 `[]` 赋值 | 改为 `dict()` |
| 4 | `academic_review_agent.py:354` | 调用不存在的 `self.reviewer.generate_summary()` | 改为 `run_full_analysis()` |
| 5 | `academic_review_agent.py:341` | `analyze_correlations` 传入不支持的 `significance_level` 参数 | 移除该参数 |
| 6 | `academic_review_agent.py:172` | `review_data.get()` 但 review_data 是 dataclass 非 dict | 改用 `.data` 属性 |
| 7 | `scientific_visualization_agent.py:351` | 拼写错误 `anaylyze_data` → `analyze_data` | 修正拼写 |
| 8 | `scientific_visualization_agent.py:356` | `generate_summary` 传入不存在的 `dataset_name` | 移除该参数 |
| 9 | `paper_writing_agent.py:296` | 同上 | 移除 `dataset_name` 参数 |
| 10 | `write_discussion.py:167` | 同上 | 移除 `dataset_name` 参数 |
| 11 | `orchestrator.py:148-149` | `%d` 格式化列表值 | 改为 `%s` 或 `len()` |
| 12 | `rag_system/index/keyword_index.py` | `CJKTokenizer` 类未实现但被引用 | 补全实现或暂时移除引用 |
| 13 | `keyword_index.py:238,357` | 变量名 `n_grams` vs `ngrams` 不一致 | 统一命名 |
| 14 | `generate_figures.py:64-66` | `NUMERIC_COLS`/`LABEL_COL` 被立即覆盖为空 | 删除覆盖行 |
| 15 | `data_loader.py:66-70` | 异常处理中 fallback 后无条件 raise | 修复逻辑 |

---

## 三、中等 Bug 清单

| # | 文件 | 问题 | 修复方案 |
|---|------|------|----------|
| 16 | `citation_audit.py:57` | 年份正则只匹配 2000-2029 | 改为 `20\d{2}` |
| 17 | `citation_schema.py:67` | 可变默认参数 `tags: list = []` | 改为 `None` |
| 18 | `self_evolving_engine.py:55` | 可变默认参数 `memory_state: dict = {}` | 改为 `None` |
| 19 | `orchestrator.py:159` | `pd.concat` 可能收到空列表 | 加空列表检查 |
| 20 | `academic_review_agent.py:240-271` | 流水线前 4 步无错误处理 | 添加 try/except |
| 21 | `generate_tables.py:12` | 硬编码桌面路径 | 改为参数化 |
| 22 | `motivation_thread.py:84` | 文档引用错误的类名 | 修正 |
| 23 | `data_loader.py` | `reference_var` 计算但未存储 | 存为属性 |
| 24 | `keyword_index.py:227` | `_stopwords` 未初始化 | 在 `__init__` 中初始化 |

---

## 四、架构级问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| A1 | **零测试覆盖** | 20+ 模块无任何测试 | 为核心模块添加 pytest 测试 |
| A2 | **无 LLM 集成** | 标称"AI Agent"但无 API 调用 | 集成 OpenAI/Anthropic API |
| A3 | **知识存储双重写入** | `LiteratureMemory`/`writing_rationale` 绕过 `KnowledgeStore` 直接写文件 | 统一通过 KnowledgeStore 访问 |
| A4 | **RAG 系统已建但未用** | 10+ 模块无消费者 | 接入写作流程或移除 |
| A5 | **text_utils.py 未集成** | 为去重创建但未被引用 | 重构 motivation_thread/citation_audit/revision_audit 使用它 |
| A6 | **6 个孤立模块** | generate_figures/tables 等未被任何模块引用 | 接入 orchestrator 或转为独立工具 |
| A7 | **无配置系统** | 路径硬编码、无 .env | 添加统一配置管理 |
| A8 | **错误处理"catch-print"** | 60+ 处 `except Exception as e: print(...)` | 添加重试/上报机制 |

---

## 五、修复计划（按优先级排序）

### Phase 1: 致命 Bug 修复（必须最先做）
1. 修复 15 个致命 Bug — 确保核心流水线能运行
2. 每个修复后验证对应代码路径

### Phase 2: 中等 Bug 修复
3. 修复 9 个中等 Bug
4. 清理未使用的 import

### Phase 3: 架构完善
5. 接入 text_utils.py 去重
6. 统一知识存储访问路径
7. 添加基础配置系统
8. 为核心模块添加测试

### Phase 4: 功能补全
9. 集成 LLM API
10. 接通 RAG 系统
11. 编写 README.md

---

## 验证方式

- Phase 1-2: 逐个修复后 `python -c "import <module>"` 验证导入
- Phase 3: 运行 `python orchestrator.py` 测试完整流水线
- Phase 4: 端到端测试
