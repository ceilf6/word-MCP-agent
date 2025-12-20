"""
Word Document MCP Server - Refactored Version

This MCP server provides comprehensive CRUD and advanced operations
for Microsoft Word documents (.docx files).
"""

import sys
import json
from pathlib import Path
from typing import List, Dict
import logging

from mcp.server.fastmcp import FastMCP

# Import core modules
from core.logger import setup_logging, get_logger
from core.path_utils import PathUtils
from core.document import DocumentManager
from config import config

# Import tool registrations
from tools.crud import register_crud_tools
from tools.formatting import register_formatting_tools
from tools.advanced import register_advanced_tools

# Setup logging
logger = setup_logging()

# Initialize FastMCP server
mcp = FastMCP("Word Document MCP Server")

logger.info("=" * 60)
logger.info("Word MCP Server Starting")
logger.info(f"Configuration: {config}")
logger.info("=" * 60)


# ==================== Register All Tools ====================

def register_all_tools() -> None:
    """Register all available tools with the MCP server."""
    logger.info("Registering tools...")
    
    try:
        # Register CRUD tools
        register_crud_tools(mcp)
        
        # Register formatting tools
        register_formatting_tools(mcp)
        
        # Register advanced tools
        register_advanced_tools(mcp)
        
        logger.info("All tools registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register tools: {e}", exc_info=True)
        raise


# Register tools
register_all_tools()


# ==================== Resources ====================

@mcp.resource("file://word_documents")
def list_documents_resource() -> str:
    """
    Get list of Word documents in the word/ subdirectory.
    
    Returns:
        JSON string with document list
    """
    try:
        logger.debug("Resource called: list_documents_resource")
        
        word_dir = PathUtils.get_default_word_dir()
        doc_manager = DocumentManager()
        
        result = doc_manager.list_documents(word_dir, recursive=False)
        
        return json.dumps({
            "directory": str(word_dir),
            "count": result.get("count", 0),
            "documents": [
                {
                    "name": doc["name"],
                    "size": doc["size"],
                    "modified": doc["modified"]
                }
                for doc in result.get("documents", [])
            ]
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in list_documents_resource: {e}", exc_info=True)
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource("file://config")
def config_resource() -> str:
    """
    Get current configuration settings.
    
    Returns:
        JSON string with configuration
    """
    try:
        logger.debug("Resource called: config_resource")
        
        return json.dumps({
            "word_directory": str(config.word_dir),
            "max_file_size": config.max_file_size,
            "max_file_size_mb": round(config.max_file_size / (1024 * 1024), 2),
            "log_level": config.log_level,
            "cache_enabled": config.enable_cache,
            "allow_absolute_paths": config.allow_absolute_paths,
            "max_list_depth": config.max_list_depth
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error in config_resource: {e}", exc_info=True)
        return json.dumps({"error": str(e)}, indent=2)


# ==================== Prompts ====================

@mcp.prompt()
def word_document_help() -> List[Dict]:
    """
    Get comprehensive help for using Word document operations.
    
    Returns:
        List of prompt messages
    """
    return [
        {
            "role": "user",
            "content": """I need help with Word document operations. Please explain:

1. **Basic Operations (CRUD)**
   - How to create a new Word document
   - How to read content from a Word document
   - How to update/modify a Word document
   - How to delete a Word document
   - How to list all Word documents in a directory

2. **Table Operations**
   - How to add tables to documents

3. **Formatting Operations**
   - How to format text (font, size, color, alignment)
   - How to insert page breaks
   - How to add bullet and numbered lists

4. **Advanced Operations**
   - How to insert images into documents
   - How to search for text in documents
   - How to search and replace text
   - How to merge multiple documents
   - How to get document statistics

Please provide examples for the most common operations."""
        }
    ]


@mcp.prompt()
def quick_start_guide() -> List[Dict]:
    """
    Get a quick start guide for common tasks.
    
    Returns:
        List of prompt messages
    """
    return [
        {
            "role": "user",
            "content": """Show me quick examples of common Word document operations:

1. Create a simple document with a title and content
2. Add a table with sample data
3. Format a paragraph (make it bold and centered)
4. Insert an image
5. Search and replace text

Keep the examples concise and practical."""
        }
    ]


@mcp.prompt()
def troubleshooting() -> List[Dict]:
    """
    Get troubleshooting help for common issues.
    
    Returns:
        List of prompt messages
    """
    return [
        {
            "role": "user",
            "content": """I'm having issues with Word document operations. Help me troubleshoot:

1. What to do if a file is not found
2. What to do if file size exceeds limits
3. What to do if an operation fails
4. How to check current configuration
5. Where to find log files for debugging

Provide practical solutions for each issue."""
        }
    ]


# ==================== Main Entry Point ====================

def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Check if running in test mode
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
            # Test mode: verify the server can be imported and initialized
            print("=" * 60)
            print("✓ Word MCP Server initialized successfully")
            print(f"✓ Default word directory: {config.word_dir}")
            print(f"✓ Log file: {config.get_log_file_path()}")
            print(f"✓ Max file size: {config.max_file_size / (1024*1024):.1f} MB")
            print(f"✓ Server type: {type(mcp).__module__}.{type(mcp).__name__}")
            print("=" * 60)
            print("\nNote: This server is designed to be used with MCP clients.")
            print("Do not run it directly. Use 'mcp run main.py' or connect via MCP client.")
            sys.exit(0)
        
        # Run the MCP server using stdio transport (standard for MCP)
        logger.info("Starting MCP server with stdio transport")
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

