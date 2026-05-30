"""text_utils.py 单元测试"""
import pytest
from text_utils import split_sentences, split_paragraphs, canonical, extract_tokens, text_similarity


class TestSplitSentences:
    def test_english_sentences(self):
        text = "Hello world. This is a test. Third sentence."
        result = split_sentences(text)
        assert len(result) == 3
        assert "Hello world" in result[0]

    def test_chinese_sentences(self):
        text = "第一句。第二句！第三句？"
        result = split_sentences(text)
        assert len(result) == 3

    def test_empty_string(self):
        assert split_sentences("") == []

    def test_single_sentence(self):
        assert len(split_sentences("Just one sentence")) == 1


class TestSplitParagraphs:
    def test_double_newline(self):
        text = "Para 1\n\nPara 2\n\nPara 3"
        result = split_paragraphs(text)
        assert len(result) == 3

    def test_single_block(self):
        assert len(split_paragraphs("Just one paragraph")) == 1


class TestCanonical:
    def test_lowercase(self):
        assert canonical("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert canonical("  test  ") == "test"

    def test_removes_punctuation(self):
        result = canonical("hello, world!")
        assert "," not in result


class TestExtractTokens:
    def test_english_tokens(self):
        tokens = extract_tokens("Hello world test")
        assert "hello" in tokens
        assert "world" in tokens

    def test_chinese_tokens(self):
        tokens = extract_tokens("碳污染物 分析")
        assert "碳污染物" in tokens

    def test_min_length(self):
        tokens = extract_tokens("a bb ccc", min_length=3)
        assert "a" not in tokens
        assert "bb" not in tokens
        assert "ccc" in tokens


class TestSimilarity:
    def test_identical(self):
        assert text_similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        assert text_similarity("abc def", "xyz uvw") == 0.0

    def test_partial_overlap(self):
        s = text_similarity("hello world test", "hello there test")
        assert 0.3 < s < 0.8

    def test_empty(self):
        assert text_similarity("", "hello") == 0.0
        assert text_similarity("hello", "") == 0.0
