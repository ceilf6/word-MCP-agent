# Word MCP Server

一个支持 **stdio** 和 **SSE** 两种传输方式的 Word 文档 MCP 服务器。

## 功能

- 📄 创建 Word 文档
- 📖 读取文档内容
- ✏️ 更新文档（追加/插入/替换）
- 🗑️ 删除文档
- 📋 列出所有文档
- 📊 添加表格
- 🔍 搜索替换

## 快速开始

### 1. 安装依赖

```bash
cd agent/_MCP/wordMCP

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装
python -m pip install -e .
```

### 2. 运行方式

#### 方式 A: SSE 服务器（推荐，支持前端调用）

```bash
# 使用启动脚本
./start.sh

# 或手动运行
source .venv/bin/activate
python server.py
```

服务器启动后访问: http://localhost:8080

#### 方式 B: stdio 方式（MCP 客户端）

```bash
source .venv/bin/activate
python main.py
```

## SSE API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务器状态 |
| `/tools` | GET | 获取工具列表 |
| `/documents` | GET | 获取文档列表 |
| `/call` | POST | 调用工具 |
| `/sse` | GET | SSE 连接 |
| `/sse/call` | POST | SSE 方式调用工具 |

### 调用示例

```bash
# 获取工具列表
curl http://localhost:8080/tools

# 创建文档
curl -X POST http://localhost:8080/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "create_document", "params": {"title": "测试", "content": "内容"}}'

# 读取文档
curl -X POST http://localhost:8080/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "read_document", "params": {"filename": "test.docx"}}'
```

## 前端集成

前端组件位于: `sandboxs/wordMCP/index.tsx`

```tsx
// 连接 SSE
const es = new EventSource('http://localhost:8080/sse');

// 调用工具
const res = await fetch('http://localhost:8080/sse/call', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tool: 'list_documents', params: {} })
});
```

## 项目结构

```
wordMCP/
├── main.py          # stdio 方式服务器
├── server.py        # SSE 方式服务器
├── start.sh         # 启动脚本
├── pyproject.toml   # 项目配置
├── mcpconfig.json   # MCP 配置
├── README.md        # 本文档
└── word/            # 文档存储目录
```

## 配置

### mcpconfig.json (openMCP 用)

```json
{
  "mcpServers": {
    "Word Document MCP Server": {
      "type": "stdio",
      "command": "mcp",
      "args": ["run", "main.py"],
      "cwd": "/path/to/wordMCP"
    }
  }
}
```

## 许可证

MIT
