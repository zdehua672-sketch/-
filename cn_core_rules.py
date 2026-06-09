"""
中文核心期刊规范模块（借鉴 xiuneng0-collab）

包含:
  1. 中文核心论文章节模板（非IMRaD结构）
  2. 投稿前检查清单
  3. 图表/公式/排版规范

用法:
    from cn_core_rules import CNCoreTemplate, SubmissionChecklist, FigureTableRules
"""
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ============================================================
# 1. 中文核心论文章节模板
# ============================================================

class CNCoreTemplate:
    """
    中文核心工程论文模板（非IMRaD）

    典型结构:
      0 摘要
      1 系统架构/实现方法
      2 数据/模型/算法
      3 实验/结果
      4 结论

    与IMRaD的区别:
      - IMRaD: Introduction → Methods → Results → Discussion
      - 中文核心: 引言 → 方法（系统/模型） → 实验验证 → 结论
      - 中文核心通常没有独立的Discussion章节
    """

    # 推荐章节结构
    RECOMMENDED_SECTIONS = [
        {
            'id': 'abstract',
            'name': '摘要',
            'order': 0,
            'word_range': (200, 400),
            'structure': '目的 + 方法 + 结果 + 结论（4-6句）',
            'key_points': [
                '直接陈述，不写"本文"',
                '包含关键数据和指标',
                '结论要具体，不写"具有一定意义"',
            ],
            'forbidden': ['本文', '本论文', '需要进一步研究'],
        },
        {
            'id': 'keywords',
            'name': '关键词',
            'order': 0.5,
            'count': (3, 5),
            'key_points': [
                '选名词/术语，不要动词短语',
                '不要用"系统设计""软件实现""实验研究"等',
            ],
        },
        {
            'id': 'introduction',
            'name': '引言',
            'order': 1,
            'word_range': (800, 1500),
            'structure': '背景 → 现有方法分类 → 各自不足 → 本文工作',
            'key_points': [
                '说明研究背景和工程需求',
                '国内外现状分为2-4类综述',
                '每类说明方法和不足',
                '末尾明确本文贡献（3-5个要点）',
            ],
            'paragraph_logic': [
                '第1段：研究领域+工程背景+问题重要性',
                '第2-N段：现有方法分类综述（每类一段）',
                '末段：本文方法+创新点+文章组织',
            ],
            'forbidden': ['随着...的发展', '扮演着关键角色', '具有重要意义'],
        },
        {
            'id': 'method',
            'name': '系统架构/实现方法',
            'order': 2,
            'word_range': (2000, 4000),
            'structure': '系统模块 → 数据流 → 关键算法 → 技术细节',
            'key_points': [
                '结构清晰，模块化描述',
                '术语统一，前后一致',
                '含架构图/流程图/时序图',
                '关键公式要推导或说明来源',
            ],
            'required_figures': ['系统架构图', '数据流图/流程图'],
        },
        {
            'id': 'experiment',
            'name': '实验/结果',
            'order': 3,
            'word_range': (1500, 3000),
            'structure': '实验环境 → 数据集/日志 → 对比实验 → 消融实验 → 分析',
            'key_points': [
                '实验环境要完整（硬件/软件/数据集）',
                '对比方法要公平可复现',
                '数据用实测值，不编造',
                '结果用具体数字（"3.2 MB/s"而非"性能提升"）',
                '表格用三线表',
            ],
            'forbidden': ['性能显著提升', '效果明显', '取得了良好效果'],
        },
        {
            'id': 'conclusion',
            'name': '结论',
            'order': 4,
            'word_range': (200, 500),
            'structure': '总结工作 → 关键结论 → 比较优势 → 应用边界',
            'key_points': [
                '总结本文实现的系统/模型',
                '列出关键数据和对比结论',
                '说明应用范围和边界',
                '不写"未来工作"（中文核心通常不写）',
            ],
            'forbidden': ['需要进一步研究', '有待完善', '值得深入探讨'],
        },
    ]

    @classmethod
    def get_template(cls, section_id: str) -> Optional[dict]:
        """获取指定章节的模板"""
        for sec in cls.RECOMMENDED_SECTIONS:
            if sec['id'] == section_id:
                return sec
        return None

    @classmethod
    def generate_outline(cls) -> str:
        """生成论文大纲模板"""
        lines = ["# 中文核心论文大纲模板", ""]
        for sec in cls.RECOMMENDED_SECTIONS:
            lines.append(f"## {sec['order']} {sec['name']}")
            if sec.get('structure'):
                lines.append(f"  Structure: {sec['structure']}")
            if sec.get('word_range'):
                lines.append(f"  Words: {sec['word_range']}")
            if sec.get('count'):
                lines.append(f"  Count: {sec['count']}")
            lines.append(f"  Key points:")
            for p in sec['key_points']:
                lines.append(f"    - {p}")
            if sec.get('forbidden'):
                lines.append(f"  Forbidden: {', '.join(sec['forbidden'])}")
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def get_section_checklist(cls, section_id: str) -> List[str]:
        """获取某章节的检查清单"""
        sec = cls.get_template(section_id)
        if not sec:
            return []
        items = []
        items.extend(sec['key_points'])
        if sec.get('forbidden'):
            items.append(f"删除禁用词: {', '.join(sec['forbidden'])}")
        if sec.get('word_range'):
            lo, hi = sec['word_range']
            items.append(f"字数范围: {lo}-{hi}字")
        return items


# ============================================================
# 2. 投稿前检查清单
# ============================================================

@dataclass
class ChecklistItem:
    """检查项"""
    category: str       # 检查类别
    item: str           # 检查内容
    status: str = ''    # pass/fail/warn
    detail: str = ''    # 详细说明


class SubmissionChecklist:
    """
    中文核心期刊投稿前检查清单

    覆盖 7 大类检查:
      1. 标题统一
      2. 摘要压缩
      3. 结论不含糊
      4. 图表规范统一
      5. 公式规范
      6. 参考文献格式统一
      7. 术语/单位统一
      8. AI痕迹清除
    """

    CHECKLIST = [
        # === 标题 ===
        ('标题', '标题字数≤25字', 'title_length'),
        ('标题', '标题不含"一种/基于/关于"等前缀', 'title_prefix'),
        ('标题', '标题不含"重要/关键/新型/高效/先进"等模糊词', 'title_vague'),
        ('标题', '全文各处标题引用一致', 'title_consistent'),

        # === 摘要 ===
        ('摘要', '摘要压缩为4-6句', 'abstract_length'),
        ('摘要', '摘要不含"本文/本论文"', 'abstract_no_self'),
        ('摘要', '摘要不含空话（需要进一步研究/具有重要意义等）', 'abstract_no_hollow'),
        ('摘要', '摘要结论落到具体数据', 'abstract_data'),
        ('摘要', '中英文摘要信息一致', 'abstract_bilingual'),

        # === 关键词 ===
        ('关键词', '关键词3-5个', 'keywords_count'),
        ('关键词', '关键词为名词/术语，非动词短语', 'keywords_type'),

        # === 结论 ===
        ('结论', '结论不含模糊表述', 'conclusion_no_vague'),
        ('结论', '结论有具体数据支撑', 'conclusion_data'),
        ('结论', '结论说明应用范围/边界', 'conclusion_boundary'),

        # === 图表 ===
        ('图表', '图有图题（图下方）', 'figure_caption'),
        ('图表', '表有表题（表上方）', 'table_caption'),
        ('图表', '图中文字≥8pt', 'figure_font'),
        ('图表', '图为黑白/灰度（非彩色）', 'figure_bw'),
        ('图表', '表格用三线表', 'table_3line'),
        ('图表', '图表在正文中均有引用', 'figure_referenced'),
        ('图表', '全文图表风格统一', 'figure_consistent'),
        ('图表', '坐标轴有标签和单位', 'figure_axis'),

        # === 公式 ===
        ('公式', '公式居中编号右对齐', 'equation_format'),
        ('公式', '公式变量用斜体', 'equation_italic'),
        ('公式', '全文公式格式统一', 'equation_consistent'),

        # === 参考文献 ===
        ('参考文献', '参考文献在正文中按首次出现顺序排列', 'ref_order'),
        ('参考文献', '引用序号与文献列表顺序一致', 'ref_consistent'),
        ('参考文献', 'GB/T 7714格式', 'ref_format'),
        ('参考文献', '英文文献保留DOI/URL', 'ref_doi'),
        ('参考文献', '参考文献数量≥15篇', 'ref_count'),

        # === 术语/单位 ===
        ('术语单位', '全文术语统一（系统名/模块名/参数名）', 'term_consistent'),
        ('术语单位', '单位统一（MB/s, MB, KB, s, ms）', 'unit_consistent'),
        ('术语单位', '缩写首次出现有全称', 'abbr_first'),

        # === AI痕迹 ===
        ('AI痕迹', '删除AI禁用词（值得/扮演/赋能/闭环等）', 'ai_forbidden'),
        ('AI痕迹', '删除空洞表达（提供参考借鉴/具有重要意义等）', 'ai_hollow'),
        ('AI痕迹', '删除PPT汇报语气（首先/其次/最后）', 'ai_ppt'),
        ('AI痕迹', '删除英文直接翻译痕迹', 'ai_translation'),
    ]

    @classmethod
    def run_check(cls, text: str, sections: dict = None) -> List[ChecklistItem]:
        """
        运行全部检查项

        Parameters
        ----------
        text : str, 全文文本
        sections : dict, {section_name: text} 解析后的章节

        Returns
        -------
        List[ChecklistItem]
        """
        results = []
        for category, item, check_id in cls.CHECKLIST:
            result = ChecklistItem(category=category, item=item)
            result.status, result.detail = cls._run_single_check(check_id, text, sections or {})
            results.append(result)
        return results

    @classmethod
    def _run_single_check(cls, check_id: str, text: str, sections: dict) -> tuple:
        """执行单项检查，返回 (status, detail)"""

        if check_id == 'title_length':
            title = sections.get('title', text.split('\n')[0])
            if len(title) > 25:
                return ('fail', f'标题{len(title)}字，超过25字限制')
            return ('pass', f'{len(title)}字')

        if check_id == 'title_prefix':
            title = sections.get('title', '')
            for prefix in ['一种', '基于', '关于']:
                if title.startswith(prefix):
                    return ('warn', f'标题以"{prefix}"开头')
            return ('pass', '')

        if check_id == 'title_vague':
            title = sections.get('title', '')
            found = [w for w in ['重要', '关键', '新型', '高效', '先进'] if w in title]
            if found:
                return ('warn', f'标题含模糊词: {", ".join(found)}')
            return ('pass', '')

        if check_id == 'abstract_no_self':
            abstract = sections.get('abstract', '')
            if '本文' in abstract or '本论文' in abstract:
                return ('fail', '摘要含"本文/本论文"')
            return ('pass', '')

        if check_id == 'abstract_no_hollow':
            abstract = sections.get('abstract', '')
            hollow = ['需要进一步研究', '具有重要意义', '提供参考借鉴', '状态良好']
            found = [p for p in hollow if p in abstract]
            if found:
                return ('fail', f'含空话: {", ".join(found)}')
            return ('pass', '')

        if check_id == 'keywords_count':
            kw = sections.get('keywords', '')
            count = len([k.strip() for k in re.split(r'[;；,，]', kw) if k.strip()])
            if count < 3 or count > 5:
                return ('warn', f'{count}个关键词，建议3-5个')
            return ('pass', f'{count}个')

        if check_id == 'conclusion_no_vague':
            conclusion = sections.get('conclusion', '')
            vague = ['需要进一步研究', '有待完善', '值得深入探讨',
                     '具有重要意义', '提供了新思路']
            found = [p for p in vague if p in conclusion]
            if found:
                return ('fail', f'含模糊表述: {", ".join(found)}')
            return ('pass', '')

        if check_id == 'figure_caption':
            if re.search(r'图\s*\d+[^。。\n]{5,}', text):
                return ('pass', '')
            return ('warn', '未检测到图题')

        if check_id == 'table_caption':
            if re.search(r'表\s*\d+[^。。\n]{5,}', text):
                return ('pass', '')
            return ('warn', '未检测到表题')

        if check_id == 'table_3line':
            if re.search(r'\|[-:]+\|', text):
                return ('pass', '检测到Markdown表格')
            return ('warn', '未检测到三线表格式')

        if check_id == 'ref_order':
            refs = re.findall(r'\[(\d+)\]', text)
            if refs:
                nums = [int(r) for r in refs]
                if nums == sorted(nums):
                    return ('pass', f'{len(nums)}个引用，顺序正确')
                return ('warn', f'引用顺序可能不正确')
            return ('warn', '未检测到引用序号')

        if check_id == 'ref_count':
            refs = re.findall(r'\[(\d+)\]', text)
            unique_refs = set(refs)
            if len(unique_refs) < 15:
                return ('warn', f'仅{len(unique_refs)}篇参考文献，建议≥15篇')
            return ('pass', f'{len(unique_refs)}篇')

        if check_id == 'ai_forbidden':
            forbidden = ['赋能', '加持', '闭环', '链路', '抓手', '打法',
                         '生态', '驱动', '引领']
            found = [w for w in forbidden if w in text]
            if found:
                return ('fail', f'含AI互联网黑话: {", ".join(found)}')
            return ('pass', '')

        if check_id == 'ai_hollow':
            hollow = ['提供参考借鉴', '具有重要意义', '值得深入探讨',
                      '需要进一步研究', '提供了新思路', '起到了关键作用']
            found = [p for p in hollow if p in text]
            if found:
                return ('fail', f'含空洞表达: {", ".join(found)}')
            return ('pass', '')

        # 默认通过
        return ('pass', '')

    @classmethod
    def generate_report(cls, items: List[ChecklistItem]) -> str:
        """生成检查报告"""
        lines = ["# 中文核心期刊投稿前检查报告", ""]

        fail_count = sum(1 for i in items if i.status == 'fail')
        warn_count = sum(1 for i in items if i.status == 'warn')
        pass_count = sum(1 for i in items if i.status == 'pass')

        lines.append(f"**结果**: {pass_count}通过 / {warn_count}警告 / {fail_count}不通过")
        lines.append("")

        if fail_count:
            lines.append("## 不通过项（必须修改）")
            lines.append("")
            for i in items:
                if i.status == 'fail':
                    lines.append(f"- [{i.category}] {i.item}: {i.detail}")
            lines.append("")

        if warn_count:
            lines.append("## 警告项（建议修改）")
            lines.append("")
            for i in items:
                if i.status == 'warn':
                    lines.append(f"- [{i.category}] {i.item}: {i.detail}")
            lines.append("")

        lines.append("## 通过项")
        lines.append("")
        for i in items:
            if i.status == 'pass':
                detail = f" ({i.detail})" if i.detail else ""
                lines.append(f"- [x] {i.item}{detail}")

        return "\n".join(lines)


# ============================================================
# 3. 图表/公式/排版规范
# ============================================================

class FigureTableRules:
    """
    中文核心期刊图表/公式/排版规范

    参考: xiuneng0-collab 中文核心图表公式细则
    """

    # 图片规范
    FIGURE_RULES = {
        'width_mm': (80, 170),           # 宽度范围（mm）
        'dpi_min': 300,                   # 最低分辨率
        'font_size_pt': 8,                # 最小字号（pt）
        'line_width_min': 0.5,            # 最小线宽（pt）
        'format_bw': True,                # 优先黑白/灰度
        'caption_position': 'below',      # 图题在图下方
        'caption_format': '图{n} {text}', # 图题格式
        'numbering': 'sequential',        # 全文顺序编号
        'border': 'none',                 # 无边框
        'forbid_effects': ['阴影', '渐变', '3D效果', 'PPT装饰'],
    }

    # 表格规范
    TABLE_RULES = {
        'style': 'three_line',            # 三线表
        'caption_position': 'above',      # 表题在表上方
        'caption_format': '表{n} {text}', # 表题格式
        'header_separator': True,         # 表头下有分隔线
        'bottom_separator': True,         # 表底有分隔线
        'no_vertical_lines': True,        # 无竖线
        'numbering': 'sequential',        # 全文顺序编号
        'units_in_header': True,          # 单位写在表头
        'bilingual_header': True,         # 中英文表头
        'data_alignment': 'decimal',      # 数字按小数点对齐
    }

    # 公式规范
    EQUATION_RULES = {
        'position': 'center',             # 居中
        'numbering': 'right',             # 编号右对齐
        'number_format': '(n)',           # 编号格式
        'variables_italic': True,         # 变量斜体
        'units_upright': True,            # 单位正体
        'greek_upright': ['sin', 'cos', 'log', 'ln', 'exp', 'max', 'min'],
        'spacing': 'adequate',            # 适当间距
        'cross_ref_format': '式(n)',      # 正文引用格式
    }

    # 排版规范
    LAYOUT_RULES = {
        'font_cn': '宋体',
        'font_en': 'Times New Roman',
        'font_title': '黑体',
        'font_size_title': '小二',
        'font_size_body': '五号',
        'font_size_abstract': '小五',
        'line_spacing': '1.5倍',
        'page_margins': '上下2.54cm, 左右3.17cm',
        'paragraph_first_indent': '2字符',
        'header_footer': '奇偶页不同',
    }

    @classmethod
    def check_figure(cls, caption: str, description: str = "") -> List[str]:
        """检查单个图片是否符合规范"""
        issues = []
        if not caption:
            issues.append("缺少图题")
        elif not re.match(r'图\s*\d+', caption):
            issues.append("图题格式不正确，应为'图n ...'")
        if description:
            for effect in cls.FIGURE_RULES['forbid_effects']:
                if effect in description:
                    issues.append(f"禁止使用{effect}效果")
        return issues

    @classmethod
    def check_table(cls, has_caption: bool, has_3line: bool,
                    caption_above: bool = True) -> List[str]:
        """检查单个表格是否符合规范"""
        issues = []
        if not has_caption:
            issues.append("缺少表题")
        if not has_3line:
            issues.append("未使用三线表格式")
        if not caption_above:
            issues.append("表题应在表格上方")
        return issues

    @classmethod
    def get_formatting_guide(cls) -> str:
        """获取排版规范指南"""
        lines = ["# 中文核心期刊排版规范", ""]

        lines.append("## 图片规范")
        for k, v in cls.FIGURE_RULES.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        lines.append("## 表格规范")
        for k, v in cls.TABLE_RULES.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        lines.append("## 公式规范")
        for k, v in cls.EQUATION_RULES.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

        lines.append("## 排版规范")
        for k, v in cls.LAYOUT_RULES.items():
            lines.append(f"- {k}: {v}")

        return "\n".join(lines)

    @classmethod
    def get_three_line_table_template(cls, headers: list, caption: str = "") -> str:
        """生成三线表Markdown模板"""
        lines = []
        if caption:
            lines.append(f"**表1 {caption}**")
            lines.append("")
        # 表头
        lines.append("| " + " | ".join(headers) + " |")
        # 分隔线
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        # 数据行（空）
        lines.append("| " + " | ".join([""] * len(headers)) + " |")
        lines.append("")
        return "\n".join(lines)


# ============================================================
# CLI入口
# ============================================================

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if "--outline" in sys.argv:
        print(CNCoreTemplate.generate_outline())

    elif "--checklist" in sys.argv:
        test_text = """本文研究了校园污水管网。
需要进一步研究表明，溶解氧具有重要意义。
赋能数据分析平台。
图1 溶解氧与甲烷的关系
表1 实验数据
[1] 张三. 研究[J]. 期刊, 2023.
"""
        items = SubmissionChecklist.run_check(test_text)
        print(SubmissionChecklist.generate_report(items))

    elif "--format" in sys.argv:
        print(FigureTableRules.get_formatting_guide())

    else:
        print("用法:")
        print("  python cn_core_rules.py --outline    # 中文核心论文章节模板")
        print("  python cn_core_rules.py --checklist  # 投稿前检查清单测试")
        print("  python cn_core_rules.py --format     # 图表/公式/排版规范")
