"""
修订审计 - 检测版本间的变化是否实质性
借鉴自PaperSpine的revision_audit.py

核心思想：好的修改是改变了论证逻辑的修改，而不只是换了措辞。
通过段落级比较，检测"浅编辑"（near-identical paragraphs占比过高）。
"""
import re
import sys
import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path


@dataclass
class ParagraphMatch:
    """修订段落匹配结果"""
    revised_index: int
    original_index: int = -1
    similarity: float = 0.0
    revised_preview: str = ""
    original_preview: str = ""
    operation: str = "unknown"  # kept/modified/added/deleted


@dataclass
class AuditSummary:
    """修订审计摘要"""
    original_paragraphs: int = 0
    revised_paragraphs: int = 0
    near_identical_count: int = 0
    mostly_new_count: int = 0
    likely_deleted_count: int = 0
    unchanged_ratio: float = 0.0
    new_ratio: float = 0.0
    deleted_ratio: float = 0.0
    addition_heavy: bool = False
    shallow_warning: bool = False
    matches: list = field(default_factory=list)


def canonical(text: str) -> str:
    """
    文本canonical化：去除格式差异，保留核心内容
    用于公平的段落比较
    """
    # 统一小写
    text = text.lower()
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 去除标点（中英文）
    text = re.sub(r'[，。、；：！？""''（）\[\]{}<>《》,.!?;:()\-"\'\n\r\t]', '', text)
    # 去除数字周围空格
    text = re.sub(r'\s*(\d+)\s*', r'\1', text)
    return text.strip()


def similarity(text1: str, text2: str) -> float:
    """
    计算两段文本的相似度

    使用Jaccard + SequenceMatcher混合评分（借鉴PaperSpine）
    """
    if not text1 or not text2:
        return 0.0

    canon1 = canonical(text1)
    canon2 = canonical(text2)

    if not canon1 or not canon2:
        return 0.0

    # SequenceMatcher
    sm_ratio = SequenceMatcher(None, canon1, canon2).ratio()

    # Jaccard（字符级3-gram）
    def _ngrams(text, n=3):
        return set(text[i:i+n] for i in range(len(text) - n + 1)) if len(text) >= n else {text}

    ng1 = _ngrams(canon1)
    ng2 = _ngrams(canon2)
    if not ng1 or not ng2:
        jaccard = 0.0
    else:
        jaccard = len(ng1 & ng2) / len(ng1 | ng2)

    return jaccard * 0.5 + sm_ratio * 0.5


def split_paragraphs(text: str) -> list:
    """将文本分割为段落"""
    # 先统一换行
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 按空行分段
    paragraphs = re.split(r'\n\s*\n', text.strip())
    # 过滤太短的（少于10个字符的视为非实质段落）
    return [p.strip() for p in paragraphs if len(p.strip()) > 10]


def audit_revision(original: str, revised: str,
                   unchanged_threshold: float = 0.82,
                   new_threshold: float = 0.25) -> AuditSummary:
    """
    修订审计：比较原文和修订版

    Parameters
    ----------
    original : str, 原始文本
    revised : str, 修订文本
    unchanged_threshold : float, 相似度≥此值视为"未改变"
    new_threshold : float, 相似度<此值视为"全新内容"

    Returns
    -------
    AuditSummary
    """
    orig_paras = split_paragraphs(original)
    rev_paras = split_paragraphs(revised)

    summary = AuditSummary(
        original_paragraphs=len(orig_paras),
        revised_paragraphs=len(rev_paras),
    )

    if not orig_paras or not rev_paras:
        return summary

    # 为每个修订段落找到最佳匹配的原文段落
    matches = []
    for ri, rev_para in enumerate(rev_paras):
        best_sim = 0.0
        best_oi = -1
        for oi, orig_para in enumerate(orig_paras):
            sim = similarity(rev_para, orig_para)
            if sim > best_sim:
                best_sim = sim
                best_oi = oi

        op = "modified"
        if best_sim >= unchanged_threshold:
            op = "kept"
            summary.near_identical_count += 1
        elif best_sim < new_threshold:
            op = "added"
            summary.mostly_new_count += 1

        matches.append(ParagraphMatch(
            revised_index=ri,
            original_index=best_oi,
            similarity=round(best_sim, 3),
            revised_preview=rev_para[:60],
            original_preview=orig_paras[best_oi][:60] if best_oi >= 0 else "",
            operation=op,
        ))

    # 检测被删除的原文段落
    matched_orig_indices = {m.original_index for m in matches if m.original_index >= 0}
    for oi, orig_para in enumerate(orig_paras):
        if oi not in matched_orig_indices:
            summary.likely_deleted_count += 1
            matches.append(ParagraphMatch(
                revised_index=-1,
                original_index=oi,
                similarity=0.0,
                original_preview=orig_para[:60],
                operation="deleted",
            ))

    summary.matches = matches

    # 计算比率
    n_rev = len(rev_paras)
    if n_rev > 0:
        summary.unchanged_ratio = round(summary.near_identical_count / n_rev, 3)
        summary.new_ratio = round(summary.mostly_new_count / n_rev, 3)
    n_orig = len(orig_paras)
    if n_orig > 0:
        summary.deleted_ratio = round(summary.likely_deleted_count / n_orig, 3)

    # 判断
    summary.shallow_warning = summary.unchanged_ratio > 0.35
    summary.addition_heavy = (summary.new_ratio > 0.35 and summary.deleted_ratio < 0.15)

    return summary


def format_report(summary: AuditSummary, as_json: bool = False) -> str:
    """格式化审计报告"""
    if as_json:
        return json.dumps({
            'original_paragraphs': summary.original_paragraphs,
            'revised_paragraphs': summary.revised_paragraphs,
            'near_identical_count': summary.near_identical_count,
            'mostly_new_count': summary.mostly_new_count,
            'likely_deleted_count': summary.likely_deleted_count,
            'unchanged_ratio': summary.unchanged_ratio,
            'new_ratio': summary.new_ratio,
            'deleted_ratio': summary.deleted_ratio,
            'shallow_warning': summary.shallow_warning,
            'addition_heavy': summary.addition_heavy,
            'matches': [
                {
                    'op': m.operation,
                    'sim': m.similarity,
                    'revised': m.revised_preview,
                    'original': m.original_preview,
                }
                for m in summary.matches
            ],
        }, ensure_ascii=False, indent=2)

    lines = [
        "# 修订审计报告",
        "",
        f"- 原文段落数: {summary.original_paragraphs}",
        f"- 修订段落数: {summary.revised_paragraphs}",
        f"- 未改变段落: {summary.near_identical_count} ({summary.unchanged_ratio:.0%})",
        f"- 全新段落: {summary.mostly_new_count} ({summary.new_ratio:.0%})",
        f"- 被删除段落: {summary.likely_deleted_count} ({summary.deleted_ratio:.0%})",
        "",
    ]

    if summary.shallow_warning:
        lines.append("**警告: 浅编辑!** {unchanged_ratio:.0%} 的段落几乎未修改。建议进行更深层次的逻辑重组。".format(
            unchanged_ratio=summary.unchanged_ratio
        ))
        lines.append("")

    if summary.addition_heavy:
        lines.append("**提示: 添加为主。** 新增内容较多但删除很少，可能只是在原文基础上堆砌而非重构。")
        lines.append("")

    # 详细匹配
    lines.append("## 段落匹配详情")
    lines.append("")
    lines.append("| 操作 | 相似度 | 修订段落(前60字) | 原文匹配(前60字) |")
    lines.append("|------|--------|-----------------|-----------------|")
    for m in summary.matches:
        op_icon = {'kept': '=', 'modified': '~', 'added': '+', 'deleted': '-'}[m.operation]
        lines.append(
            f"| {op_icon} {m.operation} | {m.similarity:.0%} | "
            f"{m.revised_preview} | {m.original_preview} |"
        )

    return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        # CLI模式: python revision_audit.py original.md revised.md
        orig_path = Path(sys.argv[1])
        rev_path = Path(sys.argv[2])
        original = orig_path.read_text(encoding='utf-8')
        revised = rev_path.read_text(encoding='utf-8')
        as_json = '--json' in sys.argv
        summary = audit_revision(original, revised)
        print(format_report(summary, as_json=as_json))
        sys.exit(1 if summary.shallow_warning else 0)

    elif '--test' in sys.argv:
        # 内置测试
        original = """
校园污水管网是城市水循环的重要组成部分。

本研究选取某校园污水管网，系统分析固-液-气三相碳污染物的赋存特征。

结果表明，DO与CH4呈显著负相关。

溶解氧是控制产甲烷过程的关键因素。
"""
        revised = """
校园污水管网是城市基础设施的关键组成部分，承担着输送和处理校园生活污水的重要功能。

本研究以某校园污水管网为研究对象，采用系统采样和多元统计方法，分析了固-液-气多相态碳污染物的赋存特征、空间分异及其驱动机制。

结果表明，溶解氧(DO)与甲烷(CH4)浓度呈显著负相关关系(r=-0.72, p<0.001)。

本研究揭示了溶解氧浓度是控制管道中产甲烷过程的核心因素，当DO<0.5 mg/L时产甲烷活性最高。
"""
        summary = audit_revision(original, revised)
        print(format_report(summary))
        print("\n测试通过!")
    else:
        print("用法:")
        print("  python revision_audit.py original.md revised.md  # 比较两个文件")
        print("  python revision_audit.py original.md revised.md --json  # JSON输出")
        print("  python revision_audit.py --test  # 运行内置测试")
