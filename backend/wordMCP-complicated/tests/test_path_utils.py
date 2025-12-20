"""
Tests for path utilities.
"""

import pytest
from pathlib import Path
import tempfile

from core.path_utils import PathUtils
from core.exceptions import InvalidPathError, FileSizeExceededError


class TestPathUtils:
    """Test suite for PathUtils."""
    
    def test_normalize_file_path_absolute(self):
        """Test normalizing absolute paths."""
        path = "/tmp/test.docx"
        result = PathUtils.normalize_file_path(path)
        assert result.is_absolute()
    
    def test_normalize_file_path_relative(self):
        """Test normalizing relative paths."""
        path = "test.docx"
        result = PathUtils.normalize_file_path(path)
        assert result.is_absolute()
        assert result.name == "test.docx"
    
    def test_validate_file_path_adds_extension(self):
        """Test that .docx extension is added if missing."""
        path = "/tmp/test"
        result = PathUtils.validate_file_path(path, must_exist=False, check_size=False)
        assert str(result).endswith(".docx")
    
    def test_validate_file_path_nonexistent(self):
        """Test validation fails for nonexistent file when must_exist=True."""
        with pytest.raises(Exception):  # DocumentNotFoundError
            PathUtils.validate_file_path(
                "/tmp/nonexistent_file_12345.docx",
                must_exist=True,
                check_size=False
            )
    
    def test_validate_image_path_invalid_format(self):
        """Test image validation fails for unsupported formats."""
        with pytest.raises(InvalidPathError):
            PathUtils.validate_image_path("/tmp/test.txt", must_exist=False)
    
    def test_validate_image_path_valid_format(self):
        """Test image validation passes for valid formats."""
        for ext in ['.jpg', '.jpeg', '.png', '.gif']:
            path = f"/tmp/test{ext}"
            result = PathUtils.validate_image_path(path, must_exist=False)
            assert result.suffix.lower() == ext
    
    def test_ensure_parent_directory(self, tmp_path):
        """Test ensuring parent directory exists."""
        test_file = tmp_path / "subdir" / "test.docx"
        assert not test_file.parent.exists()
        
        PathUtils.ensure_parent_directory(test_file)
        assert test_file.parent.exists()
    
    def test_get_default_word_dir(self):
        """Test getting default word directory."""
        word_dir = PathUtils.get_default_word_dir()
        assert word_dir.exists()
        assert word_dir.is_dir()

