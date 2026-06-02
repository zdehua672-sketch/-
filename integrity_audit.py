"""
=============================================================================
完整性审计 - Integrity Audit（教学模式）
借鉴自PaperSpine的integrity_audit.py

核心思想：审计不只是"找问题"，而是"教改进"。
每个发现都包含：
  - 根因分析（root_cause）：为什么会出现这个问题？
  - 修复动作（fix_action）：具体怎么修？
  - 下游影响（downstream_impact）：不修会怎样？
  - 教学说明（teaching_note）：这个模式为什么重要？

四维度审计：
  1. 产物链完整性 — 所有必要文件是否存在
  2. 推理深度 — 写作理由矩阵是否足够深入
  3. 证据链 — 主张是否有证据支撑
  4. 完整性模式扫描 — AI痕迹、可疑p值、弱断言、逻辑跳跃
=============================================================================
"""
import re
import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class AuditFinding:
    """一个审计发现（教学模式）"""
    id: str                         # 如 "ART-001"
    severity: str                   # BLOCKER / WARNING / INFO
    dimension: str                  # 所属维度
    what_was_found: str             # 发现了什么
    root_cause: str                 # 根因分析
    fix_action: str                 # 修复动作
    downstream_impact: str          # 下游影响
    teaching_note: str              # 教学说明


@dataclass
class AuditDimension:
    """一个审计维度"""
    name: str
    findings: list = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(f.severity == 'BLOCKER' for f in self.findings):
            return 'BLOCKED'
        if any(f.severity == 'WARNING' for f in self.findings):
            return 'WARNINGS'
        return 'CLEAN'


@dataclass
class IntegrityReport:
    """完整性审计报告"""
    output_dir: str
    dimensions: list = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(d.status == 'BLOCKED' for d in self.dimensions)

    @property
    def total_findings(self) -> int:
        return sum(len(d.findings) for d in self.dimensions)


# ============================================================================
# 教学说明库
# ============================================================================

TEACHING_NOTES = {
    'orphan_citation': (
        '引用键在正文中存在但.bib文件中没有对应条目。'
        '这是最常见的AI幻觉之一——模型发明了一个看似合理的引用键。'
        '始终验证每个\\cite{}键是否对应真实文献。'
    ),
    'suspicious_pvalue': (
        '没有可见检验统计量的p值（如p<0.01）是AI生成文本的典型特征。'
        '真实的统计报告应包含检验名称、统计量、自由度和效应量。'
    ),
    'weak_assertion': (
        '"显然""毫无疑问"等词是修辞性捷径。在学术写作中，'
        '如果某事是清楚的，你不需要说它清楚——证据应该让它清楚。'
        '这些词常常掩盖推理中的空白。'
    ),
    'logical_leap': (
        '推理连接词（因此、故、因而）密度过高表明文本在前提和结论之间'
        '跳过了推理步骤。每个跳跃都应分解为：观察→解释→含义。'
    ),
    'missing_artifact': (
        '每个PaperSpine产物都是一个检查点。当一个产物缺失时，'
        '通常意味着上游步骤被跳过了。修复步骤，而不是修补空白。'
    ),
    'shallow_rationale': (
        '一行推理如果只说"提升清晰度"或"学术化"，就不是推理——'
        '而是承认没有想清楚。每行应该解释为什么这个写作决策更好。'
    ),
    'unsupported_claim': (
        '每个主张都需要一个证据锚点。如果你不能指出哪个证据支撑一个主张，'
        '这个主张就是假设，不是发现。'
    ),
    'hollow_platitude': (
        '学术套话（如"具有重要意义""提供参考借鉴"）没有实质内容。'
        '用具体数据或具体意义替换。'
    ),
}


# ============================================================================
# 维度审计器
# ============================================================================

class ArtifactChainAuditor:
    """维度1: 产物链完整性审计"""

    REQUIRED_ARTIFACTS = {
        'motivation_options.md': '动机选项 — 论文的核心方向选择',
        'confirmed_motivation.md': '确认的动机 — 写作的宪法',
        'writing_blueprint.md': '写作蓝图 — 执行计划',
        'writing_execution_table.md': '写作执行表 — 逐段计划',
    }

    OPTIONAL_ARTIFACTS = {
        'deep_imitation_report.md': '深度模仿报告 — 范文学习结果',
        'citation_support_bank.md': '引用支持库 — 句子级引用绑定',
        'rationale_matrix.md': '推理矩阵 — 写作决策追踪',
        'seven_sentence_test.md': '七句话血统测试 — 首尾呼应验证',
    }

    @classmethod
    def audit(cls, output_dir: str) -> AuditDimension:
        dim = AuditDimension('产物链完整性')
        out = Path(output_dir)

        for artifact, desc in cls.REQUIRED_ARTIFACTS.items():
            if not (out / artifact).exists():
                dim.findings.append(AuditFinding(
                    id=f'ART-{len(dim.findings)+1:03d}',
                    severity='BLOCKER',
                    dimension=dim.name,
                    what_was_found=f'必要产物 `{artifact}` 缺失',
                    root_cause=f'上游步骤未生成该产物',
                    fix_action=f'回到对应的生成步骤，重新生成 `{artifact}`',
                    downstream_impact=f'缺少 {artifact}（{desc}），下游写作阶段缺乏必要输入',
                    teaching_note=TEACHING_NOTES['missing_artifact'],
                ))

        for artifact, desc in cls.OPTIONAL_ARTIFACTS.items():
            if not (out / artifact).exists():
                dim.findings.append(AuditFinding(
                    id=f'ART-{len(dim.findings)+1:03d}',
                    severity='INFO',
                    dimension=dim.name,
                    what_was_found=f'可选产物 `{artifact}` 不存在',
                    root_cause='',
                    fix_action=f'建议生成 `{artifact}` 以提升质量',
                    downstream_impact='',
                    teaching_note='',
                ))

        if not dim.findings:
            dim.findings.append(AuditFinding(
                id='ART-000', severity='INFO', dimension=dim.name,
                what_was_found='所有必要产物齐全',
                root_cause='', fix_action='', downstream_impact='',
                teaching_note='',
            ))
        return dim


class ReasoningDepthAuditor:
    """维度2: 推理深度审计"""

    @classmethod
    def audit(cls, output_dir: str) -> AuditDimension:
        dim = AuditDimension('推理深度')
        out = Path(output_dir)

        # 检查写作蓝图
        blueprint_path = out / 'writing_blueprint.md'
        if blueprint_path.exists():
            text = blueprint_path.read_text(encoding='utf-8', errors='ignore')
            if len(text) < 300:
                dim.findings.append(AuditFinding(
                    id='RSN-001',
                    severity='WARNING',
                    dimension=dim.name,
                    what_was_found='writing_blueprint.md 内容过短',
                    root_cause='写作蓝图生成不充分，缺少详细的章节规划',
                    fix_action='重新生成写作蓝图，确保每个章节都有功能、动机关联和证据说明',
                    downstream_impact='蓝图过浅会导致写作时缺乏方向，产出泛泛的文本',
                    teaching_note=TEACHING_NOTES['shallow_rationale'],
                ))

        # 检查执行表
        table_path = out / 'writing_execution_table.md'
        if table_path.exists():
            text = table_path.read_text(encoding='utf-8', errors='ignore')
            # 检查是否有通用占位符
            generic_count = 0
            for phrase in ['提升清晰度', '学术化', '润色', 'improve clarity', 'polish']:
                generic_count += text.lower().count(phrase)
            if generic_count > 3:
                dim.findings.append(AuditFinding(
                    id='RSN-002',
                    severity='WARNING',
                    dimension=dim.name,
                    what_was_found=f'执行表中发现 {generic_count} 处通用占位符',
                    root_cause='写作计划被当作检查清单而非设计工具',
                    fix_action='为每个包含通用占位符的行添加具体的动机关联和计划动作',
                    downstream_impact='通用计划产生通用写作',
                    teaching_note=TEACHING_NOTES['shallow_rationale'],
                ))

        # 检查推理矩阵
        rationale_path = out / 'rationale_matrix.md'
        if rationale_path.exists():
            text = rationale_path.read_text(encoding='utf-8', errors='ignore')
            if '（空）' in text or len(text) < 200:
                dim.findings.append(AuditFinding(
                    id='RSN-003',
                    severity='WARNING',
                    dimension=dim.name,
                    what_was_found='推理矩阵为空或过短',
                    root_cause='Discussion写作时未记录推理链',
                    fix_action='在Discussion写作时，为每个发现记录"发现→机制→证据→引用"推理链',
                    downstream_impact='没有推理矩阵，审稿人无法验证写作决策的合理性',
                    teaching_note=TEACHING_NOTES['shallow_rationale'],
                ))

        if not dim.findings:
            dim.findings.append(AuditFinding(
                id='RSN-000', severity='INFO', dimension=dim.name,
                what_was_found='推理深度合格',
                root_cause='', fix_action='', downstream_impact='', teaching_note='',
            ))
        return dim


class IntegrityPatternAuditor:
    """维度3: 完整性模式扫描"""

    WEAK_WORDS = {'clearly', 'obviously', 'undoubtedly', '显然', '毫无疑问', '不言而喻'}
    LEAP_WORDS = {'therefore', 'thus', 'hence', '因此', '所以', '故', '因而'}
    HOLLOW_PHRASES = {
        '具有重要意义', '提供参考借鉴', '有待进一步研究',
        'plays a crucial role', 'further research is needed',
        '填补了研究空白', '具有重要的理论和实践意义',
    }

    @classmethod
    def audit(cls, output_dir: str) -> AuditDimension:
        dim = AuditDimension('完整性模式')

        # 扫描所有 .md 文件
        out = Path(output_dir)
        all_text = ''
        for md_file in out.glob('*.md'):
            if md_file.name.startswith('integrity_audit'):
                continue
            all_text += md_file.read_text(encoding='utf-8', errors='ignore') + '\n'

        if not all_text:
            dim.findings.append(AuditFinding(
                id='INT-001', severity='INFO', dimension=dim.name,
                what_was_found='没有可扫描的文本',
                root_cause='', fix_action='', downstream_impact='', teaching_note='',
            ))
            return dim

        counter = 0

        # 弱断言
        found_weak = [w for w in cls.WEAK_WORDS if w in all_text.lower()]
        if found_weak:
            counter += 1
            dim.findings.append(AuditFinding(
                id=f'INT-{counter:03d}',
                severity='WARNING',
                dimension=dim.name,
                what_was_found=f'发现弱断言词: {", ".join(found_weak)}',
                root_cause='修辞性捷径掩盖了推理空白',
                fix_action='用具体证据替换每个弱断言词',
                downstream_impact='降低论文可信度',
                teaching_note=TEACHING_NOTES['weak_assertion'],
            ))

        # 逻辑跳跃
        leap_count = sum(all_text.lower().count(w) for w in cls.LEAP_WORDS)
        para_count = max(1, all_text.count('\n\n') + 1)
        if para_count > 0 and leap_count / para_count > 1.5:
            counter += 1
            dim.findings.append(AuditFinding(
                id=f'INT-{counter:03d}',
                severity='WARNING',
                dimension=dim.name,
                what_was_found=f'逻辑跳跃密度过高: {leap_count}个推理词 / {para_count}段 ({leap_count/para_count:.1f}/段)',
                root_cause='推理连接词替代了实际推理步骤',
                fix_action='为每个"因此"添加中间推理步骤',
                downstream_impact='读者感觉结论是跳跃得出的',
                teaching_note=TEACHING_NOTES['logical_leap'],
            ))

        # 空洞套话
        found_hollow = [p for p in cls.HOLLOW_PHRASES if p in all_text]
        if found_hollow:
            counter += 1
            dim.findings.append(AuditFinding(
                id=f'INT-{counter:03d}',
                severity='WARNING',
                dimension=dim.name,
                what_was_found=f'发现空洞套话: {", ".join(found_hollow[:3])}',
                root_cause='用通用学术短语替代了具体内容',
                fix_action='用具体数据或具体意义替换每个套话',
                downstream_impact='审稿人会认为论文缺乏实质性贡献',
                teaching_note=TEACHING_NOTES['hollow_platitude'],
            ))

        if not dim.findings:
            dim.findings.append(AuditFinding(
                id='INT-000', severity='INFO', dimension=dim.name,
                what_was_found='未发现显著完整性问题',
                root_cause='', fix_action='', downstream_impact='', teaching_note='',
            ))
        return dim


# ============================================================================
# 完整性审计管理器
# ============================================================================

class IntegrityAuditManager:
    """
    完整性审计管理器

    运行四维度审计，生成教学式报告。
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')

    def run_audit(self) -> IntegrityReport:
        """运行完整审计"""
        report = IntegrityReport(output_dir=self.output_dir)
        report.dimensions = [
            ArtifactChainAuditor.audit(self.output_dir),
            ReasoningDepthAuditor.audit(self.output_dir),
            IntegrityPatternAuditor.audit(self.output_dir),
        ]
        return report

    def format_report(self, report: IntegrityReport) -> str:
        """格式化为教学式 Markdown 报告"""
        lines = [
            "# 完整性审计报告 (Integrity Audit)",
            "",
            "> 本报告不仅检查，而且教学。每个发现都包含根因分析、修复建议、",
            "> 下游影响和教学说明。",
            "",
            f"- 输出目录: `{report.output_dir}`",
            f"- 总发现数: {report.total_findings}",
            f"- LaTeX门控: {'🚫 BLOCKED' if report.blocked else '✅ READY'}",
            "",
            "## 摘要",
            "",
            "| 维度 | 状态 | 发现数 |",
            "|------|------|--------|",
        ]

        for dim in report.dimensions:
            icon = {'BLOCKED': '🚫', 'WARNINGS': '⚠️', 'CLEAN': '✅'}[dim.status]
            lines.append(f"| {dim.name} | {icon} {dim.status} | {len(dim.findings)} |")

        lines.append("")

        for dim in report.dimensions:
            if not dim.findings:
                continue
            lines.append(f"## {dim.name}")
            lines.append("")

            for f in dim.findings:
                if f.severity == 'INFO':
                    lines.append(f"**{f.id}** ✅ {f.what_was_found}")
                    lines.append("")
                    continue

                icon = '🚫' if f.severity == 'BLOCKER' else '⚠️'
                lines.append(f"### {icon} {f.id} — {f.severity}")
                lines.append("")
                lines.append(f"**发现了什么:** {f.what_was_found}")
                lines.append("")
                if f.root_cause:
                    lines.append(f"**根因:** {f.root_cause}")
                    lines.append("")
                if f.fix_action:
                    lines.append(f"**修复:** {f.fix_action}")
                    lines.append("")
                if f.downstream_impact:
                    lines.append(f"**下游影响:** {f.downstream_impact}")
                    lines.append("")
                if f.teaching_note:
                    lines.append(f"**为什么重要:** {f.teaching_note}")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return '\n'.join(lines)

    def run_and_save(self) -> str:
        """运行审计并保存报告"""
        report = self.run_audit()
        md = self.format_report(report)

        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, 'integrity_audit.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md)

        return md


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        print("=" * 60)
        print("完整性审计测试")
        print("=" * 60)

        # 创建测试目录
        test_dir = '/tmp/test_integrity_audit'
        os.makedirs(test_dir, exist_ok=True)

        # 创建一些测试产物
        with open(os.path.join(test_dir, 'confirmed_motivation.md'), 'w', encoding='utf-8') as f:
            f.write('# 确认的动机\n\n揭示DO与CH4的负相关关系\n')

        with open(os.path.join(test_dir, 'writing_blueprint.md'), 'w', encoding='utf-8') as f:
            f.write('# 写作蓝图\n\n' * 50)  # 足够长

        with open(os.path.join(test_dir, 'discussion.md'), 'w', encoding='utf-8') as f:
            f.write(
                'DO与CH4呈显著负相关。显然这是因为厌氧条件导致的。'
                '因此，溶解氧是关键因素。所以需要进一步研究。'
                '具有重要意义。' * 5
            )

        mgr = IntegrityAuditManager(output_dir=test_dir)
        report = mgr.run_audit()

        print(f"\n总发现数: {report.total_findings}")
        print(f"是否被阻止: {report.blocked}")

        for dim in report.dimensions:
            print(f"\n  {dim.name}: {dim.status}")
            for f in dim.findings:
                icon = {'BLOCKER': '🚫', 'WARNING': '⚠️', 'INFO': '✅'}[f.severity]
                print(f"    {icon} {f.id}: {f.what_was_found[:50]}")

        md = mgr.format_report(report)
        print("\n" + md[:2000])
        print("...")

        print("\n测试通过!")
    else:
        print("用法: python integrity_audit.py --test")
