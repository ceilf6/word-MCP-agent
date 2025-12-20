# Word MCP Server v2.0 - 快速参考

## 🚀 快速开始

```bash
# 1. 激活环境
source .venv/bin/activate

# 2. 验证安装
python verify_installation.py

# 3. 测试运行
python main_new.py --test

# 4. 运行测试
pytest tests/ -v
```

## 📦 基础操作

### 创建文档
```python
create_word_document(
    file_path="report.docx",     # 可选
    title="年度报告",
    content="这是内容"
)
```

### 读取文档
```python
read_word_document("report.docx")
```

### 更新文档
```python
# 追加
update_word_document("report.docx", action="append", content="新内容")

# 插入
update_word_document("report.docx", action="insert", paragraph_index=2, content="插入内容")

# 替换
update_word_document("report.docx", action="replace", paragraph_index=0, content="替换内容")

# 添加标题
update_word_document("report.docx", action="add_heading", content="第二章", heading_level=2)
```

### 删除文档
```python
delete_word_document("old.docx")
```

### 列出文档
```python
list_word_documents("word", recursive=True, max_depth=3)
```

### 添加表格
```python
add_table_to_document(
    "report.docx",
    table_data=[["姓名", "年龄"], ["张三", "25"]],
    title="人员表"
)
```

## 🎨 格式化操作

### 格式化段落
```python
format_paragraph(
    "report.docx",
    paragraph_index=0,
    font_name="Arial",
    font_size=14,
    bold=True,
    italic=False,
    color="FF0000",      # 红色
    alignment="center"   # left/center/right/justify
)
```

### 插入分页符
```python
insert_page_break("report.docx")
```

### 添加项目符号列表
```python
add_bullet_list(
    "report.docx",
    items=["项目 1", "项目 2", "项目 3"],
    title="待办"
)
```

### 添加编号列表
```python
add_numbered_list(
    "report.docx",
    items=["步骤 1", "步骤 2", "步骤 3"],
    title="流程"
)
```

## 🔧 高级功能

### 插入图片
```python
insert_image(
    "report.docx",
    image_path="/path/to/image.png",
    width=5.0,           # 英寸
    caption="图片说明"
)
```

### 搜索文本
```python
search_text(
    "report.docx",
    search_text="关键词",
    match_case=False
)
```

### 替换文本
```python
replace_text(
    "report.docx",
    search_text="旧文本",
    replace_text="新文本",
    match_case=False,
    max_replacements=10  # 可选
)
```

### 合并文档
```python
merge_documents(
    output_path="合并.docx",
    file_paths=["doc1.docx", "doc2.docx", "doc3.docx"],
    add_page_breaks=True
)
```

### 文档统计
```python
get_document_stats("report.docx")
# 返回: 字数、段落数、表格数等
```

## ⚙️ 配置

### 环境变量
```bash
# 文档目录
export WORDMCP_DIR="/custom/path"

# 最大文件大小（字节）
export WORDMCP_MAX_SIZE=104857600  # 100MB

# 日志级别
export WORDMCP_LOG_LEVEL="DEBUG"   # DEBUG/INFO/WARNING/ERROR

# 日志目录
export WORDMCP_LOG_DIR="/path/to/logs"

# 启用缓存
export WORDMCP_CACHE="true"

# 允许绝对路径
export WORDMCP_ALLOW_ABSOLUTE="true"

# 最大深度
export WORDMCP_MAX_DEPTH=3

# 最大图片大小
export WORDMCP_MAX_IMAGE_SIZE=10485760  # 10MB
```

## 📊 资源

### 查看文档列表
```
file://word_documents
```

### 查看配置
```
file://config
```

## 💬 提示模板

### 获取帮助
```
word_document_help
```

### 快速入门
```
quick_start_guide
```

### 故障排除
```
troubleshooting
```

## 🔍 调试

### 查看日志
```bash
tail -f logs/wordmcp.log

# 搜索错误
grep ERROR logs/wordmcp.log

# 搜索警告
grep WARNING logs/wordmcp.log
```

### 运行测试
```bash
# 所有测试
pytest tests/ -v

# 特定测试
pytest tests/test_document.py -v

# 带覆盖率
pytest tests/ --cov=core --cov=tools --cov-report=html
```

## 🐛 常见问题

### 问题：找不到模块
```bash
# 解决方案
pip install -e .
```

### 问题：权限错误
```bash
# 解决方案
chmod 755 logs/
chmod 755 word/
```

### 问题：虚拟环境未激活
```bash
# 解决方案
source .venv/bin/activate
```

### 问题：文件未找到
```python
# 使用绝对路径或确保文件在 word/ 目录
read_word_document("/absolute/path/to/file.docx")
# 或
read_word_document("file.docx")  # 自动在 word/ 目录查找
```

## 📱 MCP 客户端配置

### openMCP
```
命令: /path/to/wordMCP/.venv/bin/python
参数: main_new.py
工作目录: /path/to/wordMCP
```

### 标准 MCP CLI
```bash
cd /path/to/wordMCP
source .venv/bin/activate
mcp run main_new.py
```

## 📚 更多信息

- 完整文档: `README_NEW.md`
- 迁移指南: `MIGRATION.md`
- 优化总结: `OPTIMIZATION_SUMMARY.md`
- 更新日志: `CHANGELOG.md`
- 测试文档: `tests/README.md`

## 🎯 常用命令速查

```bash
# 安装
pip install -e .

# 验证
python verify_installation.py

# 测试
python main_new.py --test

# 运行测试
pytest tests/ -v

# 查看日志
tail -f logs/wordmcp.log

# 新版启动脚本
./run_new.sh

# 旧版（兼容）
python main.py --test
```

## 📞 获取帮助

1. 查看日志: `logs/wordmcp.log`
2. 运行验证: `python verify_installation.py`
3. 查看配置: 通过 MCP 客户端调用 `file://config`
4. 使用提示: 调用 `troubleshooting` prompt
5. 运行测试: `pytest tests/ -v`

---

**版本**: v2.0.0  
**文档更新**: 2024-12-20

