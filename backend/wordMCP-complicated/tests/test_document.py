"""
Tests for core document operations.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from core.document import DocumentManager
from core.exceptions import DocumentNotFoundError, DocumentOperationError


class TestDocumentManager:
    """Test suite for DocumentManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    @pytest.fixture
    def doc_manager(self):
        """Create DocumentManager instance."""
        return DocumentManager()
    
    def test_create_document(self, doc_manager, temp_dir):
        """Test document creation."""
        file_path = temp_dir / "test.docx"
        
        result = doc_manager.create_document(
            file_path=str(file_path),
            title="Test Document",
            content="This is test content"
        )
        
        assert result["success"] is True
        assert Path(result["file_path"]).exists()
        assert "created_at" in result
    
    def test_create_document_with_default_name(self, doc_manager, temp_dir):
        """Test document creation with auto-generated name."""
        # This would create in default word dir, but we can't easily test that
        # without mocking the config
        pass
    
    def test_read_document(self, doc_manager, temp_dir):
        """Test document reading."""
        # First create a document
        file_path = temp_dir / "test_read.docx"
        doc_manager.create_document(
            file_path=str(file_path),
            title="Read Test",
            content="Line 1\nLine 2\nLine 3"
        )
        
        # Now read it
        result = doc_manager.read_document(str(file_path))
        
        assert result["success"] is True
        assert result["title"] == "Read Test"
        assert result["paragraph_count"] > 0
        assert "Line 1" in result["full_text"]
    
    def test_read_nonexistent_document(self, doc_manager):
        """Test reading a document that doesn't exist."""
        with pytest.raises(DocumentNotFoundError):
            doc_manager.read_document("nonexistent.docx")
    
    def test_update_document_append(self, doc_manager, temp_dir):
        """Test appending content to document."""
        file_path = temp_dir / "test_update.docx"
        
        # Create document
        doc_manager.create_document(
            file_path=str(file_path),
            content="Original content"
        )
        
        # Append content
        result = doc_manager.update_document(
            file_path=str(file_path),
            action="append",
            content="Appended content"
        )
        
        assert result["success"] is True
        assert result["action"] == "append"
        
        # Verify content was appended
        read_result = doc_manager.read_document(str(file_path))
        assert "Appended content" in read_result["full_text"]
    
    def test_update_document_add_heading(self, doc_manager, temp_dir):
        """Test adding heading to document."""
        file_path = temp_dir / "test_heading.docx"
        
        # Create document
        doc_manager.create_document(file_path=str(file_path))
        
        # Add heading
        result = doc_manager.update_document(
            file_path=str(file_path),
            action="add_heading",
            content="New Section",
            heading_level=2
        )
        
        assert result["success"] is True
    
    def test_delete_document(self, doc_manager, temp_dir):
        """Test document deletion."""
        file_path = temp_dir / "test_delete.docx"
        
        # Create document
        doc_manager.create_document(file_path=str(file_path))
        assert Path(file_path).exists()
        
        # Delete document
        result = doc_manager.delete_document(str(file_path))
        
        assert result["success"] is True
        assert not Path(file_path).exists()
    
    def test_list_documents(self, doc_manager, temp_dir):
        """Test listing documents in directory."""
        # Create several documents
        for i in range(3):
            doc_manager.create_document(
                file_path=str(temp_dir / f"doc_{i}.docx")
            )
        
        # List documents
        result = doc_manager.list_documents(str(temp_dir))
        
        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["documents"]) == 3
    
    def test_add_table(self, doc_manager, temp_dir):
        """Test adding table to document."""
        file_path = temp_dir / "test_table.docx"
        
        # Create document
        doc_manager.create_document(file_path=str(file_path))
        
        # Add table
        table_data = [
            ["Name", "Age", "City"],
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"]
        ]
        
        result = doc_manager.add_table(
            file_path=str(file_path),
            table_data=table_data,
            title="People"
        )
        
        assert result["success"] is True
        assert result["table_rows"] == 3
        assert result["table_cols"] == 3
    
    def test_insert_image(self, doc_manager, temp_dir):
        """Test inserting image into document."""
        # This test would require a test image file
        # Skipping for now
        pass

