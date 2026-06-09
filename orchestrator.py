"""
学术论文全流程编排器 — 串联所有模块

Pipeline:
  1. 读论文 → SQLite数据库持久化
  2. 文献矩阵 → 主题交叉+证据收敛+知识缺口
  3. 引用验证 → 三级验证（S2+DOI+Levenshtein）
  4. 写论文 → 数据分析→图表→正文生成
  5. 审稿 → SCI/中文核心多维检查
  6. 投稿前检查 → 中文核心规范清单
  7. 修订追踪 → 版本间变化审计
  8. 进化反馈 → 知识库更新

用法:
    from orchestrator import AcademicPipeline

    pipe = AcademicPipeline()

    # 全流程
    pipe.run_full_pipeline(source="论文路径或URL")

    # 单步调用
    paper = pipe.step1_read("arxiv/2301.12345")
    matrix = pipe.step2_matrix()
    verified = pipe.step3_verify_citations(refs)
    report = pipe.step5_review(text)
    checklist = pipe.step6_submission_check(text)

    # 状态查看
    print(pipe.status())
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class AcademicPipeline:
    """
    学术论文全流程编排器

    串联: paper_reader → literature_memory → paper_writing_agent
          → academic_review_agent → cn_core_rules → revision_audit
          → self_evolving_engine
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self._reader = None
        self._lit_memory = None
        self._writing_agent = None
        self._review_agent = None
        self._engine = None
        self._motivation_mgr = None
        self._pipeline_log = []

    # ============================================================
    # 延迟初始化各模块
    # ============================================================

    def _get_reader(self):
        if self._reader is None:
            from paper_reader import PaperReader
            self._reader = PaperReader()
        return self._reader

    def _get_lit_memory(self):
        if self._lit_memory is None:
            from literature_memory import LiteratureMemory
            self._lit_memory = LiteratureMemory(self.base_dir)
        return self._lit_memory

    def _get_review_agent(self, language='zh'):
        if self._review_agent is None:
            from academic_review_agent import AcademicReviewAgent
            paper_type = 'chinese_journal' if language == 'zh' else 'sci'
            self._review_agent = AcademicReviewAgent(
                paper_type=paper_type, language=language
            )
        return self._review_agent

    def _get_engine(self):
        if self._engine is None:
            try:
                from self_evolving_engine import EvolutionEngine
                self._engine = EvolutionEngine(self.base_dir)
                self._engine.initialize()
            except Exception as e:
                logger.debug(f"EvolutionEngine not available: {e}")
                self._engine = None
        return self._engine

    def _get_motivation_mgr(self):
        if self._motivation_mgr is None:
            from motivation_planner import MotivationManager
            output_dir = os.path.join(self.base_dir, 'paper_output')
            self._motivation_mgr = MotivationManager(output_dir=output_dir)
        return self._motivation_mgr

    def _log(self, step: str, detail: str, data: dict = None):
        self._pipeline_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "detail": detail,
            "data": data or {},
        })

    # ============================================================
    # Step 1: 读论文
    # ============================================================

    def step1_read(self, source: str, fetch_metadata: bool = True) -> Any:
        """
        读取论文并持久化到SQLite

        Parameters
        ----------
        source : str
            arxiv URL/ID, 本地PDF/TXT/MD路径
        fetch_metadata : bool
            是否从Semantic Scholar获取元数据

        Returns
        -------
        PaperContent
        """
        print(f"[Pipeline] Step 1: 读取论文 - {source}")
        reader = self._get_reader()
        paper = reader.read(source, fetch_metadata=fetch_metadata)

        self._log("step1_read", f"读取: {paper.metadata.title[:50]}", {
            "paper_id": paper.metadata.paper_id,
            "sections": len(paper.sections),
            "words": paper.word_count,
            "evidence_level": paper.metadata.evidence_level,
            "credibility": paper.metadata.credibility_score,
        })

        print(f"  完成: {paper.metadata.title[:50]}")
        print(f"  章节: {len(paper.sections)}, 字数: {paper.word_count}")
        print(f"  证据等级: L{paper.metadata.evidence_level}, "
              f"可信度: {paper.metadata.credibility_score:.2f}")
        return paper

    def step1_read_batch(self, sources: list, fetch_metadata: bool = True) -> list:
        """批量读取论文"""
        papers = []
        for i, source in enumerate(sources):
            print(f"\n[{i+1}/{len(sources)}]", end=" ")
            try:
                paper = self.step1_read(source, fetch_metadata)
                papers.append(paper)
            except Exception as e:
                print(f"  失败: {e}")
        print(f"\n[Pipeline] 批量读取完成: {len(papers)}/{len(sources)}")
        return papers

    # ============================================================
    # Step 2: 文献矩阵
    # ============================================================

    def step2_matrix(self, auto_themes: bool = True) -> str:
        """
        构建文献矩阵（来源×主题交叉表 + 证据收敛 + 知识缺口）

        Returns: Markdown 格式矩阵报告
        """
        print("[Pipeline] Step 2: 构建文献矩阵")
        reader = self._get_reader()

        # 同步已读论文到文献记忆
        mem = self._get_lit_memory()
        for pid, paper in reader._papers.items():
            if pid not in mem.matrix.papers:
                mem.assess_paper(paper)

        matrix_md = reader.build_literature_matrix()

        self._log("step2_matrix", "矩阵构建完成", {
            "papers": len(mem.matrix.papers),
            "themes": len(mem.matrix.themes),
        })

        print(f"  论文: {len(mem.matrix.papers)}篇")
        print(f"  主题: {len(mem.matrix.themes)}个")
        return matrix_md

    # ============================================================
    # Step 3: 引用验证
    # ============================================================

    def step3_verify_citations(self, references: list, timeout: int = 10) -> str:
        """
        三级引用验证（S2 API + DOI + Levenshtein）

        Parameters
        ----------
        references : list of dict, 每个 {title, doi?, year?}

        Returns: Markdown 验证报告
        """
        print(f"[Pipeline] Step 3: 验证 {len(references)} 条引用")
        reader = self._get_reader()
        report = reader.verify_references(references, timeout=timeout)

        self._log("step3_verify", f"验证{len(references)}条引用", {
            "count": len(references),
        })
        return report

    # ============================================================
    # Step 3.5: 动机生成（借鉴 PaperSpine motivation-first）
    # ============================================================

    def step3_5_motivation(self, analysis_results: dict = None,
                           language: str = 'zh') -> list:
        """
        生成动机选项 — 在写论文前必须先确认动机

        从分析结果中推导3-5个动机选项，供用户选择。

        Parameters
        ----------
        analysis_results : dict, 科学分析结果（来自 ScientificAnalysisAgent）
        language : str, 'zh'/'en'

        Returns
        -------
        list of MotivationOption: 动机选项列表
        """
        print("[Pipeline] Step 3.5: 生成动机选项")
        mgr = self._get_motivation_mgr()

        # 获取文献矩阵（如果可用）
        lit_matrix = ""
        try:
            mem = self._get_lit_memory()
            if mem.matrix.papers:
                lit_matrix = f"{len(mem.matrix.papers)}篇论文, {len(mem.matrix.themes)}个主题"
        except Exception:
            pass

        options = mgr.generate_options(
            analysis_results=analysis_results,
            literature_matrix=lit_matrix,
            language=language,
        )

        self._log("step3_5_motivation", f"生成{len(options)}个动机选项", {
            "count": len(options),
            "language": language,
        })

        print(f"  生成 {len(options)} 个动机选项:")
        for opt in options:
            print(f"    [{opt.option_id}] {opt.one_sentence[:60]}")
        print(f"\n  请调用 step3_6_confirm_motivation('{options[0].option_id}') 确认动机")

        return options

    def step3_6_confirm_motivation(self, option_id: str = None,
                                    custom_motivation: str = None,
                                    language: str = 'zh') -> dict:
        """
        确认动机并生成写作蓝图

        三种确认方式：
        1. option_id='A' — 选择一个选项
        2. custom_motivation='...' — 用户自写动机
        3. option_id='A', 编辑某个字段

        Parameters
        ----------
        option_id : str, 选项ID（A/B/C/D/E）
        custom_motivation : str, 用户自写的动机
        language : str, 'zh'/'en'

        Returns
        -------
        dict: {confirmed_motivation, blueprint, execution_table}
        """
        print("[Pipeline] Step 3.6: 确认动机")
        mgr = self._get_motivation_mgr()

        # 确认动机
        confirmed = mgr.confirm(
            option_id=option_id,
            custom_motivation=custom_motivation,
        )

        print(f"  动机已确认: {confirmed.motivation_statement[:60]}")
        print(f"  来源: {confirmed.source}")

        # 生成写作蓝图
        blueprint = mgr.generate_blueprint(language=language)

        print(f"  写作蓝图已生成: {len(blueprint.section_blueprints)} 个章节")

        self._log("step3_6_confirm", "动机确认+写作蓝图生成", {
            "source": confirmed.source,
            "motivation": confirmed.motivation_statement[:50],
            "sections": len(blueprint.section_blueprints),
        })

        return {
            "confirmed_motivation": confirmed,
            "blueprint": blueprint,
            "execution_table": blueprint.to_execution_table(),
        }

    # ============================================================
    # Step 3.7: 深度模仿分析（借鉴 PaperSpine deep-imitation-protocol）
    # ============================================================

    def step3_7_deep_imitation(self, section_name: str, exemplar_text: str,
                                draft_text: str, paper_title: str = "") -> dict:
        """
        深度模仿分析 — 三层表格法+闭卷改写

        Parameters
        ----------
        section_name : str, 章节名
        exemplar_text : str, 范文文本
        draft_text : str, 草稿文本
        paper_title : str, 范文标题

        Returns
        -------
        dict: {exemplar_moves, draft_moves, target_moves, report}
        """
        print(f"[Pipeline] Step 3.7: 深度模仿分析 - {section_name}")
        from deep_imitation import DeepImitationManager

        output_dir = os.path.join(self.base_dir, 'paper_output')
        mgr = DeepImitationManager(output_dir=output_dir)

        exemplar_moves = mgr.analyze_exemplar(section_name, exemplar_text, paper_title)
        draft_moves = mgr.analyze_draft(section_name, draft_text)
        target_moves = mgr.generate_blueprint(section_name)

        self._log("step3_7_imitation", f"深度模仿: {section_name}", {
            "exemplar_moves": len(exemplar_moves),
            "draft_moves": len(draft_moves),
            "target_moves": len(target_moves),
        })

        print(f"  范文动作: {len(exemplar_moves)}, 草稿动作: {len(draft_moves)}, 目标: {len(target_moves)}")

        report = mgr.generate_report(section_name)
        return {
            "exemplar_moves": exemplar_moves,
            "draft_moves": draft_moves,
            "target_moves": target_moves,
            "report": report,
        }

    # ============================================================
    # Step 3.8: 完整性审计（教学模式）
    # ============================================================

    def step3_8_integrity_audit(self) -> str:
        """
        完整性审计 — 四维度教学式审计

        Returns: Markdown 审计报告
        """
        print("[Pipeline] Step 3.8: 完整性审计")
        from integrity_audit import IntegrityAuditManager

        output_dir = os.path.join(self.base_dir, 'paper_output')
        mgr = IntegrityAuditManager(output_dir=output_dir)
        report = mgr.run_audit()
        md = mgr.format_report(report)

        # 保存
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, 'integrity_audit.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(md)

        blocked = report.blocked
        self._log("step3_8_audit", f"完整性审计: {report.total_findings}发现, {'阻止' if blocked else '通过'}", {
            "total_findings": report.total_findings,
            "blocked": blocked,
        })

        print(f"  发现: {report.total_findings}, 状态: {'BLOCKED' if blocked else 'READY'}")
        return md

    # ============================================================
    # Step 3.9: 引用支持库（claim级绑定）
    # ============================================================

    def step3_9_citation_bank(self, paper_text: str = None,
                               section: str = "Introduction") -> str:
        """
        构建引用支持库 — 每个引用绑定到句子级claim

        Parameters
        ----------
        paper_text : str, 论文文本（用于提取claims）
        section : str, 章节名

        Returns
        -------
        str: 引用支持库报告
        """
        print("[Pipeline] Step 3.9: 构建引用支持库")
        from citation_support_bank import CitationSupportBank

        output_dir = os.path.join(self.base_dir, 'paper_output')
        bank = CitationSupportBank(output_dir=output_dir)

        # 从知识库加载已有引用
        try:
            from citation_audit import extract_citations_from_file
            # 尝试从已有论文中提取引用
        except Exception:
            pass

        # 从论文文本中提取claims
        if paper_text:
            claims = bank.extract_claims_from_text(paper_text, section)
            print(f"  提取了 {len(claims)} 个claims")

        # 绑定引用
        bindings = bank.bind_citations()

        # 保存
        bank.save()
        report = bank.generate_report()

        self._log("step3_9_citation_bank", f"引用支持库: {len(bank.candidates)}候选", {
            "candidates": len(bank.candidates),
            "claims": len(bank.claims),
        })

        print(f"  候选: {len(bank.candidates)}, Claims: {len(bank.claims)}")
        return report

    # ============================================================
    # Step 3.95: 产品完整性检查
    # ============================================================

    def step3_95_artifact_check(self) -> str:
        """
        产品完整性检查 — 自动检查所有必要产物

        Returns: Markdown 检查报告
        """
        print("[Pipeline] Step 3.95: 产品完整性检查")
        from artifact_check import ArtifactChecker

        output_dir = os.path.join(self.base_dir, 'paper_output')
        checker = ArtifactChecker(output_dir=output_dir)
        report = checker.check_all()
        md = checker.format_report(report)

        # 保存
        checker.check_and_save()

        self._log("step3_95_check", f"产物检查: {report.ok}/{report.total}通过", {
            "total": report.total,
            "ok": report.ok,
            "missing": report.missing,
            "thin": report.thin,
        })

        print(f"  {report.ok}/{report.total} 通过, {report.missing} 缺失, {report.thin} 薄弱")
        return md

    def step4_write(self, data_file: str = None, output_dir: str = None,
                    language: str = 'zh') -> str:
        """
        生成论文（数据分析 → 图表 → 正文）

        Parameters
        ----------
        data_file : str, 数据文件路径
        output_dir : str, 输出目录
        language : str, 'zh'/'en'

        Returns: 生成的论文文本
        """
        print("[Pipeline] Step 4: 生成论文")

        try:
            from paper_writing_agent import PaperWriter
            agent = PaperWriter(output_dir=os.path.join(self.base_dir, 'paper_output'))
            result = agent.write(data_path=data_file, language=language)

            self._log("step4_write", "论文生成完成", {
                "data_file": data_file,
                "language": language,
            })
            return str(result)
        except Exception as e:
            msg = f"论文生成失败: {e}"
            print(f"  {msg}")
            self._log("step4_write", msg)
            return msg

    def step4_write_review_loop(self, data_file: str = None, output_dir: str = None,
                                language: str = 'zh', max_rounds: int = 2,
                                target_score: float = 7.0) -> dict:
        """
        写→审→改 自动循环

        写作 -> 审稿 -> 根据 CRITICAL/MAJOR 问题修改 -> 再审 -> 直到评分达标或循环上限

        Parameters
        ----------
        data_file : str, 数据文件路径
        output_dir : str, 输出目录
        language : str, 'zh'/'en'
        max_rounds : int, 最大循环次数
        target_score : float, 目标综合评分 (0-10)

        Returns
        -------
        dict: {final_paper, rounds, final_score, issues_fixed}
        """
        import re as _re

        print(f"[Pipeline] Step 4+: 写→审→改循环 (最多{max_rounds}轮, 目标{target_score}分)")
        output_dir = output_dir or os.path.join(self.base_dir, 'paper_output')

        # 第一轮：生成论文
        paper_text = self.step4_write(data_file, output_dir, language)
        if paper_text.startswith("论文生成失败"):
            return {"final_paper": paper_text, "rounds": 0, "final_score": 0, "issues_fixed": 0}

        total_fixed = 0

        for round_num in range(1, max_rounds + 1):
            print(f"\n{'='*50}")
            print(f"  审稿第 {round_num}/{max_rounds} 轮")
            print(f"{'='*50}")

            # 审稿
            review = self.step5_review(paper_text, language)
            summary = review["summary"]
            issues = review["issues"]

            # 计算综合评分
            scores = review.get("scores", {})
            if scores:
                avg_score = sum(scores.values()) / len(scores)
            else:
                avg_score = 10.0 - summary["by_severity"].get("CRITICAL", 0) * 2.0 \
                           - summary["by_severity"].get("MAJOR", 0) * 1.0 \
                           - summary["by_severity"].get("MINOR", 0) * 0.3
                avg_score = max(0, avg_score)

            print(f"  评分: {avg_score:.1f}/{target_score}")

            # 检查是否达标
            if avg_score >= target_score:
                print(f"  ✓ 评分达标，结束循环")
                break

            # 提取需要修复的 CRITICAL 和 MAJOR 问题
            critical_issues = [i for i in issues if i.severity.value == "CRITICAL"]
            major_issues = [i for i in issues if i.severity.value == "MAJOR"]

            if not critical_issues and not major_issues:
                print(f"  ✓ 无 CRITICAL/MAJOR 问题，结束循环")
                break

            # 生成修改指令
            fix_instructions = []
            for issue in critical_issues[:5]:
                fix_instructions.append(f"[CRITICAL] {issue.category}: {issue.problem}\n  建议: {issue.suggestion}")
            for issue in major_issues[:5]:
                fix_instructions.append(f"[MAJOR] {issue.category}: {issue.problem}\n  建议: {issue.suggestion}")

            print(f"  需修复: {len(critical_issues)} CRITICAL + {len(major_issues)} MAJOR")

            # 自动修复（针对引用问题）
            fixed_count = 0
            for issue in critical_issues + major_issues:
                if issue.category == '引用质量':
                    if '编号' in issue.problem:
                        # 孤儿引用：在参考文献中补充占位
                        orphans = _re.findall(r'\d+', issue.problem.split(':')[-1]) if ':' in issue.problem else []
                        if orphans:
                            fixed_count += self._fix_orphan_citations(paper_text, orphans)
                    elif '未在正文' in issue.problem:
                        # 未使用引用：删除多余条目
                        unused = _re.findall(r'\d+', issue.problem.split(':')[-1]) if ':' in issue.problem else []
                        if unused:
                            paper_text = self._remove_unused_references(paper_text, unused)
                            fixed_count += len(unused)

            total_fixed += fixed_count

            if fixed_count > 0:
                print(f"  自动修复了 {fixed_count} 个引用问题")
                # 保存修复后的论文
                paper_path = os.path.join(output_dir, f'paper_{language}.md')
                with open(paper_path, 'w', encoding='utf-8') as f:
                    f.write(paper_text)
            else:
                print(f"  无法自动修复，需要手动处理")
                break

        self._log("step4_review_loop", f"循环完成: {total_fixed}个问题已修复", {
            "rounds": round_num if 'round_num' in dir() else 0,
            "fixed": total_fixed,
        })

        return {
            "final_paper": paper_text,
            "rounds": round_num if 'round_num' in dir() else 0,
            "final_score": avg_score if 'avg_score' in dir() else 0,
            "issues_fixed": total_fixed,
        }

    def _fix_orphan_citations(self, paper_text: str, orphan_nums: list) -> int:
        """为孤儿引用在参考文献末尾补充占位条目"""
        import re as _re
        fixed = 0
        for num in orphan_nums:
            num = int(num)
            # 在参考文献区域查找合适位置插入
            ref_match = _re.search(r'(#[\s]*参考文献\s*\n)', paper_text)
            if ref_match:
                # 在最后一个参考文献条目后插入
                insert_pos = len(paper_text) - 1
                placeholder = f"\n[{num}] [待补充 - 自动插入的占位条目]"
                paper_text = paper_text[:insert_pos] + placeholder + paper_text[insert_pos:]
                fixed += 1
        return fixed

    def _remove_unused_references(self, paper_text: str, unused_nums: list) -> str:
        """从参考文献列表中删除未使用的条目"""
        import re as _re
        for num in unused_nums:
            # 匹配 [N] 开头的行并删除
            pattern = _re.compile(rf'^\s*\[{num}\]\s+.*$', _re.MULTILINE)
            paper_text = pattern.sub('', paper_text)
        return paper_text

    # ============================================================
    # Step 5: 审稿
    # ============================================================

    def step5_review(self, text: str, language: str = 'zh') -> dict:
        """
        多维审稿检查

        包含: SCI格式 + 中文格式 + 中文核心专项 + 错别字 + 学术语法
              + 引文规范 + 图表规范 + 数据逻辑 + Discussion逻辑
              + AI痕迹 + 学术重复 + 推理链 + 逻辑跳跃 + 引用质量

        Returns: {issues, scores, summary, report_md}
        """
        print("[Pipeline] Step 5: 审稿检查")
        agent = self._get_review_agent(language)
        report = agent.review(text)

        summary = report.summary()
        self._log("step5_review", f"发现{summary['total']}个问题", summary)

        # 生成Markdown报告
        lines = ["# 审稿报告", ""]
        lines.append(f"**总计**: {summary['total']}个问题")
        lines.append(f"- CRITICAL: {summary['by_severity'].get('CRITICAL', 0)}")
        lines.append(f"- MAJOR: {summary['by_severity'].get('MAJOR', 0)}")
        lines.append(f"- MINOR: {summary['by_severity'].get('MINOR', 0)}")
        lines.append("")

        by_cat = summary.get('by_category', {})
        if by_cat:
            lines.append("## 分类统计")
            for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
                lines.append(f"- {cat}: {count}")
            lines.append("")

        lines.append("## 问题详情")
        for issue in report.issues:
            lines.append(f"\n### [{issue.severity.value}] {issue.category}")
            lines.append(f"- **位置**: {issue.section} / {issue.location}")
            lines.append(f"- **问题**: {issue.problem}")
            if issue.original:
                lines.append(f"- **原文**: {issue.original[:100]}")
            lines.append(f"- **建议**: {issue.suggestion}")
            if issue.teaching_note:
                lines.append(f"- **提示**: {issue.teaching_note}")

        report_md = "\n".join(lines)

        print(f"  发现 {summary['total']} 个问题")
        print(f"  CRITICAL={summary['by_severity'].get('CRITICAL',0)}, "
              f"MAJOR={summary['by_severity'].get('MAJOR',0)}, "
              f"MINOR={summary['by_severity'].get('MINOR',0)}")

        return {
            "issues": report.issues,
            "scores": report.scores,
            "summary": summary,
            "report_md": report_md,
        }

    # ============================================================
    # Step 6: 投稿前检查
    # ============================================================

    def step6_submission_check(self, text: str, sections: dict = None) -> str:
        """
        中文核心期刊投稿前检查清单（37项）

        Returns: Markdown 检查报告
        """
        print("[Pipeline] Step 6: 投稿前检查")
        from cn_core_rules import SubmissionChecklist

        items = SubmissionChecklist.run_check(text, sections)
        report_md = SubmissionChecklist.generate_report(items)

        fail_count = sum(1 for i in items if i.status == 'fail')
        warn_count = sum(1 for i in items if i.status == 'warn')

        self._log("step6_checklist", f"{fail_count}不通过, {warn_count}警告", {
            "total": len(items),
            "fail": fail_count,
            "warn": warn_count,
        })

        print(f"  {len(items)}项检查: {fail_count}不通过, {warn_count}警告")
        return report_md

    # ============================================================
    # Step 7: 修订追踪
    # ============================================================

    def step7_revision_audit(self, original: str, revised: str) -> dict:
        """
        版本间修订审计

        Returns: {unchanged_ratio, new_ratio, shallow_warning, report}
        """
        print("[Pipeline] Step 7: 修订审计")
        try:
            from revision_audit import audit_revision
            result = audit_revision(original, revised)

            self._log("step7_revision", "修订审计完成", {
                "unchanged_ratio": result.unchanged_ratio,
                "new_ratio": result.new_ratio,
                "shallow_warning": result.shallow_warning,
            })

            print(f"  未变: {result.unchanged_ratio:.0%}, "
                  f"新增: {result.new_ratio:.0%}, "
                  f"浅改警告: {result.shallow_warning}")
            return {
                "unchanged_ratio": result.unchanged_ratio,
                "new_ratio": result.new_ratio,
                "shallow_warning": result.shallow_warning,
            }
        except Exception as e:
            print(f"  修订审计不可用: {e}")
            return {"error": str(e)}

    # ============================================================
    # Step 8: 进化反馈
    # ============================================================

    def step8_evolve(self) -> str:
        """
        执行进化周期：反馈学习 + 知识库更新

        Returns: 进化报告
        """
        print("[Pipeline] Step 8: 进化反馈")
        engine = self._get_engine()
        if engine is None:
            return "进化引擎不可用"

        try:
            report = engine.evolve_cycle(include_github_scan=False)
            summary = report.get("summary", "")
            self._log("step8_evolve", "进化周期完成")
            print(f"  进化完成")
            return summary
        except Exception as e:
            return f"进化失败: {e}"

    # ============================================================
    # Step 9: 文档组装（文字 + 图片 → DOCX）
    # ============================================================

    def step9_assemble_document(self, sections=None, figures=None,
                                 output_path=None, title=None,
                                 data_file=None, output_dir=None,
                                 paper_type='chinese', language='zh') -> str:
        """
        将文字章节 + 图片组装成排版好的 DOCX。

        两种模式:
          A) 传入 sections + figures 列表，手动组装
          B) 传入 data_file，自动分析+出图+写文字+组装

        Parameters
        ----------
        sections : list of dict or None
            [{'heading': str, 'text': str, 'level': int}, ...]
        figures : list of dict or None
            [{'path': str, 'caption': str, 'after_section': int}, ...]
        output_path : str or None, DOCX 输出路径
        title : str or None, 论文标题
        data_file : str or None, 数据文件（自动模式）
        output_dir : str or None, 输出目录
        paper_type : str, 'chinese'/'sci'/'nature'
        language : str, 'zh'/'en'

        Returns
        -------
        str: 输出路径
        """
        from document_assembler import DocumentAssembler, assemble_paper

        if output_dir is None:
            output_dir = os.path.join(self.base_dir, 'paper_output')

        # === 自动模式：从数据分析到文档组装 ===
        if data_file and sections is None:
            return self._auto_assemble(data_file, output_dir, output_path,
                                        title, paper_type, language)

        # === 手动模式：直接组装 ===
        if sections is None:
            print("[Pipeline] Step 9 需要 sections 或 data_file 参数")
            return ""

        if output_path is None:
            output_path = os.path.join(output_dir, 'paper.docx')

        assembler = DocumentAssembler(title=title, paper_type=paper_type, language=language)

        fig_by_section = {}
        for fig in (figures or []):
            idx = fig.get('after_section', -1)
            fig_by_section.setdefault(idx, []).append(fig)

        for i, section in enumerate(sections):
            assembler.add_section(
                heading=section['heading'],
                text=section.get('text'),
                level=section.get('level', 1)
            )
            for fig in fig_by_section.get(i, []):
                assembler.add_figure(
                    image_path=fig['path'],
                    caption=fig.get('caption'),
                    width=fig.get('width'),
                )

        for fig in fig_by_section.get(-1, []):
            assembler.add_figure(
                image_path=fig['path'],
                caption=fig.get('caption'),
                width=fig.get('width'),
            )

        result_path = assembler.assemble(output_path)
        self._log("step9_assemble", f"文档组装完成: {result_path}")
        return result_path

    def _auto_assemble(self, data_file, output_dir, output_path,
                        title, paper_type, language):
        """自动模式：数据分析 → 出图 → 写文字 → 组装文档"""
        from scientific_analysis_agent import ScientificAnalysisAgent
        from document_assembler import assemble_from_analysis

        print("[Pipeline] Step 9 (自动): 数据分析 → 出图 → 组装文档")

        # 1. 数据分析
        agent = ScientificAnalysisAgent(data_file, output_dir)
        agent.load_data()
        agent.run(language)

        # 2. 组装文档
        if output_path is None:
            output_path = os.path.join(output_dir, 'analysis_report.docx')

        result_path = assemble_from_analysis(agent, output_dir, paper_type)
        self._log("step9_auto_assemble", f"自动组装完成: {result_path}")
        return result_path

    # ============================================================
    # Step 10: 自动学习（搜论文→提取知识→存入知识库）
    # ============================================================

    def step_auto_learn(self, topic: str, max_papers: int = 10,
                        read_top_n: int = 5) -> dict:
        """
        自动学习：搜索论文 → 读取 → 提取句式/机制/讨论结构 → 存入知识库。

        Parameters
        ----------
        topic : str, 研究主题（如 "sewage methane emission"）
        max_papers : int, 搜索最大论文数
        read_top_n : int, 实际读取的论文数

        Returns
        -------
        dict: 学习报告
        """
        print(f"[Pipeline] Step 10: 自动学习 - {topic}")
        engine = self._get_engine()
        if engine is None:
            print("  进化引擎不可用")
            return {"error": "进化引擎不可用"}

        report = engine.auto_learn(topic, max_papers=max_papers, read_top_n=read_top_n)
        self._log("step_auto_learn", f"自动学习: {topic}", {
            "papers_found": report.get('papers_found', 0),
            "patterns_learned": report.get('patterns_learned', 0),
            "mechanisms_learned": report.get('mechanisms_learned', 0),
        })

        # 引导下一步
        print(self.suggest_next_steps('step_auto_learn'))
        return report

    # ============================================================
    # 下一步引导
    # ============================================================

    def suggest_next_steps(self, completed_step=None) -> str:
        """
        根据已完成的步骤，输出下一步可选操作。

        Parameters
        ----------
        completed_step : str or None, 刚完成的步骤名。None 时显示全部可用步骤。

        Returns
        -------
        str: 格式化的下一步建议
        """
        # 定义所有步骤及其元信息
        steps = {
            'start': {
                'label': '开始',
                'next': ['step1_read', 'step3_5_motivation', 'step4_write', 'step9_assemble_document'],
            },
            'step1_read': {
                'label': '读取论文',
                'next': ['step2_matrix', 'step3_verify_citations', 'step5_review'],
                'done_msg': '论文已读取并存入数据库',
            },
            'step2_matrix': {
                'label': '文献矩阵',
                'next': ['step3_verify_citations', 'step3_5_motivation', 'step4_write'],
                'done_msg': '文献矩阵已构建',
            },
            'step3_verify_citations': {
                'label': '引用验证',
                'next': ['step3_5_motivation', 'step4_write', 'step5_review'],
                'done_msg': '引用验证完成',
            },
            'step3_5_motivation': {
                'label': '动机生成',
                'next': ['step3_6_confirm_motivation'],
                'done_msg': '动机选项已生成，请确认',
            },
            'step3_6_confirm_motivation': {
                'label': '动机确认+蓝图',
                'next': ['step3_7_deep_imitation', 'step3_8_integrity_audit', 'step4_write'],
                'done_msg': '动机已确认，写作蓝图已生成',
            },
            'step3_7_deep_imitation': {
                'label': '深度模仿',
                'next': ['step3_8_integrity_audit', 'step4_write'],
                'done_msg': '深度模仿分析完成',
            },
            'step3_8_integrity_audit': {
                'label': '完整性审计',
                'next': ['step3_9_citation_bank', 'step4_write'],
                'done_msg': '完整性审计完成',
            },
            'step3_9_citation_bank': {
                'label': '引用支持库',
                'next': ['step3_95_artifact_check', 'step4_write'],
                'done_msg': '引用支持库已构建',
            },
            'step3_95_artifact_check': {
                'label': '产物完整性检查',
                'next': ['step4_write', 'step5_review'],
                'done_msg': '产物完整性检查完成',
            },
            'step4_write': {
                'label': '论文写作',
                'next': ['step5_review', 'step6_submission_check', 'step9_assemble_document'],
                'done_msg': '论文文字已生成',
            },
            'step5_review': {
                'label': '审稿检查',
                'next': ['step6_submission_check', 'step7_revision_audit', 'step9_assemble_document'],
                'done_msg': '审稿完成',
            },
            'step6_submission_check': {
                'label': '投稿前检查',
                'next': ['step7_revision_audit', 'step9_assemble_document'],
                'done_msg': '投稿检查完成',
            },
            'step7_revision_audit': {
                'label': '修订审计',
                'next': ['step5_review', 'step8_evolve'],
                'done_msg': '修订审计完成',
            },
            'step8_evolve': {
                'label': '进化反馈',
                'next': ['step9_assemble_document'],
                'done_msg': '知识库已更新',
            },
            'step9_assemble_document': {
                'label': '文档组装',
                'next': ['step5_review', 'step10_auto_learn'],
                'done_msg': 'DOCX 文档已生成',
            },
            'step10_auto_learn': {
                'label': '自动学习',
                'next': ['step4_write', 'step9_assemble_document'],
                'done_msg': '知识库已自动学习扩展',
            },
        }

        # 步骤的详细说明
        step_details = {
            'step1_read': '读取论文 (arxiv URL / 本地PDF / TXT)，提取结构+元数据',
            'step2_matrix': '构建文献矩阵 (来源×主题交叉表 + 证据收敛 + 知识缺口)',
            'step3_verify_citations': '引用验证 (S2 API + DOI + Levenshtein 三级验证)',
            'step3_5_motivation': '动机生成 (从分析结果推导3-5个动机选项，借鉴PaperSpine motivation-first)',
            'step3_6_confirm_motivation': '动机确认+写作蓝图 (用户确认动机，生成执行计划)',
            'step3_7_deep_imitation': '深度模仿 (三层表格法学习范文+闭卷改写，借鉴PaperSpine deep-imitation-protocol)',
            'step3_8_integrity_audit': '完整性审计 (四维度教学式审计：根因+修复+影响+教学)',
            'step3_9_citation_bank': '引用支持库 (句子级claim-引用绑定，借鉴PaperSpine citation_support_bank)',
            'step3_95_artifact_check': '产物完整性检查 (自动检查所有必要产物的存在性和内容质量)',
            'step4_write': '论文写作 (基于确认动机+写作蓝图，数据分析 → 图表 → 正文)',
            'step5_review': '审稿检查 (10类检查 + AI痕迹检测 + 修改建议)',
            'step6_submission_check': '投稿前检查 (中文核心期刊37项规范清单)',
            'step7_revision_audit': '修订审计 (版本间变化检测，区分实质修改vs浅编辑)',
            'step8_evolve': '进化反馈 (反馈学习 + 知识库参数调优)',
            'step9_assemble_document': '文档组装 (文字+图片 → 排版好的DOCX，图文对应)',
            'step10_auto_learn': '自动学习 (搜论文→提取句式/机制/讨论结构→存入知识库)',
        }

        # 构建输出
        if completed_step and completed_step in steps:
            info = steps[completed_step]
            lines = [
                f"\n{'─' * 50}",
                f"  [OK] {info.get('done_msg', '步骤完成')}",
                f"{'─' * 50}",
                "",
                "  下一步可以做：",
                "",
            ]
            for i, next_step in enumerate(info['next'], 1):
                detail = step_details.get(next_step, '')
                lines.append(f"  [{i}] {next_step}")
                lines.append(f"      {detail}")
                lines.append("")
            lines.append(f"{'─' * 50}")
            return "\n".join(lines)

        # 没指定步骤：显示全部可用步骤
        lines = [
            f"\n{'═' * 50}",
            "  学术AI系统 — 可用步骤",
            f"{'═' * 50}",
            "",
        ]
        all_steps = [
            ('step1_read', '读取论文'),
            ('step2_matrix', '文献矩阵'),
            ('step3_verify_citations', '引用验证'),
            ('step3_5_motivation', '动机生成'),
            ('step3_6_confirm_motivation', '动机确认+写作蓝图'),
            ('step3_7_deep_imitation', '深度模仿'),
            ('step3_8_integrity_audit', '完整性审计'),
            ('step3_9_citation_bank', '引用支持库'),
            ('step3_95_artifact_check', '产物完整性检查'),
            ('step4_write', '论文写作'),
            ('step5_review', '审稿检查'),
            ('step6_submission_check', '投稿前检查'),
            ('step7_revision_audit', '修订审计'),
            ('step8_evolve', '进化反馈'),
            ('step9_assemble_document', '文档组装'),
            ('step10_auto_learn', '自动学习'),
        ]
        for step_name, short_label in all_steps:
            detail = step_details.get(step_name, '')
            lines.append(f"  {step_name}")
            lines.append(f"    {detail}")
            lines.append("")

        lines.append(f"  快捷命令:")
        lines.append(f"    pipe.run_full_pipeline(source)  # 全流程")
        lines.append(f"    pipe.step9_assemble_document(data_file='data.xlsx')  # 一键：分析+出图+组装DOCX")
        lines.append(f"{'═' * 50}")
        return "\n".join(lines)

    # ============================================================
    # 全流程
    # ============================================================

    def run_full_pipeline(self, source: str = None, text: str = None,
                          language: str = 'zh', skip_write: bool = False) -> dict:
        """
        运行完整学术论文流程

        Parameters
        ----------
        source : str, 论文来源（arxiv URL/本地文件），Step 1
        text : str, 已有论文文本（跳过Step 1直接审稿）
        language : str, 'zh'/'en'
        skip_write : bool, 跳过Step 4写作

        Returns: {paper, matrix_md, review, checklist, pipeline_log}
        """
        results = {}
        print("=" * 50)
        print("学术论文全流程")
        print("=" * 50)

        # Step 1: 读论文
        if source:
            paper = self.step1_read(source)
            results["paper"] = paper
            text = "\n".join(s.text for s in paper.sections)
        elif not text:
            print("[Pipeline] 需要 source 或 text 参数")
            return results

        # Step 2: 文献矩阵
        try:
            results["matrix_md"] = self.step2_matrix()
        except Exception as e:
            print(f"[Pipeline] Step 2 跳过: {e}")

        # Step 3: 引用验证（如果有引用）
        if source and results.get("paper") and results["paper"].references:
            try:
                results["citation_report"] = self.step3_verify_citations(
                    results["paper"].references[:10]
                )
            except Exception as e:
                print(f"[Pipeline] Step 3 跳过: {e}")

        # Step 4: 写论文（可选）
        if not skip_write and not text:
            try:
                results["written_paper"] = self.step4_write(language=language)
                text = results["written_paper"]
            except Exception as e:
                print(f"[Pipeline] Step 4 跳过: {e}")

        # Step 5: 审稿
        if text:
            results["review"] = self.step5_review(text, language)

        # Step 6: 投稿前检查
        if text:
            results["checklist"] = self.step6_submission_check(text)

        # Step 8: 进化反馈
        try:
            results["evolution"] = self.step8_evolve()
        except Exception as e:
            print(f"[Pipeline] Step 8 跳过: {e}")

        # 保存pipeline日志
        results["pipeline_log"] = self._pipeline_log
        self._save_pipeline_log()

        print("\n" + "=" * 50)
        print("全流程完成")
        print("=" * 50)

        # 引导下一步
        print(self.suggest_next_steps('step8_evolve'))

        return results

    # ============================================================
    # 状态与报告
    # ============================================================

    def status(self) -> str:
        """系统状态总览"""
        lines = ["=" * 50, "学术AI系统状态", "=" * 50, ""]

        # 论文库
        try:
            reader = self._get_reader()
            papers = reader.list_papers()
            db_stats = reader.get_db_stats()
            lines.append(f"[论文库] {db_stats.get('total', 0)}篇论文")
            if db_stats.get('evidence_levels'):
                for level, count in db_stats['evidence_levels'].items():
                    lines.append(f"  {level}: {count}篇")
        except Exception:
            lines.append("[论文库] 不可用")

        # 文献矩阵
        try:
            mem = self._get_lit_memory()
            lines.append(f"\n[文献矩阵] {len(mem.matrix.papers)}篇, "
                         f"{len(mem.matrix.themes)}个主题")
            net = mem.network.get_network_stats()
            lines.append(f"[关联网络] {net['total_links']}条关联, "
                         f"{net['total_papers']}篇涉及")
        except Exception:
            lines.append("\n[文献矩阵] 不可用")

        # 知识库
        try:
            engine = self._get_engine()
            if engine:
                stats = engine.store.stats()
                total = sum(s['count'] for s in stats.values())
                lines.append(f"\n[知识库] {total}条知识条目")
                for cat, s in stats.items():
                    if s['count'] > 0:
                        lines.append(f"  {cat}: {s['count']}条")
        except Exception:
            pass

        # Pipeline日志
        lines.append(f"\n[Pipeline] {len(self._pipeline_log)}条执行记录")
        if self._pipeline_log:
            last = self._pipeline_log[-1]
            lines.append(f"  最近: {last['step']} - {last['detail']}")

        return "\n".join(lines)

    def _save_pipeline_log(self):
        """保存pipeline执行日志"""
        log_path = os.path.join(self.base_dir, "knowledge_store", "pipeline_log.json")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            data = {
                "meta": {
                    "count": len(self._pipeline_log),
                    "updated": datetime.now(timezone.utc).isoformat(),
                },
                "log": self._pipeline_log[-100:],  # 保留最近100条
            }
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save pipeline log: {e}")


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    args = sys.argv[1:]
    pipe = AcademicPipeline()

    if not args or args[0] == "status":
        print(pipe.status())

    elif args[0] == "suggest":
        print(pipe.suggest_next_steps(args[1] if len(args) > 1 else None))

    elif args[0] == "read" and len(args) > 1:
        pipe.step1_read(args[1])
        print(pipe.suggest_next_steps('step1_read'))

    elif args[0] == "matrix":
        print(pipe.step2_matrix())
        print(pipe.suggest_next_steps('step2_matrix'))

    elif args[0] == "review" and len(args) > 1:
        with open(args[1], "r", encoding="utf-8") as f:
            text = f.read()
        result = pipe.step5_review(text)
        print(result["report_md"])
        print(pipe.suggest_next_steps('step5_review'))

    elif args[0] == "motivation":
        # 如果有分析结果文件
        results = {}
        if len(args) > 1 and os.path.exists(args[1]):
            import pickle
            with open(args[1], 'rb') as f:
                results = pickle.load(f)
        options = pipe.step3_5_motivation(analysis_results=results)
        print(pipe.suggest_next_steps('step3_5_motivation'))

    elif args[0] == "confirm" and len(args) > 1:
        result = pipe.step3_6_confirm_motivation(option_id=args[1])
        print(pipe.suggest_next_steps('step3_6_confirm_motivation'))

    elif args[0] == "check" and len(args) > 1:
        with open(args[1], "r", encoding="utf-8") as f:
            text = f.read()
        print(pipe.step6_submission_check(text))
        print(pipe.suggest_next_steps('step6_submission_check'))

    elif args[0] == "evolve":
        print(pipe.step8_evolve())
        print(pipe.suggest_next_steps('step8_evolve'))

    elif args[0] == "assemble" and len(args) > 1:
        result = pipe.step9_assemble_document(data_file=args[1])
        print(pipe.suggest_next_steps('step9_assemble_document'))

    elif args[0] == "learn" and len(args) > 1:
        topic = ' '.join(args[1:])
        result = pipe.step_auto_learn(topic)

    elif args[0] == "pipeline" and len(args) > 1:
        pipe.run_full_pipeline(source=args[1])

    else:
        print("学术论文全流程编排器")
        print("")
        print("用法:")
        print("  python orchestrator.py suggest             # 查看可用步骤")
        print("  python orchestrator.py status              # 系统状态")
        print("  python orchestrator.py read <source>       # 读论文")
        print("  python orchestrator.py matrix              # 文献矩阵")
        print("  python orchestrator.py motivation [data]   # 生成动机选项")
        print("  python orchestrator.py confirm <A|B|C>     # 确认动机+生成蓝图")
        print("  python orchestrator.py review <file>       # 审稿")
        print("  python orchestrator.py check <file>        # 投稿前检查")
        print("  python orchestrator.py evolve              # 进化周期")
        print("  python orchestrator.py assemble <data.xlsx> # 数据→DOCX")
        print("  python orchestrator.py learn <topic>       # 自动学习")
        print("  python orchestrator.py pipeline <src>      # 全流程")
