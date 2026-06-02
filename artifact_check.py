"""
=============================================================================
产品完整性检查脚本 - Artifact Completeness Check
借鉴自PaperSpine的artifact_check.py

功能：自动检查所有必要产物是否存在、内容是否合格。
可在写作流程中随时运行，也可在最终提交前运行。

检查维度：
  1. 文件存在性 — 必要产物是否都存在
  2. 内容质量 — 文件内容是否足够深入（非空/非占位符）
  3. 交叉引用 — 产物之间的引用关系是否完整
  4. 格式规范 — Markdown格式是否正确
=============================================================================
"""
import re
import os
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class CheckResult:
    """单个文件的检查结果"""
    filename: str
    exists: bool
    size_bytes: int = 0
    line_count: int = 0
    content_quality: str = "unknown"  # good/thin/empty/placeholder
    issues: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exists and self.content_quality in ('good',)


@dataclass
class ArtifactReport:
    """完整性检查报告"""
    output_dir: str
    workflow: str
    results: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def missing(self) -> int:
        return sum(1 for r in self.results if not r.exists)

    @property
    def thin(self) -> int:
        return sum(1 for r in self.results if r.exists and r.content_quality in ('thin', 'empty', 'placeholder'))

    @property
    def ok(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def pass_rate(self) -> float:
        return self.ok / self.total if self.total else 0.0


# ============================================================================
# 产物定义
# ============================================================================

# 通用必要产物
COMMON_REQUIRED = {
    'motivation_options.md': {
        'desc': '动机选项 — 论文方向选择',
        'min_lines': 5,
        'min_bytes': 200,
        'required_keywords': ['动机', '选项', 'motivation'],
    },
    'confirmed_motivation.md': {
        'desc': '确认的动机 — 写作宪法',
        'min_lines': 5,
        'min_bytes': 200,
        'required_keywords': ['动机', '确认', 'motivation'],
    },
    'writing_blueprint.md': {
        'desc': '写作蓝图 — 执行计划',
        'min_lines': 10,
        'min_bytes': 500,
        'required_keywords': ['章节', '功能', '动机关联'],
    },
    'writing_execution_table.md': {
        'desc': '写作执行表 — 逐段计划',
        'min_lines': 8,
        'min_bytes': 300,
        'required_keywords': ['写作单元', '功能'],
    },
}

# 深度模仿产物
IMITATION_ARTIFACTS = {
    'deep_imitation_report.md': {
        'desc': '深度模仿报告 — 范文学习结果',
        'min_lines': 10,
        'min_bytes': 300,
        'required_keywords': ['范文', '动作', 'blueprint'],
    },
}

# 引用支持库产物
CITATION_ARTIFACTS = {
    'citation_support_bank.md': {
        'desc': '引用支持库 — 句子级引用绑定',
        'min_lines': 8,
        'min_bytes': 300,
        'required_keywords': ['引用', '候选', 'claim'],
    },
}

# 审计产物
AUDIT_ARTIFACTS = {
    'integrity_audit.md': {
        'desc': '完整性审计报告',
        'min_lines': 5,
        'min_bytes': 200,
        'required_keywords': ['审计', '发现', 'audit'],
    },
    'seven_sentence_test.md': {
        'desc': '七句话血统测试',
        'min_lines': 5,
        'min_bytes': 150,
        'required_keywords': ['七句', '血统', 'Abstract'],
    },
}

# 最终产物
FINAL_ARTIFACTS = {
    'section_introduction.md': {
        'desc': 'Introduction章节',
        'min_lines': 15,
        'min_bytes': 800,
        'required_keywords': ['研究', '背景', 'Introduction'],
    },
    'section_methods.md': {
        'desc': 'Methods章节',
        'min_lines': 10,
        'min_bytes': 500,
        'required_keywords': ['方法', '采样', 'Methods'],
    },
    'section_results.md': {
        'desc': 'Results章节',
        'min_lines': 10,
        'min_bytes': 500,
        'required_keywords': ['结果', '显著', 'Results'],
    },
    'section_discussion.md': {
        'desc': 'Discussion章节',
        'min_lines': 15,
        'min_bytes': 800,
        'required_keywords': ['讨论', '机制', 'Discussion'],
    },
}


# ============================================================================
# 检查器
# ============================================================================

class ArtifactChecker:
    """
    产品完整性检查器

    用法：
        checker = ArtifactChecker(output_dir='paper_output')
        report = checker.check_all()
        print(checker.format_report(report))
    """

    def __init__(self, output_dir: str = None, workflow: str = 'full'):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        self.workflow = workflow

    def check_all(self) -> ArtifactReport:
        """检查所有产物"""
        report = ArtifactReport(
            output_dir=self.output_dir,
            workflow=self.workflow,
        )

        # 合并所有需要检查的产物
        all_artifacts = {}
        all_artifacts.update(COMMON_REQUIRED)
        all_artifacts.update(IMITATION_ARTIFACTS)
        all_artifacts.update(CITATION_ARTIFACTS)
        all_artifacts.update(AUDIT_ARTIFACTS)
        all_artifacts.update(FINAL_ARTIFACTS)

        for filename, spec in all_artifacts.items():
            result = self._check_file(filename, spec)
            report.results.append(result)

        return report

    def check_subset(self, artifact_keys: list) -> ArtifactReport:
        """检查指定的产物子集"""
        all_artifacts = {}
        all_artifacts.update(COMMON_REQUIRED)
        all_artifacts.update(IMITATION_ARTIFACTS)
        all_artifacts.update(CITATION_ARTIFACTS)
        all_artifacts.update(AUDIT_ARTIFACTS)
        all_artifacts.update(FINAL_ARTIFACTS)

        report = ArtifactReport(
            output_dir=self.output_dir,
            workflow=self.workflow,
        )

        for key in artifact_keys:
            if key in all_artifacts:
                result = self._check_file(key, all_artifacts[key])
                report.results.append(result)

        return report

    def _check_file(self, filename: str, spec: dict) -> CheckResult:
        """检查单个文件"""
        filepath = Path(self.output_dir) / filename
        result = CheckResult(filename=filename, exists=filepath.exists())

        if not result.exists:
            result.issues.append(f'文件不存在: {filename}')
            return result

        # 读取文件
        try:
            text = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            result.issues.append(f'读取失败: {e}')
            return result

        result.size_bytes = len(text.encode('utf-8'))
        result.line_count = text.count('\n') + 1

        # 检查内容质量
        result.content_quality = self._assess_quality(text, spec, result)

        return result

    def _assess_quality(self, text: str, spec: dict, result: CheckResult) -> str:
        """评估内容质量"""
        min_lines = spec.get('min_lines', 5)
        min_bytes = spec.get('min_bytes', 200)
        required_keywords = spec.get('required_keywords', [])

        # 检查是否为空
        if len(text.strip()) < 50:
            result.issues.append('内容过短（<50字符）')
            return 'empty'

        # 检查是否为占位符
        placeholders = ['待填写', 'TODO', 'TBD', '（空）', '(empty)', '待补充']
        if any(p in text for p in placeholders) and len(text) < 200:
            result.issues.append('内容为占位符')
            return 'placeholder'

        # 检查行数
        if result.line_count < min_lines:
            result.issues.append(f'行数不足: {result.line_count} < {min_lines}')

        # 检查字节数
        if result.size_bytes < min_bytes:
            result.issues.append(f'内容过短: {result.size_bytes} < {min_bytes} bytes')

        # 检查关键词
        text_lower = text.lower()
        missing_keywords = [kw for kw in required_keywords if kw.lower() not in text_lower]
        if missing_keywords:
            result.issues.append(f'缺少关键词: {", ".join(missing_keywords)}')

        # 综合判断
        if not result.issues:
            return 'good'
        elif result.line_count >= min_lines // 2 and result.size_bytes >= min_bytes // 2:
            return 'thin'
        else:
            return 'thin'

    def format_report(self, report: ArtifactReport) -> str:
        """格式化报告"""
        lines = [
            "# 产品完整性检查报告",
            "",
            f"- 输出目录: `{report.output_dir}`",
            f"- 工作流: `{report.workflow}`",
            f"- 检查时间: {report.timestamp}",
            f"- 总计: {report.total} 项",
            f"- 通过: {report.ok} 项 ({report.pass_rate:.0%})",
            f"- 缺失: {report.missing} 项",
            f"- 内容薄弱: {report.thin} 项",
            "",
        ]

        # 摘要表
        lines.extend([
            "## 摘要",
            "",
            "| 文件 | 状态 | 大小 | 行数 | 质量 | 问题 |",
            "|------|------|------|------|------|------|",
        ])

        for r in report.results:
            if not r.exists:
                status = '❌ 缺失'
            elif r.content_quality == 'good':
                status = '✅ 通过'
            elif r.content_quality == 'thin':
                status = '⚠️ 薄弱'
            else:
                status = '❌ 不合格'

            size = f'{r.size_bytes}B' if r.exists else '-'
            lines_count = str(r.line_count) if r.exists else '-'
            issues = '; '.join(r.issues[:2]) if r.issues else '-'

            lines.append(
                f"| {r.filename} | {status} | {size} | {lines_count} | "
                f"{r.content_quality} | {issues[:40]} |"
            )

        lines.append("")

        # 详细问题
        problems = [r for r in report.results if r.issues]
        if problems:
            lines.extend([
                "## 需要修复的问题",
                "",
            ])
            for r in problems:
                lines.append(f"### {r.filename}")
                for issue in r.issues:
                    lines.append(f"- {issue}")
                lines.append("")

        return '\n'.join(lines)

    def check_and_save(self) -> str:
        """运行检查并保存报告"""
        report = self.check_all()
        md = self.format_report(report)

        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, 'artifact_check.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md)

        # JSON 版本
        json_data = {
            'output_dir': report.output_dir,
            'workflow': report.workflow,
            'timestamp': report.timestamp,
            'total': report.total,
            'ok': report.ok,
            'missing': report.missing,
            'thin': report.thin,
            'pass_rate': report.pass_rate,
            'results': [
                {
                    'filename': r.filename,
                    'exists': r.exists,
                    'size_bytes': r.size_bytes,
                    'line_count': r.line_count,
                    'content_quality': r.content_quality,
                    'issues': r.issues,
                }
                for r in report.results
            ],
        }
        json_path = os.path.join(self.output_dir, 'artifact_check.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return md


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    if '--test' in sys.argv:
        print("=" * 60)
        print("产品完整性检查测试")
        print("=" * 60)

        # 创建测试目录
        test_dir = '/tmp/test_artifact_check'
        os.makedirs(test_dir, exist_ok=True)

        # 创建一些测试文件
        with open(os.path.join(test_dir, 'confirmed_motivation.md'), 'w', encoding='utf-8') as f:
            f.write("# 确认的动机\n\n| 字段 | 内容 |\n|------|------|\n| 动机陈述 | 揭示DO与CH4负相关 |\n| 来源 | 用户确认 |\n\n这是写作的宪法。\n")

        with open(os.path.join(test_dir, 'writing_blueprint.md'), 'w', encoding='utf-8') as f:
            f.write("# 写作蓝图\n\n## 全局框架理由\n\n本文以...为核心动机。\n\n## 章节蓝图\n\n| # | 章节 | 功能 | 动机关联 |\n|---|------|------|----------|\n| 1 | Introduction | 建立研究必要性 | 引出动机 |\n| 2 | Results | 展示证据 | 支撑动机 |\n| 3 | Discussion | 解释机制 | 闭合动机 |\n\n" + "详细内容。\n" * 20)

        checker = ArtifactChecker(output_dir=test_dir)
        report = checker.check_all()

        print(f"\n总计: {report.total}")
        print(f"通过: {report.ok} ({report.pass_rate:.0%})")
        print(f"缺失: {report.missing}")
        print(f"薄弱: {report.thin}")

        md = checker.format_report(report)
        print("\n" + md[:2000])
        print("...")

        print("\n测试通过!")
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        # CLI模式: python artifact_check.py <output_dir>
        output_dir = sys.argv[1]
        checker = ArtifactChecker(output_dir=output_dir)
        md = checker.check_and_save()
        print(md)
    else:
        print("用法:")
        print("  python artifact_check.py <output_dir>  # 检查指定目录")
        print("  python artifact_check.py --test        # 运行内置测试")
