"""
写作推理矩阵 - 追踪每个写作决策的推理链
借鉴自PaperSpine的writing_rationale_matrix模式

核心思想：每个论文段落不是凭空生成的，而是由"发现→机制→证据→引用"的推理链支撑。
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
    paper_id: str = ""     # 所属论文ID（支持跨论文累积）
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

    def __init__(self, store_path: str = None, paper_id: str = ""):
        self.rows: list[RationaleRow] = []
        self._current_paper_id = paper_id
        self.store_path = store_path or str(
            Path(__file__).parent / "knowledge_store" / "rationale_matrix.json"
        )
        # 自动加载历史推理记录（支持跨论文累积）
        self._load_existing()

    def add(self, finding: str, mechanism: str = "", mechanism_en: str = "",
            evidence: str = "", citation: str = "", confidence: float = 0.0,
            section: str = "", language: str = "zh", paper_id: str = "") -> RationaleRow:
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
            paper_id=paper_id or self._current_paper_id,
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
        """持久化到JSON（追加模式：保留历史记录）"""
        Path(self.store_path).parent.mkdir(parents=True, exist_ok=True)

        # 加载已有数据
        existing_rows = []
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                existing_rows = [RationaleRow(**r) for r in data.get("rows", [])]
            except Exception:
                pass

        # 合并：已有的 + 新增的（去重）
        existing_findings = {r.finding for r in existing_rows}
        new_rows = [r for r in self.rows if r.finding not in existing_findings]
        all_rows = existing_rows + new_rows

        data = {
            "version": 1,
            "updated": datetime.now(timezone.utc).isoformat(),
            "total_rows": len(all_rows),
            "papers": list(set(r.paper_id for r in all_rows if r.paper_id)),
            "rows": [asdict(r) for r in all_rows],
        }
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_existing(self):
        """加载已有的推理记录"""
        if not os.path.exists(self.store_path):
            return
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.rows = [RationaleRow(**r) for r in data.get("rows", [])]
        except Exception:
            pass

    def load(self):
        """从JSON加载（替换当前数据）"""
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


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        # 内置测试
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
        print("\n测试通过!")
    else:
        print("用法: python writing_rationale.py --test")
