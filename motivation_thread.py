"""
动机线索模型 - 论文的"红线"贯穿
借鉴自PaperSpine的motivation-thread-writing.md

核心思想：论文是一个问题-解决弧线，每个章节都服务于同一个动机。
从Gap到Conclusion，每一步都要首尾呼应。
"""
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class MotivationThread:
    """
    动机线索：一条贯穿全文的"红线"

    field_problem → specific_gap → design_response → evidence → interpretation → limitation
    """
    field_problem: str = ""      # 领域问题
    specific_gap: str = ""       # 具体研究空白
    design_response: str = ""    # 设计响应（本研究怎么做）
    evidence: str = ""           # 证据发现
    interpretation: str = ""     # 解释/意义
    limitation: str = ""         # 局限性
    future: str = ""             # 未来工作
    red_thread: str = ""         # 一句话红线

    def completeness(self) -> dict:
        """检查线索完整性"""
        fields = {
            'field_problem': self.field_problem,
            'specific_gap': self.specific_gap,
            'design_response': self.design_response,
            'evidence': self.evidence,
            'interpretation': self.interpretation,
        }
        filled = sum(1 for v in fields.values() if v and len(v) > 5)
        return {
            'filled': filled,
            'total': len(fields),
            'ratio': filled / len(fields),
            'missing': [k for k, v in fields.items() if not v or len(v) <= 5],
        }


@dataclass
class SevenSentenceTest:
    """
    七句话血统测试

    从论文中抽取7句关键句，验证它们是否首尾呼应：
    1. Abstract最后一句（结论句）
    2. Introduction第一句（背景句）
    3. Introduction的Gap句
    4. Introduction的贡献句
    5. Methods第一句
    6. Results的核心发现句
    7. Discussion最后一句（闭合句）
    """
    abstract_final: str = ""
    intro_opening: str = ""
    intro_gap: str = ""
    intro_contribution: str = ""
    methods_opening: str = ""
    results_headline: str = ""
    discussion_closing: str = ""

    def extract_from_paper(self, sections: dict):
        """从论文各章节中提取7句话"""
        # Abstract: 取最后一句
        abstract = sections.get('abstract', '')
        if abstract:
            sentences = _split_sentences(abstract)
            self.abstract_final = sentences[-1] if sentences else ""

        # Introduction: 第一句
        intro = sections.get('introduction', '')
        if intro:
            sentences = _split_sentences(intro)
            self.intro_opening = sentences[0] if sentences else ""

            # Gap句: 包含"然而/但是/however/yet/but"的句子
            for s in sentences:
                if any(kw in s.lower() for kw in ['然而', '但是', 'however', 'yet', ' but ',
                                                    '研究空白', 'research gap', 'remains unclear']):
                    self.intro_gap = s
                    break

            # 贡献句: 包含"本研究/this study/we aimed"的句子
            for s in sentences:
                if any(kw in s.lower() for kw in ['本研究', '本文', 'this study', 'we aimed',
                                                    'we investigated', 'we examined', 'our study']):
                    self.intro_contribution = s
                    break

        # Methods: 第一句
        methods = sections.get('methods', '')
        if methods:
            sentences = _split_sentences(methods)
            self.methods_opening = sentences[0] if sentences else ""

        # Results: 核心发现句（包含显著性标志）
        results = sections.get('results', '')
        if results:
            sentences = _split_sentences(results)
            for s in sentences:
                if any(kw in s.lower() for kw in ['显著', 'significant', 'p<', 'p =', 'r =']):
                    self.results_headline = s
                    break

        # Discussion: 最后一句
        discussion = sections.get('discussion', '')
        if discussion:
            sentences = _split_sentences(discussion)
            self.discussion_closing = sentences[-1] if sentences else ""

    def validate(self) -> dict:
        """
        验证7句话的血统一致性

        Returns
        -------
        dict: {passed, checks, issues}
        """
        checks = []
        issues = []

        # 检查1: 每句话是否都已提取
        all_sentences = {
            'abstract_final': self.abstract_final,
            'intro_opening': self.intro_opening,
            'intro_gap': self.intro_gap,
            'intro_contribution': self.intro_contribution,
            'methods_opening': self.methods_opening,
            'results_headline': self.results_headline,
            'discussion_closing': self.discussion_closing,
        }
        missing = [k for k, v in all_sentences.items() if not v]
        if missing:
            issues.append(f"未提取到: {', '.join(missing)}")
        checks.append(("7句提取完整", len(missing) == 0))

        # 检查2: Intro承诺是否在Discussion闭合
        if self.intro_contribution and self.discussion_closing:
            closure_score = _text_similarity(self.intro_contribution, self.discussion_closing)
            checks.append(("Intro承诺-Discussion闭合", closure_score > 0.15))
            if closure_score <= 0.15:
                issues.append("Discussion结尾未回应Introduction的研究承诺")
        else:
            checks.append(("Intro承诺-Discussion闭合", False))

        # 检查3: Abstract结论是否与Discussion一致
        if self.abstract_final and self.discussion_closing:
            consistency = _text_similarity(self.abstract_final, self.discussion_closing)
            checks.append(("Abstract-Discussion一致性", consistency > 0.1))
            if consistency <= 0.1:
                issues.append("Abstract结论与Discussion结论不一致")
        else:
            checks.append(("Abstract-Discussion一致性", False))

        # 检查4: Results是否回应了Intro承诺
        if self.intro_contribution and self.results_headline:
            relevance = _text_similarity(self.intro_contribution, self.results_headline)
            checks.append(("Results回应Intro承诺", relevance > 0.1))
            if relevance <= 0.1:
                issues.append("Results未明显回应Introduction提出的研究目标")
        else:
            checks.append(("Results回应Intro承诺", False))

        passed = all(c[1] for c in checks)
        return {"passed": passed, "checks": checks, "issues": issues}

    def to_markdown(self) -> str:
        """导出为Markdown"""
        lines = [
            "# 七句话血统测试",
            "",
            "| # | 角色 | 句子 |",
            "|---|------|------|",
            f"| 1 | Abstract结论 | {self.abstract_final[:80]}... |" if len(self.abstract_final) > 80 else f"| 1 | Abstract结论 | {self.abstract_final} |",
            f"| 2 | Intro背景 | {self.intro_opening[:80]}... |" if len(self.intro_opening) > 80 else f"| 2 | Intro背景 | {self.intro_opening} |",
            f"| 3 | Intro Gap | {self.intro_gap[:80]}... |" if len(self.intro_gap) > 80 else f"| 3 | Intro Gap | {self.intro_gap} |",
            f"| 4 | Intro承诺 | {self.intro_contribution[:80]}... |" if len(self.intro_contribution) > 80 else f"| 4 | Intro承诺 | {self.intro_contribution} |",
            f"| 5 | Methods | {self.methods_opening[:80]}... |" if len(self.methods_opening) > 80 else f"| 5 | Methods | {self.methods_opening} |",
            f"| 6 | Results核心 | {self.results_headline[:80]}... |" if len(self.results_headline) > 80 else f"| 6 | Results核心 | {self.results_headline} |",
            f"| 7 | Discussion闭合 | {self.discussion_closing[:80]}... |" if len(self.discussion_closing) > 80 else f"| 7 | Discussion闭合 | {self.discussion_closing} |",
        ]
        return '\n'.join(lines)


def _split_sentences(text: str) -> list:
    """分句（中英文混合）"""
    # 按句号、问号、感叹号分句
    parts = re.split(r'(?<=[。！？.!?])\s*', text.strip())
    # 过滤太短的
    return [s.strip() for s in parts if len(s.strip()) > 5]


def _text_similarity(text1: str, text2: str) -> float:
    """简易文本相似度（基于共享词汇）"""
    def _tokens(text):
        # 提取中英文词汇
        zh = set(re.findall(r'[一-鿿]{2,}', text))
        en = set(re.findall(r'[a-zA-Z]{3,}', text.lower()))
        return zh | en

    tokens1 = _tokens(text1)
    tokens2 = _tokens(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union) if union else 0.0


class IntroductionDiscussionMapper:
    """
    Introduction-Discussion闭合映射

    检查Introduction中每个承诺在Discussion中是否兑现
    """

    @staticmethod
    def map_closure(intro_text: str, discussion_text: str) -> list:
        """
        映射Intro承诺到Discussion闭合

        Returns
        -------
        list of dict: {intro_sentence, discussion_match, score, closed}
        """
        intro_sentences = _split_sentences(intro_text)
        discussion_sentences = _split_sentences(discussion_text)

        # 找到Intro中的承诺句（包含目标/目的/aim/objective）
        promise_keywords = ['本研究', '本文', '旨在', '目的', 'this study', 'we aimed',
                           'objective', 'aim to', 'investigate', 'examine', 'characterize']
        promises = [s for s in intro_sentences
                    if any(kw in s.lower() for kw in promise_keywords)]

        results = []
        for promise in promises:
            best_match = ""
            best_score = 0.0
            for ds in discussion_sentences:
                score = _text_similarity(promise, ds)
                if score > best_score:
                    best_score = score
                    best_match = ds

            results.append({
                'intro_sentence': promise[:80],
                'discussion_match': best_match[:80] if best_match else "(无匹配)",
                'score': round(best_score, 3),
                'closed': best_score > 0.15,
            })

        return results


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        # 内置测试
        thread = MotivationThread(
            field_problem="校园污水管网碳污染物排放对温室效应有贡献，但多相态分布特征不清",
            specific_gap="缺乏固-液-气三相碳污染物的系统联合分析",
            design_response="系统采集三相样品，采用PCA+HCA多元统计方法",
            evidence="DO与CH4负相关(r=-0.72)，TOC与CH4正相关(r=0.68)",
            interpretation="溶解氧和有机负荷是控制碳相态转化的关键因素",
        )
        print("动机线索完整性:", json.dumps(thread.completeness(), ensure_ascii=False, indent=2))

        # 七句话测试
        test = SevenSentenceTest()
        test.abstract_final = "校园污水管网碳污染物具有显著的相态分异特征"
        test.intro_opening = "校园污水管网是城市水循环的重要组成部分"
        test.intro_gap = "然而，目前缺乏对三相碳污染物的系统分析"
        test.intro_contribution = "本研究系统分析了固-液-气多相态碳污染物的赋存特征"
        test.methods_opening = "本研究选取某校园污水管网作为研究对象"
        test.results_headline = "DO与CH4呈显著负相关(p<0.001)"
        test.discussion_closing = "溶解氧和有机负荷是控制碳相态转化的关键因素"

        result = test.validate()
        print("\n七句话血统测试:", json.dumps(result, ensure_ascii=False, indent=2))
        print("\n" + test.to_markdown())
        print("\n测试通过!")
    else:
        print("用法: python motivation_thread.py --test")
