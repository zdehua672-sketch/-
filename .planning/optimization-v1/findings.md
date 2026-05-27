# 审计发现

## Bug
- `academic_review_agent.py:1060`: `Severity.WARNING` → 已修复为 `Severity.MINOR`

## 孤岛模块（已实现但未被调用）
| 模块 | 当前状态 | 应集成到 |
|------|---------|---------|
| citation_audit.py | 独立CLI | PaperWriter.write() + ReviewAgent |
| revision_audit.py | 独立CLI | 进化引擎 evolve_cycle() |
| rag_system/ | 独立包 | PaperWriter Discussion生成 |

## 缺失知识存储
| 文件 | 用途 |
|------|------|
| writing_templates.json | 学术句式模板 |
| domain_terms.json | 领域术语 |
| methods.json | 分析方法库 |
| rationale_matrix.json | 推理矩阵（已定义category，无文件） |
| revision_history.json | 修订历史（已定义category，无文件） |

## 架构重复
- ReviewKB._rules 硬编码了审稿规则，但 review_rules.json 也有 → 应统一为从JSON加载
- Scorer.DIMENSIONS 硬编码了12个维度和权重，但 parameters.json 的 agent.writing.scorer 也定义了 → 应统一
