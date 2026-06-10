# -*- coding: utf-8 -*-
"""
Claude Writer — 基于 Claude Code CLI 的学术写作引擎

通过 subprocess 调用本地 Claude Code CLI (claude) 生成高质量学术文本。
替代原有的硬编码模板，实现真正的 AI 写作。

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
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# 默认超时（秒）
DEFAULT_TIMEOUT = 120


class ClaudeWriter:
    """
    通过 Claude Code CLI 生成学术文本。

    每次调用都是独立的 subprocess，不依赖 API key。
    """

    def __init__(self, model: str = None, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.model = model  # None = 使用默认模型

    def _call_claude(self, prompt: str, system: str = "") -> str:
        """
        调用 Claude CLI 生成文本。

        Parameters
        ----------
        prompt : str
            用户提示
        system : str
            系统提示（可选）

        Returns
        -------
        str
            Claude 生成的文本
        """
        cmd = ["claude", "-p", prompt, "--output-format", "text"]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace',
            )
            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr[:500]}")
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Claude CLI timeout after {self.timeout}s")
            return ""
        except FileNotFoundError:
            logger.error("Claude CLI not found. Please install: npm install -g @anthropic-ai/claude-code")
            return ""
        except Exception as e:
            logger.error(f"Claude CLI call failed: {e}")
            return ""

    # ================================================================
    # 章节写作接口
    # ================================================================

    def write_introduction(self, findings: list, domain: str = "污水管网碳排放",
                           language: str = "zh", recalled_refs: list = None) -> str:
        """
        生成 Introduction 章节。

        Parameters
        ----------
        findings : list
            DataExplorer 输出的发现列表
        domain : str
            研究领域
        language : str
            语言 ('zh' 或 'en')
        recalled_refs : list
            从知识库召回的参考文献
        """
        # 构建发现摘要
        findings_text = self._summarize_findings(findings)

        # 构建参考文献文本
        refs_text = ""
        if recalled_refs:
            refs_text = "\n\n可用的参考文献:\n"
            for ref in recalled_refs[:10]:
                title = ref.get('title', '')
                year = ref.get('year', '')
                authors = ref.get('authors', '')
                if isinstance(authors, list):
                    authors = ', '.join(authors[:3])
                refs_text += f"- {authors} ({year}). {title}\n"

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请根据以下数据分析发现，撰写论文的"引言"章节（约1500-2000字）。

要求：
1. 遵循"倒三角"结构：领域重要性 → 现有研究 → 研究不足 → 本文目标
2. 引用3-5篇相关文献（使用提供的参考文献）
3. 语言要符合中文学术论文规范（SCI期刊水平）
4. 最后明确列出本文的研究目标（2-3个）
5. 不要使用"本文"开头，用"本研究"
6. 适当使用学术连接词（然而、此外、值得注意的是）

数据分析发现:
{findings_text}
{refs_text}

请直接输出引言正文，不要加标题或说明。用 ## 标记子章节（如 ## 1.1 研究背景）。"""
        else:
            prompt = f"""You are a senior environmental scientist writing an academic paper about {domain}.

Write the Introduction section (1500-2000 words) based on the following data analysis findings.

Requirements:
1. Follow the inverted triangle structure: field importance -> existing research -> gaps -> this study's objectives
2. Cite 3-5 relevant references from the provided list
3. Use formal academic English suitable for SCI journals
4. End with 2-3 clear research objectives
5. Use appropriate hedging language

Data analysis findings:
{findings_text}
{refs_text}

Write the Introduction directly, no headers or explanations. Use ## for subsections."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Introduction 失败，回退到模板")
            return ""
        logger.info(f"Introduction: Claude 生成 {len(result)} 字")
        return result

    def write_abstract(self, sections: dict, domain: str = "污水管网碳排放",
                       language: str = "zh") -> str:
        """
        生成 Abstract。

        Parameters
        ----------
        sections : dict
            已有章节 {'introduction': ..., 'methods': ..., 'results': ..., 'discussion': ...}
        """
        # 提取各章节摘要
        intro_summary = sections.get('introduction', '')[:500]
        methods_summary = sections.get('methods', '')[:500]
        results_summary = sections.get('results', '')[:800]
        discussion_summary = sections.get('discussion', '')[:500]

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
{intro_summary}

方法要点:
{methods_summary}

结果要点:
{results_summary}

讨论要点:
{discussion_summary}

请直接输出摘要正文，格式：
【摘要】（正文）
【关键词】（关键词列表）"""
        else:
            prompt = f"""You are a senior environmental scientist. Write an abstract (250-300 words) for a paper about {domain}.

Structure: Objective -> Methods -> Results -> Conclusions
Include key statistics (correlation coefficients, p-values, major differences).
End with 5-8 keywords.

Introduction: {intro_summary}
Methods: {methods_summary}
Results: {results_summary}
Discussion: {discussion_summary}

Write the abstract directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Abstract 失败，回退到模板")
            return ""
        logger.info(f"Abstract: Claude 生成 {len(result)} 字")
        return result

    def write_discussion(self, findings: list, mechanisms: dict = None,
                         domain: str = "污水管网碳排放", language: str = "zh",
                         recalled_refs: list = None) -> str:
        """
        生成 Discussion 章节。

        Parameters
        ----------
        findings : list
            DataExplorer 输出的发现列表
        mechanisms : dict
            机制知识库条目 {var_pair: mechanism_text}
        """
        findings_text = self._summarize_findings(findings)

        mech_text = ""
        if mechanisms:
            mech_text = "\n\n已知机制解释:\n"
            for pair, mech in mechanisms.items():
                mech_text += f"- {pair}: {mech}\n"

        refs_text = ""
        if recalled_refs:
            refs_text = "\n\n可用的参考文献:\n"
            for ref in recalled_refs[:10]:
                title = ref.get('title', '')
                year = ref.get('year', '')
                authors = ref.get('authors', '')
                if isinstance(authors, list):
                    authors = ', '.join(authors[:3])
                refs_text += f"- {authors} ({year}). {title}\n"

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请根据以下数据分析发现和已知机制，撰写"讨论"章节（约2000-3000字）。

要求：
1. 结构：主要发现概述 → 逐项讨论（与文献对比） → 机制解释 → 研究意义 → 局限性
2. 每个重要发现都要：(a) 陈述发现 (b) 与已有文献对比 (c) 给出机制解释
3. 引用提供的参考文献来支撑论点
4. 使用适当的学术限定语（可能、初步表明、这暗示）
5. 讨论部分要解释"为什么"，不只是重复结果
6. 局限性要诚实、具体，不要泛泛而谈

数据分析发现:
{findings_text}
{mech_text}
{refs_text}

请直接输出讨论正文，用 ## 标记子章节。"""
        else:
            prompt = f"""You are a senior environmental scientist writing a Discussion section about {domain}.

Write the Discussion (2000-3000 words) based on findings and known mechanisms.

Requirements:
1. Structure: Overview -> Point-by-point discussion (compare with literature) -> Mechanisms -> Significance -> Limitations
2. For each key finding: (a) state it (b) compare with literature (c) explain mechanism
3. Use appropriate hedging language
4. Explain "why", don't just repeat results

Findings: {findings_text}
{mech_text}
{refs_text}

Write the Discussion directly, use ## for subsections."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Discussion 失败，回退到模板")
            return ""
        logger.info(f"Discussion: Claude 生成 {len(result)} 字")
        return result

    def write_conclusion(self, findings: list, domain: str = "污水管网碳排放",
                         language: str = "zh") -> str:
        """
        生成 Conclusion 章节。
        """
        findings_text = self._summarize_findings(findings)

        if language == "zh":
            prompt = f"""你是一位环境科学领域的资深学者，正在撰写一篇关于{domain}的中文学术论文。

请根据以下数据分析发现，撰写"结论"章节（约500-800字）。

要求：
1. 列出3-5条主要结论，每条用编号标注
2. 每条结论要包含具体数据支撑（不要泛泛而谈）
3. 最后指出研究的科学意义和实际应用价值
4. 语言精炼、有力
5. 不要重复摘要内容

数据分析发现:
{findings_text}

请直接输出结论正文，用 (1) (2) (3) 编号。"""
        else:
            prompt = f"""Write a Conclusion section (300-500 words) for a paper about {domain}.

Requirements:
1. List 3-5 numbered conclusions with specific data support
2. End with scientific significance and practical implications
3. Be concise and decisive

Findings: {findings_text}

Write the Conclusion directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Conclusion 失败，回退到模板")
            return ""
        logger.info(f"Conclusion: Claude 生成 {len(result)} 字")
        return result

    def write_methods(self, data_info: dict = None, domain: str = "污水管网碳排放",
                      language: str = "zh") -> str:
        """
        生成 Methods 章节。

        Parameters
        ----------
        data_info : dict
            数据信息 {'n_samples': ..., 'variables': ..., 'seasons': ...}
        """
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
Reference national standards where applicable.
{info_text}
Write the Methods directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Methods 失败，回退到模板")
            return ""
        logger.info(f"Methods: Claude 生成 {len(result)} 字")
        return result

    def polish_text(self, text: str, instruction: str = "润色这段学术文本，保持原意但提升表达质量") -> str:
        """
        通用文本润色。
        """
        prompt = f"""请对以下学术文本进行润色：

{instruction}

原文:
{text}

请直接输出润色后的文本。"""

        result = self._call_claude(prompt)
        return result if result else text

    # ================================================================
    # 辅助方法
    # ================================================================

    def _summarize_findings(self, findings: list) -> str:
        """将 findings 列表转为可读文本摘要"""
        if not findings:
            return "暂无数据分析发现。"

        lines = []
        for i, f in enumerate(findings[:20]):  # 最多20条
            ftype = f.get('type', 'unknown')
            importance = f.get('importance', 'medium')
            var = f.get('variable', '')
            vars_ = f.get('variables', ('', ''))
            data = f.get('data', {})
            desc = f.get('description', '')

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
                lines.append(f"[异常值] {var}: {data.get('n_outliers', 0)}个异常值 "
                           f"在{data.get('outlier_range', '')}")
            else:
                lines.append(f"[{ftype}] {var or vars_}: {desc}")

        return '\n'.join(lines)
