"""
=============================================================================
深度模仿协议 - Deep Imitation Protocol
借鉴自PaperSpine的deep-imitation-protocol.md

核心思想：学习范文不是"读一遍"，而是用三层表格法提取可复用的写作决策。
然后用"闭卷改写"方法：提取事实 → 读蓝图 → 不看原文 → 重新写 → 对照验证。

三层表格法：
  Table 1: 范文动作表（每段做了什么 move）
  Table 2: 用户草稿动作表（当前每段的问题）
  Table 3: 目标蓝图（每段应该怎么改）

闭卷改写：
  1. 从原文提取事实、数据、引用
  2. 读范文动作表和目标蓝图
  3. 不看原文，从笔记和蓝图重新写
  4. 对照原文验证：数据、引用、图表引用是否保留
=============================================================================
"""
import re
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class ExemplarMove:
    """范文中一个段落的写作动作"""
    paper_title: str         # 范文标题
    paragraph_index: int     # 段落序号
    section: str             # 所属章节
    move_type: str           # 动作类型（背景/现状/空白/回应/证据/解释等）
    opening_function: str    # 开头功能
    closing_function: str    # 结尾功能
    evidence_type: str       # 证据类型（数据/引用/类比/权威等）
    notes: str = ""          # 分析笔记
    raw_text: str = ""       # 原始文本片段


@dataclass
class DraftMove:
    """用户草稿中一个段落的写作动作"""
    paragraph_index: int     # 段落序号
    current_move: str        # 当前动作
    evidence_present: str    # 存在的证据
    problem: str             # 问题诊断
    keepable_content: str    # 可保留的内容
    raw_text: str = ""       # 原始文本


@dataclass
class TargetMove:
    """目标蓝图中一个段落的写作计划"""
    paragraph_index: int     # 段落序号
    move_type: str           # 目标动作类型
    source_evidence: str     # 来源证据
    exemplar_pattern: str    # 范文模式来源
    target_length: str       # 目标长度
    operation: str           # 操作类型 REWRITE/SPLIT/MERGE/DELETE/MOVE/ADD/KEEP


@dataclass
class SectionAnalysis:
    """一个章节的三层分析结果"""
    section_name: str
    exemplar_moves: list = field(default_factory=list)   # list of ExemplarMove
    draft_moves: list = field(default_factory=list)      # list of DraftMove
    target_moves: list = field(default_factory=list)     # list of TargetMove
    closed_book_draft: str = ""                          # 闭卷改写结果
    verification_notes: str = ""                         # 验证笔记


# ============================================================================
# 范文动作提取器
# ============================================================================

class ExemplarAnalyzer:
    """
    从范文中提取写作动作

    不是读全文，而是逐段分析每个写作决策：
    - 这段做了什么？（move_type）
    - 开头怎么引导读者？（opening_function）
    - 结尾怎么过渡？（closing_function）
    - 用什么类型的证据？（evidence_type）
    """

    # 段落动作分类关键词
    MOVE_KEYWORDS = {
        'background': ['背景', '概述', '介绍', 'background', 'overview', 'context'],
        'importance': ['重要', '关键', '意义', 'important', 'crucial', 'significance'],
        'status': ['现状', '进展', '研究', '进展', 'state of art', 'progress', 'recent'],
        'gap': ['空白', '不足', '缺乏', '然而', 'gap', 'however', 'limitation', 'lack'],
        'response': ['本研究', '本文', '提出', '采用', 'this study', 'we propose', 'we present'],
        'evidence': ['结果', '发现', '数据', '表明', 'results', 'found', 'showed', 'data'],
        'mechanism': ['机制', '原因', '解释', '因为', 'mechanism', 'because', 'explain', 'reason'],
        'comparison': ['比较', '对比', '一致', '类似', 'comparison', 'consistent', 'similar'],
        'limitation': ['局限', '不足', '未能', 'limitation', 'however', 'could not'],
        'future': ['展望', '未来', '进一步', 'future', 'further', 'next'],
    }

    @classmethod
    def analyze_paragraph(cls, text: str, paper_title: str = "",
                         paragraph_index: int = 0, section: str = "") -> ExemplarMove:
        """分析一个段落的写作动作"""
        text_lower = text.lower()

        # 识别动作类型
        move_type = 'unknown'
        for move, keywords in cls.MOVE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                move_type = move
                break

        # 识别开头功能
        opening = cls._analyze_opening(text)

        # 识别结尾功能
        closing = cls._analyze_closing(text)

        # 识别证据类型
        evidence = cls._analyze_evidence(text)

        return ExemplarMove(
            paper_title=paper_title,
            paragraph_index=paragraph_index,
            section=section,
            move_type=move_type,
            opening_function=opening,
            closing_function=closing,
            evidence_type=evidence,
            raw_text=text[:200],
        )

    @classmethod
    def analyze_paper(cls, sections: dict, paper_title: str = "") -> list:
        """
        分析一篇范文的所有章节

        Parameters
        ----------
        sections : dict, {section_name: text}
        paper_title : str

        Returns
        -------
        list of ExemplarMove
        """
        all_moves = []
        for section_name, text in sections.items():
            paragraphs = _split_paragraphs(text)
            for i, para in enumerate(paragraphs):
                if len(para) < 20:
                    continue
                move = cls.analyze_paragraph(
                    para, paper_title, len(all_moves), section_name
                )
                all_moves.append(move)
        return all_moves

    @classmethod
    def _analyze_opening(cls, text: str) -> str:
        """分析段落开头功能"""
        first_sentence = text.split('。')[0].split('.')[0] if text else ''
        first_lower = first_sentence.lower()

        if any(kw in first_lower for kw in ['在', '随着', '近年来', 'with', 'as', 'recently']):
            return '背景引入'
        if any(kw in first_lower for kw in ['然而', '但是', 'however', 'but', 'yet']):
            return '转折/指出空白'
        if any(kw in first_lower for kw in ['本研究', '本文', 'this study', 'we', 'our']):
            return '提出本研究'
        if any(kw in first_lower for kw in ['结果', '发现', '数据', 'results', 'findings']):
            return '展示结果'
        if any(kw in first_lower for kw in ['因此', '综上', 'thus', 'therefore', 'in summary']):
            return '总结/推论'
        return '承接上文'

    @classmethod
    def _analyze_closing(cls, text: str) -> str:
        """分析段落结尾功能"""
        sentences = text.split('。')
        last = sentences[-2] if len(sentences) > 1 else sentences[-1]
        last_lower = last.lower()

        if any(kw in last_lower for kw in ['因此', '表明', '说明', 'thus', 'suggest', 'indicate']):
            return '得出结论'
        if any(kw in last_lower for kw in ['有待', '需要', '未来', 'further', 'need', 'remain']):
            return '引出未来方向'
        if any(kw in last_lower for kw in ['本研究', '本文', 'this study', 'we']):
            return '引出本研究'
        return '自然收束'

    @classmethod
    def _analyze_evidence(cls, text: str) -> str:
        """分析段落使用的证据类型"""
        evidence_types = []
        if re.search(r'\d+\.?\d*\s*(%|mg|mmol|倍|个|篇)', text):
            evidence_types.append('定量数据')
        if re.search(r'\([A-Z][a-z]+\s*(et al\.?)?,?\s*\d{4}\)', text):
            evidence_types.append('文献引用')
        if re.search(r'(图|表|Figure|Table|Fig\.)\s*\d', text):
            evidence_types.append('图表引用')
        if any(kw in text for kw in ['研究表明', '已有研究', 'previous studies', 'it has been reported']):
            evidence_types.append('文献综述')

        return '; '.join(evidence_types) if evidence_types else '论述/推理'


# ============================================================================
# 草稿动作分析器
# ============================================================================

class DraftAnalyzer:
    """
    分析用户草稿的写作动作

    识别每个段落的问题：
    - 当前做了什么 move？
    - 存在什么证据？
    - 有什么问题？
    - 有什么可保留？
    """

    PROBLEM_PATTERNS = {
        'wrong_move': ['但是', '然而', 'however'],  # 出现在不该出现的位置
        'multiple_moves': 3,  # 一个段落超过3个不同 move 关键词
        'unsupported_claim': ['显著', '重要', '关键', 'significant', 'important'],
        'weak_transition': ['另外', '此外', '同时', 'also', 'additionally', 'meanwhile'],
        'no_evidence': [],  # 没有数字、引用或图表
    }

    @classmethod
    def analyze_paragraph(cls, text: str, paragraph_index: int = 0) -> DraftMove:
        """分析一个草稿段落"""
        text_lower = text.lower()

        # 识别当前动作
        current_move = ExemplarAnalyzer._analyze_opening(text)

        # 识别存在的证据
        evidence = ExemplarAnalyzer._analyze_evidence(text)

        # 诊断问题
        problems = cls._diagnose_problems(text)

        # 识别可保留内容
        keepable = cls._identify_keepable(text)

        return DraftMove(
            paragraph_index=paragraph_index,
            current_move=current_move,
            evidence_present=evidence,
            problem='; '.join(problems) if problems else '无明显问题',
            keepable_content=keepable,
            raw_text=text[:200],
        )

    @classmethod
    def _diagnose_problems(cls, text: str) -> list:
        """诊断段落问题"""
        problems = []

        # 检查是否有证据支撑
        evidence = ExemplarAnalyzer._analyze_evidence(text)
        if evidence == '论述/推理' and len(text) > 100:
            problems.append('缺少数据/引用支撑')

        # 检查是否过于空洞
        hollow_patterns = [
            '具有重要意义', '提供参考', '有待进一步研究',
            'plays a crucial role', 'further research is needed',
        ]
        if any(p in text for p in hollow_patterns):
            problems.append('包含空洞套话')

        # 检查逻辑跳跃
        leap_words = ['因此', '所以', '故', 'thus', 'therefore', 'hence']
        leap_count = sum(text.count(w) for w in leap_words)
        if leap_count > 2 and len(text) < 500:
            problems.append('逻辑跳跃过多')

        return problems

    @classmethod
    def _identify_keepable(cls, text: str) -> str:
        """识别可保留的核心内容"""
        keepable = []

        # 提取数据
        data_matches = re.findall(r'\d+\.?\d*\s*(%|mg/L|mmol/L|p<|r=)', text)
        if data_matches:
            keepable.append(f'数据: {len(data_matches)}处')

        # 提取引用
        ref_matches = re.findall(r'\([A-Z][a-z]+[^)]*\d{4}[^)]*\)', text)
        if ref_matches:
            keepable.append(f'引用: {len(ref_matches)}处')

        # 提取图表引用
        fig_matches = re.findall(r'(图|表|Figure|Table|Fig\.)\s*\d', text)
        if fig_matches:
            keepable.append(f'图表引用: {len(fig_matches)}处')

        return '; '.join(keepable) if keepable else '核心论述（需重组）'


# ============================================================================
# 目标蓝图生成器
# ============================================================================

class BlueprintGenerator:
    """
    从范文动作表和草稿动作表生成目标蓝图

    每个目标段落都有明确的操作指令：
    - REWRITE: 保留证据，重写结构和措辞
    - SPLIT: 一个段落拆成多个
    - MERGE: 多个弱段落合并
    - DELETE: 删除无支撑内容
    - MOVE: 移到更好的位置
    - ADD: 添加连接性或解释性文本
    - KEEP: 基本保留（需明确理由）
    """

    @classmethod
    def generate(cls, exemplar_moves: list, draft_moves: list,
                 section_name: str = "") -> list:
        """
        生成目标蓝图

        Parameters
        ----------
        exemplar_moves : list of ExemplarMove
        draft_moves : list of DraftMove
        section_name : str

        Returns
        -------
        list of TargetMove
        """
        target_moves = []

        # 分析范文模式
        exemplar_pattern = cls._extract_pattern(exemplar_moves)

        # 为每个草稿段落生成目标
        for draft in draft_moves:
            # 匹配范文中最接近的 move
            best_match = cls._find_best_exemplar(draft, exemplar_moves)

            # 决定操作类型
            operation = cls._decide_operation(draft, best_match)

            # 生成目标 move
            target = TargetMove(
                paragraph_index=draft.paragraph_index,
                move_type=best_match.move_type if best_match else draft.current_move,
                source_evidence=draft.evidence_present,
                exemplar_pattern=f"{best_match.move_type}: {best_match.opening_function}" if best_match else '',
                target_length='中等' if operation in ('REWRITE', 'KEEP') else '短',
                operation=operation,
            )
            target_moves.append(target)

        # 检查是否缺少范文中有的 obligatory moves
        draft_move_types = {d.current_move for d in draft_moves}
        for exemplar in exemplar_moves:
            if exemplar.move_type not in draft_move_types and exemplar.move_type in ('gap', 'response', 'mechanism'):
                target_moves.append(TargetMove(
                    paragraph_index=len(target_moves),
                    move_type=exemplar.move_type,
                    source_evidence='',
                    exemplar_pattern=f"{exemplar.move_type}: {exemplar.opening_function}",
                    target_length='中等',
                    operation='ADD',
                ))

        return target_moves

    @classmethod
    def _extract_pattern(cls, exemplar_moves: list) -> str:
        """从范文动作中提取结构模式"""
        if not exemplar_moves:
            return ''
        sequence = [m.move_type for m in exemplar_moves[:8]]
        return ' → '.join(sequence)

    @classmethod
    def _find_best_exemplar(cls, draft: DraftMove,
                           exemplar_moves: list) -> Optional[ExemplarMove]:
        """为草稿段落找到最匹配的范文 move"""
        for exemplar in exemplar_moves:
            if exemplar.move_type == draft.current_move:
                return exemplar
        # 按位置匹配
        if draft.paragraph_index < len(exemplar_moves):
            return exemplar_moves[draft.paragraph_index]
        return exemplar_moves[0] if exemplar_moves else None

    @classmethod
    def _decide_operation(cls, draft: DraftMove,
                         exemplar: Optional[ExemplarMove]) -> str:
        """决定操作类型"""
        # 如果问题严重
        if '空洞套话' in draft.problem and '缺少数据' in draft.problem:
            return 'REWRITE'
        if '空洞套话' in draft.problem:
            return 'REWRITE'
        if '逻辑跳跃过多' in draft.problem:
            return 'REWRITE'

        # 如果缺少关键 move
        if exemplar and exemplar.move_type in ('gap', 'response') and draft.current_move not in ('gap', 'response'):
            return 'REWRITE'

        # 如果证据充足且无大问题
        if draft.evidence_present != '论述/推理' and '无明显问题' in draft.problem:
            return 'KEEP'

        return 'REWRITE'


# ============================================================================
# 闭卷改写器
# ============================================================================

class ClosedBookRewriter:
    """
    闭卷改写方法

    流程：
    1. 从原文提取事实、数据、引用到笔记
    2. 读范文动作表和目标蓝图
    3. 不看原文，从笔记和蓝图重新写
    4. 对照原文验证
    """

    @classmethod
    def extract_facts(cls, text: str) -> dict:
        """
        从原文提取事实到笔记

        Returns
        -------
        dict: {numbers, citations, figure_refs, key_claims}
        """
        facts = {
            'numbers': [],
            'citations': [],
            'figure_refs': [],
            'key_claims': [],
        }

        # 提取数字数据
        numbers = re.findall(r'(\d+\.?\d*)\s*(%|mg/L|mmol/L|p<0\.\d+|r=-?\d+\.\d+)', text)
        facts['numbers'] = [f"{n}{u}" for n, u in numbers]

        # 提取引用
        citations = re.findall(r'\([A-Z][a-z]+[^)]*\d{4}[^)]*\)', text)
        facts['citations'] = citations

        # 提取图表引用
        figs = re.findall(r'(图|表|Figure|Table|Fig\.)\s*\d+', text)
        facts['figure_refs'] = figs

        # 提取关键主张（包含显著性标记的句子）
        sentences = re.split(r'[。.！!？?]', text)
        for s in sentences:
            if any(kw in s for kw in ['显著', '重要', '关键', 'significant', 'important', 'p<', 'r=']):
                facts['key_claims'].append(s.strip())

        return facts

    @classmethod
    def verify_against_original(cls, new_text: str, original_facts: dict) -> dict:
        """
        验证闭卷改写是否保留了原文的关键信息

        Returns
        -------
        dict: {missing_numbers, missing_citations, missing_figures, status}
        """
        new_numbers = set(re.findall(r'\d+\.?\d*\s*(%|mg/L|mmol/L)', new_text))
        orig_numbers = set(original_facts.get('numbers', []))

        new_cites = set(re.findall(r'\([A-Z][a-z]+[^)]*\d{4}[^)]*\)', new_text))
        orig_cites = set(original_facts.get('citations', []))

        new_figs = set(re.findall(r'(图|表|Figure|Table|Fig\.)\s*\d+', new_text))
        orig_figs = set(original_facts.get('figure_refs', []))

        missing_numbers = orig_numbers - new_numbers
        missing_citations = orig_cites - new_cites
        missing_figures = orig_figs - new_figs

        status = 'PASS'
        if missing_numbers or missing_citations:
            status = 'WARN'
        if missing_figures:
            status = 'WARN' if status == 'PASS' else 'FAIL'

        return {
            'missing_numbers': list(missing_numbers),
            'missing_citations': list(missing_citations),
            'missing_figures': list(missing_figures),
            'status': status,
        }


# ============================================================================
# 深度模仿管理器
# ============================================================================

class DeepImitationManager:
    """
    深度模仿协议管理器

    端到端工作流：
    1. analyze_exemplar() — 分析范文
    2. analyze_draft() — 分析草稿
    3. generate_blueprint() — 生成目标蓝图
    4. closed_book_rewrite_notes() — 生成闭卷改写笔记
    5. verify_rewrite() — 验证改写结果
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.sections: dict = {}  # section_name -> SectionAnalysis

    def analyze_exemplar(self, section_name: str, exemplar_text: str,
                        paper_title: str = "") -> list:
        """分析范文的一个章节"""
        paragraphs = _split_paragraphs(exemplar_text)
        moves = []
        for i, para in enumerate(paragraphs):
            if len(para) < 20:
                continue
            move = ExemplarAnalyzer.analyze_paragraph(
                para, paper_title, i, section_name
            )
            moves.append(move)

        if section_name not in self.sections:
            self.sections[section_name] = SectionAnalysis(section_name=section_name)
        self.sections[section_name].exemplar_moves = moves
        return moves

    def analyze_draft(self, section_name: str, draft_text: str) -> list:
        """分析用户草稿的一个章节"""
        paragraphs = _split_paragraphs(draft_text)
        moves = []
        for i, para in enumerate(paragraphs):
            if len(para) < 20:
                continue
            move = DraftAnalyzer.analyze_paragraph(para, i)
            moves.append(move)

        if section_name not in self.sections:
            self.sections[section_name] = SectionAnalysis(section_name=section_name)
        self.sections[section_name].draft_moves = moves
        return moves

    def generate_blueprint(self, section_name: str) -> list:
        """为一个章节生成目标蓝图"""
        if section_name not in self.sections:
            return []

        section = self.sections[section_name]
        target_moves = BlueprintGenerator.generate(
            section.exemplar_moves, section.draft_moves, section_name
        )
        section.target_moves = target_moves
        return target_moves

    def closed_book_rewrite_notes(self, section_name: str,
                                   draft_text: str) -> dict:
        """生成闭卷改写笔记"""
        facts = ClosedBookRewriter.extract_facts(draft_text)
        return {
            'section': section_name,
            'facts': facts,
            'fact_count': sum(len(v) for v in facts.values()),
        }

    def verify_rewrite(self, section_name: str, new_text: str,
                      original_text: str) -> dict:
        """验证闭卷改写结果"""
        original_facts = ClosedBookRewriter.extract_facts(original_text)
        return ClosedBookRewriter.verify_against_original(new_text, original_facts)

    def generate_report(self, section_name: str = None) -> str:
        """生成完整的深度模仿分析报告"""
        sections_to_report = [section_name] if section_name else list(self.sections.keys())

        lines = ["# 深度模仿分析报告", ""]

        for name in sections_to_report:
            if name not in self.sections:
                continue
            section = self.sections[name]

            lines.append(f"## {name}")
            lines.append("")

            # 范文动作表
            if section.exemplar_moves:
                lines.append("### Table 1: 范文动作表")
                lines.append("")
                lines.append("| # | 动作类型 | 开头功能 | 结尾功能 | 证据类型 |")
                lines.append("|---|---------|---------|---------|---------|")
                for m in section.exemplar_moves:
                    lines.append(
                        f"| {m.paragraph_index} | {m.move_type} | "
                        f"{m.opening_function} | {m.closing_function} | {m.evidence_type} |"
                    )
                lines.append("")

            # 草稿动作表
            if section.draft_moves:
                lines.append("### Table 2: 草稿动作表")
                lines.append("")
                lines.append("| # | 当前动作 | 存在证据 | 问题 | 可保留内容 |")
                lines.append("|---|---------|---------|------|----------|")
                for d in section.draft_moves:
                    lines.append(
                        f"| {d.paragraph_index} | {d.current_move} | "
                        f"{d.evidence_present[:20]} | {d.problem[:30]} | {d.keepable_content[:20]} |"
                    )
                lines.append("")

            # 目标蓝图
            if section.target_moves:
                lines.append("### Table 3: 目标蓝图")
                lines.append("")
                lines.append("| # | 目标动作 | 来源证据 | 范文模式 | 操作 |")
                lines.append("|---|---------|---------|---------|------|")
                for t in section.target_moves:
                    op_icon = {
                        'REWRITE': '🔄', 'SPLIT': '✂️', 'MERGE': '🔗',
                        'DELETE': '🗑️', 'MOVE': '↔️', 'ADD': '➕', 'KEEP': '✅',
                    }.get(t.operation, '❓')
                    lines.append(
                        f"| {t.paragraph_index} | {t.move_type} | "
                        f"{t.source_evidence[:20]} | {t.exemplar_pattern[:20]} | "
                        f"{op_icon} {t.operation} |"
                    )
                lines.append("")

                # 操作统计
                ops = [t.operation for t in section.target_moves]
                from collections import Counter
                op_counts = Counter(ops)
                lines.append("**操作统计:**")
                for op, count in op_counts.most_common():
                    icon = {
                        'REWRITE': '🔄', 'SPLIT': '✂️', 'MERGE': '🔗',
                        'DELETE': '🗑️', 'MOVE': '↔️', 'ADD': '➕', 'KEEP': '✅',
                    }.get(op, '❓')
                    lines.append(f"- {icon} {op}: {count}")
                lines.append("")

                # 浅编辑警告
                keep_ratio = ops.count('KEEP') / len(ops) if ops else 0
                if keep_ratio > 0.25:
                    lines.append(f"**⚠️ 警告:** KEEP 操作占 {keep_ratio:.0%}，超过 25%。"
                                "建议进行更深层次的逻辑重组。")
                    lines.append("")

        return '\n'.join(lines)

    def save(self):
        """保存所有分析结果"""
        for name, section in self.sections.items():
            data = {
                'section_name': name,
                'exemplar_moves': [asdict(m) for m in section.exemplar_moves],
                'draft_moves': [asdict(m) for m in section.draft_moves],
                'target_moves': [asdict(m) for m in section.target_moves],
                'updated': datetime.now(timezone.utc).isoformat(),
            }
            path = os.path.join(self.output_dir, f'deep_imitation_{name}.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        # 保存报告
        report_path = os.path.join(self.output_dir, 'deep_imitation_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())


# ============================================================================
# 辅助函数
# ============================================================================

def _split_paragraphs(text: str) -> list:
    """分段"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if len(p.strip()) > 10]


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        # 内置测试
        exemplar_text = """
城市污水管网系统是城市基础设施的重要组成部分。近年来，随着城镇化进程加快，管网中碳污染物问题日益突出（Jiang et al., 2011）。

已有研究表明，污水管道不仅是输送通道，更是复杂的生物化学反应器。Guisasola等（2008）发现厌氧条件下产甲烷活动可降解50%以上的有机碳。

然而，现有研究多关注城市级管网，针对校园尺度的碳污染特征研究不足。特别是固-液-气三相碳污染物的联合分析尚未开展。

本研究以某校园污水管网为对象，系统采集三相样品，采用PCA和HCA等多元统计方法，揭示碳污染物的赋存特征和驱动机制。
"""

        draft_text = """
校园污水管网是城市水循环的重要组成部分。

很多研究了污水管网碳污染物的特征。一些研究发现了一些规律。

然而，研究还不够全面。需要进一步研究。

本研究做了一些分析，得到了一些结果。
"""

        print("=" * 60)
        print("深度模仿协议测试")
        print("=" * 60)

        mgr = DeepImitationManager(output_dir='/tmp/test_deep_imitation')

        # 1. 分析范文
        print("\n[1] 分析范文...")
        exemplar_moves = mgr.analyze_exemplar('Introduction', exemplar_text, '示例论文')
        print(f"  提取了 {len(exemplar_moves)} 个范文动作")
        for m in exemplar_moves:
            print(f"    [{m.move_type}] 开头: {m.opening_function}, 证据: {m.evidence_type}")

        # 2. 分析草稿
        print("\n[2] 分析草稿...")
        draft_moves = mgr.analyze_draft('Introduction', draft_text)
        print(f"  提取了 {len(draft_moves)} 个草稿动作")
        for d in draft_moves:
            print(f"    [{d.current_move}] 问题: {d.problem[:40]}")

        # 3. 生成目标蓝图
        print("\n[3] 生成目标蓝图...")
        target_moves = mgr.generate_blueprint('Introduction')
        print(f"  生成了 {len(target_moves)} 个目标动作")
        for t in target_moves:
            print(f"    [{t.operation}] {t.move_type} - {t.exemplar_pattern[:30]}")

        # 4. 闭卷改写笔记
        print("\n[4] 闭卷改写笔记...")
        notes = mgr.closed_book_rewrite_notes('Introduction', draft_text)
        print(f"  提取了 {notes['fact_count']} 个事实")

        # 5. 验证
        print("\n[5] 验证改写结果...")
        verification = mgr.verify_rewrite('Introduction', exemplar_text, draft_text)
        print(f"  状态: {verification['status']}")

        # 6. 生成报告
        print("\n[6] 生成报告...")
        report = mgr.generate_report('Introduction')
        print(report[:1500])
        print("...")

        # 保存
        mgr.save()
        print("\n测试通过!")
    else:
        print("用法: python deep_imitation.py --test")
