#!/bin/bash
# Word MCP Server v2.0 启动脚本
# 
# 注意：MCP 服务器需要通过 MCP 客户端连接使用，而不是直接运行
# 此脚本主要用于测试服务器是否能正常初始化

cd "$(dirname "$0")"

# 检查虚拟环境是否存在
if [ ! -d ".venv" ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    python3 -m venv .venv
    echo "✓ 虚拟环境创建成功"
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖是否安装
if ! python -c "import mcp" 2>/dev/null; then
    echo "⚠️  依赖未安装，正在安装..."
    pip install -e .
    echo "✓ 依赖安装成功"
fi

# 测试模式：验证服务器是否能正常初始化
echo ""
echo "=========================================="
echo "  Word MCP Server v2.0 测试模式"
echo "=========================================="
echo ""

python main_new.py --test

echo ""
echo "=========================================="
echo "  提示：要在 openMCP 中使用此服务器，请配置："
echo ""
echo "  命令: $(pwd)/.venv/bin/python"
echo "  参数: main_new.py"
echo "  工作目录: $(pwd)"
echo "=========================================="

