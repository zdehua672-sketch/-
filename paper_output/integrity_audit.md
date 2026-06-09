# 完整性审计报告 (Integrity Audit)

> 本报告不仅检查，而且教学。每个发现都包含根因分析、修复建议、
> 下游影响和教学说明。

- 输出目录: `C:\Users\Administrator\python-sdk\paper_output`
- 总发现数: 6
- LaTeX门控: ✅ READY

## 摘要

| 维度 | 状态 | 发现数 |
|------|------|--------|
| 产物链完整性 | ✅ CLEAN | 4 |
| 推理深度 | ✅ CLEAN | 1 |
| 完整性模式 | ⚠️ WARNINGS | 1 |

## 产物链完整性

**ART-001** ✅ 可选产物 `deep_imitation_report.md` 不存在

**ART-002** ✅ 可选产物 `citation_support_bank.md` 不存在

**ART-003** ✅ 可选产物 `rationale_matrix.md` 不存在

**ART-004** ✅ 可选产物 `seven_sentence_test.md` 不存在

---

## 推理深度

**RSN-000** ✅ 推理深度合格

---

## 完整性模式

### ⚠️ INT-001 — WARNING

**发现了什么:** 发现弱断言词: obviously, clearly

**根因:** 修辞性捷径掩盖了推理空白

**修复:** 用具体证据替换每个弱断言词

**下游影响:** 降低论文可信度

**为什么重要:** "显然""毫无疑问"等词是修辞性捷径。在学术写作中，如果某事是清楚的，你不需要说它清楚——证据应该让它清楚。这些词常常掩盖推理中的空白。

---
