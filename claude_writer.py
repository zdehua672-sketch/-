# -*- coding: utf-8 -*-
"""
Claude Writer — 基于 Claude Code CLI 的学术写作引擎

通过 subprocess 调用本地 Claude Code CLI (claude) 生成高质量学术文本。
深度整合文献学习成果（句式模式、讨论结构、机制知识、领域术语）。

用法:
    from claude_writer import ClaudeWriter

    writer = ClaudeWriter()
    intro = writer.write_introduction(findings, domain="污水管网碳排放")
    abstract = writer.write_abstract(sections)
"""

import subprocess
import json
import logging
import os
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300


class ClaudeWriter:
    """
    通过 Claude Code CLI 生成学术文本。
    深度整合文献学习成果，实现"学了就用"。
    支持多领域配置，不再硬编码域名。
    """

    def __init__(self, model: str = None, timeout: int = DEFAULT_TIMEOUT, domain_config=None):
        self.timeout = timeout
        self.model = model
        self.domain_config = domain_config

    def _get_domain_context(self) -> str:
        """从领域配置生成上下文文本"""
        if not self.domain_config:
            return ""
        dc = self.domain_config
        lines = []
        if dc.standards:
            std_text = ', '.join(f'{k}({v})' for k, v in list(dc.standards.items())[:8])
            lines.append(f"分析标准: {std_text}")
        if dc.typical_limitations:
            lines.append(f"典型局限性参考: {'; '.join(dc.typical_limitations[:3])}")
        return '\n'.join(lines)

    def _call_claude(self, prompt: str) -> str:
        """调用 Claude CLI 生成文本"""
        # 自动查找 claude CLI 路径
        claude_cmd = "claude"
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            candidate = os.path.join(path_dir, 'claude')
            if os.path.exists(candidate) or os.path.exists(candidate + '.cmd'):
                claude_cmd = candidate
                break
        # Windows npm 全局安装路径
        npm_global = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm', 'claude.cmd')
        if os.path.exists(npm_global):
            claude_cmd = npm_global

        cmd = [claude_cmd, "-p", prompt, "--output-format", "text"]
        if self.model:
            cmd.extend(["--model", self.model])
        try:
            # 修复 SSL 证书问题
            env = os.environ.copy()
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, encoding='utf-8', errors='replace',
                env=env,
            )
            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr[:300]}")
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Claude CLI timeout after {self.timeout}s")
            return ""
        except FileNotFoundError:
            logger.error("Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code")
            return ""
        except Exception as e:
            logger.error(f"Claude CLI call failed: {e}")
            return ""

    # ================================================================
    # 核心写作接口
    # ================================================================

    def write_results(self, findings: list, figures: dict = None,
                      domain: str = "污水管网碳排放", language: str = "zh",
                      learned_patterns: dict = None) -> str:
        """
        生成 Results 章节。

        Parameters
        ----------
        findings : list
            DataExplorer 输出的发现列表
        figures : dict
            可用图表 {name: {'path': ..., 'caption': ...}}
        learned_patterns : dict
            从文献中学到的写作模式
        """
        findings_text = self._summarize_findings(findings)
        figures_text = self._format_figures(figures)
        patterns_hint = self._format_patterns_hint(learned_patterns, 'result')

        if language == "zh":
            prompt = f"""你是环境科学学者，撰写{domain}论文的"结果"章节(1000-1500字)。

要求：
1. 结构：描述统计 → 季节差异 → 相关性
2. 每个发现必须有具体数据(均值、p值、r值)
3. 客观陈述，不解释原因
4. 引用图表(如图1所示)

发现:
{findings_text}
{figures_text}

直接输出结果正文，用 ## 标记子章节。"""
        else:
            prompt = f"""You are a senior environmental scientist writing Results for a paper about {domain}.

Write the Results section (1500-2500 words).

Requirements:
1. Structure: Descriptive stats -> Seasonal differences -> Correlations -> Outliers
2. Include specific data (mean, SD, p-value, r-value) for every finding
3. Reference figures/tables (e.g., "as shown in Fig. 1")
4. Be objective - save interpretation for Discussion
{patterns_hint}

Findings: {findings_text}
{figures_text}

Write the Results directly, use ## for subsections."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Results 失败")
            return ""
        logger.info(f"Results: Claude 生成 {len(result)} 字")
        return result

    def write_discussion(self, findings: list, mechanisms: dict = None,
                         domain: str = "污水管网碳排放", language: str = "zh",
                         recalled_refs: list = None,
                         learned_patterns: dict = None) -> str:
        """
        生成 Discussion 章节，深度整合文献学习成果。
        """
        findings_text = self._summarize_findings(findings)
        mech_text = self._format_mechanisms(mechanisms)
        refs_text = self._format_references(recalled_refs)
        patterns_hint = self._format_patterns_hint(learned_patterns, 'discussion')
        structures_text = self._format_discussion_structures(learned_patterns)
        domain_terms = self._format_domain_terms(learned_patterns)

        if language == "zh":
            prompt = f"""你是环境科学学者，撰写{domain}论文的"讨论"章节(1500-2500字)。

要求：
1. 结构：概述 → 逐项讨论(发现+机制+文献对比) → 意义 → 局限性
2. 每个发现要解释"为什么"
3. 用学术限定语(可能、归因于、表明)

发现:
{findings_text}

{mech_text}

{refs_text}

直接输出讨论正文，用 ## 标记子章节。"""
        else:
            prompt = f"""You are a senior environmental scientist writing a Discussion about {domain}.

Write the Discussion (2000-3000 words).

Requirements:
1. Structure: Overview -> Point-by-point (literature comparison + mechanism) -> Significance -> Limitations
2. For each key finding: (a) state it (b) compare with literature (c) explain mechanism
3. Use hedging language (may, suggest, indicate, attribute to)
{patterns_hint}

Findings: {findings_text}
{mech_text}
{refs_text}

Write the Discussion directly, use ## for subsections."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Discussion 失败")
            return ""
        logger.info(f"Discussion: Claude 生成 {len(result)} 字")
        return result

    def write_introduction(self, findings: list, domain: str = "污水管网碳排放",
                           language: str = "zh", recalled_refs: list = None,
                           learned_patterns: dict = None) -> str:
        """生成 Introduction 章节"""
        findings_text = self._summarize_findings(findings)
        refs_text = self._format_references(recalled_refs)
        patterns_hint = self._format_patterns_hint(learned_patterns, 'background')

        if language == "zh":
            prompt = f"""你是环境科学学者，撰写{domain}论文的"引言"(1000-1500字)。

要求：
1. 倒三角：领域重要性 → 现有研究 → 不足 → 本文目标
2. 引用3-5篇文献
3. 用"本研究"不用"本文"
4. 列出2-3个研究目标

发现摘要:
{findings_text}

{refs_text}

直接输出引言正文，用 ## 标记子章节。"""
        else:
            prompt = f"""You are a senior environmental scientist writing an Introduction about {domain}.

Write the Introduction (1500-2000 words).

Requirements:
1. Inverted triangle: field importance -> existing research -> gaps -> objectives
2. Cite 3-5 references
3. End with 2-3 clear research objectives
{patterns_hint}

Findings: {findings_text}
{refs_text}

Write the Introduction directly, use ## for subsections."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Introduction 失败")
            return ""
        logger.info(f"Introduction: Claude 生成 {len(result)} 字")
        return result

    def write_abstract(self, sections: dict, domain: str = "污水管网碳排放",
                       language: str = "zh") -> str:
        """基于实际章节内容生成 Abstract"""
        intro = sections.get('introduction', '')[:600]
        methods = sections.get('methods', '')[:600]
        results = sections.get('results', '')[:800]
        discussion = sections.get('discussion', '')[:600]

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请根据以下各章节内容，撰写论文的"摘要"（300-400字）。

要求：
1. 结构：目的 → 方法 → 结果 → 结论（四段式）
2. 结果部分必须包含关键数据（相关系数、显著性水平、主要差异）
3. 结论要指出研究的科学意义和应用价值
4. 语言精炼，每句话都有信息量
5. 不要引用参考文献
6. 最后列出5-8个关键词

引言要点:
{intro}

方法要点:
{methods}

结果要点:
{results}

讨论要点:
{discussion}

请直接输出摘要正文，格式：
【摘要】（正文）
【关键词】（关键词列表）"""
        else:
            prompt = f"""Write an abstract (250-300 words) for a paper about {domain}.

Structure: Objective -> Methods -> Results -> Conclusions
Include key statistics. End with 5-8 keywords.

Introduction: {intro}
Methods: {methods}
Results: {results}
Discussion: {discussion}

Write the abstract directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Abstract 失败")
            return ""
        logger.info(f"Abstract: Claude 生成 {len(result)} 字")
        return result

    def write_conclusion(self, findings: list, domain: str = "污水管网碳排放",
                         language: str = "zh") -> str:
        """生成 Conclusion 章节"""
        findings_text = self._summarize_findings(findings)

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请根据以下数据分析发现，撰写"结论"章节（约500-800字）。

要求：
1. 列出3-5条主要结论，每条用编号标注
2. 每条结论要包含具体数据支撑
3. 最后指出研究的科学意义和实际应用价值
4. 语言精炼、有力
5. 不要重复摘要内容

数据分析发现:
{findings_text}

请直接输出结论正文，用 (1) (2) (3) 编号。"""
        else:
            prompt = f"""Write a Conclusion (300-500 words) for a paper about {domain}.

Requirements:
1. 3-5 numbered conclusions with data support
2. End with scientific significance and practical implications

Findings: {findings_text}

Write the Conclusion directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Conclusion 失败")
            return ""
        logger.info(f"Conclusion: Claude 生成 {len(result)} 字")
        return result

    def write_methods(self, data_info: dict = None, domain: str = "污水管网碳排放",
                      language: str = "zh") -> str:
        """生成 Methods 章节"""
        info_text = ""
        if data_info:
            info_text = f"""
数据概况:
- 样本数: {data_info.get('n_samples', '未知')}
- 变量数: {data_info.get('n_variables', '未知')}
- 变量列表: {', '.join(data_info.get('variables', [])[:20])}
- 分组: {', '.join(data_info.get('groups', []))}
"""

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请撰写"材料与方法"章节（约1000-1500字）。

要求：
1. 结构：研究区域概况 → 采样方法 → 分析方法 → 数据处理方法
2. 分析方法要引用国家标准（如 TOC用HJ 501-2009，COD用GB 11914-89）
3. 统计方法要具体（Pearson相关、t检验/Mann-Whitney U、PCA、HCA等）
4. 语言要让同行能复现实验
{info_text}
请直接输出方法正文，用 ## 标记子章节。"""
        else:
            prompt = f"""Write a Methods section (800-1200 words) for a paper about {domain}.

Structure: Study area -> Sampling -> Analytical methods -> Statistical methods
{info_text}
Write the Methods directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Methods 失败")
            return ""
        logger.info(f"Methods: Claude 生成 {len(result)} 字")
        return result

    # ================================================================
    # 文本润色
    # ================================================================

    def polish_text(self, text: str, instruction: str = None,
                    learned_patterns: dict = None) -> str:
        """
        润色文本，可选融入学到的句式模式。
        """
        patterns_hint = ""
        if learned_patterns:
            sentence_patterns = learned_patterns.get('sentence_patterns', {})
            if sentence_patterns:
                # 提取前5个句式作为参考
                examples = []
                for section_type, patterns in list(sentence_patterns.items())[:3]:
                    for p in patterns[:2]:
                        if isinstance(p, dict) and p.get('skeleton'):
                            examples.append(f"  {section_type}: {p['skeleton']}")
                if examples:
                    patterns_hint = f"\n\n参考句式模式（从文献中提取）:\n" + '\n'.join(examples[:5])

        if not instruction:
            instruction = "润色这段学术文本，保持原意但提升表达质量，避免重复句式"

        prompt = f"""请对以下学术文本进行润色：

{instruction}
{patterns_hint}

原文:
{text}

请直接输出润色后的文本，不要加说明。"""

        result = self._call_claude(prompt)
        return result if result else text

    # ================================================================
    # 辅助格式化方法
    # ================================================================

    def _summarize_findings(self, findings: list) -> str:
        """将 findings 列表转为可读文本摘要（精简版，避免超时）"""
        if not findings:
            return "暂无数据分析发现。"
        # 只取最重要的发现，严格限制数量
        critical = [f for f in findings if f.get('importance') == 'critical']
        high = [f for f in findings if f.get('importance') == 'high']
        selected = (critical + high)[:8] if (critical + high) else findings[:6]
        lines = []
        for f in selected:
            ftype = f.get('type', 'unknown')
            importance = f.get('importance', 'medium')
            var = f.get('variable', '')
            vars_ = f.get('variables', ('', ''))
            data = f.get('data', {})
            if ftype == 'distribution':
                lines.append(f"[分布] {var}: 均值={data.get('mean', 0):.2f}, "
                           f"CV={data.get('cv', 0):.1f}%, 偏度={data.get('skewness', 0):.2f}")
            elif ftype == 'group_difference':
                p = data.get('p_value', 1)
                lines.append(f"[组间差异] {var}: {data.get('test', '')} p={p:.4f}, "
                           f"均值={data.get('means', [])} [{importance}]")
            elif ftype == 'correlation':
                r = data.get('r', 0)
                p = data.get('p', 1)
                lines.append(f"[相关性] {vars_[0]} vs {vars_[1]}: r={r:.3f}, p={p:.4f} [{importance}]")
            elif ftype == 'outlier':
                lines.append(f"[异常值] {var}: {data.get('n_outliers', 0)}个异常值")
            else:
                lines.append(f"[{ftype}] {var or vars_}: {f.get('description', '')}")
        return '\n'.join(lines)

    def _format_figures(self, figures: dict) -> str:
        """格式化图表信息"""
        if not figures:
            return ""
        lines = ["\n\n可用图表:"]
        for name, info in figures.items():
            caption = info.get('caption', name)
            lines.append(f"- {name}: {caption}")
        return '\n'.join(lines)

    def _format_mechanisms(self, mechanisms: dict) -> str:
        """格式化机制知识（精简版）"""
        if not mechanisms:
            return ""
        lines = ["已知机制:"]
        for pair, mech in list(mechanisms.items())[:5]:
            # 截断过长的机制描述
            mech_short = mech[:200] + '...' if len(mech) > 200 else mech
            lines.append(f"- {pair}: {mech_short}")
        return '\n'.join(lines)

    def _format_references(self, refs: list) -> str:
        """格式化参考文献（精简版）"""
        if not refs:
            return ""
        lines = ["参考文献:"]
        for ref in refs[:5]:
            title = ref.get('title', '')
            year = ref.get('year', '')
            authors = ref.get('authors', '')
            if isinstance(authors, list):
                authors = ', '.join(authors[:3])
            lines.append(f"- {authors} ({year}). {title}")
        return '\n'.join(lines)

    def _format_patterns_hint(self, learned_patterns: dict, section_type: str) -> str:
        """从学到的模式中提取写作提示"""
        if not learned_patterns:
            return ""

        hints = []

        # 句式模式
        sentence_patterns = learned_patterns.get('sentence_patterns', {})
        if sentence_patterns:
            relevant = []
            for stype, patterns in sentence_patterns.items():
                if section_type in stype or stype in ['result', 'discussion', 'background']:
                    for p in patterns[:2]:
                        if isinstance(p, dict) and p.get('skeleton'):
                            relevant.append(p['skeleton'])
            if relevant:
                hints.append(f"参考句式: {'; '.join(relevant[:3])}")

        # 机制知识
        mechanisms = learned_patterns.get('mechanisms', [])
        if mechanisms:
            mech_hints = []
            for m in mechanisms[:3]:
                if isinstance(m, dict):
                    var1 = m.get('var1', '')
                    var2 = m.get('var2', '')
                    relation = m.get('relation', '')
                    if var1 and var2:
                        mech_hints.append(f"{var1} {relation} {var2}")
            if mech_hints:
                hints.append(f"已知变量关系: {', '.join(mech_hints)}")

        if hints:
            return "\n从文献学习中获得的参考:\n" + '\n'.join(f"- {h}" for h in hints)
        return ""

    def _format_discussion_structures(self, learned_patterns: dict) -> str:
        """格式化讨论结构模式"""
        if not learned_patterns:
            return ""
        structures = learned_patterns.get('discussion_structures', [])
        if not structures:
            return ""
        lines = ["从文献中学到的讨论结构模式:"]
        for s in structures[:3]:
            if isinstance(s, dict):
                name = s.get('pattern_name', '')
                moves = s.get('moves', [])
                if name and moves:
                    lines.append(f"- {name}: {' → '.join(moves[:5])}")
        return '\n'.join(lines) if len(lines) > 1 else ""

    def _format_domain_terms(self, learned_patterns: dict) -> str:
        """格式化领域术语"""
        if not learned_patterns:
            return ""
        terms = learned_patterns.get('domain_terms', [])
        if not terms:
            return ""
        return f"领域术语: {', '.join(terms[:10])}"
