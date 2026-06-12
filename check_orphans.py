# -*- coding: utf-8 -*-
"""
孤立模块检查器
==============
检查根目录下所有 .py 模块是否被其他模块导入（即是否接入管线）。
每次新增模块或合并分支后运行此脚本。

用法:
    python check_orphans.py

退出码:
    0 = 无孤立模块
    1 = 有孤立模块
"""

import os
import sys


def find_orphans(root_dir='.'):
    """找出所有未被任何其他 .py 文件导入的模块"""
    # 收集根目录所有 .py 文件（排除 test_ 开头和 check_orphans 自身）
    all_py = [
        f for f in os.listdir(root_dir)
        if f.endswith('.py')
        and not f.startswith('test_')
        and f != 'check_orphans.py'
        and f != 'conftest.py'
    ]

    # 收集所有文件的导入语句
    imports_in_files = {}
    for f in all_py:
        filepath = os.path.join(root_dir, f)
        try:
            with open(filepath, encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            imports_in_files[f] = content
        except Exception:
            imports_in_files[f] = ''

    # 检查每个模块是否被其他文件导入
    orphaned = []
    connected = []

    for f in sorted(all_py):
        module_name = f[:-3]  # 去掉 .py
        is_imported = False
        importers = []

        for other_f, content in imports_in_files.items():
            if other_f == f:
                continue
            # 检查 import xxx 或 from xxx import
            if (f'import {module_name}' in content or
                f'from {module_name}' in content):
                is_imported = True
                importers.append(other_f)

        if is_imported:
            connected.append((f, importers))
        else:
            # paper_context.py 是编排器入口，被 test_full_pipeline 导入，不算孤立
            if module_name in ('paper_context', 'web_app'):
                connected.append((f, ['[entry point]']))
            else:
                orphaned.append(f)

    return orphaned, connected


def main():
    print("=" * 60)
    print("  孤立模块检查器")
    print("=" * 60)
    print()

    orphaned, connected = find_orphans()

    print(f"[已连通] {len(connected)} 个模块:")
    for f, importers in connected:
        print(f"  OK  {f:35s} <- {', '.join(importers)}")

    print()

    if orphaned:
        print(f"[孤立] {len(orphaned)} 个模块未接入管线:")
        for f in orphaned:
            print(f"  XX  {f}")
        print()
        print("请在 paper_context.py 中注册这些模块。")
        print("参考 CLAUDE.md 第5条：模块注册规则。")
        sys.exit(1)
    else:
        print("[OK] 0 个孤立模块，全部已连通。")
        sys.exit(0)


if __name__ == '__main__':
    main()
