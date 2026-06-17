---
name: reference_engramory
description: Engramory 项目设计原则参考
metadata:
  type: reference
created: 2026-06-18
updated: 2026-06-18
---

# Engramory 设计原则

## 项目信息
- 仓库：https://github.com/tinqiao-oss/engramory
- 版本：v0.3.0 (experimental)
- 许可：MIT

## 核心设计原则

### 1. 一个文件 = 一个事实
每条知识独立存储为 markdown 文件，便于阅读、编辑、diff。

### 2. 四类记忆本体
- `user` — 用户是谁
- `feedback` — Agent 应如何行为（必须有 Why: 和 How to apply:）
- `project` — 当前工作状态
- `reference` — 外部资源指针

### 3. 写前去重 (dedup-before-write)
检查是否已存在相同知识，存在则更新而非新增。

### 4. 错了就删 (delete-when-wrong)
过期知识直接删除，不标记为 stale。

### 5. 索引不腐烂 (bounded index)
- `MEMORY.md` 每次会话加载
- 警告阈值：150行 / 20KB
- 硬上限：200行 / 25KB

## 验证工具
- `engramory_doctor.py` — 全面验证
- `engramory_check.py` — 轻量写后检查
- `engramory_init.py` — 初始化助手

**Why:** 为 Claude 的记忆管理提供结构化参考
**How to apply:** 写入记忆时遵循上述原则
