# -*- coding: utf-8 -*-
"""
=============================================================================
运行时指标收集器 - Runtime Metrics
=============================================================================

收集系统运行时指标：
1. 成功率 - 各模块的调用成功率
2. 平均延迟 - 各模块的平均响应时间
3. 幻觉率 - 事实检查失败率
4. 人工复核率 - 需要人工复核的比例
5. 成本指标 - 每文档的 token 消耗

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


@dataclass
class ModuleMetrics:
    """模块指标"""
    call_count: int = 0                # 调用次数
    success_count: int = 0             # 成功次数
    failure_count: int = 0             # 失败次数
    total_duration: float = 0.0        # 总耗时（秒）
    min_duration: float = float('inf') # 最小耗时
    max_duration: float = 0.0          # 最大耗时

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count

    @property
    def avg_duration(self) -> float:
        """平均耗时"""
        if self.success_count == 0:
            return 0.0
        return self.total_duration / self.success_count

    def to_dict(self) -> Dict:
        return {
            'call_count': self.call_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': round(self.success_rate, 3),
            'avg_duration': round(self.avg_duration, 3),
            'min_duration': round(self.min_duration, 3) if self.min_duration != float('inf') else 0,
            'max_duration': round(self.max_duration, 3),
        }


@dataclass
class QualityMetrics:
    """质量指标"""
    total_checks: int = 0              # 总检查次数
    fact_check_failures: int = 0       # 事实检查失败次数
    needs_review_count: int = 0        # 需要人工复核次数
    avg_quality_score: float = 0.0     # 平均质量分数
    total_tokens: int = 0              # 总 token 消耗
    total_documents: int = 0           # 总文档数

    @property
    def hallucination_rate(self) -> float:
        """幻觉率"""
        if self.total_checks == 0:
            return 0.0
        return self.fact_check_failures / self.total_checks

    @property
    def review_rate(self) -> float:
        """人工复核率"""
        if self.total_checks == 0:
            return 0.0
        return self.needs_review_count / self.total_checks

    @property
    def tokens_per_document(self) -> float:
        """每文档 token 消耗"""
        if self.total_documents == 0:
            return 0.0
        return self.total_tokens / self.total_documents

    def to_dict(self) -> Dict:
        return {
            'total_checks': self.total_checks,
            'fact_check_failures': self.fact_check_failures,
            'hallucination_rate': round(self.hallucination_rate, 3),
            'needs_review_count': self.needs_review_count,
            'review_rate': round(self.review_rate, 3),
            'avg_quality_score': round(self.avg_quality_score, 1),
            'total_tokens': self.total_tokens,
            'total_documents': self.total_documents,
            'tokens_per_document': round(self.tokens_per_document, 0),
        }


class RuntimeMetrics:
    """
    运行时指标收集器

    用法:
        metrics = RuntimeMetrics()
        metrics.record_call('writer_results', success=True, duration=2.5)
        metrics.record_quality_check(passed=True, quality_score=80)
        metrics.save('metrics.json')
    """

    def __init__(self, metrics_dir: str = None):
        """
        初始化指标收集器

        Parameters
        ----------
        metrics_dir : str, 指标存储目录
        """
        if metrics_dir is None:
            metrics_dir = os.path.join(os.path.dirname(__file__), 'metrics')
        self.metrics_dir = metrics_dir
        os.makedirs(metrics_dir, exist_ok=True)

        self.module_metrics: Dict[str, ModuleMetrics] = defaultdict(ModuleMetrics)
        self.quality_metrics = QualityMetrics()
        self.session_start = datetime.now()

    def record_call(self, module_name: str, success: bool, duration: float,
                    tokens: int = 0):
        """
        记录模块调用

        Parameters
        ----------
        module_name : str, 模块名称
        success : bool, 是否成功
        duration : float, 耗时（秒）
        tokens : int, token 消耗
        """
        metrics = self.module_metrics[module_name]
        metrics.call_count += 1
        if success:
            metrics.success_count += 1
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
        else:
            metrics.failure_count += 1

        if tokens > 0:
            self.quality_metrics.total_tokens += tokens

    def record_quality_check(self, passed: bool, quality_score: float = 0.0,
                             needs_review: bool = False):
        """
        记录质量检查

        Parameters
        ----------
        passed : bool, 是否通过事实检查
        quality_score : float, 质量分数
        needs_review : bool, 是否需要人工复核
        """
        self.quality_metrics.total_checks += 1
        if not passed:
            self.quality_metrics.fact_check_failures += 1
        if needs_review:
            self.quality_metrics.needs_review_count += 1

        # 更新平均质量分数
        n = self.quality_metrics.total_checks
        old_avg = self.quality_metrics.avg_quality_score
        self.quality_metrics.avg_quality_score = (old_avg * (n - 1) + quality_score) / n

    def record_document(self, tokens: int = 0):
        """
        记录文档生成

        Parameters
        ----------
        tokens : int, token 消耗
        """
        self.quality_metrics.total_documents += 1
        if tokens > 0:
            self.quality_metrics.total_tokens += tokens

    def get_summary(self) -> Dict:
        """获取指标摘要"""
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'modules': {
                name: metrics.to_dict()
                for name, metrics in self.module_metrics.items()
            },
            'quality': self.quality_metrics.to_dict(),
        }

    def save(self, filepath: str = None):
        """保存指标到文件"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(self.metrics_dir, f'metrics_{timestamp}.json')

        data = self.get_summary()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"指标已保存: {filepath}")

    def print_summary(self):
        """打印指标摘要"""
        summary = self.get_summary()

        print("=" * 60)
        print("运行时指标摘要")
        print("=" * 60)

        print(f"\n会话时长: {summary['session_duration']:.1f} 秒")

        print("\n模块调用统计:")
        print("-" * 60)
        print(f"{'模块名称':<25} {'调用次数':<10} {'成功率':<10} {'平均耗时':<10}")
        print("-" * 60)
        for name, metrics in summary['modules'].items():
            print(f"{name:<25} {metrics['call_count']:<10} "
                  f"{metrics['success_rate']:<10.1%} "
                  f"{metrics['avg_duration']:<10.3f}")

        print("\n质量指标:")
        print("-" * 60)
        quality = summary['quality']
        print(f"总检查次数: {quality['total_checks']}")
        print(f"幻觉率: {quality['hallucination_rate']:.1%}")
        print(f"人工复核率: {quality['review_rate']:.1%}")
        print(f"平均质量分数: {quality['avg_quality_score']:.1f}")
        print(f"总文档数: {quality['total_documents']}")
        print(f"每文档 token: {quality['tokens_per_document']:.0f}")


# 全局单例
_metrics = None

def get_runtime_metrics() -> RuntimeMetrics:
    """获取运行时指标单例"""
    global _metrics
    if _metrics is None:
        _metrics = RuntimeMetrics()
    return _metrics


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    metrics = get_runtime_metrics()

    # 模拟一些调用
    metrics.record_call('writer_results', success=True, duration=2.5, tokens=1000)
    metrics.record_call('writer_results', success=True, duration=3.0, tokens=1200)
    metrics.record_call('writer_discussion', success=False, duration=0.5)

    metrics.record_quality_check(passed=True, quality_score=80)
    metrics.record_quality_check(passed=False, quality_score=50, needs_review=True)

    metrics.record_document(tokens=2000)

    metrics.print_summary()
    metrics.save()
