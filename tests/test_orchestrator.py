"""orchestrator.py 集成测试"""
import pytest
from orchestrator import AcademicPipeline


SAMPLE_TEXT = """校园污水管网碳污染物赋存特征

摘 要：本研究分析了校园污水管网碳污染物赋存特征。

关键词：碳污染物

1 引言
校园污水管网是重要基础设施。然而缺乏系统研究。本研究分析碳污染物赋存特征。

2 材料与方法
本研究选取校园污水管网。采用气相色谱法测定。

3 结果与分析
DO与CH4呈显著负相关(r=-0.72, p<0.001)。

4 讨论
厌氧条件促进甲烷产生。

5 结论
溶解氧是关键因素。

参考文献
[1] Guisasola A, et al. Water Research, 2008, 42(6-7): 1421-1430.
"""


class TestAcademicPipeline:
    def test_init(self):
        pipe = AcademicPipeline()
        assert pipe.base_dir is not None
        assert pipe._pipeline_log == []

    def test_step5_review(self):
        pipe = AcademicPipeline()
        result = pipe.step5_review(SAMPLE_TEXT, language="zh")
        assert "issues" in result
        assert "scores" in result
        assert "report_md" in result
        assert len(result["issues"]) > 0

    def test_step6_submission_check(self):
        pipe = AcademicPipeline()
        report = pipe.step6_submission_check(SAMPLE_TEXT)
        assert len(report) > 0
        assert "检查" in report or "pass" in report.lower() or "fail" in report.lower()

    def test_step7_revision_audit(self):
        pipe = AcademicPipeline()
        result = pipe.step7_revision_audit(SAMPLE_TEXT, SAMPLE_TEXT)
        assert "unchanged_ratio" in result
        assert result["unchanged_ratio"] == 1.0

    def test_step7_different_versions(self):
        pipe = AcademicPipeline()
        revised = SAMPLE_TEXT.replace("0.72", "0.75")
        result = pipe.step7_revision_audit(SAMPLE_TEXT, revised)
        assert result["unchanged_ratio"] < 1.0

    def test_step8_evolve(self):
        pipe = AcademicPipeline()
        result = pipe.step8_evolve()
        assert isinstance(result, str)

    def test_pipeline_log(self):
        pipe = AcademicPipeline()
        pipe.step5_review(SAMPLE_TEXT, language="zh")
        assert len(pipe._pipeline_log) > 0
        assert pipe._pipeline_log[-1]["step"] == "step5_review"

    def test_status(self):
        pipe = AcademicPipeline()
        status = pipe.status()
        assert "学术AI系统状态" in status
        assert "Pipeline" in status
