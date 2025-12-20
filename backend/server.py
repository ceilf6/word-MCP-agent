"""
Word MCP Server with SSE Transport + LLM Agent

启动方式:
    python server.py

服务器会在 http://localhost:8080 启动 SSE 端点
使用 mcpconfig.json 中的 defaultLLM 配置调用大模型
"""

import asyncio
import json
import logging
from typing import Optional, List, Any
from pathlib import Path
from datetime import datetime
import re
import httpx

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# 默认字体设置
DEFAULT_FONT_NAME = "宋体"
DEFAULT_FONT_SIZE = Pt(12)


def set_run_font(run, font_name: str = DEFAULT_FONT_NAME, font_size=DEFAULT_FONT_SIZE):
    """设置 run 的字体为宋体"""
    run.font.name = font_name
    run.font.size = font_size
    # 设置中文字体（东亚字体）
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 应用
app = FastAPI(title="Word MCP Server")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文档目录
WORD_DIR = Path("word")
WORD_DIR.mkdir(exist_ok=True)

# ==================== 加载配置 ====================

def load_config() -> dict:
    """从 mcpconfig.json 加载所有配置"""
    config_path = Path(__file__).parent / "mcpconfig.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return {}

CONFIG = load_config()
LLM_CONFIG = CONFIG.get("defaultLLM", {})
GOOGLE_API_KEY = CONFIG.get("google", "")

logger.info(f"LLM 配置: baseURL={LLM_CONFIG.get('baseURL')}, model={LLM_CONFIG.get('model')}")
logger.info(f"Google API Key: {'已配置' if GOOGLE_API_KEY else '未配置'}")


# ==================== 工具函数 ====================

def get_file_path(filename: str) -> Path:
    """获取文件完整路径"""
    path = Path(filename)
    if not path.is_absolute():
        path = WORD_DIR / filename
    if not str(path).endswith('.docx'):
        path = Path(str(path) + '.docx')
    return path


# ==================== MCP 工具定义 ====================

TOOLS = {
    "create_document": {
        "description": "创建新的 Word 文档",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名（不含扩展名）"},
                "title": {"type": "string", "description": "文档标题"},
                "content": {"type": "string", "description": "初始内容（可包含多行）"}
            },
            "required": []
        }
    },
    "read_document": {
        "description": "读取 Word 文档内容",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"}
            },
            "required": ["filename"]
        }
    },
    "update_document": {
        "description": "更新 Word 文档，支持追加内容、添加标题、插入段落、替换段落",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"},
                "action": {"type": "string", "enum": ["append", "insert", "replace", "add_heading"], "description": "操作类型"},
                "content": {"type": "string", "description": "要写入的内容"},
                "paragraph_index": {"type": "integer", "description": "段落索引（insert/replace 时使用）"}
            },
            "required": ["filename", "action"]
        }
    },
    "delete_document": {
        "description": "删除 Word 文档",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"}
            },
            "required": ["filename"]
        }
    },
    "list_documents": {
        "description": "列出所有 Word 文档",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "add_table": {
        "description": "向文档添加表格",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"},
                "table_data": {"type": "array", "description": "表格数据（二维数组），第一行为表头", "items": {"type": "array", "items": {"type": "string"}}},
                "title": {"type": "string", "description": "表格标题（可选）"}
            },
            "required": ["filename", "table_data"]
        }
    },
    "search_replace": {
        "description": "搜索并替换文档中的文本",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"},
                "search_text": {"type": "string", "description": "要搜索的文本"},
                "replace_text": {"type": "string", "description": "替换为的文本"}
            },
            "required": ["filename", "search_text", "replace_text"]
        }
    },
    "google_search": {
        "description": "使用 Google 搜索获取信息。当需要查询最新资讯、获取某个主题的详细信息时使用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "num_results": {"type": "integer", "description": "返回结果数量，默认5条", "default": 5}
            },
            "required": ["query"]
        }
    },
    "google_image_search": {
        "description": "使用 Google 搜索图片。返回图片 URL 列表，可配合 download_image 下载后用 insert_image 插入文档。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "图片搜索关键词"},
                "num_results": {"type": "integer", "description": "返回结果数量，默认5条", "default": 5}
            },
            "required": ["query"]
        }
    },
    "download_image": {
        "description": "从 URL 下载图片到本地。下载后可使用 insert_image 工具将图片插入文档。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "图片的 URL 地址"},
                "filename": {"type": "string", "description": "保存的文件名（可选）"}
            },
            "required": ["url"]
        }
    },
    "insert_image": {
        "description": "将本地图片插入到 Word 文档中。需要先用 download_image 下载图片。",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Word 文档文件名"},
                "image_path": {"type": "string", "description": "图片的本地路径"},
                "width": {"type": "number", "description": "图片宽度（英寸），可选"}
            },
            "required": ["filename", "image_path"]
        }
    }
}


# ==================== 工具实现 ====================

def create_document(filename: str = None, title: str = None, content: str = None) -> dict:
    """创建新文档（默认使用宋体）"""
    try:
        if not filename:
            filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        file_path = get_file_path(filename)
        doc = Document()
        
        if title:
            heading = doc.add_heading(title, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 设置标题字体为宋体
            for run in heading.runs:
                set_run_font(run, font_size=Pt(18))
        
        if content:
            for line in content.split('\n'):
                para = doc.add_paragraph()
                run = para.add_run(line.strip() if line.strip() else "")
                set_run_font(run)
        
        doc.save(str(file_path))
        
        return {
            "success": True,
            "message": "文档创建成功",
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_document(filename: str) -> dict:
    """读取文档"""
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {filename}"}
        
        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs]
        
        tables = []
        for table in doc.tables:
            table_data = [[cell.text for cell in row.cells] for row in table.rows]
            tables.append(table_data)
        
        return {
            "success": True,
            "file_path": str(file_path),
            "paragraphs": paragraphs,
            "paragraph_count": len(paragraphs),
            "tables": tables,
            "table_count": len(tables),
            "full_text": "\n".join(paragraphs)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_document(filename: str, action: str, content: str = None, paragraph_index: int = None) -> dict:
    """更新文档（默认使用宋体）"""
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {filename}"}
        
        doc = Document(str(file_path))
        
        if action == "append" and content:
            for line in content.split('\n'):
                para = doc.add_paragraph()
                run = para.add_run(line)
                set_run_font(run)
        elif action == "add_heading" and content:
            heading = doc.add_heading(content, level=2)
            for run in heading.runs:
                set_run_font(run, font_size=Pt(16))
        elif action == "insert" and content and paragraph_index is not None:
            if paragraph_index < len(doc.paragraphs):
                new_para = doc.paragraphs[paragraph_index].insert_paragraph_before()
                run = new_para.add_run(content)
                set_run_font(run)
        elif action == "replace" and paragraph_index is not None:
            if paragraph_index < len(doc.paragraphs):
                para = doc.paragraphs[paragraph_index]
                para.clear()
                run = para.add_run(content or "")
                set_run_font(run)
        else:
            return {"success": False, "error": "无效的操作或缺少参数"}
        
        doc.save(str(file_path))
        return {"success": True, "message": "文档更新成功", "action": action}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_document(filename: str) -> dict:
    """删除文档"""
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {filename}"}
        
        file_path.unlink()
        return {"success": True, "message": "文档删除成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_documents() -> dict:
    """列出所有文档"""
    try:
        docs = []
        for file in WORD_DIR.glob("*.docx"):
            stat = file.stat()
            docs.append({
                "name": file.name,
                "path": str(file),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return {"success": True, "count": len(docs), "documents": docs}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_table(filename: str, table_data: list, title: str = None) -> dict:
    """添加表格（默认使用宋体）"""
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {filename}"}
        
        doc = Document(str(file_path))
        
        if title:
            heading = doc.add_heading(title, level=2)
            for run in heading.runs:
                set_run_font(run, font_size=Pt(16))
        
        if table_data:
            rows = len(table_data)
            cols = max(len(row) for row in table_data)
            table = doc.add_table(rows=rows, cols=cols)
            table.style = 'Light Grid Accent 1'
            
            for i, row_data in enumerate(table_data):
                for j, cell_data in enumerate(row_data):
                    if j < cols:
                        cell = table.rows[i].cells[j]
                        cell.text = ""  # 清空默认文本
                        para = cell.paragraphs[0]
                        run = para.add_run(str(cell_data))
                        set_run_font(run)
        
        doc.save(str(file_path))
        return {"success": True, "message": "表格添加成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_replace(filename: str, search_text: str, replace_text: str) -> dict:
    """搜索替换"""
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文件不存在: {filename}"}
        
        doc = Document(str(file_path))
        count = 0
        
        for para in doc.paragraphs:
            for run in para.runs:
                if search_text in run.text:
                    run.text = run.text.replace(search_text, replace_text)
                    count += 1
        
        doc.save(str(file_path))
        return {"success": True, "message": f"替换了 {count} 处", "count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def google_search_async(query: str, num_results: int = 5) -> dict:
    """
    使用 Serper.dev API 进行 Google 搜索（异步版本）
    需要 GOOGLE_API_KEY 配置（从 serper.dev 获取）
    """
    if not GOOGLE_API_KEY:
        return {"success": False, "error": "Google API Key 未配置"}
    
    try:
        # 使用 Serper.dev API
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": GOOGLE_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results,
            "hl": "zh-CN",
            "gl": "cn"
        }
        
        async with httpx.AsyncClient(timeout=30.0, proxy=None) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        
        # 解析搜索结果
        results = []
        
        # 提取有机搜索结果
        organic_results = data.get("organic", [])
        for item in organic_results[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        
        # 如果有答案框
        if "answerBox" in data:
            answer = data["answerBox"]
            results.insert(0, {
                "title": answer.get("title", "答案"),
                "link": answer.get("link", ""),
                "snippet": answer.get("answer", answer.get("snippet", ""))
            })
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
        
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"搜索请求失败: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"搜索出错: {str(e)}"}


def google_search(query: str, num_results: int = 5) -> dict:
    """
    使用 Google 搜索（同步包装器）
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, google_search_async(query, num_results))
                return future.result()
        else:
            return asyncio.run(google_search_async(query, num_results))
    except Exception as e:
        return {"success": False, "error": f"搜索执行失败: {str(e)}"}


def google_image_search(query: str, num_results: int = 5) -> dict:
    """
    使用 Serper.dev API 搜索图片
    """
    if not GOOGLE_API_KEY:
        return {"success": False, "error": "Google API Key 未配置"}
    
    try:
        # 使用 Serper.dev 图片搜索 API
        url = "https://google.serper.dev/images"
        headers = {
            "X-API-KEY": GOOGLE_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results,
            "hl": "zh-CN"
        }
        
        with httpx.Client(timeout=30.0, proxy=None) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        
        results = []
        images_results = data.get("images", [])
        
        for item in images_results[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "image_url": item.get("imageUrl", ""),
                "thumbnail": item.get("thumbnailUrl", ""),
                "source": item.get("source", ""),
                "link": item.get("link", "")
            })
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "images": results
        }
        
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"搜索请求失败: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"搜索出错: {str(e)}"}


def download_image(url: str, filename: str = None) -> dict:
    """
    从 URL 下载图片到本地
    """
    try:
        # 创建图片目录
        images_dir = WORD_DIR / "images"
        images_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        if not filename:
            url_filename = url.split("/")[-1].split("?")[0]
            if url_filename and "." in url_filename:
                filename = url_filename
            else:
                filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        else:
            if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                filename = f"{filename}.jpg"
        
        file_path = images_dir / filename
        
        # 下载图片
        with httpx.Client(timeout=30.0, follow_redirects=True, proxy=None) as client:
            response = client.get(url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                return {"success": False, "error": f"URL 不是图片: {content_type}"}
            
            with open(file_path, "wb") as f:
                f.write(response.content)
        
        return {
            "success": True,
            "message": "图片下载成功",
            "local_path": str(file_path),
            "filename": filename,
            "size": file_path.stat().st_size
        }
        
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"下载失败: HTTP {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"下载出错: {str(e)}"}


def insert_image(filename: str, image_path: str, width: float = None) -> dict:
    """
    将图片插入到 Word 文档中
    """
    try:
        file_path = get_file_path(filename)
        
        if not file_path.exists():
            return {"success": False, "error": f"文档不存在: {filename}"}
        
        if not Path(image_path).exists():
            return {"success": False, "error": f"图片不存在: {image_path}"}
        
        doc = Document(str(file_path))
        
        if width:
            doc.add_picture(image_path, width=Inches(width))
        else:
            doc.add_picture(image_path, width=Inches(4))  # 默认宽度 4 英寸
        
        doc.save(str(file_path))
        
        return {
            "success": True,
            "message": "图片插入成功",
            "image_path": image_path
        }
    except Exception as e:
        return {"success": False, "error": f"插入图片失败: {str(e)}"}


# 工具映射
TOOL_HANDLERS = {
    "create_document": create_document,
    "read_document": read_document,
    "update_document": update_document,
    "delete_document": delete_document,
    "list_documents": list_documents,
    "add_table": add_table,
    "search_replace": search_replace,
    "google_search": google_search,
    "google_image_search": google_image_search,
    "download_image": download_image,
    "insert_image": insert_image,
}


# ==================== LLM 调用 ====================

def get_tools_for_llm() -> list:
    """将工具定义转换为 OpenAI function calling 格式"""
    tools = []
    for name, info in TOOLS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"]
            }
        })
    return tools


async def call_llm(messages: list, tools: list = None) -> dict:
    """调用 LLM API"""
    if not LLM_CONFIG:
        raise ValueError("LLM 配置未加载")
    
    base_url = LLM_CONFIG.get("baseURL", "").rstrip("/")
    api_token = LLM_CONFIG.get("apiToken")
    model = LLM_CONFIG.get("model")
    
    if not all([base_url, api_token, model]):
        raise ValueError("LLM 配置不完整")
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """执行工具调用"""
    if tool_name not in TOOL_HANDLERS:
        return {"success": False, "error": f"未知工具: {tool_name}"}
    
    handler = TOOL_HANDLERS[tool_name]
    return handler(**arguments)


def parse_qwen_tool_calls(reasoning_content: str) -> list:
    """
    解析 Qwen 模型 reasoning_content 中的 <tool_call> 标签
    格式: <tool_call>\n{"name": "xxx", "arguments": {...}}\n</tool_call>
    """
    tool_calls = []
    
    # 匹配 <tool_call>...</tool_call> 中的 JSON
    pattern = r'<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)'
    matches = re.findall(pattern, reasoning_content, re.DOTALL)
    
    for idx, json_str in enumerate(matches):
        try:
            # 清理 JSON 字符串（处理可能的截断）
            json_str = json_str.strip()
            
            # 尝试修复不完整的 JSON（如果被截断）
            if not json_str.endswith('}'):
                # 尝试找到最后一个完整的 }
                last_brace = json_str.rfind('}')
                if last_brace > 0:
                    json_str = json_str[:last_brace + 1]
            
            data = json.loads(json_str)
            tool_name = data.get("name")
            arguments = data.get("arguments", {})
            
            if tool_name and tool_name in TOOL_HANDLERS:
                tool_calls.append({
                    "id": f"qwen_call_{idx}",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments, ensure_ascii=False) if isinstance(arguments, dict) else arguments
                    }
                })
        except json.JSONDecodeError as e:
            logger.warning(f"解析工具调用 JSON 失败: {e}, 原始内容: {json_str[:200]}")
            continue
    
    return tool_calls


# ==================== API 端点 ====================

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool: str
    params: dict = {}


class AgentRequest(BaseModel):
    """Agent 请求"""
    query: str
    title: Optional[str] = None
    filename: Optional[str] = None


def _sanitize_filename(name: str) -> str:
    """清理文件名"""
    s = re.sub(r"\s+", "_", name.strip())
    s = re.sub(r"[^\w\u4e00-\u9fa5_-]+", "", s)
    return s[:40] if s else ""


@app.get("/")
async def root():
    """服务器状态"""
    return {
        "name": "Word MCP Server",
        "version": "2.0.0",
        "status": "running",
        "llm": {
            "baseURL": LLM_CONFIG.get("baseURL"),
            "model": LLM_CONFIG.get("model")
        },
        "endpoints": {
            "tools": "/tools",
            "call": "/call (POST)",
            "sse": "/sse",
            "sse_agent": "/sse/agent (POST)",
            "documents": "/documents"
        }
    }


@app.get("/tools")
async def get_tools():
    """获取可用工具列表"""
    return {"tools": TOOLS}


@app.post("/call")
async def call_tool(request: ToolCallRequest):
    """直接调用工具（不经过 LLM）"""
    tool_name = request.tool
    params = request.params
    
    if tool_name not in TOOL_HANDLERS:
        return {"success": False, "error": f"未知工具: {tool_name}"}
    
    handler = TOOL_HANDLERS[tool_name]
    result = handler(**params)
    
    logger.info(f"工具调用: {tool_name}({params}) -> {result.get('success')}")
    return result


@app.get("/documents")
async def get_documents():
    """获取文档列表"""
    return list_documents()


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 端点 - 用于实时事件流"""
    
    async def event_generator():
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE 连接成功'})}\n\n"
        yield f"data: {json.dumps({'type': 'tools', 'tools': list(TOOLS.keys())})}\n\n"
        
        while True:
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps({'type': 'heartbeat', 'time': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(30)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/sse/call")
async def sse_call_tool(request: ToolCallRequest):
    """SSE 方式调用工具"""
    
    async def stream_response():
        tool_name = request.tool
        params = request.params
        
        yield f"data: {json.dumps({'type': 'start', 'tool': tool_name})}\n\n"
        
        if tool_name not in TOOL_HANDLERS:
            yield f"data: {json.dumps({'type': 'error', 'error': f'未知工具: {tool_name}'})}\n\n"
            return
        
        handler = TOOL_HANDLERS[tool_name]
        result = handler(**params)
        
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/sse/agent")
async def sse_agent(request: AgentRequest, http_request: Request):
    """
    LLM Agent SSE 端点
    
    1. 接收用户的自然语言查询
    2. 调用 LLM 理解意图并决定调用哪些工具
    3. 执行工具调用
    4. 将结果返回给 LLM 继续处理
    5. 循环直到 LLM 给出最终答案
    """

    async def stream_response():
        query = request.query
        title = (request.title or "").strip()
        filename_hint = (request.filename or "").strip()
        
        # 构建系统提示
        system_prompt = """你是一个智能文档助手。你必须通过调用工具来完成用户的请求。

【重要规则】
1. 必须直接调用工具，不要描述步骤或解释如何操作
2. 用户让你创建文档，你就调用 create_document 工具
3. 用户让你读取文档，你就调用 read_document 工具
4. 用户让你列出文档，你就调用 list_documents 工具
5. 如果需要查询信息来写文档，先调用 google_search 搜索，再根据搜索结果创建文档
6. 如果需要插入图片，按顺序：google_image_search → download_image → insert_image
7. 不要输出 HTML、代码块或步骤说明，直接调用工具

【工具说明】
文档操作：
- create_document(filename, title, content): 创建新文档
- read_document(filename): 读取文档内容
- update_document(filename, action, content): 更新文档
- delete_document(filename): 删除文档
- list_documents(): 列出所有文档
- add_table(filename, table_data, title): 添加表格
- search_replace(filename, search_text, replace_text): 搜索替换

搜索功能：
- google_search(query, num_results): 搜索文字信息
- google_image_search(query, num_results): 搜索图片，返回图片URL列表

图片操作：
- download_image(url, filename): 从URL下载图片到本地，返回本地路径
- insert_image(filename, image_path, width): 将本地图片插入文档

【图片插入流程示例】
1. google_image_search(query="可爱猫咪") → 获取图片URL
2. download_image(url="图片URL") → 下载到本地，获取 local_path
3. insert_image(filename="文档名", image_path="local_path") → 插入文档

现在，请直接调用工具来完成用户的请求。"""

        # 初始化消息历史
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户请求: {query}" + (f"\n建议标题: {title}" if title else "") + (f"\n建议文件名: {filename_hint}" if filename_hint else "")}
        ]
        
        tools = get_tools_for_llm()
        
        yield f"data: {json.dumps({'type': 'start', 'message': '正在理解您的需求...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
        
        max_iterations = 10  # 防止无限循环
        iteration = 0
        
        while iteration < max_iterations:
            if await http_request.is_disconnected():
                logger.info("客户端断开连接")
                break
            
            iteration += 1
            
            try:
                # 调用 LLM
                yield f"data: {json.dumps({'type': 'thinking', 'message': f'正在思考 (第 {iteration} 轮)...'}, ensure_ascii=False)}\n\n"
                
                llm_response = await call_llm(messages, tools)
                logger.info(f"LLM 原始响应: {json.dumps(llm_response, ensure_ascii=False)[:500]}")


                choice = llm_response.get("choices", [{}])[0]
                message = choice.get("message", {})
                
                # 检查是否有工具调用
                tool_calls = message.get("tool_calls", [])
                
                # Qwen 模型特殊处理：从 reasoning_content 中解析 <tool_call> 标签
                if not tool_calls:
                    reasoning_content = message.get("reasoning_content", "")
                    if reasoning_content and "<tool_call>" in reasoning_content:
                        tool_calls = parse_qwen_tool_calls(reasoning_content)
                        logger.info(f"从 reasoning_content 解析出工具调用: {tool_calls}")
                
                if tool_calls:
                    # 添加助手消息到历史
                    messages.append(message)
                    
                    # 执行每个工具调用
                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_id = tool_call["id"]
                        
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'arguments': arguments}, ensure_ascii=False)}\n\n"
                        
                        # 执行工具
                        result = execute_tool(tool_name, arguments)
                        
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': result}, ensure_ascii=False)}\n\n"
                        
                        # 添加工具结果到消息历史
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                        
                        await asyncio.sleep(0)
                else:
                    # 没有工具调用，LLM 给出了最终回答
                    content = message.get("content", "")
                    
                    # Qwen 模型特殊处理：如果 content 为空，使用 reasoning_content
                    if not content:
                        reasoning_content = message.get("reasoning_content", "")
                        if reasoning_content and "<tool_call>" not in reasoning_content:
                            content = reasoning_content
                    
                    # 处理 Qwen 模型的思考标签
                    if content:
                        # 移除 <think>...</think> 标签内容
                        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                    
                    yield f"data: {json.dumps({'type': 'response', 'content': content}, ensure_ascii=False)}\n\n"
                    break
                    
            except httpx.HTTPStatusError as e:
                error_msg = f"LLM API 错误: {e.response.status_code}"
                logger.error(f"{error_msg}: {e.response.text}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                break
            except Exception as e:
                error_msg = f"处理错误: {str(e)}"
                logger.exception(error_msg)
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                break
        
        if iteration >= max_iterations:
            yield f"data: {json.dumps({'type': 'warning', 'message': '达到最大迭代次数限制'}, ensure_ascii=False)}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat")
async def chat(request: AgentRequest):
    """
    非流式 Chat 端点（用于简单请求）
    """
    query = request.query
    title = (request.title or "").strip()
    filename_hint = (request.filename or "").strip()
    
    system_prompt = """你是一个专业的 Word 文档助手。请根据用户的请求，决定需要调用哪些工具并执行。"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"用户请求: {query}" + (f"\n建议标题: {title}" if title else "") + (f"\n建议文件名: {filename_hint}" if filename_hint else "")}
    ]
    
    tools = get_tools_for_llm()
    results = []
    
    max_iterations = 10
    for _ in range(max_iterations):
        try:
            llm_response = await call_llm(messages, tools)
            choice = llm_response.get("choices", [{}])[0]
            message = choice.get("message", {})
            
            tool_calls = message.get("tool_calls", [])
            
            if tool_calls:
                messages.append(message)
                
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_id = tool_call["id"]
                    
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    result = execute_tool(tool_name, arguments)
                    results.append({"tool": tool_name, "arguments": arguments, "result": result})
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
            else:
                content = message.get("content", "")
                if content:
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return {
                    "success": True,
                    "response": content,
                    "tool_calls": results
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "达到最大迭代次数"}


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("Word MCP Server (SSE + LLM Agent)")
    print("=" * 50)
    print(f"文档目录: {WORD_DIR.absolute()}")
    print(f"服务地址: http://localhost:8080")
    print(f"LLM: {LLM_CONFIG.get('model')} @ {LLM_CONFIG.get('baseURL')}")
    print("=" * 50)
    print("\n可用端点:")
    print("  GET  /           - 服务器状态")
    print("  GET  /tools      - 工具列表")
    print("  POST /call       - 直接调用工具")
    print("  GET  /sse        - SSE 连接")
    print("  POST /sse/call   - SSE 调用工具")
    print("  POST /sse/agent  - LLM Agent (SSE 流式)")
    print("  POST /chat       - LLM Agent (非流式)")
    print("  GET  /documents  - 文档列表")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
