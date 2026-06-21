# -*- coding: utf-8 -*-
"""
=============================================================================
人工在环系统 - Human-in-the-Loop
=============================================================================

标记低置信输出，支持人工复核：
1. 自动检测需要人工复核的内容
2. 提供复核接口
3. 记录复核结果
4. 反馈到学习系统

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime


@dataclass
class ReviewItem:
    """复核项目"""
    id: str = ''                       # 项目ID
    section_type: str = ''             # 章节类型
    text: str = ''                     # 待复核文本
    location: str = ''                 # 位置（句子/段落）
    reason: str = ''                   # 需要复核的原因
    confidence: float = 0.0            # 置信度
    severity: str = 'MAJOR'            # 严重程度
    created_at: str = ''               # 创建时间
    status: str = 'pending'            # 状态（pending/approved/rejected/modified）
    reviewer_notes: str = ''           # 复核者备注
    reviewed_at: str = ''              # 复核时间
    original_text: str = ''            # 原始文本
    modified_text: str = ''            # 修改后的文本

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ReviewResult:
    """复核结果"""
    total_items: int = 0               # 总项目数
    approved_count: int = 0            # 批准数量
    rejected_count: int = 0            # 拒绝数量
    modified_count: int = 0            # 修改数量
    pending_count: int = 0             # 待处理数量

    def to_dict(self) -> Dict:
        return {
            'total_items': self.total_items,
            'approved_count': self.approved_count,
            'rejected_count': self.rejected_count,
            'modified_count': self.modified_count,
            'pending_count': self.pending_count,
        }


class HumanInTheLoop:
    """
    人工在环系统

    用法:
        hitl = HumanInTheLoop()
        items = hitl.detect_review_needed(text, quality_score, fact_check_result)
        hitl.submit_review(item_id, 'approved', notes='Looks good')
    """

    # 置信度阈值
    LOW_CONFIDENCE_THRESHOLD = 0.6     # 低置信度阈值
    VERY_LOW_CONFIDENCE_THRESHOLD = 0.4  # 极低置信度阈值

    # 需要复核的模式
    REVIEW_PATTERNS = {
        'low_quality': {
            'threshold': 50,
            'reason': '质量分数过低',
            'severity': 'MAJOR',
        },
        'fact_check_failed': {
            'threshold': None,
            'reason': '事实检查失败',
            'severity': 'CRITICAL',
        },
        'strong_assertion': {
            'threshold': None,
            'reason': '包含强断言',
            'severity': 'MINOR',
        },
        'low_confidence_memory': {
            'threshold': 0.4,
            'reason': '使用低置信度记忆',
            'severity': 'MINOR',
        },
    }

    def __init__(self, review_dir: str = None):
        """
        初始化人工在环系统

        Parameters
        ----------
        review_dir : str, 复核记录目录
        """
        if review_dir is None:
            review_dir = os.path.join(os.path.dirname(__file__), 'review_queue')
        self.review_dir = review_dir
        os.makedirs(review_dir, exist_ok=True)

        self.review_items: Dict[str, ReviewItem] = {}
        self._load_pending_items()

    def _load_pending_items(self):
        """加载待处理项目"""
        pending_file = os.path.join(self.review_dir, 'pending.json')
        if os.path.exists(pending_file):
            try:
                with open(pending_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item_data in data:
                    item = ReviewItem(**item_data)
                    self.review_items[item.id] = item
            except Exception as e:
                print(f"加载待处理项目失败: {e}")

    def _save_pending_items(self):
        """保存待处理项目"""
        pending_file = os.path.join(self.review_dir, 'pending.json')
        pending_items = [
            item.to_dict()
            for item in self.review_items.values()
            if item.status == 'pending'
        ]
        try:
            with open(pending_file, 'w', encoding='utf-8') as f:
                json.dump(pending_items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存待处理项目失败: {e}")

    def detect_review_needed(self, text: str, section_type: str,
                             quality_score: float = 0.0,
                             fact_check_passed: bool = True,
                             fact_check_issues: List[Dict] = None,
                             memory_confidence: float = 1.0) -> List[ReviewItem]:
        """
        检测需要人工复核的内容

        Parameters
        ----------
        text : str, 待检测文本
        section_type : str, 章节类型
        quality_score : float, 质量分数
        fact_check_passed : bool, 事实检查是否通过
        fact_check_issues : list of dict, 事实检查问题
        memory_confidence : float, 记忆置信度

        Returns
        -------
        list of ReviewItem : 需要复核的项目
        """
        items = []

        # 1. 低质量分数
        if quality_score < self.REVIEW_PATTERNS['low_quality']['threshold']:
            items.append(self._create_review_item(
                section_type=section_type,
                text=text[:200],
                reason=self.REVIEW_PATTERNS['low_quality']['reason'],
                confidence=quality_score / 100,
                severity=self.REVIEW_PATTERNS['low_quality']['severity'],
            ))

        # 2. 事实检查失败
        if not fact_check_passed:
            for issue in (fact_check_issues or []):
                # 支持FactCheckIssue对象和dict两种格式
                if hasattr(issue, 'location'):
                    # FactCheckIssue对象
                    items.append(self._create_review_item(
                        section_type=section_type,
                        text=issue.location or text[:200],
                        reason=f"{issue.category or '事实不一致'}: {issue.problem}",
                        confidence=0.3,
                        severity=issue.severity,
                    ))
                else:
                    # dict格式
                    items.append(self._create_review_item(
                        section_type=section_type,
                        text=issue.get('location', text[:200]),
                        reason=f"{issue.get('category', '事实不一致')}: {issue.get('problem', '')}",
                        confidence=0.3,
                        severity=issue.get('severity', 'CRITICAL'),
                    ))

        # 3. 低置信度记忆
        if memory_confidence < self.REVIEW_PATTERNS['low_confidence_memory']['threshold']:
            items.append(self._create_review_item(
                section_type=section_type,
                text=text[:200],
                reason=self.REVIEW_PATTERNS['low_confidence_memory']['reason'],
                confidence=memory_confidence,
                severity=self.REVIEW_PATTERNS['low_confidence_memory']['severity'],
            ))

        # 保存到待处理队列
        for item in items:
            self.review_items[item.id] = item
        self._save_pending_items()

        return items

    def _create_review_item(self, section_type: str, text: str,
                            reason: str, confidence: float,
                            severity: str) -> ReviewItem:
        """创建复核项目"""
        import uuid
        item_id = str(uuid.uuid4())[:8]
        return ReviewItem(
            id=item_id,
            section_type=section_type,
            text=text,
            location=text[:50],
            reason=reason,
            confidence=confidence,
            severity=severity,
            created_at=datetime.now().isoformat(),
            status='pending',
            original_text=text,
        )

    def submit_review(self, item_id: str, decision: str,
                      notes: str = '', modified_text: str = '') -> bool:
        """
        提交复核结果

        Parameters
        ----------
        item_id : str, 项目ID
        decision : str, 决定（approved/rejected/modified）
        notes : str, 备注
        modified_text : str, 修改后的文本

        Returns
        -------
        bool : 是否成功
        """
        if item_id not in self.review_items:
            print(f"项目 {item_id} 不存在")
            return False

        item = self.review_items[item_id]
        item.status = decision
        item.reviewer_notes = notes
        item.reviewed_at = datetime.now().isoformat()

        if decision == 'modified' and modified_text:
            item.modified_text = modified_text

        self._save_pending_items()
        self._archive_item(item)

        return True

    def _archive_item(self, item: ReviewItem):
        """归档已处理项目"""
        archive_file = os.path.join(self.review_dir, 'archive.json')
        try:
            archive = []
            if os.path.exists(archive_file):
                with open(archive_file, 'r', encoding='utf-8') as f:
                    archive = json.load(f)
            archive.append(item.to_dict())
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(archive, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"归档项目失败: {e}")

    def get_pending_items(self, section_type: str = None) -> List[ReviewItem]:
        """获取待处理项目"""
        items = [
            item for item in self.review_items.values()
            if item.status == 'pending'
        ]
        if section_type:
            items = [i for i in items if i.section_type == section_type]
        return items

    def get_review_summary(self) -> ReviewResult:
        """获取复核摘要"""
        result = ReviewResult()
        for item in self.review_items.values():
            result.total_items += 1
            if item.status == 'approved':
                result.approved_count += 1
            elif item.status == 'rejected':
                result.rejected_count += 1
            elif item.status == 'modified':
                result.modified_count += 1
            else:
                result.pending_count += 1
        return result

    def get_accepted_text(self, item_id: str) -> Optional[str]:
        """获取被接受的文本（用于学习）"""
        if item_id not in self.review_items:
            return None

        item = self.review_items[item_id]
        if item.status == 'approved':
            return item.original_text
        elif item.status == 'modified':
            return item.modified_text
        return None

    def format_review_queue(self) -> str:
        """格式化复核队列为可读文本"""
        pending = self.get_pending_items()
        if not pending:
            return "没有待复核的项目"

        lines = ["待复核项目:"]
        lines.append("-" * 60)
        for i, item in enumerate(pending, 1):
            lines.append(f"{i}. [{item.severity}] {item.section_type}")
            lines.append(f"   原因: {item.reason}")
            lines.append(f"   置信度: {item.confidence:.2f}")
            lines.append(f"   文本: {item.text[:100]}...")
            lines.append(f"   ID: {item.id}")
            lines.append("")
        return '\n'.join(lines)


# 全局单例
_hitl = None

def get_human_in_loop() -> HumanInTheLoop:
    """获取人工在环系统单例"""
    global _hitl
    if _hitl is None:
        _hitl = HumanInTheLoop()
    return _hitl


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    hitl = get_human_in_loop()

    # 检测需要复核的内容
    test_text = "本研究证明CH4浓度必然与pH负相关..."
    items = hitl.detect_review_needed(
        text=test_text,
        section_type='results',
        quality_score=45.0,
        fact_check_passed=False,
        fact_check_issues=[
            {'category': '数值不一致', 'problem': 'p值不匹配', 'severity': 'MAJOR'},
        ],
    )

    print(f"检测到 {len(items)} 个需要复核的项目")
    print(hitl.format_review_queue())

    # 模拟复核
    if items:
        hitl.submit_review(items[0].id, 'approved', notes='确认无误')
        print(f"\n复核后待处理: {len(hitl.get_pending_items())}")
