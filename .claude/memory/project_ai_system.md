---
name: project_ai_system
description: AI学术系统项目概述和当前状态
metadata:
  type: project
created: 2026-06-18
updated: 2026-06-18
---

# AI学术系统项目状态

## 项目概述
一个完整的AI辅助学术论文写作系统，支持从数据加载到论文生成的全流程。

## 核心模块
- `paper_context.py` — 中央上下文和模块编排器
- `scientific_visualization_agent.py` — 图表生成（8种基础图表）
- `statistical_analysis.py` — 统计分析（Cohen's d、ANOVA等）
- `data_driven_pipeline.py` — 数据驱动的写作流程
- `auto_paper_finder.py` — 论文搜索（Google Scholar、Semantic Scholar）

## 已完成功能
1. 8种基础图表类型（bar/line/scatter/box/violin/pie/radar/waterfall）
2. ensure_chinese_text() 中文文本处理
3. AutoRecommender 图表推荐器
4. Cohen's d 效应量、Shapiro-Wilk 正态性检验
5. ANOVA/Mann-Whitney/Kruskal-Wallis 统计检验
6. GoogleScholarSearcher 和 ConnectedPapersSearcher
7. MethodologyLearner 方法论学习器
8. Writer 自检功能

## 验证命令
```bash
python check_orphans.py  # 应输出 "0 orphaned modules"
```

**Why:** 了解项目全貌，避免重复工作
**How to apply:** 新增模块时参考现有架构，确保接入管线
