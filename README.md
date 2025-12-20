# Word MCP Agent

一个基于 MCP (Model Context Protocol) 的智能 Word 文档助手。通过自然语言指令创建、编辑和管理 Word 文档。

## 功能特性

### 文档操作
- 📝 **创建文档** - 自动生成带标题和内容的 Word 文档
- 📖 **读取文档** - 提取文档文本和表格内容
- ✏️ **更新文档** - 追加内容、插入段落、替换文本
- 🗑️ **删除文档** - 删除指定文档
- 📋 **列出文档** - 查看所有已创建的文档

### 高级功能
- 📊 **添加表格** - 向文档插入格式化表格
- 🔍 **搜索替换** - 批量替换文档中的文本
- 🌐 **Google 搜索** - 查询信息后自动整理成文档
- 🖼️ **图片搜索/插入** - 搜索图片并插入到文档中

### 智能 Agent
- 使用 DeepSeek-V3 大模型理解自然语言指令
- 自动规划多步骤任务（如：搜索信息 → 整理内容 → 创建文档）
- SSE 实时流式响应，展示执行过程

## 项目结构

```
word-MCP-agent/
├── backend/                 # 后端服务
│   ├── server.py           # FastAPI 主服务器 (SSE + LLM Agent)
│   ├── main.py             # MCP 工具定义
│   ├── mcpconfig.json      # 配置文件 (LLM、API Keys)
│   ├── pyproject.toml      # Python 依赖
│   ├── start.sh            # 启动脚本
│   └── word/               # 生成的文档存放目录
│
├── frontend/                # 前端应用
│   ├── index.tsx           # React 主组件
│   ├── __entry.tsx         # React 入口
│   ├── index.html          # HTML 入口
│   ├── vite.config.ts      # Vite 配置
│   ├── tsconfig.json       # TypeScript 配置
│   └── package.json        # Node 依赖
│
└── README.md
```

## 快速开始

### 1. 配置后端

```bash
cd backend

# 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 或使用启动脚本 (自动处理环境)
./start.sh
```

### 2. 配置 `mcpconfig.json`

编辑 `backend/mcpconfig.json`，填入你的 API 密钥：

```json
{
  "defaultLLM": {
    "baseURL": "https://api.siliconflow.cn/v1",
    "apiToken": "your-api-token",
    "model": "deepseek-ai/DeepSeek-V3"
  },
  "google": "your-serper-api-key"
}
```

- **LLM**: 支持任何 OpenAI 兼容的 API（推荐 SiliconFlow + DeepSeek）
- **Google**: [Serper.dev](https://serper.dev) API Key（用于搜索功能）

### 3. 启动后端服务

```bash
cd backend
source venv/bin/activate
python server.py
```

服务器启动后运行在 `http://localhost:8080`

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务器状态 |
| `/tools` | GET | 获取可用工具列表 |
| `/documents` | GET | 获取文档列表 |
| `/call` | POST | 直接调用工具 |
| `/sse` | GET | SSE 连接 |
| `/sse/call` | POST | SSE 方式调用工具 |
| `/sse/agent` | POST | LLM Agent (SSE 流式) |
| `/chat` | POST | LLM Agent (非流式) |

## 使用示例

在前端界面输入自然语言指令：

```
创建一个关于 React 的介绍文档
```

```
列出所有文档
```

```
帮我搜索一下人工智能的最新发展，然后写成一篇文档
```

```
在文档中添加一个产品对比表格
```

## 技术栈

**后端**
- Python 3.10+
- FastAPI - Web 框架
- python-docx - Word 文档处理
- httpx - HTTP 客户端
- MCP (Model Context Protocol) - 工具协议

**前端**
- React 18
- TypeScript
- Vite - 构建工具
- SSE (Server-Sent Events) - 实时通信

**AI**
- DeepSeek-V3 (via SiliconFlow)
- Serper.dev (Google Search API)

## 开发

### 后端开发

```bash
cd backend
source venv/bin/activate
python server.py
```

### 前端开发

```bash
cd frontend
npm run dev
```

### 构建前端

```bash
cd frontend
npm run build
```

## License

MIT

