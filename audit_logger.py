# -*- coding: utf-8 -*-
"""
=============================================================================
审计日志系统 - Audit Logger
=============================================================================

记录写作过程中的所有关键信息，用于回溯和质量优化：
1. 记录 prompt、模型参数、候选稿、版本
2. 记录 reviewer 反馈和评分
3. 支持按 session/section 查询
4. 支持导出为 JSON/Markdown

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


@dataclass
class AuditEntry:
    """审计日志条目"""
    id: str = ''                           # 条目ID
    session_id: str = ''                   # 会话ID
    timestamp: str = ''                    # 时间戳

    # 写作信息
    section_type: str = ''                 # 章节类型
    step_name: str = ''                    # 步骤名称

    # Prompt 信息
    prompt: str = ''                       # 输入 prompt
    prompt_tokens: int = 0                 # Prompt token 数

    # 模型参数
    model: str = ''                        # 模型名称
    temperature: float = 0.0               # 温度参数
    max_tokens: int = 0                    # 最大 token 数

    # 输出信息
    output: str = ''                       # 模型输出
    output_tokens: int = 0                 # 输出 token 数
    candidates: List[str] = field(default_factory=list)  # 候选输出

    # 质量评分
    quality_score: float = 0.0             # 质量分数
    score_details: Dict = field(default_factory=dict)  # 评分详情

    # 审稿反馈
    review_issues: List[Dict] = field(default_factory=list)  # 审稿问题
    review_score: float = 0.0              # 审稿分数

    # 元数据
    metadata: Dict = field(default_factory=dict)  # 其他元数据


class AuditLogger:
    """
    审计日志记录器

    用法:
        logger = AuditLogger('audit_logs/')
        logger.log(entry)
        entries = logger.query(session_id='xxx')
        logger.export_markdown('report.md')
    """

    def __init__(self, log_dir: str = None):
        """
        初始化日志记录器

        Parameters
        ----------
        log_dir : str, 日志存储目录
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'audit_logs')
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.entries: List[AuditEntry] = []
        self.session_id = str(uuid.uuid4())[:8]
        self._current_file = os.path.join(log_dir, f"session_{self.session_id}.json")

    def log(self, entry: AuditEntry):
        """
        记录审计条目

        Parameters
        ----------
        entry : AuditEntry, 审计条目
        """
        if not entry.id:
            entry.id = str(uuid.uuid4())[:8]
        if not entry.session_id:
            entry.session_id = self.session_id
        if not entry.timestamp:
            entry.timestamp = datetime.now().isoformat()

        self.entries.append(entry)
        self._save_entry(entry)

    def log_writing(self, section_type: str, step_name: str,
                    prompt: str, output: str, candidates: List[str] = None,
                    quality_score: float = 0.0, score_details: Dict = None,
                    **kwargs):
        """
        记录写作过程

        Parameters
        ----------
        section_type : str, 章节类型
        step_name : str, 步骤名称
        prompt : str, 输入 prompt
        output : str, 模型输出
        candidates : list of str, 候选输出
        quality_score : float, 质量分数
        score_details : dict, 评分详情
        **kwargs : 其他参数
        """
        entry = AuditEntry(
            section_type=section_type,
            step_name=step_name,
            prompt=prompt,
            output=output,
            candidates=candidates or [],
            quality_score=quality_score,
            score_details=score_details or {},
            **kwargs,
        )
        self.log(entry)

    def log_review(self, section_type: str, review_issues: List[Dict],
                   review_score: float, **kwargs):
        """
        记录审稿反馈

        Parameters
        ----------
        section_type : str, 章节类型
        review_issues : list of dict, 审稿问题
        review_score : float, 审稿分数
        **kwargs : 其他参数
        """
        entry = AuditEntry(
            section_type=section_type,
            step_name='review',
            review_issues=review_issues,
            review_score=review_score,
            **kwargs,
        )
        self.log(entry)

    def _save_entry(self, entry: AuditEntry):
        """保存条目到文件"""
        try:
            # 读取现有数据
            entries = []
            if os.path.exists(self._current_file):
                with open(self._current_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)

            # 添加新条目
            entries.append(asdict(entry))

            # 保存
            with open(self._current_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存审计日志失败: {e}")

    def query(self, session_id: str = None, section_type: str = None,
              step_name: str = None, limit: int = 100) -> List[AuditEntry]:
        """
        查询审计日志

        Parameters
        ----------
        session_id : str, 会话ID
        section_type : str, 章节类型
        step_name : str, 步骤名称
        limit : int, 最大返回数量

        Returns
        -------
        list of AuditEntry : 查询结果
        """
        results = self.entries

        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if section_type:
            results = [e for e in results if e.section_type == section_type]
        if step_name:
            results = [e for e in results if e.step_name == step_name]

        return results[-limit:]

    def get_session_summary(self, session_id: str = None) -> Dict:
        """
        获取会话摘要

        Parameters
        ----------
        session_id : str, 会话ID

        Returns
        -------
        dict : 会话摘要
        """
        if session_id is None:
            session_id = self.session_id

        entries = self.query(session_id=session_id)

        if not entries:
            return {}

        # 统计信息
        sections = set(e.section_type for e in entries if e.section_type)
        avg_score = sum(e.quality_score for e in entries if e.quality_score) / len(entries)
        total_issues = sum(len(e.review_issues) for e in entries)

        return {
            'session_id': session_id,
            'entry_count': len(entries),
            'sections': list(sections),
            'avg_quality_score': round(avg_score, 1),
            'total_review_issues': total_issues,
            'first_entry': entries[0].timestamp if entries else None,
            'last_entry': entries[-1].timestamp if entries else None,
        }

    def export_markdown(self, filepath: str = None, session_id: str = None):
        """
        导出为 Markdown 格式

        Parameters
        ----------
        filepath : str, 输出文件路径
        session_id : str, 会话ID
        """
        if filepath is None:
            filepath = os.path.join(self.log_dir, f"audit_{self.session_id}.md")

        entries = self.query(session_id=session_id)

        lines = []
        lines.append("# 审计日志报告\n")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"会话ID: {session_id or self.session_id}\n")
        lines.append(f"日志条目: {len(entries)}\n")

        # 按章节分组
        by_section = {}
        for entry in entries:
            section = entry.section_type or 'other'
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(entry)

        for section, section_entries in by_section.items():
            lines.append(f"\n## {section}\n")

            for entry in section_entries:
                lines.append(f"### {entry.step_name} ({entry.timestamp})\n")

                if entry.quality_score:
                    lines.append(f"- 质量分数: {entry.quality_score:.1f}\n")

                if entry.prompt:
                    lines.append(f"\n**Prompt:**\n```\n{entry.prompt[:500]}...\n```\n")

                if entry.output:
                    lines.append(f"\n**输出:**\n```\n{entry.output[:500]}...\n```\n")

                if entry.review_issues:
                    lines.append(f"\n**审稿问题 ({len(entry.review_issues)}):**\n")
                    for issue in entry.review_issues[:5]:
                        lines.append(f"- [{issue.get('severity', '')}] {issue.get('description', '')}\n")

                lines.append("\n---\n")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"审计日志已导出: {filepath}")

    def export_json(self, filepath: str = None, session_id: str = None):
        """
        导出为 JSON 格式

        Parameters
        ----------
        filepath : str, 输出文件路径
        session_id : str, 会话ID
        """
        if filepath is None:
            filepath = os.path.join(self.log_dir, f"audit_{self.session_id}.json")

        entries = self.query(session_id=session_id)

        data = {
            'session_id': session_id or self.session_id,
            'exported_at': datetime.now().isoformat(),
            'entry_count': len(entries),
            'entries': [asdict(e) for e in entries],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"审计日志已导出: {filepath}")


# 全局单例
_logger = None

def get_audit_logger(log_dir: str = None) -> AuditLogger:
    """获取审计日志记录器单例"""
    global _logger
    if _logger is None:
        _logger = AuditLogger(log_dir)
    return _logger


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    logger = get_audit_logger()

    # 测试记录写作过程
    logger.log_writing(
        section_type='introduction',
        step_name='writer_intro',
        prompt='请写一篇关于污水管网碳排放的引言...',
        output='本研究以某校园污水管网为研究对象...',
        quality_score=75.0,
        score_details={'citation': 80, 'coverage': 70, 'language': 75},
    )

    # 测试记录审稿反馈
    logger.log_review(
        section_type='introduction',
        review_issues=[
            {'severity': 'MAJOR', 'description': '引用不足'},
            {'severity': 'MINOR', 'description': '长句过多'},
        ],
        review_score=60.0,
    )

    # 获取会话摘要
    summary = logger.get_session_summary()
    print(f"会话摘要: {summary}")

    # 导出报告
    logger.export_markdown()
