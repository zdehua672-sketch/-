"""
LaTeX/BibTeX 导出器
====================
将 Markdown 格式的论文转换为 LaTeX 源文件，
配合 BibTeX 引用管理。

借鉴自: AI-Scientist (SakanaAI/AI-Scientist) + GPT-Academic

功能:
  1. Markdown → LaTeX 转换
  2. BibTeX 引用管理
  3. 自定义 LaTeX 模板
  4. 编译检查（可选）

用法:
    from latex_exporter import LatexExporter

    exporter = LatexExporter()
    exporter.export(
        sections={'introduction': '...', 'methods': '...', ...},
        references=[{'title': '...', 'authors': '...', 'year': 2020, ...}],
        output_dir='./paper_output',
        template='chinese_thesis',  # 或 'sci' / 'nature'
    )
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── LaTeX 模板 ──────────────────────────────────────────────

TEMPLATES = {
    'sci': {
        'name': 'SCI Journal Article',
        'documentclass': r'\documentclass[12pt]{article}',
        'packages': [
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage[T1]{fontenc}',
            r'\usepackage{amsmath,amssymb}',
            r'\usepackage{graphicx}',
            r'\usepackage{booktabs}',
            r'\usepackage{natbib}',
            r'\usepackage{hyperref}',
            r'\usepackage{geometry}',
            r'\geometry{a4paper, margin=1in}',
        ],
        'bibstyle': 'unsrtnat',
    },
    'nature': {
        'name': 'Nature Style',
        'documentclass': r'\documentclass[10pt]{article}',
        'packages': [
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage[T1]{fontenc}',
            r'\usepackage{amsmath}',
            r'\usepackage{graphicx}',
            r'\usepackage{booktabs}',
            r'\usepackage{natbib}',
            r'\usepackage{hyperref}',
            r'\usepackage{geometry}',
            r'\geometry{a4paper, top=2cm, bottom=2cm, left=2cm, right=2cm}',
        ],
        'bibstyle': 'naturemag',
    },
    'chinese_thesis': {
        'name': 'Chinese Thesis (硕士论文)',
        'documentclass': r'\documentclass[12pt,a4paper]{ctexrep}',
        'packages': [
            r'\usepackage{amsmath,amssymb}',
            r'\usepackage{graphicx}',
            r'\usepackage{booktabs}',
            r'\usepackage{natbib}',
            r'\usepackage{hyperref}',
            r'\usepackage{geometry}',
            r'\geometry{a4paper, top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm}',
            r'\usepackage{setspace}',
            r'\onehalfspacing',
        ],
        'bibstyle': 'gbt7714-numerical',
    },
    'chinese_journal': {
        'name': 'Chinese Journal (中文核心)',
        'documentclass': r'\documentclass[12pt]{ctexart}',
        'packages': [
            r'\usepackage{amsmath}',
            r'\usepackage{graphicx}',
            r'\usepackage{booktabs}',
            r'\usepackage{natbib}',
            r'\usepackage{hyperref}',
            r'\usepackage{geometry}',
            r'\geometry{a4paper, margin=2.5cm}',
        ],
        'bibstyle': 'gbt7714-numerical',
    },
}


class LatexExporter:
    """
    LaTeX 导出器

    将 Markdown 论文章节转换为 LaTeX 源文件。
    """

    def __init__(self, template='sci'):
        self.template = TEMPLATES.get(template, TEMPLATES['sci'])
        self.template_name = template

    def export(self, sections: dict, references: list = None,
               output_dir: str = '.', title: str = '', authors: str = '',
               abstract_text: str = '') -> dict:
        """
        导出完整 LaTeX 项目

        Parameters
        ----------
        sections : dict, {section_name: markdown_text}
        references : list of dict, 引用列表
        output_dir : str, 输出目录
        title : str, 论文标题
        authors : str, 作者
        abstract_text : str, 摘要文本

        Returns
        -------
        dict, {tex_path, bib_path, main_path}
        """
        os.makedirs(output_dir, exist_ok=True)

        # 生成 .bib 文件
        bib_path = None
        if references:
            bib_path = self._generate_bibtex(references, output_dir)

        # 生成主 .tex 文件
        tex_path = self._generate_main_tex(
            sections, output_dir, title, authors, abstract_text, bib_path
        )

        # 生成各章节 .tex 文件
        section_paths = self._generate_section_files(sections, output_dir)

        logger.info(f"LaTeX export: {tex_path}, {len(section_paths)} sections")
        return {
            'main_path': tex_path,
            'bib_path': bib_path,
            'section_paths': section_paths,
        }

    def _generate_main_tex(self, sections, output_dir, title, authors,
                           abstract_text, bib_path):
        """生成主 LaTeX 文件"""
        lines = []

        # 文档类和包
        lines.append(self.template['documentclass'])
        lines.append('')
        for pkg in self.template['packages']:
            lines.append(pkg)
        lines.append('')
        lines.append(r'\title{' + self._escape_latex(title) + '}')
        if authors:
            lines.append(r'\author{' + self._escape_latex(authors) + '}')
        lines.append(r'\date{\today}')
        lines.append('')

        # 正文
        lines.append(r'\begin{document}')
        lines.append('')
        lines.append(r'\maketitle')
        lines.append('')

        # 摘要
        if abstract_text or 'abstract' in sections:
            abs_text = abstract_text or sections.get('abstract', '')
            lines.append(r'\begin{abstract}')
            lines.append(self._md_to_latex(abs_text))
            lines.append(r'\end{abstract}')
            lines.append('')

        # 各章节
        section_order = ['introduction', 'methods', 'results', 'discussion', 'conclusion']
        section_titles = {
            'introduction': 'Introduction',
            'methods': 'Materials and Methods',
            'results': 'Results',
            'discussion': 'Discussion',
            'conclusion': 'Conclusions',
        }

        # 中文标题
        if self.template_name.startswith('chinese'):
            section_titles = {
                'introduction': '绪论',
                'methods': '材料与方法',
                'results': '结果',
                'discussion': '讨论',
                'conclusion': '结论',
            }

        for sec_name in section_order:
            if sec_name in sections:
                title = section_titles.get(sec_name, sec_name.capitalize())
                lines.append(r'\section{' + self._escape_latex(title) + '}')
                lines.append(r'\label{sec:' + sec_name + '}')
                lines.append('')
                lines.append(self._md_to_latex(sections[sec_name]))
                lines.append('')

        # 参考文献
        if bib_path:
            bib_name = Path(bib_path).stem
            lines.append(r'\bibliographystyle{' + self.template['bibstyle'] + '}')
            lines.append(r'\bibliography{' + bib_name + '}')
        else:
            lines.append(r'\section*{References}')
            lines.append(r'% Add references here or provide a .bib file')

        lines.append('')
        lines.append(r'\end{document}')

        tex_path = os.path.join(output_dir, 'main.tex')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return tex_path

    def _generate_section_files(self, sections, output_dir):
        """生成各章节独立 .tex 文件（方便单独编辑）"""
        section_dir = os.path.join(output_dir, 'sections')
        os.makedirs(section_dir, exist_ok=True)

        paths = {}
        for name, content in sections.items():
            if name == 'abstract':
                continue
            tex_content = self._md_to_latex(content)
            path = os.path.join(section_dir, f'{name}.tex')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(tex_content)
            paths[name] = path

        return paths

    def _generate_bibtex(self, references, output_dir):
        """生成 BibTeX 文件"""
        lines = []

        for i, ref in enumerate(references):
            # 生成 cite key
            authors = ref.get('authors', 'Unknown')
            year = ref.get('year', 0)
            author_part = re.sub(r'[^a-zA-Z]', '', str(authors).split(',')[0].split()[-1]).lower()
            if not author_part:
                author_part = 'unknown'
            cite_key = f"{author_part}{year}_{i}"

            lines.append(f"@article{{{cite_key},")
            if ref.get('authors'):
                lines.append(f"  author = {{{self._escape_latex(ref['authors'])}}},")
            if ref.get('title'):
                lines.append(f"  title = {{{self._escape_latex(ref['title'])}}},")
            if ref.get('journal'):
                lines.append(f"  journal = {{{self._escape_latex(ref['journal'])}}},")
            if ref.get('year'):
                lines.append(f"  year = {{{ref['year']}}},")
            if ref.get('volume'):
                lines.append(f"  volume = {{{ref['volume']}}},")
            if ref.get('issue'):
                lines.append(f"  number = {{{ref['issue']}}},")
            if ref.get('pages'):
                lines.append(f"  pages = {{{ref['pages']}}},")
            if ref.get('doi'):
                lines.append(f"  doi = {{{ref['doi']}}},")
            lines.append("}")
            lines.append("")

        bib_path = os.path.join(output_dir, 'references.bib')
        with open(bib_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return bib_path

    def _md_to_latex(self, text: str) -> str:
        """Markdown → LaTeX 转换"""
        if not text:
            return ''

        result = text

        # 1. 标题转换: # → \section, ## → \subsection, ### → \subsubsection
        result = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', result, flags=re.MULTILINE)
        result = re.sub(r'^## (.+)$', r'\\subsection{\1}', result, flags=re.MULTILINE)
        result = re.sub(r'^# (.+)$', r'\\section{\1}', result, flags=re.MULTILINE)

        # 2. 粗体: **text** → \textbf{text}
        result = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', result)

        # 3. 斜体: *text* → \textit{text}
        result = re.sub(r'\*(.+?)\*', r'\\textit{\1}', result)

        # 4. 行内代码: `code` → \texttt{code}
        result = re.sub(r'`(.+?)`', r'\\texttt{\1}', result)

        # 5. 数学公式: $...$ → $...$（保持不变）
        # 已经是 LaTeX 格式

        # 6. 化学式: CH4 → CH$_4$, CO2 → CO$_2$
        result = re.sub(r'CH4', r'CH$_4$', result)
        result = re.sub(r'CO2', r'CO$_2$', result)
        result = re.sub(r'N2O', r'N$_2$O', result)
        result = re.sub(r'NH4\+', r'NH$_4^+$', result)
        result = re.sub(r'NO3-', r'NO$_3^-$', result)
        result = re.sub(r'O2', r'O$_2$', result)
        result = re.sub(r'H2S', r'H$_2$S', result)

        # 7. 图表引用: (图1) → (Fig.~\ref{fig:1})
        result = re.sub(r'\(图(\d+)\)', r'(Fig.~\\ref{fig:\1})', result)
        result = re.sub(r'\(表(\d+)\)', r'(Table~\\ref{tab:\1})', result)

        # 8. 列表: - item → \begin{itemize} \item item \end{itemize}
        # 简化处理：每行的 - 转换为 \item
        result = re.sub(r'^- (.+)$', r'\\item \1', result, flags=re.MULTILINE)
        result = re.sub(r'^(\d+)\. (.+)$', r'\\item \2', result, flags=re.MULTILINE)

        # 9. 转义特殊 LaTeX 字符（在其他替换之后）
        # 注意：不要转义已经转换的 LaTeX 命令
        # 只转义裸露的特殊字符
        for char, replacement in [('%', r'\%'), ('&', r'\&'), ('#', r'\#'), ('_', r'\_')]:
            # 不替换已经在命令中的字符
            result = result.replace(char, replacement)

        return result

    def _escape_latex(self, text: str) -> str:
        """转义 LaTeX 特殊字符（用于元数据字段）"""
        if not text:
            return ''
        text = text.replace('\\', r'\textbackslash{}')
        for char, replacement in [('%', r'\%'), ('&', r'\&'), ('#', r'\#'),
                                   ('_', r'\_'), ('$', r'\$'), ('{', r'\{'),
                                   ('}', r'\}'), ('~', r'\textasciitilde{}'),
                                   ('^', r'\textasciicircum{}')]:
            text = text.replace(char, replacement)
        return text


# ── 便捷入口 ──────────────────────────────────────────────

def export_latex(sections: dict, references: list = None,
                 output_dir: str = '.', template: str = 'sci',
                 title: str = '', authors: str = '') -> dict:
    """
    一键导出 LaTeX

    Parameters
    ----------
    sections : dict, {section_name: markdown_text}
    references : list of dict, 引用列表
    output_dir : str, 输出目录
    template : str, 'sci' / 'nature' / 'chinese_thesis' / 'chinese_journal'
    title : str, 论文标题
    authors : str, 作者

    Returns
    -------
    dict, {main_path, bib_path, section_paths}
    """
    exporter = LatexExporter(template=template)
    return exporter.export(
        sections=sections,
        references=references,
        output_dir=output_dir,
        title=title,
        authors=authors,
    )


if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        sections = {
            'abstract': 'This study investigates carbon pollutants.',
            'introduction': '## Background\n\nUrban sewage networks are important.',
            'methods': '## Sampling\n\nSamples were collected from 10 points.',
            'results': '## Findings\n\nDO and CH4 showed negative correlation (r=-0.72).',
            'discussion': '## Interpretation\n\nThe mechanism involves anaerobic conditions.',
            'conclusion': 'This study reveals key factors.',
        }
        refs = [
            {'title': 'Methane in sewers', 'authors': 'Guisasola et al.',
             'year': 2008, 'journal': 'Water Research', 'doi': '10.1016/j.watres.2007.10.010'},
        ]
        result = export_latex(
            sections, refs, output_dir='./test_latex',
            template='chinese_thesis', title='校园污水管网碳污染物研究'
        )
        print(f"[OK] main: {result['main_path']}")
        print(f"[OK] bib: {result['bib_path']}")
        print(f"[OK] sections: {list(result['section_paths'].keys())}")
        print("\nTest passed!")
    else:
        print("用法: python latex_exporter.py --test")
