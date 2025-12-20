# Word Document MCP Server

这是一个用于 Word 文档增删改查操作的 MCP (Model Context Protocol) 服务器。

## 功能特性

本服务器提供了完整的 Word 文档操作功能：

### 🔧 Tools (工具)

1. **create_word_document** - 创建新的 Word 文档
   - 参数：
     - `file_path` (可选): 文档保存路径或文件名。如果未提供，自动生成带时间戳的文件名。
                         如果提供相对路径或仅文件名，默认保存到 `word/` 子目录。
                         如果提供绝对路径，则使用该路径。
     - `title` (可选): 文档标题
     - `content` (可选): 初始内容
   - 默认行为：未提供 `file_path` 时，自动保存到 `word/` 子目录

2. **read_word_document** - 读取 Word 文档内容
   - 参数：
     - `file_path` (必需): 文档路径。如果是相对路径或仅文件名，先在 `word/` 子目录中查找
   - 返回：文档内容、段落、表格、元数据等

3. **update_word_document** - 更新 Word 文档
   - 参数：
     - `file_path` (必需): 文档路径。如果是相对路径或仅文件名，先在 `word/` 子目录中查找
     - `action` (必需): 操作类型 - "append"（追加）、"insert"（插入）、"replace"（替换）、"add_heading"（添加标题）
     - `content` (可选): 要添加/插入/替换的内容
     - `paragraph_index` (可选): 段落索引（用于 insert/replace）
     - `heading_level` (可选): 标题级别（1-9，用于 add_heading）

4. **delete_word_document** - 删除 Word 文档
   - 参数：
     - `file_path` (必需): 要删除的文档路径。如果是相对路径或仅文件名，先在 `word/` 子目录中查找

5. **list_word_documents** - 列出目录中的所有 Word 文档
   - 参数：
     - `directory` (必需): 要搜索的目录路径
   - 返回：文档列表及其元数据

6. **add_table_to_document** - 向文档添加表格
   - 参数：
     - `file_path` (必需): 文档路径。如果是相对路径或仅文件名，先在 `word/` 子目录中查找
     - `table_data` (必需): 二维列表，表示表格数据（行和列）
     - `title` (可选): 表格标题

### 📦 Resources (资源)

1. **file://word_documents** - 列出 `word/` 子目录中的 Word 文档

### 💬 Prompts (提示模板)

1. **word_document_help** - Word 文档操作帮助

## 安装

### 方法 1: 使用虚拟环境（推荐）

```bash
# 进入项目目录
cd agent/a_MCP/wordMCP

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
python -m pip install --upgrade pip
python -m pip install -e .
```

### 方法 2: 使用 uv（如果已安装）

```bash
cd agent/a_MCP/wordMCP
uv sync
```

## 运行

### ⚠️ 重要提示

**MCP 服务器不能直接运行**。它需要通过 MCP 客户端（如 openMCP）连接使用。

MCP 服务器通过 stdio 接收 JSON-RPC 消息，直接运行会出现 JSON 解析错误，这是正常现象。

### 方法 1: 测试服务器（验证安装）

```bash
# 使用启动脚本测试服务器是否能正常初始化
./run.sh
```

这会验证：
- 虚拟环境是否正确
- 依赖是否已安装
- 服务器是否能正常初始化

### 方法 2: 通过 MCP 客户端连接（实际使用）

#### 使用 openMCP 连接

在 openMCP 中配置：

- **命令**：`/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP/.venv/bin/mcp`
- **参数**：`run main.py`
- **工作目录**：`/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP`

#### 使用 MCP CLI 运行（用于开发测试）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 使用 MCP CLI 运行（这会通过 stdio 与客户端通信）
mcp run main.py
```

### 方法 3: 手动测试（不推荐）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 测试模式：验证服务器初始化
python main.py --test
```

**注意**：
- ❌ 不要直接运行 `python main.py`（没有 `--test` 参数），会出现 JSON 解析错误
- ✅ 使用 `python main.py --test` 可以验证服务器是否正确安装
- ✅ 实际使用需要通过 MCP 客户端连接

## 使用示例

### 创建文档

```python
# 方式1: 不提供路径，自动保存到 word/ 子目录（推荐）
create_word_document(
    title="我的文档",
    content="这是文档的内容\n第二行内容"
)
# 自动保存为: word/document_20231219_205441.docx

# 方式2: 仅提供文件名，保存到 word/ 子目录
create_word_document(
    file_path="report.docx",
    title="报告",
    content="报告内容"
)
# 保存为: word/report.docx

# 方式3: 提供绝对路径，使用指定路径
create_word_document(
    file_path="/tmp/document.docx",
    title="我的文档",
    content="这是文档的内容\n第二行内容"
)
```

### 读取文档

```python
# 方式1: 使用文件名（在 word/ 子目录中查找）
read_word_document(file_path="report.docx")

# 方式2: 使用相对路径
read_word_document(file_path="word/report.docx")

# 方式3: 使用绝对路径
read_word_document(file_path="/path/to/document.docx")
```

### 更新文档

```python
# 追加内容
update_word_document(
    file_path="/path/to/document.docx",
    action="append",
    content="这是追加的内容"
)

# 添加标题
update_word_document(
    file_path="/path/to/document.docx",
    action="add_heading",
    content="新章节",
    heading_level=2
)
```

### 添加表格

```python
add_table_to_document(
    file_path="/path/to/document.docx",
    table_data=[
        ["姓名", "年龄", "城市"],
        ["张三", "25", "北京"],
        ["李四", "30", "上海"]
    ],
    title="人员信息表"
)
```

### 列出文档

```python
list_word_documents(directory="/path/to/documents")
```

### 删除文档

```python
delete_word_document(file_path="/path/to/document.docx")
```

## 连接 openMCP

在 openMCP 中配置：

- **命令**：`/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP/.venv/bin/mcp`
- **参数**：`run main.py`
- **工作目录**：`/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP`

## 项目结构

```
wordMCP/
├── main.py          # Word MCP 服务器主文件
├── pyproject.toml  # 项目配置和依赖
├── README.md        # 项目说明
└── .venv/           # 虚拟环境目录（创建后生成）
```

## 依赖

- `mcp[cli]>=1.24.0` - MCP 协议支持（包含 FastMCP）
- `python-docx>=1.1.0` - Word 文档操作库

## 注意事项

1. **默认保存位置**：所有文档默认保存到当前工作目录下的 `word/` 子目录
   - 如果未提供 `file_path`，会自动生成带时间戳的文件名
   - 如果提供相对路径或仅文件名，会自动保存到 `word/` 子目录
   - 如果提供绝对路径，则使用指定的绝对路径

2. **路径查找规则**：
   - 读取、更新、删除操作时，如果提供相对路径或文件名，会先在 `word/` 子目录中查找
   - 如果找不到，再尝试使用原始路径

3. 创建文档时，如果目录不存在会自动创建

4. 文档路径必须以 `.docx` 结尾（如果未提供会自动添加）

5. 更新操作支持多种模式：追加、插入、替换、添加标题

## 许可证

MIT

