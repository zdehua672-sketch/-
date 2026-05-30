"""academic_review_agent.py 单元测试"""
import pytest
from academic_review_agent import (
    AcademicReviewAgent, SectionParser, ReviewKB, Scorer,
    SCIChecker, ChineseChecker, TypoChecker, GrammarChecker,
    CitationChecker, FigureChecker, DataLogicChecker, DiscussionChecker,
    AIDetector, RepetitionChecker, review_paper,
    Issue, Severity,
)


SAMPLE_ZH_PAPER = """校园污水管网碳污染物赋存特征

摘 要：本研究分析了校园污水管网碳污染物赋存特征。DO与CH4呈显著负相关。

关键词：碳污染物；污水管网

1 引言

校园污水管网是城市水循环的重要组成部分。然而，目前缺乏对三相碳污染物的系统研究。本研究旨在分析碳污染物赋存特征。

2 材料与方法

本研究选取某校园污水管网作为研究对象。采用气相色谱法测定CH4浓度。

3 结果与分析

DO浓度范围为0.5-8.2 mg/L。CH4浓度范围为1.2-15.8 mg/m³。
DO与CH4呈显著负相关(r=-0.72, p<0.001)。TOC与CH4呈显著正相关(r=0.68, p<0.01)。

4 讨论

DO浓度降低时CH4浓度升高，这一现象可归因于厌氧条件下产甲烷菌活性增强。
与Guisasola等[1]的研究一致，本研究发现厌氧环境促进甲烷产生。
本研究存在以下局限：采样时间有限。

5 结论

溶解氧和有机负荷是控制碳相态转化的关键因素。

参考文献

[1] Guisasola A, et al. Methane production in sewer systems. Water Research, 2008, 42(6-7): 1421-1430.
[2] Jiang G, et al. Greenhouse gas emissions. Environ. Sci. Technol., 2011, 45(19): 8154-8162.
[3] 张三, 李四. 城市污水碳排放研究[J]. 环境科学, 2020, 41(3): 123-130.
[4] Wang Y. Dissolved oxygen control. Nature Water, 2023, 1(2): 156-165.
[5] Li M. Multi-phase carbon. Environ. Pollut., 2024, 345: 123456.
"""


class TestSectionParser:
    def test_detect_language_zh(self):
        assert SectionParser.detect_language("中文测试文本") == "zh"

    def test_detect_language_en(self):
        assert SectionParser.detect_language("This is English text") == "en"

    def test_parse_sections(self):
        sections = SectionParser.parse(SAMPLE_ZH_PAPER, "zh")
        assert "abstract" in sections
        assert "introduction" in sections
        assert "methods" in sections
        assert "results" in sections
        assert "discussion" in sections
        assert "conclusion" in sections

    def test_section_body_not_empty(self):
        sections = SectionParser.parse(SAMPLE_ZH_PAPER, "zh")
        # 引言应该有正文内容
        assert len(sections["introduction"].body) > 0
        # 结果应该有正文内容
        assert len(sections["results"].body) > 0


class TestAcademicReviewAgent:
    def test_review_returns_report(self):
        agent = AcademicReviewAgent(paper_type="chinese_journal", language="zh")
        report = agent.review(SAMPLE_ZH_PAPER)
        assert hasattr(report, "issues")
        assert hasattr(report, "scores")
        assert len(report.issues) > 0

    def test_review_scores_range(self):
        agent = AcademicReviewAgent(paper_type="chinese_journal", language="zh")
        report = agent.review(SAMPLE_ZH_PAPER)
        for dim, score in report.scores.items():
            if dim == "总分":
                assert 0 <= score <= 10, f"总分 {score} 超出范围"
            else:
                assert 1.0 <= score <= 10.0, f"{dim} {score} 超出范围"

    def test_review_severity_levels(self):
        agent = AcademicReviewAgent(paper_type="chinese_journal", language="zh")
        report = agent.review(SAMPLE_ZH_PAPER)
        severities = {i.severity.value for i in report.issues}
        assert severities.issubset({"CRITICAL", "MAJOR", "MINOR", "INFO"})

    def test_review_summary(self):
        agent = AcademicReviewAgent(paper_type="chinese_journal", language="zh")
        report = agent.review(SAMPLE_ZH_PAPER)
        summary = report.summary()
        assert "total" in summary
        assert "by_severity" in summary
        assert summary["total"] == len(report.issues)

    def test_generate_report(self):
        agent = AcademicReviewAgent(paper_type="chinese_journal", language="zh")
        report = agent.review(SAMPLE_ZH_PAPER)
        text = agent.generate_report(report)
        assert len(text) > 0
        assert "评分" in text or "Score" in text


class TestReviewPaper:
    def test_basic(self):
        report, text = review_paper(SAMPLE_ZH_PAPER, language="zh")
        assert len(report.issues) >= 0
        assert len(text) > 0


class TestScorer:
    def test_no_issues_perfect_score(self):
        scores = Scorer.score([])
        assert scores["总分"] == 10.0

    def test_weights_sum_to_one(self):
        total = sum(c['weight'] for c in Scorer.DIMENSIONS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_critical_penalty(self):
        issue = Issue(
            category="数据逻辑", severity=Severity.CRITICAL,
            section="Results", location="test",
            problem="test", original="", suggestion="",
        )
        scores = Scorer.score([issue])
        assert scores["数据逻辑"] < 10.0

    def test_score_decreases_with_issues(self):
        no_issue = Scorer.score([])
        one_issue = Scorer.score([
            Issue(category="SCI格式", severity=Severity.MAJOR,
                  section="test", location="test",
                  problem="test", original="", suggestion="")
        ])
        assert one_issue["总分"] < no_issue["总分"]


class TestTypoChecker:
    def test_detects_typo_in_text(self):
        # 将含错别字的文本放入一个章节的body中
        from academic_review_agent import SectionContent
        sections = {"test": SectionContent(
            title="test",
            body="我们分折了碳污染物的赋存特征",
            paragraphs=["我们分折了碳污染物的赋存特征"],
            sentences=["我们分折了碳污染物的赋存特征"],
        )}
        issues = TypoChecker.check(sections, "zh")
        assert any("分折" in i.problem for i in issues)

    def test_no_false_positives(self):
        from academic_review_agent import SectionContent
        sections = {"test": SectionContent(
            title="test",
            body="我们分析了碳污染物的赋存特征",
            paragraphs=["我们分析了碳污染物的赋存特征"],
            sentences=["我们分析了碳污染物的赋存特征"],
        )}
        issues = TypoChecker.check(sections, "zh")
        assert len(issues) == 0
