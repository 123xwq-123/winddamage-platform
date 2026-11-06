#!/bin/bash
# 风电结构损伤检测智能平台 — 一键启动脚本
# 用法: ./start.sh

set -e

# ─── 配置 ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${HOME}/miniforge3/envs/winddamage/bin/python"
PORT=7860

cd "$SCRIPT_DIR"

echo "============================================================"
echo "  风电塔灾损测算多模态大模型可视化软件 V1.0"
echo "  风电机组结构损伤智能检测与评估系统"
echo "============================================================"

# ─── 检查 Python 环境 ─────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo "❌ 未找到 winddamage 环境 ($PYTHON)"
    echo "   请先运行:"
    echo "   conda create -n winddamage python=3.11 -y"
    echo "   conda activate winddamage"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# ─── 检查模型 ─────────────────────────────────────────────
if [ ! -f "qwen3.5-4b/config.json" ]; then
    echo "❌ 未找到模型文件: qwen3.5-4b/config.json"
    exit 1
fi

# ─── 检查端口占用 ─────────────────────────────────────────
if lsof -i :$PORT >/dev/null 2>&1; then
    echo "⚠️  端口 $PORT 被占用，尝试 $((PORT + 1))..."
    PORT=$((PORT + 1))
fi

echo "  Python:  $PYTHON"
echo "  模型:    $SCRIPT_DIR/qwen3.5-4b/"
echo "  端口:    $PORT"
echo "  访问:    http://localhost:$PORT"
echo "============================================================"

# ─── 启动 ─────────────────────────────────────────────────
exec "$PYTHON" app.py
