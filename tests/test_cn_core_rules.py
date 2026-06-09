"""cn_core_rules.py 单元测试"""
import pytest
from cn_core_rules import CNCoreTemplate, SubmissionChecklist, ChecklistItem


class TestSubmissionChecklist:
    def test_run_check_returns_items(self):
        items = SubmissionChecklist.run_check("测试文本内容")
        assert len(items) > 0
        assert all(hasattr(i, "item") for i in items)
        assert all(hasattr(i, "status") for i in items)

    def test_statuses_valid(self):
        items = SubmissionChecklist.run_check("测试")
        valid = {"pass", "fail", "warn", "skip"}
        for item in items:
            assert item.status in valid

    def test_generate_report(self):
        items = SubmissionChecklist.run_check("测试文本")
        report = SubmissionChecklist.generate_report(items)
        assert len(report) > 0

    def test_empty_text(self):
        items = SubmissionChecklist.run_check("")
        assert len(items) > 0  # 即使空文本也应该返回检查项
