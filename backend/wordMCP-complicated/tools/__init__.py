"""
MCP Tools for Word document operations.
"""

from .crud import register_crud_tools
from .formatting import register_formatting_tools
from .advanced import register_advanced_tools

__all__ = [
    'register_crud_tools',
    'register_formatting_tools', 
    'register_advanced_tools'
]

