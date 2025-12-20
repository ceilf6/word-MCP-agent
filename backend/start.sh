#!/bin/bash
# Word MCP Server (SSE) 启动脚本

cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查/安装依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 安装依赖..."
    python -m pip install --upgrade pip
    python -m pip install -e .
fi

echo ""
echo "🚀 启动 Word MCP Server (SSE)"
echo ""

# 运行服务器
python server.py

