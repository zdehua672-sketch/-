"""revision_audit.py 单元测试"""
import pytest
from revision_audit import audit_revision


class TestAuditRevision:
    def test_identical(self):
        text = "This is a test paragraph."
        result = audit_revision(text, text)
        assert result.unchanged_ratio == 1.0
        assert result.new_ratio == 0.0

    def test_completely_new(self):
        original = "Old text here."
        revised = "Brand new completely different content."
        result = audit_revision(original, revised)
        assert result.new_ratio > 0.5

    def test_minor_edit(self):
        original = "The concentration was 50 mg/L in winter."
        revised = "The concentration was 52 mg/L in winter."
        result = audit_revision(original, revised)
        # 应该识别为大部分未变
        assert result.unchanged_ratio > 0.5

    def test_empty_original(self):
        result = audit_revision("", "New text")
        assert result.new_ratio == 1.0

    def test_empty_revised(self):
        result = audit_revision("Old text", "")
        assert result.unchanged_ratio == 1.0

    def test_shallow_warning(self):
        original = "Word " * 100
        revised = "Word " * 100 + "extra"
        result = audit_revision(original, revised)
        # 高未变率应该触发浅改警告
        assert result.unchanged_ratio > 0.9

    def test_multi_paragraph(self):
        original = "Para 1 content.\n\nPara 2 content.\n\nPara 3 content."
        revised = "Para 1 revised.\n\nPara 2 content.\n\nPara 3 new content here."
        result = audit_revision(original, revised)
        assert 0 < result.unchanged_ratio < 1.0
