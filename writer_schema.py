# -*- coding: utf-8 -*-
"""
=============================================================================
写作接口统一 Schema - Writer Schema
=============================================================================

定义 writer 模块的统一输入/输出 schema，消除 ad-hoc 字符串拼接。

核心思想：
1. 所有 writer 函数接受统一的 WritingRequest 结构
2. 所有 writer 函数返回统一的 WritingResponse 结构
3. schema 支持验证和序列化

作者：AI学术写作系统
版本：1.0
=============================================================================
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class SectionType(Enum):
    """章节类型"""
    ABSTRACT = 'abstract'
    INTRODUCTION = 'introduction'
    METHODS = 'methods'
    RESULTS = 'results'
    DISCUSSION = 'discussion'
    RESULTS_DISCUSSION = 'results_discussion'
    CONCLUSION = 'conclusion'


class WritingStyle(Enum):
    """写作风格"""
    CHINESE_CORE = 'chinese_core'      # 中文核心期刊
    SCI = 'sci'                        # SCI 期刊
    NATURE = 'nature'                  # Nature 系列
    CUSTOM = 'custom'                  # 自定义


@dataclass
class MetadataContext:
    """元数据上下文"""
    n_samples: int = 0                 # 样本数
    n_variables: int = 0               # 变量数
    variables: List[str] = field(default_factory=list)  # 变量列表
    groups: List[str] = field(default_factory=list)      # 分组列表
    sampling_points: int = 0           # 采样点数
    winter_samples: int = 0            # 冬季样本数
    spring_samples: int = 0            # 春季样本数

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FindingContext:
    """数据发现上下文"""
    type: str = ''                     # 发现类型
    detail: str = ''                   # 详细描述
    importance: str = ''               # 重要性（critical/high/medium/low）
    data: Dict = field(default_factory=dict)  # 数据值（p值、r值等）
    section: str = ''                  # 关联章节

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MemoryContext:
    """记忆上下文"""
    patterns: List[Dict] = field(default_factory=list)      # 写作模式
    mechanisms: List[Dict] = field(default_factory=list)     # 机制知识
    templates: List[Dict] = field(default_factory=list)      # 模板
    references: List[Dict] = field(default_factory=list)     # 参考文献
    domain_terms: List[str] = field(default_factory=list)    # 领域术语
    avoid_patterns: List[str] = field(default_factory=list)  # 应避免的模式

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WritingConfig:
    """写作配置"""
    style: WritingStyle = WritingStyle.CHINESE_CORE
    language: str = 'zh'               # 语言（zh/en）
    domain: str = ''                   # 研究领域
    temperature: float = 0.7           # 温度参数
    max_tokens: int = 4000             # 最大 token 数
    num_candidates: int = 1            # 候选数量
    enable_fact_check: bool = True     # 启用事实检查
    enable_assertion_control: bool = True  # 启用断言控制

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WritingRequest:
    """统一写作请求"""
    section_type: SectionType          # 章节类型
    metadata: MetadataContext = field(default_factory=MetadataContext)
    findings: List[FindingContext] = field(default_factory=list)
    memory: MemoryContext = field(default_factory=MemoryContext)
    config: WritingConfig = field(default_factory=WritingConfig)
    motivation: str = ''               # 研究动机
    injection_context: str = ''        # 注入上下文
    figures: Dict = field(default_factory=dict)  # 可用图表

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'WritingRequest':
        """从字典创建请求"""
        # 处理枚举类型
        if 'section_type' in data and isinstance(data['section_type'], str):
            data['section_type'] = SectionType(data['section_type'])
        if 'config' in data and 'style' in data['config']:
            if isinstance(data['config']['style'], str):
                data['config']['style'] = WritingStyle(data['config']['style'])

        # 处理嵌套对象
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = MetadataContext(**data['metadata'])
        if 'config' in data and isinstance(data['config'], dict):
            data['config'] = WritingConfig(**data['config'])

        return cls(**data)


@dataclass
class QualityMetrics:
    """质量指标"""
    total_score: float = 0.0           # 总分（0-100）
    citation_score: float = 0.0        # 引用一致性分数
    coverage_score: float = 0.0        # 信息覆盖度分数
    language_score: float = 0.0        # 语言质量分数
    academic_score: float = 0.0        # 学术规范分数
    fact_check_score: float = 0.0      # 事实一致性分数

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WritingResponse:
    """统一写作响应"""
    success: bool = True               # 是否成功
    text: str = ''                     # 生成的文本
    candidates: List[str] = field(default_factory=list)  # 候选文本
    selected_index: int = 0            # 选中的候选索引
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    needs_review: bool = False         # 是否需要人工复核
    review_reasons: List[str] = field(default_factory=list)  # 复核原因
    fact_check_issues: List[Dict] = field(default_factory=list)  # 事实检查问题
    audit_id: str = ''                 # 审计日志 ID

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================================
# Schema 验证器
# ============================================================================

class SchemaValidator:
    """Schema 验证器"""

    @staticmethod
    def validate_request(request: WritingRequest) -> List[str]:
        """
        验证写作请求

        Parameters
        ----------
        request : WritingRequest, 待验证请求

        Returns
        -------
        list of str : 错误信息列表（空列表表示验证通过）
        """
        errors = []

        # 验证章节类型
        if not request.section_type:
            errors.append("section_type 不能为空")

        # 验证配置
        if request.config.temperature < 0 or request.config.temperature > 2:
            errors.append("temperature 必须在 0-2 之间")

        if request.config.max_tokens < 100 or request.config.max_tokens > 10000:
            errors.append("max_tokens 必须在 100-10000 之间")

        if request.config.num_candidates < 1 or request.config.num_candidates > 5:
            errors.append("num_candidates 必须在 1-5 之间")

        # 验证元数据
        if request.metadata.n_samples < 0:
            errors.append("n_samples 不能为负数")

        return errors

    @staticmethod
    def validate_response(response: WritingResponse) -> List[str]:
        """
        验证写作响应

        Parameters
        ----------
        response : WritingResponse, 待验证响应

        Returns
        -------
        list of str : 错误信息列表（空列表表示验证通过）
        """
        errors = []

        if response.success and not response.text:
            errors.append("成功响应必须包含 text")

        if response.quality.total_score < 0 or response.quality.total_score > 100:
            errors.append("total_score 必须在 0-100 之间")

        return errors


# ============================================================================
# 辅助函数
# ============================================================================

def create_request_from_context(ctx, section_type: str) -> WritingRequest:
    """
    从 PaperContext 创建 WritingRequest

    Parameters
    ----------
    ctx : PaperContext, 论文上下文
    section_type : str, 章节类型

    Returns
    -------
    WritingRequest : 写作请求
    """
    # 构建元数据上下文
    metadata = MetadataContext(
        n_samples=len(ctx.df) if ctx.has('df') else 0,
        n_variables=len(ctx.df.columns) if ctx.has('df') else 0,
        variables=list(ctx.df.columns) if ctx.has('df') else [],
    )

    # 构建发现上下文
    findings = []
    for f in ctx.findings[:20]:  # 限制数量
        findings.append(FindingContext(
            type=f.get('type', ''),
            detail=f.get('detail', ''),
            importance=f.get('importance', ''),
            data=f.get('data', {}),
        ))

    # 构建记忆上下文
    memory = MemoryContext()
    if ctx.has('learned_patterns'):
        memory.patterns = ctx.learned_patterns.get('sentence_patterns', [])
    if ctx.has('learned_mechanisms'):
        memory.mechanisms = ctx.learned_mechanisms[:10]
    if ctx.has('recalled_references'):
        memory.references = ctx.recalled_references[:10]

    # 构建配置
    config = WritingConfig(
        language=ctx.language,
        domain=ctx.domain or '',
    )

    return WritingRequest(
        section_type=SectionType(section_type),
        metadata=metadata,
        findings=findings,
        memory=memory,
        config=config,
        motivation=ctx.motivation if ctx.has('motivation') else '',
        figures=ctx.figures if ctx.has('figures') else {},
    )


def extract_findings_data(findings: List[FindingContext]) -> List[Dict]:
    """
    提取发现数据用于事实检查

    Parameters
    ----------
    findings : list of FindingContext, 发现列表

    Returns
    -------
    list of dict : 数据值列表
    """
    data_points = []
    for f in findings:
        if f.data:
            data_points.append({
                'type': f.type,
                'detail': f.detail,
                'p': f.data.get('p'),
                'r': f.data.get('r'),
                'mean': f.data.get('mean'),
                'std': f.data.get('std'),
            })
    return data_points


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == '__main__':
    # 测试 schema 创建
    request = WritingRequest(
        section_type=SectionType.RESULTS,
        metadata=MetadataContext(n_samples=40, n_variables=25),
        findings=[
            FindingContext(
                type='correlation',
                detail='CH4与pH显著负相关',
                importance='high',
                data={'r': -0.534, 'p': 0.022},
            ),
        ],
        config=WritingConfig(
            language='zh',
            domain='污水管网碳排放',
        ),
    )

    print("WritingRequest:")
    print(request.to_json())

    # 测试验证
    errors = SchemaValidator.validate_request(request)
    print(f"\n验证结果: {'通过' if not errors else errors}")

    # 测试响应
    response = WritingResponse(
        success=True,
        text='本研究结果表明...',
        quality=QualityMetrics(total_score=75.0),
    )

    print("\nWritingResponse:")
    print(response.to_json())
