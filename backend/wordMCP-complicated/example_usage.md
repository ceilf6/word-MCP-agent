# Word MCP 使用示例

## 基本操作示例

### 1. 创建文档

```python
# 创建新文档
create_word_document(
    file_path="/tmp/test.docx",
    title="测试文档",
    content="这是第一段内容\n这是第二段内容"
)
```

### 2. 读取文档

```python
# 读取文档内容
read_word_document(file_path="/tmp/test.docx")
```

### 3. 更新文档

```python
# 追加内容
update_word_document(
    file_path="/tmp/test.docx",
    action="append",
    content="这是追加的内容"
)

# 添加标题
update_word_document(
    file_path="/tmp/test.docx",
    action="add_heading",
    content="新章节",
    heading_level=2
)

# 替换段落（替换第一个段落）
update_word_document(
    file_path="/tmp/test.docx",
    action="replace",
    content="替换后的内容",
    paragraph_index=0
)
```

### 4. 添加表格

```python
# 添加表格到文档
add_table_to_document(
    file_path="/tmp/test.docx",
    table_data=[
        ["姓名", "年龄", "城市"],
        ["张三", "25", "北京"],
        ["李四", "30", "上海"],
        ["王五", "28", "广州"]
    ],
    title="人员信息表"
)
```

### 5. 列出文档

```python
# 列出目录中的所有 Word 文档
list_word_documents(directory="/tmp")
```

### 6. 删除文档

```python
# 删除文档
delete_word_document(file_path="/tmp/test.docx")
```

## 完整工作流示例

```python
# 1. 创建文档
create_word_document(
    file_path="/tmp/report.docx",
    title="月度报告",
    content="这是报告的第一部分内容"
)

# 2. 添加章节标题
update_word_document(
    file_path="/tmp/report.docx",
    action="add_heading",
    content="数据统计",
    heading_level=2
)

# 3. 添加表格
add_table_to_document(
    file_path="/tmp/report.docx",
    table_data=[
        ["项目", "数量", "金额"],
        ["产品A", "100", "10000"],
        ["产品B", "200", "20000"]
    ],
    title="销售数据"
)

# 4. 追加总结
update_word_document(
    file_path="/tmp/report.docx",
    action="append",
    content="\n总结：本月销售情况良好。"
)

# 5. 读取完整文档
result = read_word_document(file_path="/tmp/report.docx")
print(result["full_text"])
```

