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

DEFAULT_TIMEOUT = 600


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
        # 安全改进：不再全局禁用 SSL 验证
        # 如果确实需要禁用 SSL，应该通过配置文件或环境变量显式设置
        # os.environ['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'  # 已移除

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

    def _sanitize_prompt(self, prompt: str) -> str:
        """
        清理 prompt，移除潜在的注入风险

        Parameters
        ----------
        prompt : str, 原始 prompt

        Returns
        -------
        str : 清理后的 prompt
        """
        import re
        # 移除可能导致命令注入的字符
        # 保留基本的标点和换行符
        sanitized = prompt
        # 移除控制字符（保留换行和制表符）
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', sanitized)
        # 限制长度，避免过长的 prompt
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + '...'
            logger.warning(f"Prompt 过长，已截断到 {max_length} 字符")
        return sanitized

    def _clean_output(self, text: str) -> str:
        """清理 Claude 输出中的元评论和残留"""
        if not text:
            return text
        import re

        lines = text.split('\n')
        clean = []

        for line in lines:
            s = line.strip()

            # 跳过元评论行（只跳过该行，不影响后续）
            is_meta = False

            # 检查元评论模式
            meta_starts = [
                '以下是为您', '以上为', '我已仔细', '请授权', '文件写入需要',
                'I have all', 'Since file writing', 'Please authorize',
                '后续部分规划', '全文约', '数据均取自实际',
                '包含以下逻辑', '补充了具体', '各claim均有', '解决了原版',
                '引言结构说明', '建议的改进优先', '需要重点改进',
                '论文现状评估', '已完成的工作', '论文框架基本', '数据基础扎实',
                '我们可以讨论', '您可以复制',
            ]
            if any(s.startswith(p) for p in meta_starts):
                is_meta = True

            # 检查 "第X部分" 模式
            if re.match(r'^第\d部分[：:]', s):
                is_meta = True

            # 检查英文元评论
            if re.match(r'^(I have all|Since file|Please authorize|Here is the|The following is)', s):
                is_meta = True

            # 检查交互式文字（短行）
            if len(s) < 30 and re.match(r'^(如需调整|请告知|如有需要|若有需要|如有疑问)', s):
                is_meta = True

            # 检查 "如上所述" 等（但不包括 "如图X所示" 等正常学术用语）
            if re.match(r'^(如上所述|如前所述|以上分析)', s) and len(s) < 30:
                is_meta = True

            if not is_meta:
                clean.append(line)

        result = '\n'.join(clean)
        # 移除连续空行
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        return result.strip()

    def _replace_figure_refs(self, text: str, figures: dict) -> str:
        """将图X占位符替换为实际图号"""
        if not text or not figures:
            return text
        import re

        # 建立 caption -> fig_num 映射
        fig_map = {}
        for name, info in figures.items():
            fig_num = info.get('fig_num', '')
            caption = info.get('caption', '')
            if fig_num:
                fig_map[name] = str(fig_num)
                # 也按关键词映射
                if 'boxplot' in name or '箱线' in caption:
                    fig_map['箱线图'] = str(fig_num)
                if 'heatmap' in name or '热图' in caption or '相关' in caption:
                    fig_map['热图'] = str(fig_num)
                if 'spatial' in name or '空间' in caption:
                    fig_map['空间分布'] = str(fig_num)
                if 'comparison' in name or '对比' in caption:
                    fig_map['对比'] = str(fig_num)
                if 'phase' in name or '耦合' in caption:
                    fig_map['耦合'] = str(fig_num)
                if 'anomaly' in name or '异常' in caption:
                    fig_map['异常'] = str(fig_num)
                if 'cluster' in name or '聚类' in caption:
                    fig_map['聚类'] = str(fig_num)

        # 替换 "图X" 为实际图号（按出现顺序）
        fig_nums = sorted(set(info.get('fig_num', '') for info in figures.values() if info.get('fig_num')))
        fig_idx = 0

        def replace_fig_x(match):
            nonlocal fig_idx
            if fig_idx < len(fig_nums):
                num = fig_nums[fig_idx]
                fig_idx += 1
                return f'图{num}'
            return match.group(0)

        result = re.sub(r'图X', replace_fig_x, text)

        # 替换 "表X" 为表号（从1开始）
        table_idx = [1]
        def replace_table_x(match):
            num = table_idx[0]
            table_idx[0] += 1
            return f'表{num}'

        result = re.sub(r'表X', replace_table_x, result)

        return result

    def _call_claude(self, prompt: str) -> str:
        """调用 Claude CLI 生成文本"""
        # 清理 prompt
        prompt = self._sanitize_prompt(prompt)

        # 自动查找 claude CLI 路径
        claude_cmd = "claude"
        # Windows: 优先使用批处理包装器
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
            # 安全改进：使用完整的可执行路径，避免 shell=True
            # 对于 Windows，使用完整路径可以避免命令注入风险
            env = os.environ.copy()

            # 安全改进：不再全局禁用 SSL 验证
            # 如果确实需要，可以通过配置文件设置
            # env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

            # 安全改进：避免 shell=True，使用完整可执行路径
            # 对于 .cmd 文件，需要通过 cmd.exe 调用
            is_windows = os.name == 'nt'
            if is_windows and claude_cmd.endswith('.cmd'):
                # Windows .cmd 文件需要通过 cmd.exe 调用
                cmd = ['cmd', '/c'] + cmd

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, encoding='utf-8', errors='replace',
                env=env,
                shell=False,  # 安全改进：不使用 shell=True
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
3. 报告显著结果(p<0.05)和接近显著(0.05<p<0.10)
4. 引用图表(如图1所示)
5. 客观陈述，不解释原因

数据发现:
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
        result = self._clean_output(result)
        logger.info(f"Results: Claude 生成 {len(result)} 字")
        return result

    def write_results_discussion(self, findings: list, mechanisms: dict = None,
                                  domain: str = "污水管网碳排放", language: str = "zh",
                                  recalled_refs: list = None,
                                  learned_patterns: dict = None,
                                  injection_context: str = None,
                                  figures: dict = None) -> str:
        """
        生成结果与讨论交织的章节（单次生成，避免多段式空小节问题）
        """
        findings_text = self._summarize_findings(findings)
        mech_text = self._format_mechanisms(mechanisms)
        refs_text = self._format_references(recalled_refs)

        # 分离不同类型的发现
        seasonal = [f for f in findings if f.get('type') == 'group_difference'][:6]
        corr = [f for f in findings if f.get('type') == 'correlation'][:6]
        distribution = [f for f in findings if f.get('type') == 'distribution'][:4]
        anomaly = [f for f in findings if f.get('type') == 'anomaly_story'][:3]

        seasonal_text = self._summarize_findings(seasonal)
        corr_text = self._summarize_findings(corr)
        distribution_text = self._summarize_findings(distribution)
        anomaly_text = self._summarize_findings(anomaly)

        # 构建注入上下文
        injection_hint = ""
        if injection_context:
            injection_hint = f"\n\n【补充分析结果】\n{injection_context}"

        # 构建图片提示
        figures_hint = ""
        if figures:
            fig_list = []
            for name, info in figures.items():
                caption = info.get('caption', '')
                fig_num = info.get('fig_num', '')
                if caption:
                    fig_list.append(f"图{fig_num}: {caption}")
            if fig_list:
                figures_hint = "\n\n【可用图片】\n" + "\n".join(fig_list[:9])

        # 单次生成完整结果与讨论章节
        if language == "zh":
            prompt = f"""你是学术论文写作引擎。直接输出论文正文，禁止任何元评论。

写{domain}论文的"结果与分析"章节，必须包含以下所有子章节，每个子章节必须有实质内容（不能只有标题）：

## 3.1 气相碳污染物分布特征
- 描述CH4、CO2、VOCs等气相碳污染物的分布特征（均值、标准差、CV%）
- 引用图片（如"如图1所示"）
- 讨论分布特征的机制原因
- 引用文献支撑

## 3.2 季节差异分析
- 描述冬春季节的差异数据（均值、p值、效应量d）
- 讨论季节差异的机制（温度、水文等）
- 引用文献支撑

## 3.3 多变量相关性分析
- 描述关键相关性结果（r值、p值、样本量n）
- 引用相关性热图
- 讨论相关性的机制意义

## 3.4 固相碳赋存特征与多相态碳分布
- 描述固相碳的赋存特征
- 描述三相碳的分布格局
- 讨论碳在不同相态间的迁移机制

## 3.5 回归分析
- 描述TOC、DO、COD、pH等与CH4的回归关系
- 讨论回归结果的环境意义

## 3.6 碳平衡分析
- 描述三相碳含量分布特征
- 分析碳在三相中的分配比例
- 讨论季节对碳分配的影响

写作规则：
1. 每个 ## 标题下必须有至少3段正文内容
2. 所有数据必须包含具体数值（均值、标准差、p值、r值等）
3. 引用图片用"如图X所示"格式
4. 引用文献用[1]格式
5. 每个发现都要有机制解释

禁止输出：
- 不要写"以下是"、"以上为"等元评论
- 不要写"如需调整"、"请告知"等交互文字
- 不要写"I have"、"Since"等英文元评论
- 不要写"第X部分"、"后续规划"等说明
- 不要写"小节)"、"5个小节"等规划文字
- 只输出论文正文

【数据发现】
{seasonal_text}

{corr_text}

{distribution_text}

{anomaly_text}

{injection_hint}

{refs_text}
{mech_text}
{figures_hint}

直接输出完整正文，用 ## 标记子章节。"""
        else:
            prompt = f"""Write the complete Results & Discussion section for {domain}.

Include all subsections with substantial content under each heading.

Write directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Results-Discussion 失败")
            return ""

        # 清洗输出
        result = self._clean_output(result)

        # 替换图表引用占位符
        result = self._replace_figure_refs(result, figures)

        logger.info(f"Results-Discussion 总计: {len(result)} 字")
        return result

    def write_discussion(self, findings: list, mechanisms: dict = None,
                         domain: str = "污水管网碳排放", language: str = "zh",
                         recalled_refs: list = None,
                         learned_patterns: dict = None,
                         injection_context: str = None) -> str:
        """
        生成 Discussion 章节（单次生成，避免空小节问题）
        """
        findings_text = self._summarize_findings(findings)
        mech_text = self._format_mechanisms(mechanisms)
        refs_text = self._format_references(recalled_refs)

        # 分离不同类型的发现
        seasonal = [f for f in findings if f.get('type') == 'group_difference'][:6]
        corr = [f for f in findings if f.get('type') == 'correlation'][:6]
        seasonal_text = self._summarize_findings(seasonal)
        corr_text = self._summarize_findings(corr)

        # 构建注入上下文
        injection_hint = ""
        if injection_context:
            injection_hint = f"\n\n【补充分析结果】\n{injection_context}"

        # 单次生成完整讨论章节
        if language == "zh":
            prompt = f"""你是学术论文写作引擎。直接输出论文正文，禁止任何元评论。

写{domain}论文的"讨论"章节，必须包含以下所有子章节，每个子章节必须有实质内容：

## 4.1 主要发现概述
用1-2段话总结研究的核心发现。

## 4.2 季节差异分析
对每个季节差异给出机制解释，引用文献支撑。

## 4.3 相关性与机制分析
对重要相关关系给出机制解释。

## 4.4 研究意义
本研究的科学价值和实际应用价值。

## 4.5 研究局限性
列出2-3条具体的局限性。

写作规则：
1. 每个 ## 标题下必须有至少2段正文内容
2. 每个机制解释必须引用1-2篇文献（用[1]格式）
3. 使用 [数字] 格式引用文献
4. 直接输出正文，用 ## 标记子章节

禁止输出：不要写元评论、交互文字、英文说明。只输出论文正文。

季节差异发现:
{seasonal_text}

相关性发现:
{corr_text}

{injection_hint}

{refs_text}
{mech_text}

直接输出完整正文，用 ## 标记子章节。"""
        else:
            prompt = f"""Write the complete Discussion section for {domain}.

Include all subsections with substantial content.

Findings:
{seasonal_text}

{corr_text}

{refs_text}
{mech_text}

Write directly."""

        result = self._call_claude(prompt)
        if not result:
            logger.warning("Claude 生成 Discussion 失败")
            return ""

        # 清洗输出
        result = self._clean_output(result)

        logger.info(f"Discussion 总计: {len(result)} 字")
        return result

    def write_introduction(self, findings: list, domain: str = "污水管网碳排放",
                           language: str = "zh", recalled_refs: list = None,
                           learned_patterns: dict = None,
                           motivation_context: str = None) -> str:
        """生成 Introduction 章节"""
        findings_text = self._summarize_findings(findings)
        refs_text = self._format_references(recalled_refs)
        patterns_hint = self._format_patterns_hint(learned_patterns, 'background')

        # 构建动机上下文
        motivation_hint = ""
        if motivation_context:
            motivation_hint = f"\n\n【研究动机】\n{motivation_context}\n\n请在引言中体现这些研究动机。"

        if language == "zh":
            prompt = f"""你是学术论文写作引擎。直接输出论文正文，禁止任何元评论。

撰写{domain}论文的"引言"章节，必须包含以下所有子章节，每个子章节必须有实质内容：

## 1.1 研究背景与意义
从全球→区域→具体问题递进，引用文献支撑。

## 1.2 国内外研究现状
综述已有研究，引用3-5篇文献。

## 1.3 现有研究不足
明确指出2-3个研究空白。

## 1.4 研究内容与目标
列出2-3个具体研究目标。

写作规则：
1. 每个 ## 标题下必须有至少2段正文内容
2. 引用3-5篇文献，使用 [数字] 格式
3. 用"本研究"不用"本文"
4. 倒三角结构：领域重要性 → 现有研究 → 不足 → 本文目标

禁止输出：不要写元评论、交互文字、英文说明、"以下是"、"以上为"、"第X部分"。只输出论文正文。

发现摘要:
{findings_text}

{refs_text}
{motivation_hint}

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
        result = self._clean_output(result)
        logger.info(f"Introduction: Claude 生成 {len(result)} 字")
        return result

    def write_abstract(self, sections: dict, domain: str = "污水管网碳排放",
                       language: str = "zh") -> str:
        """基于实际章节内容生成 Abstract（精简prompt避免超时）"""
        # 只取关键数据点，不取全文
        results_summary = self._extract_key_stats(sections.get('results', ''))

        if language == "zh":
            prompt = f"""写{domain}论文摘要，严格控制在300-400字。

结构：目的→方法→结果→结论
结果必须包含关键数据（3-5个具体数值）。最后列5-8个关键词。

关键数据:
{results_summary}

写作规则：
1. 严格控制在300-400字，不要超过400字
2. 必须包含具体数据（如 r=0.647, p=0.004）
3. 直接输出：
【摘要】(正文)
【关键词】(列表)

禁止输出：不要写元评论、交互文字、英文说明、"以下是"、"以上为"。只输出摘要正文。"""
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
        result = self._clean_output(result)
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

请根据以下数据分析发现，撰写"结论"章节。

要求：
1. 列出3-5条主要结论，每条用编号标注
2. 每条结论要包含具体数据支撑（如 r=0.647, p=0.004）
3. 最后指出研究的科学意义和实际应用价值
4. 语言精炼、有力
5. 不要重复摘要内容

数据分析发现:
{findings_text}

禁止输出：不要写元评论、交互文字、英文说明、"以下是"、"以上为"。只输出结论正文。

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
        result = self._clean_output(result)
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
            prompt = f"""你是学术论文写作引擎。直接输出论文正文，禁止任何元评论。

撰写{domain}论文的"材料与方法"章节（约1000-1500字），必须包含以下所有子章节：

## 2.1 研究区域概况
描述研究区域的基本情况。

## 2.2 采样方案
描述采样点设置、采样时间、采样方法。

## 2.3 分析方法
描述气相、液相、固相的分析方法，引用国家标准。

## 2.4 数据处理与统计分析
描述统计方法（Pearson相关、Mann-Whitney U、PCA、HCA等）。

写作规则：
1. 每个 ## 标题下必须有实质内容
2. 分析方法引用国家标准（如 TOC用HJ 501-2009，COD用GB 11914-89）
3. 统计方法要具体
4. 语言要让同行能复现实验

禁止输出：不要写元评论、交互文字、英文说明、"以下是"、"以上为"。只输出方法正文。
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
        result = self._clean_output(result)
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
        if result:
            result = self._clean_output(result)
        return result if result else text

    def enhance_introduction(self, intro_text: str, findings: list = None,
                             domain_config=None, language: str = 'zh') -> str:
        """
        增强引言：补充研究背景、研究空白、创新点，使引言更丰满有逻辑。

        Parameters
        ----------
        intro_text : str, 现有引言文本
        findings : list, 数据分析发现
        domain_config, 领域配置
        language : str, 语言

        Returns
        -------
        str, 增强后的引言
        """
        findings_hint = ""
        if findings:
            key_findings = self._summarize_findings(findings[:5])
            findings_hint = f"\n\n关键发现（用于引出研究意义）:\n{key_findings}"

        domain_hint = self._get_domain_context()

        prompt = f"""你是一位资深环境科学学术作者。请对以下引言进行扩写增强。

要求：
1. 保持原有核心内容和逻辑框架
2. 补充研究背景的广度（从全球→区域→具体问题）
3. 明确指出现有研究的空白/不足
4. 突出本研究的创新点和科学意义
5. 逻辑递进：大背景 → 具体问题 → 研究空白 → 本文目的
6. 学术语气，避免口语化
7. 字数扩写到原来的1.5-2倍
{domain_hint}
{findings_hint}

现有引言:
{intro_text}

请直接输出增强后的引言文本，不要加说明。"""

        result = self._call_claude(prompt)
        if result:
            result = self._clean_output(result)
        return result if result else intro_text

    def enhance_discussion(self, discussion_text: str, findings: list = None,
                           mechanisms: list = None, recalled_refs: list = None,
                           language: str = 'zh') -> str:
        """
        增强讨论：补充机制解释、文献对比、研究意义。

        Parameters
        ----------
        discussion_text : str, 现有讨论文本
        findings : list, 数据分析发现
        mechanisms : list, 学到的机制知识
        recalled_refs : list, 回忆的相关文献
        language : str, 语言

        Returns
        -------
        str, 增强后的讨论
        """
        findings_hint = ""
        if findings:
            key_findings = self._summarize_findings(findings[:5])
            findings_hint = f"\n\n关键发现:\n{key_findings}"

        mechanisms_hint = ""
        if mechanisms:
            mech_lines = []
            for m in mechanisms[:3]:
                if isinstance(m, dict):
                    mech_lines.append(f"- {m.get('description', str(m)[:150])}")
            if mech_lines:
                mechanisms_hint = "\n\n已知机制:\n" + '\n'.join(mech_lines)

        refs_hint = ""
        if recalled_refs:
            ref_lines = []
            for r in recalled_refs[:3]:
                if isinstance(r, dict):
                    ref_lines.append(f"- {r.get('title', str(r)[:100])}")
            if ref_lines:
                refs_hint = "\n\n可引用文献:\n" + '\n'.join(ref_lines)

        prompt = f"""你是一位资深环境科学学术作者。请对以下讨论部分进行扩写增强。

要求：
1. 保持原有核心分析和逻辑框架
2. 深入解释观测到的现象背后的机制
3. 与已有文献进行对比讨论（一致/不一致及原因）
4. 讨论研究的实践意义和政策启示
5. 客观承认研究局限性
6. 提出未来研究方向
7. 学术语气，逻辑严密
8. 字数扩写到原来的1.5-2倍
{findings_hint}
{mechanisms_hint}
{refs_hint}

现有讨论:
{discussion_text}

请直接输出增强后的讨论文本，不要加说明。"""

        result = self._call_claude(prompt)
        if result:
            result = self._clean_output(result)
        return result if result else discussion_text

    # ================================================================
    # 辅助格式化方法
    # ================================================================

    def _summarize_findings(self, findings: list) -> str:
        """将 findings 列表转为可读文本摘要 — 精简版，避免超时"""
        if not findings:
            return "暂无数据分析发现。"

        # 只取最重要的发现，严格限制数量
        critical = [f for f in findings if f.get('importance') == 'critical'][:3]
        high = [f for f in findings if f.get('importance') == 'high'][:3]
        anomaly = [f for f in findings if f.get('type') == 'anomaly_story'][:3]
        selected = critical + high + anomaly

        lines = []
        for f in selected:
            detail = f.get('detail', '')
            if detail:
                lines.append(f'- {detail[:100]}')

        # 添加统计摘要
        sig_count = len([f for f in findings if f.get('data', {}).get('p', 1) < 0.05])
        near_count = len([f for f in findings if 0.05 <= f.get('data', {}).get('p', 1) < 0.10])
        lines.append(f'总计: {sig_count}个显著, {near_count}个接近显著, {len(findings)}个发现')

        return '\n'.join(lines)
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
