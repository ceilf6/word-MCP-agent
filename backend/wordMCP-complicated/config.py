"""
Configuration management for Word MCP Server.
"""

import os
from pathlib import Path
from typing import Optional
import logging


class Config:
    """Configuration manager for Word MCP Server."""
    
    def __init__(self):
        """Initialize configuration with environment variables or defaults."""
        # Directory settings
        self.word_dir = Path(
            os.getenv("WORDMCP_DIR", Path.cwd() / "word")
        )
        
        # File size limits (default: 50MB)
        self.max_file_size = int(
            os.getenv("WORDMCP_MAX_SIZE", 50 * 1024 * 1024)
        )
        
        # Log settings
        self.log_level = os.getenv("WORDMCP_LOG_LEVEL", "INFO").upper()
        self.log_dir = Path(
            os.getenv("WORDMCP_LOG_DIR", Path.cwd() / "logs")
        )
        
        # Cache settings
        self.enable_cache = os.getenv(
            "WORDMCP_CACHE", "true"
        ).lower() == "true"
        self.cache_size = int(os.getenv("WORDMCP_CACHE_SIZE", 128))
        
        # Security settings
        self.allow_absolute_paths = os.getenv(
            "WORDMCP_ALLOW_ABSOLUTE", "true"
        ).lower() == "true"
        
        # Performance settings
        self.max_list_depth = int(os.getenv("WORDMCP_MAX_DEPTH", 3))
        self.recursive_list = os.getenv(
            "WORDMCP_RECURSIVE", "true"
        ).lower() == "true"
        
        # Image settings
        self.max_image_size = int(
            os.getenv("WORDMCP_MAX_IMAGE_SIZE", 10 * 1024 * 1024)
        )
        self.allowed_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        
        # Initialize directories
        self.ensure_directories()
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.word_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_file_path(self) -> Path:
        """Get the log file path."""
        return self.log_dir / "wordmcp.log"
    
    def get_numeric_log_level(self) -> int:
        """Convert string log level to numeric value."""
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(self.log_level, logging.INFO)
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"Config(word_dir={self.word_dir}, "
            f"max_file_size={self.max_file_size}, "
            f"log_level={self.log_level})"
        )


# Global configuration instance
config = Config()

