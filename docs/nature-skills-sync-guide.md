# nature-skills 对接更新同步指南

> **更新提交**: `78f8663` (2026-06-09)
> **分支**: `feature/paper-context-integration`
> **仓库**: https://github.com/zdehua672-sketch/-.git

---

## 一、最简同步方式（推荐）

对方只需要做：

```bash
# 1. 链接你的仓库
git remote add upstream https://github.com/zdehua672-sketch/-.git

# 2. 拉取更新
git fetch upstream
git merge upstream/feature/paper-context-integration

# 或者直接 cherry-pick 这一个提交
git cherry-pick 78f8663
```

同步后对方就有了全部更新。以下是**每个文件改了什么、为什么改**的详细说明。

---

## 二、更新文件清单

| # | 文件 | 改动量 | 对接的 skill | 核心改动 |
|---|---|---|---|---|
| 1 | `chart_qa.py` | +217 行 | nature-figure | 新增 Nature 交付级 QA + 导出 |
| 2 | `scientific_visualization_agent.py` | +82/-6 行 | nature-figure | Nature QA 集成 + rcParams + 色板 |
| 3 | `academic_review_agent.py` | +237/-4 行 | nature-polishing | 结构性诊断 + 证据动词分级 |
| 4 | `auto_revision.py` | +47 行 | nature-polishing | 英文替代表 + 局限性模板 |
| 5 | `knowledge_memory.py` | +220 行 | nature-data | FAIR 审计 + 数据可用性声明生成 |
| 6 | `self_evolving_engine.py` | +28 行 | nature-data | data_availability 分类 + 反馈记录 |
| 7 | `knowledge_store/data_availability.json` | +12 行 (新建) | nature-data | 空的知识分类文件 |

---

## 三、逐文件详细说明

### 3.1 `chart_qa.py` — Nature 交付级 QA

**来源**: `~/.claude/skills/nature-figure/references/qa-contract.md` (119行)

**新增内容（第235行之后插入）**:

#### 常量
```python
NATURE_SIZES = {'single': 89, 'double': 183, 'full': 183}  # mm
NATURE_FONT_SIZES = {'body_min': 5, 'body_max': 7, 'panel_label': 8, 'tick_min': 5}
NATURE_PALETTE = {...}  # 14色 figures4papers 色盲安全色板
```

#### 新函数: `check_nature_delivery(fig, target_journal, auto_fix)`
在已有 `check_chart_quality()` 基础上追加 6 项 Nature 专项检查：

| 检查项 | 严重级 | 说明 |
|---|---|---|
| `NATURE_FONT_VIOLATION` | MAJOR | 字体必须是 Arial/Helvetica/sans-serif，检测 Times/Georgia/Palatino |
| `NATURE_COLORMAP` | MAJOR | 禁止 rainbow/jet/hsv/hot，自动替换为 viridis |
| `NATURE_RED_GREEN` | MAJOR | 红绿双色编码对色盲不友好 |
| `NATURE_PANEL_LABEL_SIZE` | MINOR | 面板标签 (a)(b)(c) 字号应 >= 8pt |
| `NATURE_STATS_INFO` | INFO | 提示添加 n值/检验方法/p值标注 |
| `NATURE_LEGEND_STRATEGY` | MINOR | 超过 2 个图例时建议用共享图例 |

#### 新函数: `nature_export_bundle(fig, filename, dpi=600)`
一键导出三格式：
- `.svg` — 可编辑文本（`svg.fonttype='none'`）
- `.pdf` — 矢量（`pdf.fonttype=42`）
- `.tiff` — 600dpi 位图预览

---

### 3.2 `scientific_visualization_agent.py` — Nature QA 集成

**来源**: `~/.claude/skills/nature-figure/static/fragments/backend/python.md` + `references/design-theory.md`

#### 改动 1: 新增导入（第29行之后）
```python
from chart_qa import (
    check_chart_quality, print_qa_report,
    check_nature_delivery, nature_export_bundle,
    NATURE_PALETTE, NATURE_SIZES,
)
```

#### 改动 2: Nature 风格 rcParams 微调（第118行附近）
```python
# 旧值 → 新值（来自 Nature 2026 实测数据）
'font.size': 5.5 → 7          # Nature 2026: 5-7pt for dense panels
'axes.titlesize': 7 → 9
'axes.labelsize': 6 → 8
'axes.linewidth': 0.5 → 0.8   # Nature 2026: 0.8-1.2
```

#### 改动 3: `get_palette()` 使用 figures4papers 色板
Nature 风格从硬编码色表改为 `NATURE_PALETTE`（色盲安全）：
```python
['#0F4D92', '#3775BA', '#8BCF8B', '#B64342', '#42949E', '#9A4D8E', '#767676', '#4D4D4D']
```

#### 改动 4: 新增 `nature_rcparams()` 类方法
一行调用获取 Nature 2026 年版完整 rcParams 预设。

#### 改动 5: `_plot_with_review()` 自评循环集成 Nature QA
当 `style='nature'` 时，自评循环自动追加 `check_nature_delivery()` 检查，输出到 `attempt_record['nature_qa']`。

---

### 3.3 `academic_review_agent.py` — 结构性诊断

**来源**: `~/.claude/skills/nature-polishing/static/core/failure-modes.md` + `references/section-moves.md` + `references/phrasebank-playbook.md`

#### 改动 1: `ReviewKB` 新增知识（第264行之后）

```python
# 证据强度动词分级
EVIDENCE_VERBS = {
    'strong': ['show', 'demonstrate', 'establish', 'reveal', 'identify'],
    'moderate': ['suggest', 'indicate', 'support the view that', ...],
    'speculative': ['may reflect', 'could arise from', 'appears to', ...],
}

# 差距语言（替代 "no one has ever studied"）
GAP_LANGUAGE = {
    'good': ['remains poorly understood', 'has not been examined in ...', ...],
    'avoid': ['no one has ever studied', 'completely unknown', ...],
}

# 与前人比较表达
COMPARISON_LANGUAGE = {'align': [...], 'diverge': [...]}

# 局限性语言模板
LIMITATION_LANGUAGE = ['These findings should be interpreted with caution because ...', ...]

# 段落间过渡
PARAGRAPH_LINKS = {'restatement': ..., 'definite': ..., 'participial': ..., 'zero': ...}

# 结构性失败模式（9种）
STRUCTURAL_FAILURE_MODES = {
    'wrong_paper_type', 'missing_gap', 'claim_without_evidence',
    'evidence_without_claim', 'missing_boundary', 'results_discussion_mixed',
    'weak_title_abstract', 'terminology_inconsistent', 'sentence_clutter_only',
}

# 修复优先级
FIX_PRIORITY = ['paper_type', 'section_job', 'paragraph_logic', 'claim_evidence_boundary', 'sentence_polish']
```

#### 改动 2: 新增 `StructuralDiagnosisChecker` 类（第1440行之后）

5 项结构性检查：

| 检查 | 严重级 | 原理 |
|---|---|---|
| 缺少必要章节 | MAJOR | Introduction/Methods/Results/Discussion/Conclusion 必须存在 |
| Introduction 缺 gap | MAJOR | 必须有 "however...remains poorly understood" 类语句 |
| Results 混入讨论 | MAJOR | 检测 "this suggests/indicates/mechanism" 等讨论性表述 >= 3 处 |
| Discussion 缺局限性 | MINOR | 必须有 limitation/caveat/caution 类语句 |
| 术语不一致 | MINOR | CO₂/CO2/CO_2 等写法跨章节不一致 |

#### 改动 3: `Scorer.DIMENSIONS` 新增维度
```python
'Nature结构诊断': {'weight': 0.10, 'description': '结构完整性（Nature标准）'}
```
总权重重新平衡，Nature 结构诊断占 10%。

---

### 3.4 `auto_revision.py` — 英文替代表

**来源**: `~/.claude/skills/nature-polishing/references/phrasebank-playbook.md`

#### 新增常量（第55行之后）

```python
# 英文证据动词降级（prove → demonstrate, confirm → indicate）
EVIDENCE_VERB_REPLACEMENTS = {
    'prove': 'demonstrate', 'proves': 'demonstrates', 'proven': 'demonstrated',
    'confirm': 'indicate', 'confirms': 'indicates', 'confirmed': 'indicated',
    'definitive': 'suggestive', 'unprecedented': 'not previously reported',
    'groundbreaking': 'notable', 'revolutionary': 'significant',
    'first ever': 'among the first', 'novel discovery': 'observation',
    'breakthrough': 'advance',
}

# 差距语言替换
GAP_LANGUAGE_REPLACEMENTS = {
    'no one has ever studied': 'few studies have examined',
    'completely unknown': 'remains poorly understood',
    'ignored by all previous work': 'has received limited attention',
}

# 局限性模板（5个，替代 "有待进一步研究"）
LIMITATION_TEMPLATES = [
    'These findings should be interpreted with caution because {reason}.',
    'A limitation of this study is that {limitation}.',
    ...
]
```

#### 新增中文替代表（在 `AI_PHRASES` 字典中追加）
```python
'证实了': '表明',
'确证了': '支持',
'首次发现': '观察到',
'填补了研究空白': '扩展了对...的理解',
'有待进一步研究': '需要在更大样本中验证',
...
```

---

### 3.5 `knowledge_memory.py` — FAIR 审计

**来源**: `~/.claude/skills/nature-data/references/fair-metadata-checklist.md` + `static/core/workflow.md`

#### 新增常量
```python
FAIR_CHECKLIST = {
    'findable': {'persistent_id': ..., 'rich_metadata': ..., 'searchable_record': ..., 'metadata_links_id': ...},
    'accessible': {'standard_protocol': ..., 'explicit_conditions': ..., 'public_metadata': ...},
    'interoperable': {'community_formats': ..., 'shared_vocabulary': ..., 'qualified_links': ...},
    'reusable': {'licence_clear': ..., 'provenance': ..., 'quality_notes': ..., 'community_metadata': ...},
}

DATA_ACCESS_ROUTES = {
    'public_repository': '公共仓库', 'controlled_access': '受控访问',
    'within_paper': '论文/补充材料中', 'reused_public': '复用公共数据',
    'third_party_restricted': '第三方受限', 'justified_request': '合理请求', 'not_applicable': '不适用',
}

REPOSITORY_MAP = {
    'environmental': ['Zenodo', 'Figshare', 'Dryad', 'PANGAEA'],
    'genomics': ['NCBI SRA', 'ENA', 'DDBJ'],
    ...
}
```

#### 新函数: `audit_fair_metadata(datasets)`
输入数据集列表，输出 FAIR 四原则审计结果：
```python
# 输入格式
datasets = [{
    'name': 'sewer_carbon_data',
    'description': '...',
    'identifier': '10.5281/zenodo.12345',  # DOI 或 Accession
    'repository': 'Zenodo',
    'access_route': 'public_repository',
    'licence': 'CC-BY-4.0',
    'format': '.csv',
    'has_readme': True,
    'variables_documented': True,
}]

# 输出格式
{'overall_score': 'PASS'/'WARN'/'FAIL', 'per_dataset': [...], 'blocking_issues': [...], 'summary': '...'}
```

检查项：
- **F**: 有持久标识符？描述充分？
- **A**: 受限数据有访问流程？
- **I**: 文件格式是否开放（xlsx→csv 建议）？
- **R**: 有许可证？有 README？变量已文档化？

#### 新函数: `generate_data_availability_statement(datasets, journal)`
自动生成可直接粘贴的 Data Availability 声明文本，支持 6 种访问路径。

---

### 3.6 `self_evolving_engine.py` — 数据集管理

**改动 1**: `KnowledgeStore.CATEGORIES` 新增
```python
"data_availability": "数据可用性声明（数据集+仓库+许可证+FAIR元数据）"
```

**改动 2**: `FeedbackCollector` 新增方法
```python
def log_data_availability(self, datasets, statement, audit_result, journal='nature'):
    """记录数据可用性声明到知识库"""
```

---

### 3.7 `knowledge_store/data_availability.json`（新建）
空的 JSON 知识分类文件，由 `KnowledgeStore` 自动初始化。

---

## 四、依赖关系

这些更新**不引入新的外部依赖**。所有新增功能都基于已有的 `matplotlib`、`json`、`re` 等标准库。

唯一需要注意的依赖链：
```
scientific_visualization_agent.py → chart_qa.py (新增的 check_nature_delivery)
academic_review_agent.py → StructuralDiagnosisChecker (新增的类)
knowledge_memory.py → audit_fair_metadata / generate_data_availability_statement (新增函数)
```

---

## 五、对方同步后的验证

同步完成后，对方可以运行以下命令验证：

```bash
cd python-sdk

# 验证 chart_qa 导入
python -c "from chart_qa import check_nature_delivery, nature_export_bundle, NATURE_PALETTE; print('OK')"

# 验证 review agent
python -c "from academic_review_agent import StructuralDiagnosisChecker, ReviewKB; print('OK')"

# 验证 auto_revision
python -c "from auto_revision import EVIDENCE_VERB_REPLACEMENTS, LIMITATION_TEMPLATES; print('OK')"

# 验证 FAIR 审计
python -c "from knowledge_memory import audit_fair_metadata, generate_data_availability_statement; print('OK')"

# 验证 self_evolving_engine
python -c "from self_evolving_engine import KnowledgeStore; print('OK')"
```

全部输出 `OK` 即为同步成功。

---

## 六、前置条件

对方机器上需要先安装 nature-skills（如果要使用 skill 本身的功能）：

```bash
# 通过镜像代理安装（GitHub 直连可能超时）
npx skills add yuan1z0825/nature-skills@nature-figure -g -y
npx skills add yuan1z0825/nature-skills@nature-polishing -g -y
npx skills add yuan1z0825/nature-skills@nature-data -g -y
```

> 注意：代码层面的对接**不依赖** skill 安装。skill 安装后可以在 Claude Code 中直接调用 `/nature-figure` 等命令。
