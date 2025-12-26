# Word MCP Agent

一个基于 MCP (Model Context Protocol) 的智能 Word 文档助手。通过自然语言指令创建、编辑和管理 Word 文档，具备**多 Agent 协作**和**记忆能力**。

## ✨ 核心特性

### 🤖 多 Agent 流水线

文档创建采用三阶段 Agent 协作，确保高质量输出：

```
用户请求
    ↓
┌─────────────────────────────────────┐
│ 🔍 结构化 Agent (Structurizer)       │
│ • 解析用户意图                        │
│ • 提取参数（文件名、标题、内容要求）     │
│ • 识别缺失信息，向用户提问              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ ✍️ 创作 Agent (Writer)               │
│ • 根据结构化数据生成内容               │
│ • 调整写作风格                        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ ⭐ 评审 Agent (Reviewer)             │
│ • 评估文档质量 (1-10分)               │
│ • 评分 < 7 → 返回创作Agent重写        │
│ • 最多 3 轮迭代优化                   │
└─────────────────────────────────────┘
    ↓
高质量文档输出
```

### 🧠 三层记忆系统

| 记忆层级 | 说明 | 持久化 |
|----------|------|--------|
| **短期记忆** | 当前会话的对话历史（最近20轮） | ❌ |
| **工作记忆** | 当前任务的上下文和临时变量 | ❌ |
| **长期记忆** | 用户偏好、重要事实（自动提取） | ✅ JSON |

特点：
- 自动提取用户偏好（写作风格、命名习惯等）
- 支持多会话隔离（通过 `session_id`）
- 长期记忆按重要性自动清理

### 📝 文档操作

| 功能 | 说明 |
|------|------|
| 📝 创建文档 | 通过多Agent流水线生成高质量文档 |
| 📖 读取文档 | 提取文档文本和表格内容 |
| ✏️ 更新文档 | 追加内容、插入段落、替换文本 |
| 🗑️ 删除文档 | 删除指定文档 |
| 📋 列出文档 | 查看所有已创建的文档 |
| 📊 添加表格 | 向文档插入格式化表格 |
| 🔍 搜索替换 | 批量替换文档中的文本 |

### 🌐 外部能力

| 功能 | 说明 |
|------|------|
| 🔎 Google 搜索 | 查询信息并整理成文档 |
| 🖼️ 图片搜索 | 搜索相关图片 |
| ⬇️ 图片下载 | 从URL下载图片到本地 |
| 🖼️ 插入图片 | 将图片插入到文档中 |

## 📁 项目结构

```
word-MCP-agent/
├── backend/                 # 后端服务
│   ├── server.py           # FastAPI 主服务器 (SSE + LLM Agent + 记忆)
│   ├── main.py             # MCP 工具定义
│   ├── agents.py           # 多 Agent 模块 (结构化/创作/评审)
│   ├── memory.py           # 三层记忆系统
│   ├── mcpconfig.json      # 配置文件 (LLM、API Keys)
│   ├── pyproject.toml      # Python 依赖
│   ├── start.sh            # 启动脚本
│   ├── word/               # 生成的文档存放目录
│   └── memory_store/       # 长期记忆持久化目录
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

## 🚀 快速开始

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

- **LLM**: 支持 OpenAI 兼容的任何大模型
- **Google**: [Serper.dev](https://serper.dev) API Key（用于搜索功能）

### 3. 启动后端服务

```bash
cd backend
./start.sh
# 或
source venv/bin/activate && python server.py
```

服务器启动后运行在 `http://localhost:8080`

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`

## 📡 API 端点

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务器状态 |
| `/tools` | GET | 获取可用工具列表 |
| `/documents` | GET | 获取文档列表 |
| `/call` | POST | 直接调用工具 |
| `/sse` | GET | SSE 连接 |
| `/sse/agent` | POST | LLM Agent (SSE 流式, 带记忆) |
| `/chat` | POST | LLM Agent (非流式) |

### 记忆管理端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/memory/sessions` | GET | 列出所有会话 |
| `/memory/session/{id}` | GET | 获取会话信息 |
| `/memory/session/{id}` | DELETE | 删除会话 |
| `/memory/session/{id}/clear` | POST | 清空短期记忆 |
| `/memory/session/{id}/history` | GET | 获取对话历史 |
| `/memory/session/{id}/remember` | POST | 添加长期记忆 |
| `/memory/session/{id}/recall` | GET | 搜索长期记忆 |

## 💡 使用示例

### 基础文档创建

```
创建一个关于 React 的介绍文档
```

```
列出所有文档
```

### 多 Agent 协作

当输入较模糊时，结构化 Agent 会询问更多信息：

```
用户: 帮我写一份文档
助手: 请问文档要叫什么名字？
用户: 年度报告
助手: [创作Agent生成内容] → [评审Agent评分8/10] → 文档创建成功！
```

### 结合搜索

```
帮我搜索一下人工智能的最新发展，然后写成一篇文档
```

### 插入图片

```
创建一份关于圣诞节的文档并插入一些精美的相关图片
```

### 使用记忆功能

```javascript
// 前端发送请求时指定 session_id
fetch('/sse/agent', {
  method: 'POST',
  body: JSON.stringify({
    query: "帮我创建一个文档",
    session_id: "user_123"  // 不同用户使用不同 session_id
  })
})
```

## 🔧 可用工具

### 文档工具

| 工具名 | 说明 |
|--------|------|
| `create_document_with_agents` | 【推荐】多Agent流水线创建文档 |
| `structurize_input` | 仅结构化解析用户输入 |
| `create_document` | 直接创建文档（无质量检查） |
| `read_document` | 读取文档内容 |
| `update_document` | 更新文档 |
| `delete_document` | 删除文档 |
| `list_documents` | 列出所有文档 |
| `add_table` | 添加表格 |
| `search_replace` | 搜索替换 |

### 搜索工具

| 工具名 | 说明 |
|--------|------|
| `google_search` | Google 搜索文字信息 |
| `google_image_search` | Google 图片搜索 |
| `download_image` | 下载图片到本地 |
| `insert_image` | 将图片插入文档 |

### 记忆工具

| 工具名 | 说明 |
|--------|------|
| `save_to_memory` | 保存到长期记忆 |
| `recall_memory` | 从长期记忆检索 |
| `get_memory_stats` | 获取记忆统计 |

## 🏗️ 技术栈

**后端**
- Python 3.10+
- FastAPI - Web 框架
- python-docx - Word 文档处理
- httpx - HTTP 客户端
- MCP (Model Context Protocol) - 工具协议

**多 Agent 系统**
- 自研 Agent Pipeline
- 支持 AgentScope 集成（可选）

**记忆系统**
- 三层记忆架构
- JSON 文件持久化
- 按重要性自动清理

**前端**
- React 18
- TypeScript
- Vite - 构建工具
- SSE (Server-Sent Events) - 实时通信

**AI**
- DeepSeek-V3 / 其他大模型
- Serper.dev (Google Search API)

## 🔌 扩展开发

### 添加新 Agent

在 `backend/agents.py` 中继承 `BaseAgent`：

```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent", "系统提示词")
    
    def process(self, input_data):
        # 处理逻辑
        return result
```

### 添加新工具

在 `backend/server.py` 的 `TOOLS` 和 `TOOL_HANDLERS` 中注册：

```python
TOOLS["my_tool"] = {
    "description": "工具说明",
    "parameters": {...}
}

def my_tool_handler(**kwargs):
    return {"success": True, "result": ...}

TOOL_HANDLERS["my_tool"] = my_tool_handler
```

### 自定义记忆提取

在 `backend/memory.py` 的 `Session._extract_to_long_term` 中添加规则：

```python
def _extract_to_long_term(self, role: str, content: str):
    if "我喜欢" in content:
        self.long_term.add(
            f"用户偏好: {content}",
            category="preference",
            importance=0.8
        )
```

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (React)                             │
│                    http://localhost:3000                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSE / HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server                               │
│                    http://localhost:8080                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   LLM 调用    │  │  工具执行器   │  │  SSE 流      │            │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘           │
│         │                 │                                     │
│  ┌──────▼─────────────────▼──────┐                              │
│  │        多 Agent Pipeline       │                             │
│  │  ┌────────┐ ┌────────┐ ┌────────┐                            │
│  │  │结构化   │→│创作     │→│评审    │                            │
│  │  │Agent   │ │Agent   │ │Agent   │                            │
│  │  └────────┘ └────────┘ └────────┘                            │
│  └───────────────────────────────┘                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    记忆系统                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │    │
│  │  │短期记忆   │  │工作记忆    │  │长期记忆 (JSON持久化)│  │  │     │
│  │  └──────────┘  └──────────┘  └──────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    工具集                                │    │
│  │  文档操作 │ 搜索功能 │ 图片处理 │ 记忆操作                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   外部服务                │
              │  • LLM API               │
              │  • Serper.dev (搜索)      │
              └──────────────────────────┘
```

## 📝 更新日志

### v2.0.0
- ✨ 新增多 Agent 流水线（结构化/创作/评审）
- ✨ 新增三层记忆系统
- ✨ 新增记忆管理 API
- 🔧 优化文档创建质量

### v1.0.0
- 🎉 初始版本
- 📝 基础文档操作
- 🌐 Google 搜索集成
- 🖼️ 图片搜索和插入

## License

MIT
