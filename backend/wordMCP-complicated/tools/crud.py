"""
CRUD tools for Word document operations.
"""

from typing import Optional, List
import logging

from mcp.server.fastmcp import FastMCP

# Import from core - handle both package and direct execution
try:
    from ..core.document import DocumentManager
    from ..core.exceptions import DocumentError
except ImportError:
    from core.document import DocumentManager
    from core.exceptions import DocumentError

logger = logging.getLogger(__name__)


def register_crud_tools(mcp: FastMCP) -> None:
    """
    Register CRUD tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance
    """
    doc_manager = DocumentManager()
    
    @mcp.tool()
    def create_word_document(
        file_path: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> dict:
        """
        Create a new Word document (.docx file).
        
        Args:
            file_path: File path or filename. If not provided or relative, saves to word/ subdirectory.
                       If just filename provided, saves to word/filename.docx
            title: Optional title for the document
            content: Optional initial content for the document
        
        Returns:
            Dictionary with operation result and file path
        
        Examples:
            create_word_document(title="My Report", content="Introduction\\n\\nThis is my report.")
            create_word_document(file_path="report.docx", title="Annual Report")
        """
        try:
            logger.info(f"Tool called: create_word_document(file_path={file_path})")
            return doc_manager.create_document(file_path, title, content)
        except DocumentError as e:
            logger.error(f"Document error in create_word_document: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in create_word_document: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @mcp.tool()
    def read_word_document(file_path: str) -> dict:
        """
        Read content from a Word document.
        
        Args:
            file_path: Path to the Word document (.docx file). 
                       If relative or just filename, searches in word/ subdirectory first.
        
        Returns:
            Dictionary containing document content, paragraphs, tables, and metadata
        
        Examples:
            read_word_document("report.docx")
            read_word_document("word/annual_report.docx")
        """
        try:
            logger.info(f"Tool called: read_word_document(file_path={file_path})")
            return doc_manager.read_document(file_path)
        except DocumentError as e:
            logger.error(f"Document error in read_word_document: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in read_word_document: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @mcp.tool()
    def update_word_document(
        file_path: str,
        action: str,
        content: Optional[str] = None,
        paragraph_index: Optional[int] = None,
        heading_level: Optional[int] = 1
    ) -> dict:
        """
        Update an existing Word document.
        
        Args:
            file_path: Path to the Word document (.docx file).
                       If relative or just filename, searches in word/ subdirectory first.
            action: Action to perform - "append" (add to end), "insert" (insert at paragraph_index), 
                    "replace" (replace paragraph at paragraph_index), "add_heading" (add heading)
            content: Content to add/insert/replace
            paragraph_index: Index of paragraph for insert/replace operations (0-based)
            heading_level: Level of heading (1-9) for add_heading action
        
        Returns:
            Dictionary with operation result
        
        Examples:
            update_word_document("report.docx", action="append", content="New paragraph")
            update_word_document("report.docx", action="add_heading", content="Chapter 2", heading_level=2)
            update_word_document("report.docx", action="replace", paragraph_index=0, content="Updated intro")
        """
        try:
            logger.info(f"Tool called: update_word_document(file_path={file_path}, action={action})")
            return doc_manager.update_document(
                file_path, action, content, paragraph_index, heading_level
            )
        except DocumentError as e:
            logger.error(f"Document error in update_word_document: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in update_word_document: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @mcp.tool()
    def delete_word_document(file_path: str) -> dict:
        """
        Delete a Word document file.
        
        Args:
            file_path: Path to the Word document (.docx file) to delete.
                       If relative or just filename, searches in word/ subdirectory first.
        
        Returns:
            Dictionary with operation result
        
        Examples:
            delete_word_document("old_report.docx")
            delete_word_document("word/draft.docx")
        """
        try:
            logger.info(f"Tool called: delete_word_document(file_path={file_path})")
            return doc_manager.delete_document(file_path)
        except DocumentError as e:
            logger.error(f"Document error in delete_word_document: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in delete_word_document: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @mcp.tool()
    def list_word_documents(
        directory: str,
        recursive: bool = True,
        max_depth: int = 3
    ) -> dict:
        """
        List all Word documents (.docx files) in a directory.
        
        Args:
            directory: Directory path to search for Word documents
            recursive: Whether to search subdirectories (default: True)
            max_depth: Maximum depth for recursive search (default: 3)
        
        Returns:
            Dictionary containing list of Word documents with metadata
        
        Examples:
            list_word_documents("word")
            list_word_documents("/path/to/documents", recursive=False)
        """
        try:
            logger.info(f"Tool called: list_word_documents(directory={directory})")
            return doc_manager.list_documents(directory, recursive, max_depth)
        except DocumentError as e:
            logger.error(f"Document error in list_word_documents: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in list_word_documents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @mcp.tool()
    def add_table_to_document(
        file_path: str,
        table_data: List[List[str]],
        title: Optional[str] = None
    ) -> dict:
        """
        Add a table to a Word document.
        
        Args:
            file_path: Path to the Word document (.docx file).
                       If relative or just filename, searches in word/ subdirectory first.
            table_data: 2D list representing table data (rows and columns)
            title: Optional title/heading before the table
        
        Returns:
            Dictionary with operation result
        
        Examples:
            add_table_to_document(
                "report.docx",
                [["Name", "Age", "City"], ["Alice", "25", "NYC"], ["Bob", "30", "LA"]],
                title="Employee List"
            )
        """
        try:
            logger.info(f"Tool called: add_table_to_document(file_path={file_path})")
            return doc_manager.add_table(file_path, table_data, title)
        except DocumentError as e:
            logger.error(f"Document error in add_table_to_document: {e}")
            return e.to_dict()
        except Exception as e:
            logger.error(f"Unexpected error in add_table_to_document: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
    
    logger.info("CRUD tools registered successfully")

