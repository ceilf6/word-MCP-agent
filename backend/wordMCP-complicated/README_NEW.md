# Word Document MCP Server v2.0

这是一个功能强大、经过全面重构的 Word 文档操作 MCP (Model Context Protocol) 服务器。

## ✨ 新特性 (v2.0)

### 🎯 核心改进
- ✅ **模块化架构** - 清晰的代码组织，易于维护和扩展
- ✅ **完善的错误处理** - 自定义异常类型，精确的错误信息
- ✅ **日志系统** - 详细的操作日志，便于调试和监控
- ✅ **配置管理** - 环境变量配置，灵活的系统设置
- ✅ **安全增强** - 路径验证、文件大小限制、防路径遍历
- ✅ **性能优化** - 缓存机制、递归深度控制

### 🆕 新增功能
- 📝 **文本格式化** - 字体、大小、颜色、对齐方式
- 🖼️ **图片插入** - 支持多种图片格式，自定义尺寸
- 🔍 **搜索和替换** - 强大的文本搜索和批量替换
- 📊 **文档统计** - 字数、段落数、表格统计等
- 🔗 **文档合并** - 合并多个文档为一个
- 📋 **列表支持** - 项目符号列表和编号列表
- 📄 **分页控制** - 插入分页符

### 🧪 测试覆盖
- ✅ 单元测试套件
- ✅ 核心功能测试
- ✅ 路径工具测试

## 📁 项目结构

```
wordMCP/
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── exceptions.py        # 自定义异常
│   ├── logger.py           # 日志配置
│   ├── path_utils.py       # 路径工具
│   └── document.py         # 文档管理核心
├── tools/                   # MCP 工具
│   ├── __init__.py
│   ├── crud.py             # CRUD 操作
│   ├── formatting.py       # 格式化工具
│   └── advanced.py         # 高级功能
├── tests/                   # 测试套件
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_document.py
│   └── test_path_utils.py
├── logs/                    # 日志目录
├── word/                    # 默认文档目录
├── config.py               # 配置管理
├── main_new.py             # 新版主程序
├── main.py                 # 旧版主程序（兼容）
├── pyproject.toml          # 项目配置
└── README.md               # 本文档
```

## 🚀 安装

### 方式 1: 使用虚拟环境（推荐）

```bash
cd agent/a_MCP/wordMCP

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -e .

# 安装开发依赖（可选）
pip install -e ".[dev]"
```

### 方式 2: 使用 uv

```bash
cd agent/a_MCP/wordMCP
uv sync
```

## 📖 完整功能列表

### 1️⃣ 基础 CRUD 操作

#### `create_word_document`
创建新的 Word 文档

```python
create_word_document(
    file_path="report.docx",  # 可选，默认自动生成
    title="年度报告",
    content="这是报告内容\n第二段"
)
```

#### `read_word_document`
读取文档内容

```python
read_word_document("report.docx")
# 返回: 段落、表格、元数据等
```

#### `update_word_document`
更新文档内容

```python
# 追加内容
update_word_document("report.docx", action="append", content="新段落")

# 插入内容
update_word_document("report.docx", action="insert", paragraph_index=2, content="插入的内容")

# 替换内容
update_word_document("report.docx", action="replace", paragraph_index=0, content="新内容")

# 添加标题
update_word_document("report.docx", action="add_heading", content="第二章", heading_level=2)
```

#### `delete_word_document`
删除文档

```python
delete_word_document("old_report.docx")
```

#### `list_word_documents`
列出目录中的所有文档

```python
list_word_documents("word", recursive=True, max_depth=3)
```

#### `add_table_to_document`
添加表格

```python
add_table_to_document(
    "report.docx",
    table_data=[
        ["姓名", "年龄", "城市"],
        ["张三", "25", "北京"],
        ["李四", "30", "上海"]
    ],
    title="人员信息"
)
```

### 2️⃣ 格式化工具

#### `format_paragraph`
格式化段落文本

```python
format_paragraph(
    "report.docx",
    paragraph_index=0,
    font_name="Arial",
    font_size=14,
    bold=True,
    italic=False,
    color="FF0000",  # 红色
    alignment="center"
)
```

#### `insert_page_break`
插入分页符

```python
insert_page_break("report.docx")
```

#### `add_bullet_list`
添加项目符号列表

```python
add_bullet_list(
    "report.docx",
    items=["项目 1", "项目 2", "项目 3"],
    title="待办事项"
)
```

#### `add_numbered_list`
添加编号列表

```python
add_numbered_list(
    "report.docx",
    items=["步骤 1", "步骤 2", "步骤 3"],
    title="操作步骤"
)
```

### 3️⃣ 高级功能

#### `insert_image`
插入图片

```python
insert_image(
    "report.docx",
    image_path="/path/to/image.png",
    width=5.0,  # 英寸
    caption="图片说明"
)
```

#### `search_text`
搜索文本

```python
search_text(
    "report.docx",
    search_text="重要",
    match_case=False
)
# 返回: 匹配的段落索引和内容
```

#### `replace_text`
搜索并替换文本

```python
replace_text(
    "report.docx",
    search_text="旧文本",
    replace_text="新文本",
    match_case=False,
    max_replacements=10  # 可选，限制替换次数
)
```

#### `merge_documents`
合并多个文档

```python
merge_documents(
    output_path="合并后.docx",
    file_paths=["文档1.docx", "文档2.docx", "文档3.docx"],
    add_page_breaks=True
)
```

#### `get_document_stats`
获取文档统计信息

```python
get_document_stats("report.docx")
# 返回: 字数、段落数、表格数等
```

## ⚙️ 配置

通过环境变量配置服务器行为：

```bash
# Word 文档目录
export WORDMCP_DIR="/path/to/documents"

# 最大文件大小（字节）
export WORDMCP_MAX_SIZE=52428800  # 50MB

# 日志级别
export WORDMCP_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# 日志目录
export WORDMCP_LOG_DIR="/path/to/logs"

# 启用缓存
export WORDMCP_CACHE="true"

# 允许绝对路径
export WORDMCP_ALLOW_ABSOLUTE="true"

# 列表最大深度
export WORDMCP_MAX_DEPTH=3
```

## 🏃 运行

### 测试模式（验证安装）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行测试
python main_new.py --test
```

### 通过 MCP 客户端连接

#### openMCP 配置

- **命令**: `/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP/.venv/bin/python`
- **参数**: `main_new.py`
- **工作目录**: `/Users/a86198/Desktop/Lab/agent/a_MCP/wordMCP`

#### 使用 MCP CLI

```bash
source .venv/bin/activate
mcp run main_new.py
```

## 🧪 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
pytest tests/

# 带覆盖率报告
pytest tests/ --cov=core --cov=tools --cov-report=html

# 查看覆盖率
open htmlcov/index.html  # macOS
```

## 📋 资源 (Resources)

### `file://word_documents`
列出默认目录中的所有文档

### `file://config`
查看当前配置设置

## 💬 提示模板 (Prompts)

### `word_document_help`
获取完整的操作帮助

### `quick_start_guide`
快速入门指南

### `troubleshooting`
故障排除指南

## 🔒 安全特性

- ✅ 路径遍历防护
- ✅ 文件大小限制
- ✅ 文件类型验证
- ✅ 输入验证和清理
- ✅ 错误信息安全

## 📝 日志

日志文件位置：`logs/wordmcp.log`

日志包含：
- 操作记录
- 错误详情
- 性能信息
- 调试信息

## 🔄 从旧版本迁移

旧版 `main.py` 仍然可用，但建议使用新版 `main_new.py`：

```bash
# 旧版（仍然支持）
python main.py

# 新版（推荐）
python main_new.py
```

新版本完全向后兼容，所有旧的工具调用仍然有效。

## 🤝 贡献

欢迎贡献！请确保：
1. 代码通过所有测试
2. 添加新功能时包含测试
3. 更新文档
4. 遵循现有代码风格

## 📄 许可证

MIT

## 🙏 致谢

基于 MCP (Model Context Protocol) 构建
使用 python-docx 库进行 Word 文档操作

