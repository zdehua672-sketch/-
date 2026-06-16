# AI 学术论文自动写作系统

基于数据分析的学术论文自动生成系统。输入采样数据，自动完成：数据探索 → 统计分析 → 图表生成 → 论文写作 → 审稿修订 → DOCX排版。

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/zdehua672-sketch/ZUIXING.git
cd ZUIXING

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Claude CLI（用于 AI 写作，可选但强烈推荐）
npm install -g @anthropic-ai/claude-code
```

### 2. 准备数据

**方式 A：使用示例数据（快速测试）**
```bash
python scripts/generate_sample_data.py
# 生成 data/sample_data.xlsx（9个采样点 × 28个变量 × 冬春两季）
```

**方式 B：使用你自己的数据**
```bash
# 将你的数据文件放到以下任一位置：
#   - data/sample_data.xlsx（推荐）
#   - 桌面/冬春数据.xlsx
# 或设置环境变量：
export PAPER_DATA_FILE=/path/to/your/data.xlsx
```

**数据格式要求：**
- Excel 文件（.xlsx）
- 包含至少一个 sheet，或两个 sheet（如"冬季"/"春季"）
- 列名需包含以下变量（部分即可，系统自动识别）：

| 相态 | 变量示例 |
|------|----------|
| 气相 | CH4平均值, N2O平均值, CO2, VOCs(ppb), O2(%vol), H2S |
| 液相 | TOC（mg/L), DO(mg/L), COD（mg/L), pH, 液温, 总氮（mg/L) |
| 固相 | 固总碳（g/kg), 有机碳（g/kg), 无机碳（g/kg) |
| 环境 | 气温/℃, 泥水状况, 采样点 |

### 3. 运行管线

```bash
# 端到端测试（推荐先跑一次确认系统正常）
python test_full_pipeline.py
```

运行后会在 `paper_output/` 目录生成：
- `paper.docx` — 完整论文
- `*_results.json` — 分析结果
- `*_review.md` — 审稿报告
- `*_revision.md` — 修订报告

### 4. 安装 Git hooks（开发者）

```bash
bash scripts/install_hooks.sh
# 安装后，每次 git commit 会自动检查是否有孤立模块
```

---

## 系统架构

### 管线流程（19 个模块）

```
数据加载 → 数据探索 → 高级分析 → 动机生成 → 文献召回
    ↓
Results(Claude写作) → Discussion(Claude写作) → Introduction(Claude写作)
    ↓
Methods(Claude写作) → Conclusion(Claude写作) → Abstract(Claude写作)
    ↓
审稿检查(+投稿检查+引用安全+文本质量) → 自动修订 → DOCX排版
```

### 目录结构

```
ZUIXING/
├── paper_context.py          # 核心编排器（PaperOrchestrator + MODULE_REGISTRY）
├── claude_writer.py          # Claude CLI 写作引擎
├── data_loader.py            # 数据加载器
├── variable_registry.py      # 变量注册中心（统一变量分类）
├── data_driven_pipeline.py   # 数据探索 + 数据驱动写作
├── scientific_analysis_agent.py  # 统计分析编排器
├── scientific_visualization_agent.py  # 图表生成（10+种）
├── paper_writing_agent.py    # 论文写作代理
├── academic_review_agent.py  # 审稿代理（12类检查）
├── auto_revision.py          # 自动修订
├── document_assembler.py     # DOCX排版
├── knowledge_memory.py       # 知识记忆接口
├── self_evolving_engine.py   # 知识存储引擎
├── llm_bridge.py             # LLM API 桥接（备用）
├── data/                     # 数据文件目录
│   └── sample_data.xlsx      # 示例数据
├── knowledge_store/          # 知识库（JSON + SQLite）
├── rag_system/               # RAG 检索系统
├── scripts/                  # 一次性脚本
│   ├── generate_sample_data.py   # 生成示例数据
│   ├── install_hooks.sh          # 安装 Git hooks
│   ├── inject_*.py               # 注入知识库
│   └── run_*.py                  # 运行脚本
├── tests/                    # 单元测试
├── deprecated/               # 已归档的旧模块
├── check_orphans.py          # 孤立模块检查器
├── requirements.txt          # Python 依赖
├── CLAUDE.md                 # 开发规则
└── README.md                 # 本文件
```

---

## 核心模块说明

### PaperOrchestrator（编排器）

位于 `paper_context.py`，是系统的核心。所有模块通过 `MODULE_REGISTRY` 注册，声明 `needs/provides`，编排器自动调度。

**注册新模块的流程（铁律）：**

```python
# 1. 创建模块文件 my_module.py
class MyClass:
    def run(self, df):
        return results

# 2. 在 paper_context.py 中注册
def _run_my_module(ctx: PaperContext):
    from my_module import MyClass
    ctx.my_output = MyClass().run(ctx.df)
    return ctx.my_output

MODULE_REGISTRY['my_module'] = {
    'needs': ['df'],
    'provides': ['my_output'],
    'run': _run_my_module,
    'description': '我的新模块',
}

# 3. 验证
python check_orphans.py  # 应输出 0 orphaned
```

### ClaudeWriter（AI 写作引擎）

位于 `claude_writer.py`，通过 subprocess 调用本地 Claude CLI 生成高质量学术文本。

**支持的写作接口：**
- `write_introduction(findings)` — 基于数据发现生成引言
- `write_abstract(sections)` — 基于实际章节生成摘要
- `write_discussion(findings, mechanisms)` — 生成讨论
- `write_conclusion(findings)` — 生成结论
- `write_methods(data_info)` — 生成方法
- `polish_text(text)` — 通用文本润色

**无 Claude CLI 时自动回退到模板模式**（不会报错，只是质量降级）。

### VariableRegistry（变量注册中心）

位于 `variable_registry.py`，是全系统唯一的变量分类来源。

**所有模块必须从这里读取变量分类，禁止内联关键词列表。**

---

## 常见问题

### Q: 运行报错 "No module named 'xxx'"
```bash
pip install -r requirements.txt
```

### Q: Claude 写作不生效（输出的是模板文本）
```bash
# 检查 Claude CLI 是否可用
claude --version

# 如果未安装：
npm install -g @anthropic-ai/claude-code
```

### Q: 数据文件找不到
```bash
# 生成示例数据
python scripts/generate_sample_data.py

# 或指定自定义路径
export PAPER_DATA_FILE=/path/to/your/data.xlsx
python test_full_pipeline.py
```

### Q: 如何检查模块是否全部连通
```bash
python check_orphans.py
# 应输出: [OK] 0 orphaned modules
```

### Q: 如何添加新的分析模块
参考 CLAUDE.md 第5条"模块注册铁律"。

---

## 依赖说明

### 必需依赖（requirements.txt）
| 包 | 用途 |
|----|------|
| pandas | 数据处理 |
| numpy | 数值计算 |
| scipy | 统计分析 |
| matplotlib | 图表绑定 |
| seaborn | 绑定样式 |
| python-docx | DOCX排版 |
| requests | 网络请求 |
| openpyxl | Excel读写 |

### 可选依赖
| 包 | 用途 | 安装 |
|----|------|------|
| Claude CLI | AI写作 | `npm install -g @anthropic-ai/claude-code` |
| chromadb | 向量检索 | `pip install chromadb` |
| pymupdf | PDF解析 | `pip install pymupdf` |
| plotly | 交互图表 | `pip install plotly` |
| scienceplots | SCI样式 | `pip install scienceplots` |

---

## 外部AI调用指南（CLI脚手架）

**问题**：当外部AI（如 xiaomiMIMO）直接面对项目时，无法从 22+ 个 `.py` 文件中知道如何调用系统功能，容易自己重写代码导致质量差。

**解决方案**：系统提供了两层外部调用接口，让AI能精确调用每个功能模块。

### 方式A：CLI 命令行（推荐，开箱即用）

每个模块都有独立命令行入口：

```bash
# 数据分析
python cli.py explore                          # 数据探索，发现模式
python cli.py analyze                          # 全部分析（基础+科学+高级）
python cli.py figures                          # 生成图表

# 论文写作（逐一写章节，或一次写全部）
python cli.py write results                    # 写 Results
python cli.py write discussion                 # 写 Discussion
python cli.py write introduction               # 写 Introduction
python cli.py write methods                    # 写 Methods
python cli.py write conclusion                 # 写 Conclusion
python cli.py write abstract                   # 写 Abstract
python cli.py write all                        # 写全部章节

# 质量控制
python cli.py review                           # 审稿检查

# 全流程
python cli.py pipeline full                    # 全流程（需Claude CLI）
python cli.py pipeline quick                   # 快速流程（离线模式）

# 系统诊断
python cli.py status                           # 系统状态检查

# 指定数据文件和输出目录
python cli.py explore --data 数据.xlsx --json
python cli.py write results --data 数据.xlsx --output ./my_paper
```

**自动回退机制**：有 Claude CLI 时使用 AI 高质量写作，无 Claude CLI 时自动回退到模板引擎，系统永不中断。

### 方式B：MCP 服务器（专业AI对接）

MCP（Model Context Protocol）服务器的配置已写入 `cline_chinese_mcp_settings.json`，注册后在 AI Agent 中会看到 8 个可调用的工具：

| 工具名 | 功能 | 输入参数 |
|--------|------|----------|
| `explore_data` | 数据探索 | `data_path`（可选） |
| `analyze_all` | 全部分析 | `data_path`（可选） |
| `generate_figures` | 生成图表 | `data_path`, `output_dir`（可选） |
| `write_section` | 写论文章节 | `section`(必填), `data_path`, `output_dir` |
| `review_paper` | 审稿检查 | `paper_path`, `output_dir`（可选） |
| `pipeline_full` | 全流程管线 | `data_path`, `output_dir`（可选） |
| `pipeline_quick` | 快速离线流程 | `data_path`（可选） |
| `check_status` | 系统状态检查 | 无参数 |

### CLI 内部实现示意图

```
AI Agent (xiaomiMIMO/Claude)
        │
        ▼
python cli.py <command> [options]
        │
        ├── explore    ──→ DataExplorer (data_driven_pipeline.py)
        ├── analyze    ──→ DataExplorer + ScientificAnalysisAgent + AdvancedAnalysis
        ├── figures    ──→ _run_generate_figures (paper_context.py)
        ├── write      ──→ ClaudeWriter (优先) / 模板生成器 (回退)
        ├── review     ──→ AcademicReviewAgent (1,500+行12类检查)
        ├── pipeline   ──→ PaperOrchestrator (25+模块自动编排)
        └── status     ──→ 系统全面诊断
```

---

## 许可证

内部项目。
