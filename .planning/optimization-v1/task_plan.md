# 学术AI工具包优化计划

## 目标
基于PaperSpine集成后的全系统审计，修复bug、消除孤岛、补全缺失、统一架构。

## Phase 1: Bug修复 + 代码清理 [Day 1]
- [x] Fix: `Severity.WARNING` → `Severity.MINOR`（LogicalLeapChecker）
- [x] Fix: ReviewKB 硬编码 vs review_rules.json 规则去重 — 已确认通过 _load_evolved_knowledge() 桥接，设计合理
- [x] Fix: Scorer.DIMENSIONS vs parameters.json — 已补充2个新维度(推理链完整性/逻辑跳跃)到JSON

## Phase 2: 消除孤岛 — 集成未被调用的模块 [Day 1-2]
- [x] citation_audit.py → PaperWriter.write() 流程：生成后自动审计引用质量
- [x] citation_audit.py → AcademicReviewAgent 新增 CitationQualityChecker (#13)
- [x] revision_audit.py → 进化引擎 evolve_cycle()：追踪版本间变化
- [x] rag_system → PaperWriter：写Discussion时检索相关文献作为支撑

## Phase 3: 补全缺失知识存储 [Day 2]
- [x] knowledge_store/writing_templates.json — 学术写作句式模板（13条模板）
- [x] knowledge_store/domain_terms.json — 环境科学/碳污染物术语库（14条术语）
- [x] knowledge_store/methods.json — 统计/分析方法库（8种方法）
- [x] knowledge_store/rationale_matrix.json — 初始化空结构
- [x] knowledge_store/revision_history.json — 初始化空结构

## Phase 4: 架构统一 [Day 3]
- [x] ReviewKB：从 review_rules.json 动态加载（_load_evolved_knowledge已实现）
- [x] Scorer.DIMENSIONS：从 parameters.json 加载权重（已实现+新增引用质量维度）
- [x] 统一所有 Agent 的 feedback 提交接口（3个Agent已有）
- [x] 知识存储自动初始化：KnowledgeStore._load() 自动创建缺失JSON

## Phase 5: 端到端验证 [Day 3]
- [x] 所有模块导入验证通过
- [x] 13 checkers + 13 dimensions 验证通过
- [x] 10个知识类别 + 10个JSON文件 验证通过
- [ ] `python paper_writing_agent.py` 全流程（需数据文件，待有数据时测试）
