#!/bin/bash
# Word MCP Server 启动脚本
# 
# 注意：MCP 服务器需要通过 MCP 客户端连接使用，而不是直接运行
# 此脚本主要用于测试服务器是否能正常初始化

cd "$(dirname "$0")"
source .venv/bin/activate

# 测试模式：验证服务器是否能正常初始化
python main.py --test

