#!/bin/bash
# 安装 Git hooks
# 用法: bash scripts/install_hooks.sh

HOOK_DIR=".git/hooks"

if [ ! -d ".git" ]; then
    echo "ERROR: 不在 git 仓库根目录，请在项目根目录运行此脚本"
    exit 1
fi

# pre-commit hook: 检查孤立模块
cat > "$HOOK_DIR/pre-commit" << 'EOF'
#!/bin/bash
python check_orphans.py 2>&1
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 提交被阻止：存在未接入管线的孤立模块。"
    echo "请先将孤立模块注册到 paper_context.py 的 MODULE_REGISTRY 中。"
    echo "参考 CLAUDE.md 第5条。"
    exit 1
fi
EOF

chmod +x "$HOOK_DIR/pre-commit"
echo "✅ Git hooks 安装完成"
echo "  - pre-commit: 自动检查孤立模块"
