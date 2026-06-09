"""citation_audit.py 单元测试"""
import pytest
from citation_audit import (
    CitationEntry, extract_doi, extract_year, classify_citation,
    compute_recency_score, audit_citation, audit_citations_batch,
    gap_analysis, title_similarity,
)


class TestExtractDoi:
    def test_standard_doi(self):
        text = "DOI: 10.1016/j.watres.2007.10.010"
        assert extract_doi(text) == "10.1016/j.watres.2007.10.010"

    def test_url_doi(self):
        text = "https://doi.org/10.1038/s41586-021-03582"
        doi = extract_doi(text)
        assert doi.startswith("10.1038/")

    def test_no_doi(self):
        assert extract_doi("No DOI here") == ""


class TestExtractYear:
    def test_parenthesized(self):
        assert extract_year("Author (2020)") == 2020

    def test_comma_separated(self):
        assert extract_year("Author, 2021, Journal") == 2021

    def test_standalone(self):
        assert extract_year("Published in 2022 by Elsevier") == 2022

    def test_no_year(self):
        assert extract_year("No year here") == 0

    def test_year_2030(self):
        """验证年份正则支持2030+"""
        assert extract_year("Published 2030") == 2030

    def test_year_2050(self):
        assert extract_year("Published 2050") == 2050

    def test_prefers_recent(self):
        assert extract_year("Ref 2001, published 2020") == 2020


class TestClassifyCitation:
    def test_survey(self):
        assert classify_citation("A review of carbon emissions") == "survey"

    def test_foundational(self):
        assert classify_citation("Pioneer study by Smith") == "foundational"

    def test_benchmark(self):
        assert classify_citation("Standard method protocol") == "benchmark"

    def test_sota_default(self):
        assert classify_citation("Random paper about stuff") == "sota"


class TestComputeRecencyScore:
    def test_current_year(self):
        assert compute_recency_score(2026, current_year=2026) == 100

    def test_two_years_ago(self):
        assert compute_recency_score(2024, current_year=2026) == 90

    def test_seven_years_ago(self):
        assert compute_recency_score(2019, current_year=2026) == 50

    def test_very_old(self):
        assert compute_recency_score(2000, current_year=2026) == 20

    def test_no_year(self):
        assert compute_recency_score(0) == 30


class TestAuditCitation:
    def test_basic(self):
        entry = audit_citation("Smith, 2020. Carbon study.", verify=False)
        assert entry.year == 2020
        assert entry.status == "unverified"

    def test_with_doi(self):
        entry = audit_citation(
            "Test paper. DOI: 10.1000/test. 2021.",
            verify=False
        )
        assert entry.doi.startswith("10.1000/test")
        assert entry.resolvability_score == 50  # 未验证但有DOI

    def test_no_doi(self):
        entry = audit_citation("Old reference from 2005", verify=False)
        assert entry.doi == ""
        assert "未找到DOI" in entry.issues


class TestAuditCitationsBatch:
    def test_basic(self):
        refs = ["Ref 1. 2020.", "Ref 2. 2021.", "Ref 3. 2022."]
        result = audit_citations_batch(refs, verify=False)
        assert result['overall_score'] > 0
        assert len(result['entries']) == 3

    def test_empty(self):
        result = audit_citations_batch([], verify=False)
        assert result['overall_score'] == 0

    def test_gap_analysis(self):
        refs = [
            "Review of carbon. 2020.",
            "Standard method. 2021.",
            "Case study application. 2022.",
        ]
        result = audit_citations_batch(refs, verify=False)
        assert 'gap_analysis' in result


class TestTitleSimilarity:
    def test_identical(self):
        assert title_similarity("Same Title", "Same Title") > 0.9

    def test_different(self):
        assert title_similarity("Carbon Emissions", "Quantum Physics") < 0.3

    def test_empty(self):
        assert title_similarity("", "Something") == 0.0
