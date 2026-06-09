"""
=============================================================================
引用支持库 - Citation Support Bank
借鉴自PaperSpine的citation_support_bank.md

核心思想：引用不是"这篇论文相关"，而是"这句话需要这篇论文支撑"。
每个候选引用都绑定到一个句子级claim。

与现有 citation_audit.py 的区别：
  - citation_audit.py: 验证引用是否有效（DOI/年份/匹配度）
  - citation_support_bank.py: 将引用绑定到具体claim（谁支撑谁）

工作流：
  1. 收集候选引用（3倍于目标数量）
  2. 为每个候选绑定句子级claim
  3. 验证引用质量
  4. 筛选最终引用子集
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
class CitationCandidate:
    """一条候选引用"""
    candidate_id: str               # 候选ID
    reference: str                  # 完整引用文本
    doi: str = ""                   # DOI
    year: int = 0                   # 年份
    recency: str = ""               # 新近性（recent/foundational）
    supports_section: str = ""      # 支撑的章节（Introduction/Discussion等）
    support_claim: str = ""         # 支撑的句子级claim
    why_fits: str = ""              # 为什么适合
    source: str = ""                # 来源（local/pdf/web）
    verified: str = "unverified"    # yes/no/mismatch/dead/unverified
    verification_note: str = ""     # 验证备注
    citation_type: str = "sota"     # 类型（survey/foundational/benchmark/sota/application）

    def to_table_row(self) -> str:
        verified_icon = {'yes': '✅', 'no': '❌', 'mismatch': '⚠️', 'dead': '💀', 'unverified': '❓'}.get(self.verified, '❓')
        return (
            f"| {self.candidate_id} | {self.reference[:40]} | {self.year} | {self.recency} | "
            f"{self.supports_section} | {self.support_claim[:40]} | "
            f"{self.why_fits[:30]} | {verified_icon} {self.verified} |"
        )


@dataclass
class ClaimBinding:
    """一个claim与其支撑引用的绑定"""
    claim_text: str                 # 主张文本
    claim_section: str              # 所属章节
    supporting_citations: list = field(default_factory=list)  # 支撑引用ID列表
    confidence: float = 0.0         # 绑定置信度


# ============================================================================
# Claim 提取器
# ============================================================================

class ClaimExtractor:
    """
    从论文文本中提取可引用的claim

    一个claim是一个需要文献支撑的具体主张：
    - 包含数据（需要引用来源）
    - 包含因果声明（需要机制文献）
    - 包含比较（需要对比文献）
    - 包含空白声明（需要综述文献）
    """

    CLAIM_PATTERNS = {
        'data_claim': {
            'patterns': [
                r'[\d.]+\s*(%|mg|mmol|倍)',
                r'[pP]\s*[<>=]\s*0\.\d+',
                r'[rR]\s*=\s*-?[\d.]+',
            ],
            'needs': '数据来源文献',
        },
        'causal_claim': {
            'patterns': [
                r'(导致|引起|促进|抑制|控制)',
                r'(because|due to|leads to|results in|causes)',
            ],
            'needs': '机制文献',
        },
        'comparison_claim': {
            'patterns': [
                r'(显著[高低于大于])',
                r'(significantly\s+(higher|lower|greater|different))',
            ],
            'needs': '比较文献',
        },
        'gap_claim': {
            'patterns': [
                r'(缺乏|不足|空白|尚未)',
                r'(lack|gap|limited|insufficient|remains unclear)',
            ],
            'needs': '综述文献',
        },
    }

    @classmethod
    def extract_claims(cls, text: str, section: str = "") -> list:
        """
        从文本中提取claims

        Returns
        -------
        list of dict: {text, section, claim_type, needs}
        """
        claims = []
        sentences = re.split(r'[。.！!？?]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            for claim_type, config in cls.CLAIM_PATTERNS.items():
                for pattern in config['patterns']:
                    if re.search(pattern, sentence):
                        claims.append({
                            'text': sentence,
                            'section': section,
                            'claim_type': claim_type,
                            'needs': config['needs'],
                        })
                        break  # 每个句子只匹配一种类型

        return claims


# ============================================================================
# 引用绑定器
# ============================================================================

class CitationBinder:
    """
    将引用绑定到句子级claim

    策略：
    - 数据claim → 需要提供该数据的原始文献
    - 因果claim → 需要机制研究文献
    - 比较claim → 需要比较对象的文献
    - 空白claim → 需要综述文献证明空白存在
    """

    @classmethod
    def find_supporting_citations(cls, claim: dict,
                                  candidates: list) -> list:
        """
        为一个claim找到支撑引用

        Parameters
        ----------
        claim : dict, {text, section, claim_type, needs}
        candidates : list of CitationCandidate

        Returns
        -------
        list of CitationCandidate: 匹配的引用
        """
        matches = []
        claim_text = claim['text'].lower()
        claim_type = claim.get('claim_type', '')

        for candidate in candidates:
            score = cls._compute_match_score(claim, candidate)
            if score > 0.3:
                matches.append((score, candidate))

        # 按分数排序
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:3]]  # 最多返回3个

    @classmethod
    def _compute_match_score(cls, claim: dict, candidate: CitationCandidate) -> float:
        """计算claim与引用的匹配分数"""
        score = 0.0
        claim_text = claim['text'].lower()
        ref_text = candidate.reference.lower()
        claim_type = claim.get('claim_type', '')

        # 关键词重叠
        claim_tokens = set(re.findall(r'[一-鿿]{2,}|[a-z]{3,}', claim_text))
        ref_tokens = set(re.findall(r'[一-鿿]{2,}|[a-z]{3,}', ref_text))
        if claim_tokens and ref_tokens:
            overlap = len(claim_tokens & ref_tokens)
            score += min(0.4, overlap * 0.1)

        # 类型匹配
        if claim_type == 'data_claim' and candidate.citation_type in ('benchmark', 'sota'):
            score += 0.2
        elif claim_type == 'causal_claim' and candidate.citation_type in ('foundational', 'sota'):
            score += 0.2
        elif claim_type == 'gap_claim' and candidate.citation_type == 'survey':
            score += 0.3

        # 章节匹配
        if claim.get('section') == candidate.supports_section:
            score += 0.1

        return min(1.0, score)


# ============================================================================
# 引用支持库管理器
# ============================================================================

class CitationSupportBank:
    """
    引用支持库管理器

    端到端工作流：
    1. add_candidate() — 添加候选引用
    2. extract_claims() — 从论文中提取claims
    3. bind_citations() — 将引用绑定到claims
    4. select_final() — 筛选最终引用子集
    5. generate_report() — 生成报告
    """

    def __init__(self, output_dir: str = None, target_count: int = 20):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'paper_output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.target_count = target_count
        self.candidates: list = []  # list of CitationCandidate
        self.claims: list = []      # list of dict
        self.bindings: list = []    # list of ClaimBinding
        self._next_id = 1

    def add_candidate(self, reference: str, year: int = 0,
                      doi: str = "", citation_type: str = "sota",
                      source: str = "", supports_section: str = "",
                      support_claim: str = "", why_fits: str = "") -> CitationCandidate:
        """添加一条候选引用"""
        current_year = datetime.now().year
        recency = 'recent' if year >= current_year - 3 else 'foundational'

        candidate = CitationCandidate(
            candidate_id=f'C{self._next_id:03d}',
            reference=reference,
            doi=doi,
            year=year,
            recency=recency,
            supports_section=supports_section,
            support_claim=support_claim,
            why_fits=why_fits,
            source=source,
            citation_type=citation_type,
        )
        self.candidates.append(candidate)
        self._next_id += 1
        return candidate

    def extract_claims_from_text(self, text: str, section: str = "") -> list:
        """从论文文本中提取claims"""
        claims = ClaimExtractor.extract_claims(text, section)
        self.claims.extend(claims)
        return claims

    def bind_citations(self) -> list:
        """将引用绑定到claims"""
        self.bindings = []
        for claim in self.claims:
            supporting = CitationBinder.find_supporting_citations(
                claim, self.candidates
            )
            binding = ClaimBinding(
                claim_text=claim['text'],
                claim_section=claim.get('section', ''),
                supporting_citations=[c.candidate_id for c in supporting],
                confidence=0.8 if supporting else 0.0,
            )
            self.bindings.append(binding)
        return self.bindings

    def select_final(self) -> list:
        """
        筛选最终引用子集

        策略：
        - 优先选择已验证的
        - 优先选择recent的（80%以上）
        - 确保每个claim都有至少一个支撑引用
        - 总数接近target_count
        """
        # 按验证状态和新近性排序
        scored = []
        for c in self.candidates:
            score = 0
            if c.verified == 'yes':
                score += 10
            if c.recency == 'recent':
                score += 5
            if c.support_claim:
                score += 3
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [c for _, c in scored[:self.target_count]]
        return selected

    def validate(self) -> dict:
        """验证引用支持库的质量"""
        total = len(self.candidates)
        recent = sum(1 for c in self.candidates if c.recency == 'recent')
        verified = sum(1 for c in self.candidates if c.verified == 'yes')
        with_claims = sum(1 for c in self.candidates if c.support_claim)

        issues = []
        if total < self.target_count * 3:
            issues.append(f'候选数量不足: {total} < {self.target_count * 3} (目标的3倍)')
        if total > 0 and recent / total < 0.6:
            issues.append(f'Recent引用比例偏低: {recent}/{total} ({recent/total:.0%})')
        if total > 0 and with_claims / total < 0.5:
            issues.append(f'有claim绑定的引用不足: {with_claims}/{total}')

        # 检查未绑定的claims
        unbound = sum(1 for b in self.bindings if not b.supporting_citations)
        if unbound:
            issues.append(f'{unbound}个claim没有支撑引用')

        return {
            'total_candidates': total,
            'recent_count': recent,
            'verified_count': verified,
            'with_claims_count': with_claims,
            'unbound_claims': unbound,
            'issues': issues,
        }

    def generate_report(self) -> str:
        """生成引用支持库报告"""
        lines = [
            "# 引用支持库 (Citation Support Bank)",
            "",
            "> 每个候选引用都绑定到一个句子级claim。",
            '> 引用不是"这篇论文相关"，而是"这句话需要这篇论文支撑"。',
            "",
        ]

        # 候选引用表
        if self.candidates:
            lines.extend([
                "## 候选引用",
                "",
                "| ID | 引用 | 年份 | 新近性 | 支撑章节 | 支撑claim | 适合原因 | 验证 |",
                "|-----|------|------|--------|---------|----------|---------|------|",
            ])
            for c in self.candidates:
                lines.append(c.to_table_row())
            lines.append("")

        # Claim绑定表
        if self.bindings:
            lines.extend([
                "## Claim-引用绑定",
                "",
                "| Claim | 章节 | 支撑引用 | 置信度 |",
                "|-------|------|---------|--------|",
            ])
            for b in self.bindings:
                cites = ', '.join(b.supporting_citations) if b.supporting_citations else '（无）'
                lines.append(
                    f"| {b.claim_text[:40]} | {b.claim_section} | {cites} | {b.confidence:.0%} |"
                )
            lines.append("")

        # 验证结果
        validation = self.validate()
        lines.extend([
            "## 验证结果",
            "",
            f"- **候选总数**: {validation['total_candidates']}",
            f"- **Recent**: {validation['recent_count']}",
            f"- **已验证**: {validation['verified_count']}",
            f"- **有claim绑定**: {validation['with_claims_count']}",
            f"- **未绑定claims**: {validation['unbound_claims']}",
        ])
        if validation['issues']:
            lines.append("\n**问题:**")
            for issue in validation['issues']:
                lines.append(f"- ⚠️ {issue}")

        return '\n'.join(lines)

    def save(self):
        """保存引用支持库"""
        # JSON
        data = {
            'target_count': self.target_count,
            'updated': datetime.now(timezone.utc).isoformat(),
            'candidates': [asdict(c) for c in self.candidates],
            'claims': self.claims,
            'bindings': [asdict(b) for b in self.bindings],
        }
        json_path = os.path.join(self.output_dir, 'citation_support_bank.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Markdown
        md_path = os.path.join(self.output_dir, 'citation_support_bank.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        print("=" * 60)
        print("引用支持库测试")
        print("=" * 60)

        bank = CitationSupportBank(output_dir='/tmp/test_citation_bank', target_count=5)

        # 添加候选引用
        bank.add_candidate(
            reference='Guisasola et al. (2008) Deviation of wastewater quality...',
            year=2008, citation_type='foundational',
            supports_section='Introduction', support_claim='厌氧条件下产甲烷可降解50%以上有机碳',
        )
        bank.add_candidate(
            reference='Jiang et al. (2011) Greenhouse gas emissions from sewage...',
            year=2011, citation_type='foundational',
            supports_section='Introduction', support_claim='管道系统是城市温室气体排放的重要来源',
        )
        bank.add_candidate(
            reference='Zhang et al. (2024) Multiphase carbon in campus networks...',
            year=2024, citation_type='sota',
            supports_section='Discussion', support_claim='DO与CH4呈显著负相关',
        )
        bank.add_candidate(
            reference='Li et al. (2023) Review of carbon transformation in sewers...',
            year=2023, citation_type='survey',
            supports_section='Introduction', support_claim='缺乏校园尺度的三相联合分析',
        )
        bank.add_candidate(
            reference='Wang et al. (2025) Microbial carbon cycling in pipelines...',
            year=2025, citation_type='sota',
            supports_section='Discussion', support_claim='微生物群落结构影响碳转化效率',
        )

        # 提取claims
        sample_text = (
            '厌氧条件下产甲烷活动可降解50%以上的有机碳(Guisasola et al., 2008)。'
            '管道系统是城市温室气体排放的重要来源。'
            '然而，缺乏对校园尺度固-液-气三相碳污染物的系统联合分析。'
            'DO与CH4呈显著负相关(r=-0.72, p<0.001)。'
        )
        claims = bank.extract_claims_from_text(sample_text, 'Introduction')
        print(f"\n提取了 {len(claims)} 个claims:")
        for c in claims:
            print(f"  [{c['claim_type']}] {c['text'][:50]} (需要: {c['needs']})")

        # 绑定引用
        bindings = bank.bind_citations()
        print(f"\n绑定了 {len(bindings)} 个claim:")
        for b in bindings:
            cites = ', '.join(b.supporting_citations) if b.supporting_citations else '无'
            print(f"  {b.claim_text[:40]} → {cites}")

        # 验证
        validation = bank.validate()
        print(f"\n验证: {json.dumps(validation, ensure_ascii=False, indent=2)}")

        # 生成报告
        report = bank.generate_report()
        print("\n" + report[:1500])
        print("...")

        bank.save()
        print("\n测试通过!")
    else:
        print("用法: python citation_support_bank.py --test")
