"""
段落级写作引擎
==============
基于从论文中学到的表达模式和逻辑链，
生成学术逻辑性强的段落（而非模板填充）。

核心思想:
  每个段落 = 逻辑链 + 表达模式 + 数据填充

  不是: "把数据塞进模板"
  而是: "按逻辑链组织句子，用表达模式润色"

段落生成流程:
  1. 确定段落的逻辑目标（讨论什么发现）
  2. 选择逻辑链模式（数据→机制→文献）
  3. 用表达模式生成每个句子
  4. 添加逻辑过渡
  5. 调节论述强度
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── 论述强度等级 ──────────────────────────────────────────

class ClaimStrength:
    """
    论述强度调节器

    根据数据强度选择合适的措辞:
    - 强 (r>0.7, p<0.001): "明确表明"/"demonstrates"
    - 中 (r>0.5, p<0.01): "表明"/"indicates"
    - 弱 (r>0.3, p<0.05): "初步表明"/"suggests"
    - 推测: "可能"/"may"
    """

    ZH_LEVELS = {
        'strong': ['明确表明', '有力证实', '充分证明', '显著揭示'],
        'moderate': ['表明', '显示', '揭示', '证实'],
        'weak': ['初步表明', '可能反映', '暗示', '提示'],
        'speculative': ['可能', '或许', '推测', '有待验证'],
    }

    EN_LEVELS = {
        'strong': ['demonstrates', 'clearly indicates', 'firmly establishes', 'conclusively shows'],
        'moderate': ['indicates', 'suggests', 'reveals', 'shows'],
        'weak': ['may indicate', 'tentatively suggests', 'provides preliminary evidence'],
        'speculative': ['may', 'might', 'could potentially', 'remains to be verified'],
    }

    @classmethod
    def assess(cls, r_value=None, p_value=None, sample_size=None):
        """评估论述强度"""
        if r_value is not None and p_value is not None:
            if abs(r_value) > 0.7 and p_value < 0.001:
                return 'strong'
            elif abs(r_value) > 0.5 and p_value < 0.01:
                return 'moderate'
            elif abs(r_value) > 0.3 and p_value < 0.05:
                return 'weak'
        return 'speculative'

    @classmethod
    def get_phrase(cls, level, language='zh'):
        """获取对应强度的措辞"""
        import random
        levels = cls.ZH_LEVELS if language == 'zh' else cls.EN_LEVELS
        phrases = levels.get(level, levels['moderate'])
        return phrases[0]  # 默认取第一个


# ── 过渡句生成器 ──────────────────────────────────────────

class TransitionGenerator:
    """
    生成段落间的逻辑过渡句

    过渡类型:
    - 顺承: 此外/Moreover
    - 转折: 然而/However
    - 因果: 因此/Therefore
    - 对比: 与...不同/Unlike
    - 深化: 值得注意的是/Notably
    """

    ZH_TRANSITIONS = {
        'addition': [
            '此外，{content}',
            '另外，{content}',
            '同时，{content}',
        ],
        'contrast': [
            '然而，{content}',
            '但是，{content}',
            '尽管如此，{content}',
        ],
        'cause': [
            '因此，{content}',
            '由此可见，{content}',
            '基于上述分析，{content}',
        ],
        'comparison': [
            '与{reference}不同，{content}',
            '不同于{reference}，本研究发现{content}',
        ],
        'notable': [
            '值得注意的是，{content}',
            '特别值得关注的是，{content}',
        ],
    }

    EN_TRANSITIONS = {
        'addition': [
            'Furthermore, {content}',
            'Moreover, {content}',
            'In addition, {content}',
        ],
        'contrast': [
            'However, {content}',
            'Nevertheless, {content}',
            'In contrast, {content}',
        ],
        'cause': [
            'Therefore, {content}',
            'Consequently, {content}',
            'This suggests that {content}',
        ],
        'comparison': [
            'Unlike {reference}, {content}',
            'In contrast to {reference}, our study found that {content}',
        ],
        'notable': [
            'Notably, {content}',
            'It is worth noting that {content}',
        ],
    }

    @classmethod
    def generate(cls, transition_type, content, reference='', language='zh'):
        """生成过渡句"""
        import random
        templates = cls.ZH_TRANSITIONS if language == 'zh' else cls.EN_TRANSITIONS
        options = templates.get(transition_type, templates['addition'])
        template = random.choice(options)
        return template.format(content=content, reference=reference)


# ── 段落生成器 ──────────────────────────────────────────

class ParagraphGenerator:
    """
    段落级写作引擎

    根据逻辑链和表达模式生成学术段落，
    而非简单的模板填充。

    用法:
        gen = ParagraphGenerator(language='zh')

        # 生成 Discussion 段落
        para = gen.generate_discussion_paragraph(
            finding='TOC与CH4呈显著正相关',
            r_value=0.68,
            p_value=0.01,
            mechanism='有机碳为产甲烷提供底物',
            literature_ref='Guisasola等(2008)',
            literature_finding='类似正相关',
        )
    """

    def __init__(self, language='zh'):
        self.language = language

    def generate_discussion_paragraph(self, finding, r_value=None, p_value=None,
                                       mechanism='', literature_ref='',
                                       literature_finding='', additional_note=''):
        """
        生成一个 Discussion 段落

        逻辑链: 数据发现 → 机制解释 → 文献对比 → 补充说明

        Parameters
        ----------
        finding : str, 数据发现描述
        r_value : float, 相关系数
        p_value : float, p值
        mechanism : str, 机制解释
        literature_ref : str, 文献引用
        literature_finding : str, 文献中的发现
        additional_note : str, 补充说明
        """
        # 1. 评估论述强度
        strength = ClaimStrength.assess(r_value, p_value)
        claim_phrase = ClaimStrength.get_phrase(strength, self.language)

        # 2. 构建段落句子
        sentences = []

        # 句1: 数据发现（用强度调节的措辞）
        if self.language == 'zh':
            sent1 = self._build_claim_sentence_zh(
                finding, claim_phrase, r_value, p_value
            )
        else:
            sent1 = self._build_claim_sentence_en(
                finding, claim_phrase, r_value, p_value
            )
        sentences.append(sent1)

        # 句2: 机制解释
        if mechanism:
            if self.language == 'zh':
                sentences.append(f'{mechanism}。')
            else:
                sentences.append(f'{mechanism}.')

        # 句3: 文献对比
        if literature_ref:
            if self.language == 'zh':
                if literature_finding:
                    sentences.append(
                        f'本研究发现与{literature_ref}的研究结论一致，'
                        f'后者也报道了{literature_finding}。'
                    )
                else:
                    sentences.append(f'这一结果与{literature_ref}的研究结论一致。')
            else:
                if literature_finding:
                    sentences.append(
                        f'This finding is consistent with {literature_ref}, '
                        f'who also reported {literature_finding}.'
                    )
                else:
                    sentences.append(
                        f'This finding is consistent with the observations reported by {literature_ref}.'
                    )

        # 句4: 补充说明
        if additional_note:
            if self.language == 'zh':
                sentences.append(TransitionGenerator.generate(
                    'notable', additional_note, language='zh'
                ))
            else:
                sentences.append(TransitionGenerator.generate(
                    'notable', additional_note, language='en'
                ))

        return ' '.join(sentences)

    def generate_results_paragraph(self, variable, stats_data, group_col='季节'):
        """
        生成 Results 段落

        逻辑链: 描述统计 → 组间比较 → 显著性

        Parameters
        ----------
        variable : str, 变量名
        stats_data : dict, 统计数据 {mean, std, comparison, ...}
        """
        sentences = []

        if self.language == 'zh':
            # 描述统计
            if 'mean' in stats_data and 'std' in stats_data:
                sentences.append(
                    f'{variable}的总体均值为{stats_data["mean"]:.2f}'
                    f'±{stats_data["std"]:.2f}。'
                )

            # 组间比较
            if 'p_value' in stats_data:
                p = stats_data['p_value']
                if p < 0.05:
                    sig = '***' if p < 0.001 else ('**' if p < 0.01 else '*')
                    higher = stats_data.get('higher_group', '')
                    if higher:
                        sentences.append(
                            f'{variable}在{higher}显著高于另一季节({sig})。'
                        )
                else:
                    sentences.append(f'{variable}在两季节间无显著差异(n.s.)。')
        else:
            if 'mean' in stats_data and 'std' in stats_data:
                sentences.append(
                    f'The overall mean of {variable} was '
                    f'{stats_data["mean"]:.2f} +/- {stats_data["std"]:.2f}.'
                )
            if 'p_value' in stats_data:
                p = stats_data['p_value']
                if p < 0.05:
                    sig = '***' if p < 0.001 else ('**' if p < 0.01 else '*')
                    sentences.append(
                        f'A significant difference was observed between seasons ({sig}).'
                    )
                else:
                    sentences.append(f'No significant difference was found between seasons.')

        return ' '.join(sentences)

    def generate_transition(self, prev_topic, next_topic, transition_type='addition'):
        """生成段落间过渡句"""
        if self.language == 'zh':
            content = f'{prev_topic}的分析揭示了{next_topic}的关联'
            return TransitionGenerator.generate(transition_type, content, language='zh')
        else:
            content = f'the analysis of {prev_topic} reveals connections to {next_topic}'
            return TransitionGenerator.generate(transition_type, content, language='en')

    def _build_claim_sentence_zh(self, finding, claim_phrase, r_value, p_value):
        """构建中文主张句"""
        if r_value is not None and p_value is not None:
            p_str = f'p={p_value:.4f}' if p_value >= 0.001 else 'p<0.001'
            return f'{finding}({claim_phrase}，r={r_value:.3f}，{p_str})。'
        return f'{finding}({claim_phrase})。'

    def _build_claim_sentence_en(self, finding, claim_phrase, r_value, p_value):
        """构建英文主张句"""
        if r_value is not None and p_value is not None:
            p_str = f'p = {p_value:.4f}' if p_value >= 0.001 else 'p < 0.001'
            return f'{finding} ({claim_phrase}, r = {r_value:.3f}, {p_str}).'
        return f'{finding} ({claim_phrase}).'


# ── Discussion 完整段落组装器 ──────────────────────────────────────

class DiscussionAssembler:
    """
    Discussion 章节完整组装器

    基于数据故事线，用段落引擎逐段生成 Discussion，
    确保每段都有逻辑链支撑。
    """

    def __init__(self, analysis_results, language='zh'):
        self.results = analysis_results
        self.language = language
        self.generator = ParagraphGenerator(language)

    def assemble(self) -> str:
        """组装完整的 Discussion"""
        paragraphs = []

        # 段落1: 核心发现概述
        paragraphs.append(self._overview_paragraph())

        # 段落2-N: 逐个发现讨论
        paragraphs.extend(self._finding_paragraphs())

        # 碳平衡讨论
        paragraphs.append(self._carbon_balance_paragraph())

        # 局限性
        paragraphs.append(self._limitations_paragraph())

        # 展望
        paragraphs.append(self._future_paragraph())

        return '\n\n'.join(p for p in paragraphs if p)

    def _overview_paragraph(self):
        """核心发现概述"""
        if self.language == 'zh':
            findings = []
            if '描述统计' in self.results:
                findings.append('三相碳污染物的赋存特征')
            if '组间比较' in self.results:
                comp = self.results['组间比较']
                sig = comp[comp['显著性'] != 'n.s.']
                if len(sig) > 0:
                    findings.append(f'{len(sig)}个指标的冬春季节差异显著')
            if 'pearson相关' in self.results:
                findings.append('多指标间的显著相关关系')

            findings_str = '、'.join(findings) if findings else '数据特征'
            return (
                '## 4 讨论\n\n'
                f'本研究通过系统的采样分析和多元统计方法，揭示了校园污水管网中'
                f'固-液-气多相态碳污染物的赋存特征。主要发现包括：'
                f'{findings_str}。以下对各发现进行深入讨论。'
            )
        return ''

    def _finding_paragraphs(self):
        """逐个发现的讨论段落"""
        paragraphs = []

        # 从相关性分析中提取讨论点
        for method in ['pearson', 'spearman']:
            key = f'{method}相关'
            if key not in self.results:
                continue

            corr = self.results[key]['相关系数']
            pvals = self.results[key]['p值']

            discussed = 0
            for i in range(len(corr)):
                for j in range(i + 1, len(corr)):
                    r = corr.iloc[i, j]
                    p = pvals.iloc[i, j]
                    if abs(r) > 0.5 and p < 0.05:
                        var1 = corr.index[i]
                        var2 = corr.columns[j]
                        direction = '正' if r > 0 else '负'

                        # 用段落引擎生成
                        para = self.generator.generate_discussion_paragraph(
                            finding=f'{var1}与{var2}呈显著{direction}相关',
                            r_value=r,
                            p_value=p,
                            mechanism=self._suggest_mechanism(var1, var2),
                            literature_ref=self._find_literature(var1, var2),
                        )
                        paragraphs.append(para)
                        discussed += 1

                        if discussed >= 4:
                            break
                if discussed >= 4:
                    break

        return paragraphs

    def _carbon_balance_paragraph(self):
        """碳平衡讨论"""
        if '描述统计' not in self.results:
            return ''

        desc = self.results['描述统计']['总体']
        phase_data = {}
        for col in ['气相碳', '液相碳', '固相碳']:
            if col in desc.columns:
                phase_data[col] = desc.loc['mean', col]

        if len(phase_data) < 2:
            return ''

        total = sum(phase_data.values())
        if self.language == 'zh':
            parts = ['碳平衡分析揭示了碳在固-液-气三相之间的分配格局。']
            for phase, val in phase_data.items():
                pct = val / total * 100
                parts.append(f'{phase}占比{pct:.1f}%。')
            return ' '.join(parts)
        return ''

    def _limitations_paragraph(self):
        """局限性"""
        if self.language == 'zh':
            return (
                '### 4.5 研究局限性\n\n'
                '本研究存在以下局限性：\n\n'
                '（1）采样时间仅涵盖冬季和春季两个季节，未能覆盖夏秋季节。\n\n'
                '（2）采样频次有限，可能未能充分反映碳污染物的日变化特征。\n\n'
                '（3）未开展管道内微生物群落分析，对碳转化过程中的关键功能微生物缺乏直接证据。'
            )
        return ''

    def _future_paragraph(self):
        """展望"""
        if self.language == 'zh':
            return (
                '### 4.6 研究展望\n\n'
                '未来研究可从以下方面深入：\n\n'
                '（1）延长采样周期，覆盖四季变化。\n\n'
                '（2）结合高通量测序技术，分析管道微生物群落结构。\n\n'
                '（3）建立管道碳转化的动力学模型。'
            )
        return ''

    def _suggest_mechanism(self, var1, var2):
        """建议机制"""
        if 'DO' in var1 and 'CH4' in var2:
            return '溶解氧控制产甲烷过程：DO<0.5mg/L时产甲烷古菌活性最高'
        if 'TOC' in var1 and 'CH4' in var2:
            return 'TOC作为有机碳底物，浓度升高直接促进了产甲烷过程'
        return ''

    def _find_literature(self, var1, var2):
        """查找相关文献"""
        if 'DO' in var1 and 'CH4' in var2:
            return 'Guisasola等(2008)'
        if 'TOC' in var1 and 'CH4' in var2:
            return 'Jiang等(2011)'
        return ''
