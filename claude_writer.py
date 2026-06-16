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
        # 全局禁用 SSL 验证（Claude CLI 使用自定义 API 端点）
        os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

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
        # Windows: 优先使用批处理包装器（解决 SSL 环境变量传递问题）
        wrapper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'claude_wrapper.bat')
        if os.name == 'nt' and os.path.exists(wrapper_path):
            claude_cmd = wrapper_path
        else:
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
            # 修复 SSL 证书问题：Windows 需要 shell=True 才能正确传递环境变量
            env = os.environ.copy()
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            is_windows = os.name == 'nt'
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, encoding='utf-8', errors='replace',
                env=env,
                shell=is_windows,
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
            prompt = f"""你是环境科学学者，撰写{domain}论文的"结果"章节(1500-2500字)。

要求：
1. 结构跟随数据发现：先描述整体特征，再报告重要发现
2. 报告所有显著结果(p<0.05)，也要报告接近显著的结果(0.05<p<0.10)
3. 报告效应量(Cohen's d)，不只是p值
4. 不显著的结果也要报告（说明"未检测到显著差异"）
5. 深挖异常值故事（为什么某个采样点特别高/低？）
6. 引用图表(如图1所示)
7. 客观陈述，不解释原因（留给讨论）

数据发现（包括显著和不显著的）:
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
        生成 Discussion 章节（分段生成避免超时）。
        拆成3个小prompt：概述+季节讨论、相关性+机制、局限性+意义。
        """
        findings_text = self._summarize_findings(findings)
        mech_text = self._format_mechanisms(mechanisms)
        refs_text = self._format_references(recalled_refs)

        # 分离不同类型的发现
        seasonal = [f for f in findings if f.get('type') == 'group_difference'][:4]
        corr = [f for f in findings if f.get('type') == 'correlation'][:4]
        seasonal_text = self._summarize_findings(seasonal)
        corr_text = self._summarize_findings(corr)

        parts = []

        # 第1段：概述 + 季节差异讨论
        if language == "zh":
            prompt1 = f"""写{domain}论文讨论的前半部分(800-1200字)。

## 4.1 主要发现概述
用1-2段话总结研究的核心发现。

## 4.2 季节差异分析
对每个季节差异给出机制解释。

季节差异发现:
{seasonal_text}

{refs_text}

直接输出正文，用 ## 标记。"""
        else:
            prompt1 = f"""Write Discussion part 1 (600-1000 words) for {domain}.

## 4.1 Overview of main findings
## 4.2 Seasonal difference analysis

Seasonal findings:
{seasonal_text}

{refs_text}

Write directly."""

        part1 = self._call_claude(prompt1)
        if part1:
            parts.append(part1)
            logger.info(f"Discussion Part1: {len(part1)} 字")

        # 第2段：相关性 + 机制讨论
        if language == "zh":
            prompt2 = f"""写{domain}论文讨论的后半部分(600-1000字)。

## 4.3 相关性与机制分析
对重要相关关系给出机制解释。

相关性发现:
{corr_text}

{mech_text}

直接输出正文，用 ## 标记。"""
        else:
            prompt2 = f"""Write Discussion part 2 (500-800 words) for {domain}.

## 4.3 Correlation and mechanism analysis

Correlation findings:
{corr_text}

{mech_text}

Write directly."""

        part2 = self._call_claude(prompt2)
        if part2:
            parts.append(part2)
            logger.info(f"Discussion Part2: {len(part2)} 字")

        # 第3段：局限性 + 意义
        if language == "zh":
            prompt3 = f"""写{domain}论文讨论的结尾部分(300-500字)。

## 4.4 研究意义
本研究的科学价值和实际应用价值。

## 4.5 研究局限性
列出2-3条具体的局限性。

直接输出正文，用 ## 标记。"""
        else:
            prompt3 = f"""Write Discussion ending (200-400 words) for {domain}.

## 4.4 Significance
## 4.5 Limitations

Write directly."""

        part3 = self._call_claude(prompt3)
        if part3:
            parts.append(part3)
            logger.info(f"Discussion Part3: {len(part3)} 字")

        if not parts:
            logger.warning("Claude 生成 Discussion 全部失败")
            return ""

        result = '\n\n'.join(parts)
        logger.info(f"Discussion 总计: {len(result)} 字 ({len(parts)} 段)")
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
        """基于实际章节内容生成 Abstract（精简prompt避免超时）"""
        # 只取关键数据点，不取全文
        results_summary = self._extract_key_stats(sections.get('results', ''))

        if language == "zh":
            prompt = f"""写{domain}论文摘要(250-350字)。

结构：目的→方法→结果→结论
结果必须包含关键数据。最后列5-8个关键词。

关键数据:
{results_summary}

直接输出：
【摘要】(正文)
【关键词】(列表)"""
        else:
            prompt = f"""Write abstract (200-250 words) for {domain} paper.

Structure: Objective->Methods->Results->Conclusions
Include key stats. End with 5-8 keywords.

Key data:
{results_summary}

Write directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Abstract 失败")
            return ""
        logger.info(f"Abstract: Claude 生成 {len(result)} 字")
        return result

    def _extract_key_stats(self, text: str) -> str:
        """从结果文本中提取关键统计值（用于精简prompt）"""
        import re
        lines = []
        # 提取包含数字的关键行
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 包含 r=, p=, CV=, 均值, 显著 等关键信息的行
            if any(k in line for k in ['r=', 'p=', 'CV=', '均值', '显著', '相关', '冬季', '春季', '***', '**']):
                lines.append(line[:100])
            if len(lines) >= 15:
                break
        return '\n'.join(lines) if lines else text[:500]

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
        """将 findings 列表转为可读文本摘要 — 包括不显著的结果"""
        if not findings:
            return "暂无数据分析发现。"
        # 按类型分组
        correlations = [f for f in findings if f.get('type') == 'correlation']
        group_diffs = [f for f in findings if f.get('type') == 'group_difference']
        anomalies = [f for f in findings if f.get('type') == 'anomaly_story']
        others = [f for f in findings if f.get('type') not in ('correlation', 'group_difference', 'anomaly_story')]

        lines = []

        # 相关性：按显著性排序
        if correlations:
            sig = [f for f in correlations if f.get('data', {}).get('p', 1) < 0.05]
            near = [f for f in correlations if 0.05 <= f.get('data', {}).get('p', 1) < 0.10]
            ns = [f for f in correlations if f.get('data', {}).get('p', 1) >= 0.10 and f.get('data', {}).get('effect_size', 0) > 0.3]
            lines.append(f'[相关性] 显著{len(sig)}组, 接近显著{len(near)}组, 大效应不显著{len(ns)}组')
            for f in sig[:5]:
                lines.append(f'  显著: {f.get("detail", "")}')
            for f in near[:3]:
                lines.append(f'  接近显著: {f.get("detail", "")}')
            for f in ns[:2]:
                lines.append(f'  大效应: {f.get("detail", "")}')

        # 组间差异
        if group_diffs:
            sig = [f for f in group_diffs if f.get('data', {}).get('p', 1) < 0.05]
            near = [f for f in group_diffs if 0.05 <= f.get('data', {}).get('p', 1) < 0.10]
            big_d = [f for f in group_diffs if f.get('data', {}).get('cohens_d', 0) > 0.8]
            lines.append(f'[组间差异] 显著{len(sig)}个, 接近显著{len(near)}个, 大效应量{len(big_d)}个')
            for f in sig[:5]:
                detail = f.get('detail', '')
                lines.append(f'  显著: {detail}')
            for f in near[:3]:
                detail = f.get('detail', '')
                lines.append(f'  接近显著: {detail}')

        # 异常值故事
        if anomalies:
            lines.append(f'[异常值故事] {len(anomalies)}个')
            for f in anomalies[:5]:
                detail = f.get('detail', '')
                lines.append(f'  {detail}')
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
