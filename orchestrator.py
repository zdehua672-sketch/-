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
    # Step 4: 写论文（委托 paper_writing_agent）
    # ============================================================

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
                'next': ['step1_read', 'step4_write', 'step9_assemble_document'],
            },
            'step1_read': {
                'label': '读取论文',
                'next': ['step2_matrix', 'step3_verify_citations', 'step5_review'],
                'done_msg': '论文已读取并存入数据库',
            },
            'step2_matrix': {
                'label': '文献矩阵',
                'next': ['step3_verify_citations', 'step4_write'],
                'done_msg': '文献矩阵已构建',
            },
            'step3_verify_citations': {
                'label': '引用验证',
                'next': ['step4_write', 'step5_review'],
                'done_msg': '引用验证完成',
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
            'step4_write': '论文写作 (数据分析 → 图表 → 正文自动生成)',
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
        print("  python orchestrator.py review <file>       # 审稿")
        print("  python orchestrator.py check <file>        # 投稿前检查")
        print("  python orchestrator.py evolve              # 进化周期")
        print("  python orchestrator.py assemble <data.xlsx> # 数据→DOCX")
        print("  python orchestrator.py learn <topic>       # 自动学习")
        print("  python orchestrator.py pipeline <src>      # 全流程")
