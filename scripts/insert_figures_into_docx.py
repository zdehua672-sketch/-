import os
from document_assembler import assemble_paper

MD_PATH = os.path.join('paper_output', 'paper.md')
FIG_DIR = os.path.join('paper_output', 'figures')
OUT_DOCX = os.path.join('paper_output', 'paper_with_figures.docx')

# 1. 读取 markdown，按一级标题分割为章节
with open(MD_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

sections = []
current_heading = None
current_text_lines = []

for line in lines:
    if line.startswith('# '):
        # flush previous
        if current_heading is not None:
            sections.append({'heading': current_heading, 'text': ''.join(current_text_lines), 'level': 1})
        current_heading = line.lstrip('#').strip()
        current_text_lines = []
    else:
        current_text_lines.append(line)

# flush last
if current_heading is not None:
    sections.append({'heading': current_heading, 'text': ''.join(current_text_lines), 'level': 1})

# 2. 列出图像文件，按文件名排序
fig_files = []
if os.path.isdir(FIG_DIR):
    fig_files = sorted([f for f in os.listdir(FIG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

# 3. 构建 figures 列表：按顺序把每张图插入到对应章节后（循环分配）
figs = []
for idx, fname in enumerate(fig_files):
    figs.append({'path': os.path.join(FIG_DIR, fname), 'caption': os.path.splitext(fname)[0], 'after_section': idx % len(sections) if sections else -1})

# 4. 组装 docx
os.makedirs(os.path.dirname(OUT_DOCX), exist_ok=True)
assemble_paper(sections, figs, OUT_DOCX, title='自动生成论文（含图）', paper_type='chinese', language='zh')

# 5. 复制到桌面
desktop_out = os.path.join(os.path.expanduser('~'), 'Desktop', os.path.basename(OUT_DOCX))
try:
    import shutil
    shutil.copyfile(OUT_DOCX, desktop_out)
    print('COPIED_TO_DESKTOP:', desktop_out)
except Exception as e:
    print('COPY_FAILED:', str(e))
