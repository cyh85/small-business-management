#!/usr/bin/env bash
# 横纵分析法 Skill 一键安装器 (Mac / Linux)
# 用法: curl -fsSL https://raw.githubusercontent.com/cyh85/small-business-management/main/install.sh | bash

set -e

REPO_URL="https://github.com/cyh85/small-business-management"
ZIP_URL="$REPO_URL/archive/refs/heads/main.zip"
SKILL_NAME="hv-analysis"

# 各工具 skills 目录
TARGETS=(
    "Claude:$HOME/.claude/skills"
    "Cursor:$HOME/.cursor/skills"
    "OpenCode:$HOME/.config/opencode/skills"
)

echo ""
echo -e "\033[36m[横纵分析法] 一键安装器\033[0m"
echo -e "\033[36m================================\033[0m"

# 1. 下载 ZIP
TMPDIR=$(mktemp -d)
ZIP="$TMPDIR/repo.zip"
echo -e "\033[33m[1/4] 下载仓库 ZIP ...\033[0m"
if ! curl -fsSL "$ZIP_URL" -o "$ZIP"; then
    echo -e "\033[31m  下载失败,请检查网络(可能需要代理)或手动 clone 仓库。\033[0m"
    exit 1
fi

# 2. 解压
echo -e "\033[33m[2/4] 解压 ...\033[0m"
EXTRACT="$TMPDIR/extracted"
mkdir -p "$EXTRACT"
unzip -q "$ZIP" -d "$EXTRACT"

SOURCE=$(find "$EXTRACT" -type d -name "$SKILL_NAME" | head -n 1)
if [ -z "$SOURCE" ]; then
    echo -e "\033[31m  未找到 skills/$SKILL_NAME,仓库结构可能已变更。\033[0m"
    exit 1
fi

# 3. 检测并复制
echo -e "\033[33m[3/4] 检测 AI 工具并安装 Skill ...\033[0m"
INSTALLED_ANY=false
for entry in "${TARGETS[@]}"; do
    NAME="${entry%%:*}"
    BASE="${entry#*:}"
    if [ -d "$BASE" ]; then
        DEST="$BASE/$SKILL_NAME"
        rm -rf "$DEST"
        cp -r "$SOURCE" "$DEST"
        echo -e "\033[32m  [OK] 已安装到 $NAME: $DEST\033[0m"
        INSTALLED_ANY=true
    fi
done

if [ "$INSTALLED_ANY" = false ]; then
    BASE="$HOME/.claude/skills"
    mkdir -p "$BASE"
    DEST="$BASE/$SKILL_NAME"
    cp -r "$SOURCE" "$DEST"
    echo -e "\033[32m  [默认] 未检测到已有工具,已安装到 Claude: $DEST\033[0m"
    echo -e "\033[90m  如果你用 Cursor / OpenCode,请手动把 $DEST 复制到对应 skills 目录。\033[0m"
fi

# 4. 清理
echo -e "\033[33m[4/4] 清理临时文件 ...\033[0m"
rm -rf "$TMPDIR"

echo -e "\n\033[32m[完成] 横纵分析法 Skill 已安装!\033[0m"
echo -e "\033[37m使用方法:在 Claude / Cursor / OpenCode 中直接说\"用横纵分析法研究 XXX\"\033[0m"
echo -e "\033[90m或查看课程配套 README: https://github.com/cyh85/small-business-management\033[0m\n"
