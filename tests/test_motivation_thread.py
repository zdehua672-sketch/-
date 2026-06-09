"""motivation_thread.py 单元测试"""
import pytest
from motivation_thread import (
    MotivationThread, SevenSentenceTest,
    IntroductionDiscussionMapper, _split_sentences, _text_similarity,
)


class TestMotivationThread:
    def test_completeness_full(self):
        t = MotivationThread(
            field_problem="problem statement here",
            specific_gap="identified gap here",
            design_response="our design here",
            evidence="evidence found here",
            interpretation="interpretation here",
        )
        c = t.completeness()
        assert c["ratio"] == 1.0
        assert c["filled"] == 5
        assert len(c["missing"]) == 0

    def test_completeness_partial(self):
        t = MotivationThread(field_problem="problem")
        c = t.completeness()
        assert c["ratio"] < 0.5
        assert "specific_gap" in c["missing"]

    def test_completeness_empty(self):
        t = MotivationThread()
        c = t.completeness()
        assert c["ratio"] == 0.0


class TestSevenSentenceTest:
    def test_validate_with_coherent_text(self):
        """使用高度一致的句子测试验证"""
        s = SevenSentenceTest(
            abstract_final="碳污染物赋存特征研究表明DO是关键因素",
            intro_opening="校园污水管网碳污染物赋存特征研究",
            intro_gap="然而目前缺乏碳污染物赋存特征系统分析",
            intro_contribution="本研究分析碳污染物赋存特征并揭示DO是关键因素",
            methods_opening="本研究选取校园污水管网采集碳污染物样品",
            results_headline="碳污染物赋存特征分析表明DO是关键因素",
            discussion_closing="碳污染物赋存特征分析表明DO是控制碳转化的关键因素",
        )
        result = s.validate()
        assert "passed" in result
        assert "checks" in result
        assert len(result["checks"]) == 4
        # 至少7句提取应该完整
        assert result["checks"][0][1] is True

    def test_validate_missing(self):
        s = SevenSentenceTest()
        result = s.validate()
        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_to_markdown(self):
        s = SevenSentenceTest(abstract_final="结论句")
        md = s.to_markdown()
        assert "七句话" in md
        assert "结论句" in md

    def test_extract_from_paper(self):
        s = SevenSentenceTest()
        sections = {
            "abstract": "背景。方法。结果发现碳排放显著。",
            "introduction": "污水管网是重要基础设施。然而目前研究不足。本研究分析了碳污染物。",
            "methods": "采集固液气三相样品。",
            "results": "DO与CH4呈显著负相关(p<0.001)。",
            "discussion": "这一发现表明溶解氧是关键因素。",
        }
        s.extract_from_paper(sections)
        assert s.abstract_final != ""
        assert s.intro_opening != ""
        assert s.intro_gap != ""
        assert s.intro_contribution != ""


class TestSplitSentences:
    def test_chinese(self):
        result = _split_sentences("这是第一句测试。这是第二句测试！这是第三句测试？")
        assert len(result) == 3

    def test_english(self):
        result = _split_sentences("First. Second. Third.")
        assert len(result) == 3

    def test_filter_short(self):
        result = _split_sentences("好。This is a longer sentence.")
        # "好" 太短被过滤
        assert all(len(s) > 5 for s in result)


class TestTextSimilarity:
    def test_identical(self):
        assert _text_similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert _text_similarity("abc", "xyz") == 0.0

    def test_partial(self):
        s = _text_similarity("碳污染物 分析 特征", "碳污染物 赋存 规律")
        assert 0 < s < 1


class TestIntroductionDiscussionMapper:
    def test_map_closure(self):
        intro = "本研究旨在分析碳污染物赋存特征。采用了多元统计方法。"
        discussion = "碳污染物赋存特征与DO密切相关。多元统计方法有效识别了关键因素。"
        results = IntroductionDiscussionMapper.map_closure(intro, discussion)
        assert len(results) >= 1
        for r in results:
            assert "score" in r
            assert "closed" in r
