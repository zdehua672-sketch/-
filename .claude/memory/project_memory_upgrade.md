---
name: project_memory_upgrade
description: 记忆系统升级计划和实施状态
metadata:
  type: project
created: 2026-06-18
updated: 2026-06-18
---

# 记忆系统升级

## 背景
参考 Engramory 项目的设计理念，改进 Claude 自身的记忆管理系统。

## Engramory 核心原则
1. **一个文件 = 一个事实** — 每条知识独立存储
2. **写前去重** — 检查是否已存在相同知识
3. **错了就删** — 过期知识直接删除
4. **索引不腐烂** — MEMORY.md 有容量上限（200行/25KB）

## 实施内容
- 创建 `.claude/MEMORY.md` 索引文件
- 创建 `.claude/memory/` 目录存储详细记忆
- 采用 frontmatter 元数据格式
- 分类：project/feedback/reference

## 索引容量限制
- 警告阈值：150行 / 20KB
- 硬上限：200行 / 25KB

**Why:** 让 Claude 的记忆更有结构、更易维护
**How to apply:** 写入新记忆时遵循"一个文件=一个事实"原则
