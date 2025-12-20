"""
Logging configuration for Word MCP Server.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Import config - handle both package and direct execution
try:
    from ..config import config
except ImportError:
    from config import config


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Setup logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (uses config default if not provided)
    
    Returns:
        Configured logger instance
    """
    # Use config values if not provided
    if log_level is None:
        log_level = config.log_level
    if log_file is None:
        log_file = config.get_log_file_path()
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("wordmcp")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler (detailed logs)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler (simpler logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized: level={log_level}, file={log_file}")
    
    return logger


def get_logger(name: str = "wordmcp") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize default logger
default_logger = setup_logging()

