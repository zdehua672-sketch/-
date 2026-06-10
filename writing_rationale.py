"""
写作推理矩阵 - 追踪每个写作决策的推理链
借鉴自PaperSpine的writing_rationale_matrix模式

核心思想：每个论文段落不是凭空生成的，而是由"发现→机制→证据→引用"的推理链支撑。

升级：新增 PlanningMatrix（写作蓝图/执行计划），在写作前规划每个段落的功能、
动机关联、证据支撑和风格约束。这是 PaperSpine 的核心理念：
  - RationaleMatrix（现有）= 事后追踪，记录"为什么这样写"
  - PlanningMatrix（新增）= 事前规划，决定"应该怎么写"
"""
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class RationaleRow:
    """一行推理记录：一个发现/主张的完整推理链"""
    finding: str           # 发现/主张内容
    mechanism: str         # 支撑机制（来自MechanismKB）
    mechanism_en: str = "" # 英文机制说明
    evidence: str = ""     # 数据证据（来自分析结果）
    citation: str = ""     # 文献引用
    confidence: float = 0.0  # 置信度 0-1
    section: str = ""      # 所属章节（discussion/introduction等）
    language: str = "zh"   # 语言
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_complete(self) -> bool:
        """推理链是否完整（至少有发现+机制或发现+证据）"""
        has_finding = bool(self.finding and len(self.finding) > 10)
        has_mechanism = bool(self.mechanism)
        has_evidence = bool(self.evidence)
        return has_finding and (has_mechanism or has_evidence)

    def completeness_score(self) -> float:
        """推理链完整性评分 0-1"""
        score = 0.0
        if self.finding and len(self.finding) > 10:
            score += 0.3
        if self.mechanism:
            score += 0.25
        if self.evidence:
            score += 0.2
        if self.citation:
            score += 0.15
        if self.confidence >= 0.7:
            score += 0.1
        return score


class RationaleMatrix:
    """
    推理矩阵管理器

    管理所有RationaleRow，支持添加/查询/导出/验证。
    类似PaperSpine的writing_rationale_matrix.md，但以数据结构而非Markdown表格管理。
    """

    def __init__(self, store_path: str = None):
        self.rows: list[RationaleRow] = []
        self.store_path = store_path or str(
            Path(__file__).parent / "knowledge_store" / "rationale_matrix.json"
        )

    def add(self, finding: str, mechanism: str = "", mechanism_en: str = "",
            evidence: str = "", citation: str = "", confidence: float = 0.0,
            section: str = "", language: str = "zh") -> RationaleRow:
        """添加一行推理记录"""
        row = RationaleRow(
            finding=finding,
            mechanism=mechanism,
            mechanism_en=mechanism_en,
            evidence=evidence,
            citation=citation,
            confidence=confidence,
            section=section,
            language=language,
        )
        self.rows.append(row)
        return row

    def query(self, section: str = None, language: str = None,
              min_confidence: float = None) -> list:
        """查询推理记录"""
        results = self.rows
        if section:
            results = [r for r in results if r.section == section]
        if language:
            results = [r for r in results if r.language == language]
        if min_confidence is not None:
            results = [r for r in results if r.confidence >= min_confidence]
        return results

    def validate(self) -> dict:
        """
        验证推理矩阵的完整性

        Returns
        -------
        dict: {total, complete, incomplete, avg_completeness, issues}
        """
        total = len(self.rows)
        if total == 0:
            return {"total": 0, "complete": 0, "incomplete": 0,
                    "avg_completeness": 0.0,
                    "issues": ["推理矩阵为空，没有任何推理记录"]}

        complete = sum(1 for r in self.rows if r.is_complete())
        scores = [r.completeness_score() for r in self.rows]
        avg_score = sum(scores) / len(scores)

        issues = []
        for i, row in enumerate(self.rows):
            if not row.finding:
                issues.append(f"Row {i}: 缺少发现/主张内容")
            elif not row.mechanism and not row.evidence:
                issues.append(f"Row {i}: '{row.finding[:30]}...' 缺少机制解释和数据证据")
            elif not row.citation and row.section == 'discussion':
                issues.append(f"Row {i}: '{row.finding[:30]}...' Discussion章节缺少文献引用")

        return {
            "total": total,
            "complete": complete,
            "incomplete": total - complete,
            "avg_completeness": round(avg_score, 3),
            "issues": issues,
        }

    def save(self):
        """持久化到JSON"""
        Path(self.store_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated": datetime.now(timezone.utc).isoformat(),
            "rows": [asdict(r) for r in self.rows],
        }
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """从JSON加载"""
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.rows = [RationaleRow(**r) for r in data.get("rows", [])]

    def to_markdown(self) -> str:
        """导出为Markdown表格（兼容PaperSpine格式）"""
        if not self.rows:
            return "# 写作推理矩阵\n\n（空）\n"

        lines = [
            "# 写作推理矩阵",
            "",
            "| # | 章节 | 发现/主张 | 机制 | 数据证据 | 文献引用 | 置信度 | 完整性 |",
            "|---|------|----------|------|---------|---------|--------|--------|",
        ]
        for i, r in enumerate(self.rows):
            finding_short = r.finding[:40] + ("..." if len(r.finding) > 40 else "")
            mech_short = r.mechanism[:30] + ("..." if len(r.mechanism) > 30 else "")
            ev_short = r.evidence[:30] + ("..." if len(r.evidence) > 30 else "")
            completeness = f"{r.completeness_score():.0%}"
            lines.append(
                f"| {i+1} | {r.section} | {finding_short} | {mech_short} | "
                f"{ev_short} | {r.citation} | {r.confidence:.2f} | {completeness} |"
            )

        validation = self.validate()
        lines.extend([
            "",
            f"**总计**: {validation['total']} 行, "
            f"完整: {validation['complete']}, "
            f"平均完整性: {validation['avg_completeness']:.0%}",
        ])
        if validation['issues']:
            lines.append("\n**问题:**")
            for issue in validation['issues']:
                lines.append(f"- {issue}")

        return '\n'.join(lines)

    def __len__(self):
        return len(self.rows)

    def __repr__(self):
        return f"RationaleMatrix(rows={len(self.rows)})"


# ============================================================================
# 写作蓝图 / 执行计划（PaperSpine 的 writing_rationale_matrix 理念）
# ============================================================================

@dataclass
class PlannedRow:
    """
    一行写作计划：写作前的执行单元

    与 RationaleRow 的区别：
    - RationaleRow 是事后追踪："我为什么这样写了"
    - PlannedRow 是事前规划："我应该怎么写这个单元"
    """
    row_id: int                          # 行号
    manuscript_unit: str                 # 写作单元（段落/小节/图表等）
    function: str                        # 该单元的交际功能
    motivation_link: str                 # 与确认动机的关联
    reference_pattern: str = ""          # 从范文/SOTA学到的模式
    target_scene_norm: str = ""          # 目标场景规范（期刊/会议要求）
    evidence_anchor: str = ""            # 证据/引用锚点
    planned_change: str = ""             # 计划的写作动作
    final_check: str = ""                # 最终检查标准
    status: str = "planned"              # planned / writing / done / revised
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_actionable(self) -> bool:
        """该计划是否足够具体可以执行"""
        has_unit = bool(self.manuscript_unit and len(self.manuscript_unit) > 2)
        has_function = bool(self.function and len(self.function) > 5)
        has_motivation = bool(self.motivation_link and len(self.motivation_link) > 5)
        return has_unit and has_function and has_motivation

    def completeness_score(self) -> float:
        """计划完整性评分 0-1"""
        score = 0.0
        if self.manuscript_unit: score += 0.15
        if self.function and len(self.function) > 5: score += 0.2
        if self.motivation_link and len(self.motivation_link) > 5: score += 0.25
        if self.reference_pattern: score += 0.1
        if self.evidence_anchor: score += 0.1
        if self.planned_change: score += 0.1
        if self.final_check: score += 0.1
        return score


class PlanningMatrix:
    """
    写作计划矩阵 — 写作前的执行计划

    PaperSpine 的核心理念：在写任何段落之前，先规划好：
    1. 这个段落的交际功能是什么？
    2. 它如何服务论文的核心动机？
    3. 它应该参考什么范文模式？
    4. 它应该用什么证据支撑？
    5. 它的风格约束是什么？

    这不是事后总结，而是写作的"施工图纸"。
    """

    def __init__(self, confirmed_motivation: str = "", store_path: str = None):
        self.confirmed_motivation = confirmed_motivation
        self.rows: list[PlannedRow] = []
        self.global_rationale: str = ""  # 全局框架理由
        self.store_path = store_path or str(
            Path(__file__).parent / "knowledge_store" / "planning_matrix.json"
        )
        self._next_id = 1

    def set_global_rationale(self, rationale: str):
        """设置全局框架理由（第一行，解释为什么选这个结构）"""
        self.global_rationale = rationale

    def add_row(self, manuscript_unit: str, function: str, motivation_link: str,
                reference_pattern: str = "", target_scene_norm: str = "",
                evidence_anchor: str = "", planned_change: str = "",
                final_check: str = "") -> PlannedRow:
        """添加一行写作计划"""
        row = PlannedRow(
            row_id=self._next_id,
            manuscript_unit=manuscript_unit,
            function=function,
            motivation_link=motivation_link,
            reference_pattern=reference_pattern,
            target_scene_norm=target_scene_norm,
            evidence_anchor=evidence_anchor,
            planned_change=planned_change,
            final_check=final_check,
        )
        self.rows.append(row)
        self._next_id += 1
        return row

    def add_section_plan(self, section_name: str, moves: list,
                         motivation_link: str, evidence_items: list = None,
                         exemplar_pattern: str = "", style_constraints: str = ""):
        """
        批量添加一个章节的计划

        Parameters
        ----------
        section_name : str, 章节名
        moves : list of str, 该章节的目标动作
        motivation_link : str, 与动机的关联
        evidence_items : list of str, 支撑证据
        exemplar_pattern : str, 范文模式
        style_constraints : str, 风格约束
        """
        for i, move in enumerate(moves):
            evidence = evidence_items[i] if evidence_items and i < len(evidence_items) else ''
            self.add_row(
                manuscript_unit=f"{section_name}.{i+1}" if len(moves) > 1 else section_name,
                function=move,
                motivation_link=motivation_link,
                reference_pattern=exemplar_pattern,
                evidence_anchor=evidence,
                planned_change=move,
                final_check=style_constraints,
            )

    def update_status(self, row_id: int, status: str):
        """更新某行的状态"""
        for row in self.rows:
            if row.row_id == row_id:
                row.status = status
                break

    def validate(self) -> dict:
        """
        验证计划矩阵的完整性

        Returns
        -------
        dict: {total, actionable, avg_completeness, issues}
        """
        total = len(self.rows)
        if total == 0:
            return {"total": 0, "actionable": 0, "avg_completeness": 0.0,
                    "issues": ["计划矩阵为空，没有任何写作计划"]}

        actionable = sum(1 for r in self.rows if r.is_actionable())
        scores = [r.completeness_score() for r in self.rows]
        avg_score = sum(scores) / len(scores)

        issues = []
        # 检查全局理由
        if not self.global_rationale or len(self.global_rationale) < 50:
            issues.append("全局框架理由缺失或过短（应≥50字），无法支撑整体结构设计")

        # 检查第一行（框架行）
        if self.rows:
            first = self.rows[0]
            if first.completeness_score() < 0.6:
                issues.append(f"Row 1 ({first.manuscript_unit}): 框架行不够完整，"
                            "应详细说明全局结构、动机关联和范文模式")

        # 检查各行
        shallow_rows = []
        for row in self.rows:
            if not row.function or len(row.function) < 10:
                shallow_rows.append(row.row_id)
            elif not row.motivation_link or len(row.motivation_link) < 10:
                issues.append(f"Row {row.row_id} ({row.manuscript_unit}): "
                            "缺少与动机的关联，这个写作单元为什么存在？")

        if shallow_rows:
            issues.append(f"以下行的功能描述过浅: {shallow_rows[:5]}")

        # 检查是否有通用占位符
        generic_phrases = ['提升清晰度', '学术化', '润色', '补充细节',
                          'improve clarity', 'make academic', 'polish']
        for row in self.rows:
            combined = (row.function + row.planned_change).lower()
            if any(g in combined for g in generic_phrases):
                if not row.motivation_link or len(row.motivation_link) < 15:
                    issues.append(f"Row {row.row_id}: 使用了通用占位符但缺少具体理由")

        return {
            "total": total,
            "actionable": actionable,
            "avg_completeness": round(avg_score, 3),
            "issues": issues,
        }

    def to_markdown(self) -> str:
        """导出为 Markdown 表格（PaperSpine 兼容格式）"""
        if not self.rows:
            return "# 写作计划矩阵\n\n（空）\n"

        lines = [
            "# 写作计划矩阵 (Writing Plan Matrix)",
            "",
            "> 本文件是写作前的执行计划。每个写作单元在写作前就规划好其功能、",
            "> 动机关联、证据支撑和检查标准。",
            "",
        ]

        if self.global_rationale:
            lines.extend([
                "## 全局框架理由",
                "",
                self.global_rationale,
                "",
            ])

        if self.confirmed_motivation:
            lines.extend([
                "## 确认的动机",
                "",
                f"**{self.confirmed_motivation}**",
                "",
            ])

        lines.extend([
            "## 写作单元计划",
            "",
            "| # | 写作单元 | 功能 | 动机关联 | 参考/SOTA模式 | 证据锚点 | 计划动作 | 检查标准 | 状态 |",
            "|---|---------|------|---------|-------------|---------|---------|---------|------|",
        ])

        for r in self.rows:
            unit_short = r.manuscript_unit[:20]
            func_short = r.function[:25] + ("..." if len(r.function) > 25 else "")
            mot_short = r.motivation_link[:25] + ("..." if len(r.motivation_link) > 25 else "")
            ref_short = r.reference_pattern[:15] + ("..." if len(r.reference_pattern) > 15 else "")
            ev_short = r.evidence_anchor[:15] + ("..." if len(r.evidence_anchor) > 15 else "")
            plan_short = r.planned_change[:20] + ("..." if len(r.planned_change) > 20 else "")
            check_short = r.final_check[:15] + ("..." if len(r.final_check) > 15 else "")
            status_icon = {"planned": "📋", "writing": "✍️", "done": "✅", "revised": "🔄"}.get(r.status, "❓")
            lines.append(
                f"| {r.row_id} | {unit_short} | {func_short} | {mot_short} | "
                f"{ref_short} | {ev_short} | {plan_short} | {check_short} | {status_icon} {r.status} |"
            )

        # 验证
        validation = self.validate()
        lines.extend([
            "",
            "## 验证结果",
            "",
            f"- **总计**: {validation['total']} 行",
            f"- **可执行**: {validation['actionable']} 行",
            f"- **平均完整性**: {validation['avg_completeness']:.0%}",
        ])
        if validation['issues']:
            lines.append("\n**问题:**")
            for issue in validation['issues']:
                lines.append(f"- ⚠️ {issue}")

        return '\n'.join(lines)

    def save(self):
        """持久化到 JSON"""
        Path(self.store_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "type": "planning_matrix",
            "confirmed_motivation": self.confirmed_motivation,
            "global_rationale": self.global_rationale,
            "updated": datetime.now(timezone.utc).isoformat(),
            "rows": [asdict(r) for r in self.rows],
        }
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """从 JSON 加载"""
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.confirmed_motivation = data.get("confirmed_motivation", "")
        self.global_rationale = data.get("global_rationale", "")
        self.rows = [PlannedRow(**r) for r in data.get("rows", [])]
        if self.rows:
            self._next_id = max(r.row_id for r in self.rows) + 1

    def __len__(self):
        return len(self.rows)

    def __repr__(self):
        return f"PlanningMatrix(rows={len(self.rows)}, motivation='{self.confirmed_motivation[:30]}')"


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        # 测试1: RationaleMatrix（事后追踪）
        print("=" * 60)
        print("测试 RationaleMatrix（事后追踪）")
        print("=" * 60)
        matrix = RationaleMatrix()

        matrix.add(
            finding="DO与CH4呈显著负相关(r=-0.72, p<0.001)",
            mechanism="溶解氧控制产甲烷过程：DO<0.5mg/L时产甲烷古菌活性最高",
            evidence="Pearson相关分析显示DO-CH4相关系数-0.72",
            citation="Guisasola et al. (2008)",
            confidence=0.9,
            section="discussion",
        )
        matrix.add(
            finding="冬季TOC浓度显著高于春季",
            mechanism="温度影响微生物代谢活性",
            evidence="t检验p=0.023",
            section="discussion",
        )
        matrix.add(
            finding="PCA前2主成分解释70%方差",
            section="discussion",
        )

        print(matrix.to_markdown())
        print("\n验证结果:", json.dumps(matrix.validate(), ensure_ascii=False, indent=2))

        # 测试2: PlanningMatrix（事前规划）
        print("\n" + "=" * 60)
        print("测试 PlanningMatrix（事前规划）")
        print("=" * 60)

        plan = PlanningMatrix(
            confirmed_motivation="揭示校园污水管网碳污染物的多相态赋存特征及驱动机制"
        )
        plan.set_global_rationale(
            "本文以'多相态碳污染物赋存特征及驱动机制'为核心动机，"
            "采用'问题-空白-设计-证据-解释'的逻辑弧线组织全文。"
            "范文学习了Guisasola(2008)和Jiang(2011)的结构模式。"
        )

        # Introduction 计划
        plan.add_section_plan(
            section_name="Introduction",
            moves=[
                "建立城市污水管网碳污染物的重要性（背景）",
                "综述多相态碳分析的研究进展（现状）",
                "指出缺乏校园尺度的三相联合分析（空白）",
                "提出本研究的目标和内容（回应）",
            ],
            motivation_link="从领域问题逐步收窄到研究空白，引出本研究",
            evidence_items=["Guisasola(2008)", "Jiang(2011)", "本研究数据"],
            exemplar_pattern="漏斗结构: 背景→现状→空白→本研究",
            style_constraints="学术正式，避免过度声明",
        )

        # Results 计划
        plan.add_section_plan(
            section_name="Results",
            moves=[
                "描述性统计: 三相碳污染物浓度范围和分布特征",
                "组间差异: 冬春季节碳污染物的显著差异",
                "相关性: DO-CH4负相关、TOC-CH4正相关",
                "PCA: 前2主成分解释70%方差的变量聚类",
            ],
            motivation_link="每个子节检验Introduction的一个承诺",
            evidence_items=["均值±标准差", "t检验p值", "r值和p值", "载荷矩阵"],
            exemplar_pattern="逻辑顺序: 描述→差异→相关→降维",
            style_constraints="客观陈述，不解释机制（留给Discussion）",
        )

        # Discussion 计划
        plan.add_section_plan(
            section_name="Discussion",
            moves=[
                "核心发现概述（回应动机）",
                "DO-CH4负相关机制: 厌氧条件驱动产甲烷",
                "TOC-CH4正相关机制: 有机底物供给",
                "碳平衡的环境意义和管理启示",
                "局限性与展望",
            ],
            motivation_link="用机制解释串联发现，支撑核心动机",
            evidence_items=["MechanismKB.DO_CH4", "MechanismKB.TOC_CH4", "碳平衡数据"],
            exemplar_pattern="发现→机制→文献对比→意义",
            style_constraints="每段都要有机制解释+文献支撑",
        )

        print(plan.to_markdown())
        print("\n验证结果:", json.dumps(plan.validate(), ensure_ascii=False, indent=2))
        print("\n测试通过!")
    else:
        print("用法: python writing_rationale.py --test")
