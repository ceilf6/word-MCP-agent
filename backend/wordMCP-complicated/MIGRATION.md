# 迁移指南：从 v1.0 到 v2.0

## 重大变更概览

Word MCP Server v2.0 是一个全面重构的版本，带来了更好的性能、可维护性和功能。

## 向后兼容性

✅ **完全向后兼容** - 所有 v1.0 的工具调用在 v2.0 中仍然有效。

## 新文件结构

```
v1.0:
wordMCP/
├── main.py          # 所有代码都在这里
├── pyproject.toml
└── README.md

v2.0:
wordMCP/
├── core/            # 新增：核心模块
├── tools/           # 新增：工具模块
├── tests/           # 新增：测试套件
├── logs/            # 新增：日志目录
├── config.py        # 新增：配置管理
├── main_new.py      # 新版主程序
├── main.py          # 旧版（保留兼容）
└── ...
```

## 迁移步骤

### 1. 备份现有数据（可选）

```bash
# 备份 word 目录
cp -r word word_backup
```

### 2. 更新依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 重新安装
pip install -e .
```

### 3. 测试新版本

```bash
# 运行测试脚本
./run_new.sh

# 或直接测试
python main_new.py --test
```

### 4. 更新 MCP 客户端配置

#### openMCP 配置更新

**旧配置（仍然有效）：**
```
命令: /path/to/.venv/bin/mcp
参数: run main.py
工作目录: /path/to/wordMCP
```

**新配置（推荐）：**
```
命令: /path/to/.venv/bin/python
参数: main_new.py
工作目录: /path/to/wordMCP
```

### 5. 验证功能

使用 MCP 客户端连接后，测试基础功能：

```python
# 创建文档
create_word_document(title="测试", content="测试内容")

# 读取文档
read_word_document("document_*.docx")

# 列出文档
list_word_documents("word")
```

## 新功能使用

### 1. 文本格式化

```python
# v2.0 新功能
format_paragraph(
    "report.docx",
    paragraph_index=0,
    font_size=14,
    bold=True,
    alignment="center"
)
```

### 2. 图片插入

```python
# v2.0 新功能
insert_image(
    "report.docx",
    image_path="/path/to/image.png",
    width=5.0,
    caption="图片说明"
)
```

### 3. 搜索和替换

```python
# v2.0 新功能
search_text("report.docx", "关键词")
replace_text("report.docx", "旧文本", "新文本")
```

### 4. 文档合并

```python
# v2.0 新功能
merge_documents(
    "merged.docx",
    ["doc1.docx", "doc2.docx", "doc3.docx"]
)
```

### 5. 列表支持

```python
# v2.0 新功能
add_bullet_list("report.docx", ["项目1", "项目2", "项目3"])
add_numbered_list("report.docx", ["步骤1", "步骤2", "步骤3"])
```

## 配置系统

v2.0 引入了环境变量配置：

```bash
# 设置自定义配置
export WORDMCP_DIR="/custom/path"
export WORDMCP_MAX_SIZE=104857600  # 100MB
export WORDMCP_LOG_LEVEL="DEBUG"

# 然后运行服务器
python main_new.py
```

## 日志查看

v2.0 提供详细的日志：

```bash
# 查看日志
tail -f logs/wordmcp.log

# 搜索错误
grep ERROR logs/wordmcp.log
```

## 故障排除

### 问题：导入错误

```
ModuleNotFoundError: No module named 'core'
```

**解决方案：**
```bash
# 确保在正确的目录
cd /path/to/wordMCP

# 重新安装
pip install -e .
```

### 问题：权限错误

```
PermissionError: [Errno 13] Permission denied: 'logs/wordmcp.log'
```

**解决方案：**
```bash
# 创建日志目录并设置权限
mkdir -p logs
chmod 755 logs
```

### 问题：旧版本冲突

**解决方案：**
```bash
# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 重新安装
pip install -e . --force-reinstall
```

## 性能改进

v2.0 的性能改进：

- ⚡ **路径解析** - 缓存机制，减少重复计算
- ⚡ **文档列表** - 深度控制，避免过度遍历
- ⚡ **错误处理** - 更快的异常处理
- ⚡ **日志系统** - 异步日志写入（计划中）

## 获取帮助

如果遇到问题：

1. 查看日志文件：`logs/wordmcp.log`
2. 运行测试模式：`python main_new.py --test`
3. 查看资源：使用 MCP 客户端调用 `file://config` 资源
4. 使用提示模板：调用 `troubleshooting` prompt

## 回滚到 v1.0

如果需要回滚：

```bash
# 使用旧版主程序
python main.py

# 或在 openMCP 中使用旧配置
命令: /path/to/.venv/bin/mcp
参数: run main.py
```

## 未来计划

v2.x 路线图：
- 📄 PDF 导出支持
- 🔄 版本控制集成
- 🌐 云存储支持（Google Drive, OneDrive）
- 📊 更多图表支持
- 🎨 模板系统

