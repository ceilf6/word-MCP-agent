"""
Path utilities for Word MCP Server.
"""

import os
from pathlib import Path
from typing import Union, Optional
import logging

from .exceptions import InvalidPathError, FileSizeExceededError

# Import config - handle both package and direct execution
try:
    from ..config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


class PathUtils:
    """Utility class for path operations with security and validation."""
    
    @staticmethod
    def get_default_word_dir() -> Path:
        """
        Get the default word documents directory.
        
        Returns:
            Path to default word directory
        """
        word_dir = config.word_dir
        word_dir.mkdir(parents=True, exist_ok=True)
        return word_dir
    
    @staticmethod
    def normalize_file_path(
        file_path: Union[str, Path],
        default_dir: Optional[Path] = None
    ) -> Path:
        """
        Normalize file path with security checks.
        
        Args:
            file_path: File path (can be absolute, relative, or just filename)
            default_dir: Default directory to use (defaults to word subdirectory)
        
        Returns:
            Normalized absolute file path
            
        Raises:
            InvalidPathError: If path is invalid or unsafe
        """
        if default_dir is None:
            default_dir = PathUtils.get_default_word_dir()
        
        path = Path(file_path)
        
        # If it's already an absolute path
        if path.is_absolute():
            if not config.allow_absolute_paths:
                raise InvalidPathError(
                    "Absolute paths are not allowed",
                    str(path)
                )
            return path
        
        # If it's a relative path with directory, join with default_dir
        if path.parent != Path('.'):
            normalized = default_dir / path
        else:
            # If it's just a filename, place it in default_dir
            normalized = default_dir / path.name
        
        return normalized.resolve()
    
    @staticmethod
    def validate_file_path(
        file_path: Union[str, Path],
        must_exist: bool = False,
        check_size: bool = True,
        base_dir: Optional[Path] = None
    ) -> Path:
        """
        Validate file path with comprehensive checks.
        
        Args:
            file_path: Path to validate
            must_exist: Whether file must exist
            check_size: Whether to check file size limits
            base_dir: Base directory for security check
        
        Returns:
            Validated Path object
            
        Raises:
            InvalidPathError: If path validation fails
            FileSizeExceededError: If file size exceeds limit
        """
        path = Path(file_path).resolve()
        
        # Check file extension
        if path.suffix.lower() != '.docx':
            if not str(path).endswith('.docx'):
                # Auto-add .docx extension
                path = Path(str(path) + '.docx')
        
        # Check path traversal (security)
        if base_dir:
            base = Path(base_dir).resolve()
            try:
                path.relative_to(base)
            except ValueError:
                raise InvalidPathError(
                    f"Path must be within {base_dir}",
                    str(path)
                )
        
        # Check if file exists when required
        if must_exist and not path.exists():
            from .exceptions import DocumentNotFoundError
            raise DocumentNotFoundError(str(path))
        
        # Check file size
        if check_size and path.exists():
            file_size = path.stat().st_size
            if file_size > config.max_file_size:
                raise FileSizeExceededError(
                    file_size,
                    config.max_file_size,
                    str(path)
                )
        
        logger.debug(f"Validated path: {path}")
        return path
    
    @staticmethod
    def ensure_parent_directory(file_path: Union[str, Path]) -> None:
        """
        Ensure parent directory exists for the given file path.
        
        Args:
            file_path: Path to file
        """
        path = Path(file_path)
        if path.parent != Path('.'):
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path.parent}")
    
    @staticmethod
    def validate_image_path(
        image_path: Union[str, Path],
        must_exist: bool = True
    ) -> Path:
        """
        Validate image file path.
        
        Args:
            image_path: Path to image file
            must_exist: Whether file must exist
        
        Returns:
            Validated Path object
            
        Raises:
            InvalidPathError: If path or format is invalid
            FileSizeExceededError: If image size exceeds limit
        """
        path = Path(image_path).resolve()
        
        # Check file extension
        if path.suffix.lower() not in config.allowed_image_formats:
            raise InvalidPathError(
                f"Unsupported image format. Allowed: {config.allowed_image_formats}",
                str(path)
            )
        
        # Check if file exists
        if must_exist and not path.exists():
            raise InvalidPathError(
                f"Image file not found: {path}",
                str(path)
            )
        
        # Check image size
        if path.exists():
            image_size = path.stat().st_size
            if image_size > config.max_image_size:
                raise FileSizeExceededError(
                    image_size,
                    config.max_image_size,
                    str(path)
                )
        
        logger.debug(f"Validated image path: {path}")
        return path
    
    @staticmethod
    def find_file_in_word_dir(filename: str) -> Optional[Path]:
        """
        Search for a file in the word directory.
        
        Args:
            filename: Name of the file to search
        
        Returns:
            Path to file if found, None otherwise
        """
        word_dir = PathUtils.get_default_word_dir()
        file_path = word_dir / filename
        
        if file_path.exists():
            logger.debug(f"Found file in word directory: {file_path}")
            return file_path
        
        logger.debug(f"File not found in word directory: {filename}")
        return None
    
    @staticmethod
    def resolve_file_path(file_path: str) -> Path:
        """
        Resolve file path, checking multiple locations.
        
        Args:
            file_path: File path to resolve
        
        Returns:
            Resolved Path object
            
        Raises:
            DocumentNotFoundError: If file not found in any location
        """
        # Try normalized path first
        normalized = PathUtils.normalize_file_path(file_path)
        if normalized.exists():
            return normalized
        
        # Try original path
        original = Path(file_path)
        if original.exists():
            return original.resolve()
        
        # Try in word directory
        found = PathUtils.find_file_in_word_dir(Path(file_path).name)
        if found:
            return found
        
        # Not found anywhere
        from .exceptions import DocumentNotFoundError
        raise DocumentNotFoundError(file_path)

