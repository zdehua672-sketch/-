"""writing_rationale.py 单元测试"""
import pytest
from writing_rationale import RationaleMatrix, RationaleRow


class TestRationaleRow:
    def test_create(self):
        row = RationaleRow(
            finding="DO与CH4负相关",
            mechanism="厌氧产甲烷",
            evidence="r=-0.72, p<0.001",
            citation="Guisasola 2008",
            confidence=0.9,
        )
        assert row.finding == "DO与CH4负相关"
        assert row.confidence == 0.9

    def test_completeness_score(self):
        row = RationaleRow(
            finding="finding",
            mechanism="mechanism",
            evidence="evidence",
            citation="citation",
        )
        score = row.completeness_score()
        assert score == 1.0  # 全部填充

    def test_partial_completeness(self):
        row = RationaleRow(finding="only finding")
        score = row.completeness_score()
        assert score < 0.5


class TestRationaleMatrix:
    def test_add_row(self):
        m = RationaleMatrix()
        m.add("f", "m", "e", "c", confidence=0.8)
        assert len(m.rows) == 1

    def test_add_multiple(self):
        m = RationaleMatrix()
        m.add("f1", "m1", "e1", "c1")
        m.add("f2", "m2", "e2", "c2")
        m.add("f3", "m3", "e3", "c3")
        assert len(m.rows) == 3

    def test_completeness_score(self):
        m = RationaleMatrix()
        m.add("f", "m", "e", "c")
        score = m.completeness_score()
        assert score == 1.0

    def test_empty_matrix(self):
        m = RationaleMatrix()
        assert m.completeness_score() == 0.0

    def test_query(self):
        m = RationaleMatrix()
        m.add("DO与CH4负相关", "厌氧产甲烷", "r=-0.72", "Guisasola 2008")
        results = m.query("CH4")
        assert len(results) >= 1

    def test_export(self):
        m = RationaleMatrix()
        m.add("f", "m", "e", "c")
        data = m.export()
        assert len(data) == 1
        assert data[0]["finding"] == "f"

    def test_validate(self):
        m = RationaleMatrix()
        m.add("f", "m", "e", "c")
        report = m.validate()
        assert report["total_rows"] == 1
        assert report["complete_rows"] == 1
