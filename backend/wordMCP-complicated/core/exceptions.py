"""
Custom exceptions for Word MCP Server.
"""


class DocumentError(Exception):
    """Base exception for all document-related errors."""
    
    def __init__(self, message: str, error_code: str = "DOCUMENT_ERROR"):
        """
        Initialize DocumentError.
        
        Args:
            message: Error message
            error_code: Error code for categorization
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        return {
            "success": False,
            "error": self.message,
            "error_code": self.error_code
        }


class DocumentNotFoundError(DocumentError):
    """Exception raised when a document file is not found."""
    
    def __init__(self, file_path: str):
        """
        Initialize DocumentNotFoundError.
        
        Args:
            file_path: Path to the missing document
        """
        self.file_path = file_path
        message = f"Document not found: {file_path}"
        super().__init__(message, "NOT_FOUND")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        result["file_path"] = self.file_path
        return result


class InvalidPathError(DocumentError):
    """Exception raised for invalid file paths."""
    
    def __init__(self, message: str, file_path: str = None):
        """
        Initialize InvalidPathError.
        
        Args:
            message: Error message
            file_path: The invalid path
        """
        self.file_path = file_path
        super().__init__(message, "INVALID_PATH")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        if self.file_path:
            result["file_path"] = self.file_path
        return result


class DocumentValidationError(DocumentError):
    """Exception raised when document validation fails."""
    
    def __init__(self, message: str, field: str = None):
        """
        Initialize DocumentValidationError.
        
        Args:
            message: Error message
            field: Field that failed validation
        """
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        if self.field:
            result["field"] = self.field
        return result


class FileSizeExceededError(DocumentError):
    """Exception raised when file size exceeds limit."""
    
    def __init__(self, file_size: int, max_size: int, file_path: str = None):
        """
        Initialize FileSizeExceededError.
        
        Args:
            file_size: Actual file size in bytes
            max_size: Maximum allowed size in bytes
            file_path: Path to the file
        """
        self.file_size = file_size
        self.max_size = max_size
        self.file_path = file_path
        message = (
            f"File size ({file_size} bytes) exceeds maximum "
            f"allowed size ({max_size} bytes)"
        )
        super().__init__(message, "FILE_SIZE_EXCEEDED")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        result.update({
            "file_size": self.file_size,
            "max_size": self.max_size
        })
        if self.file_path:
            result["file_path"] = self.file_path
        return result


class DocumentOperationError(DocumentError):
    """Exception raised when a document operation fails."""
    
    def __init__(self, operation: str, message: str, file_path: str = None):
        """
        Initialize DocumentOperationError.
        
        Args:
            operation: The operation that failed
            message: Error message
            file_path: Path to the document
        """
        self.operation = operation
        self.file_path = file_path
        full_message = f"Operation '{operation}' failed: {message}"
        super().__init__(full_message, "OPERATION_ERROR")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        result["operation"] = self.operation
        if self.file_path:
            result["file_path"] = self.file_path
        return result


class ImageError(DocumentError):
    """Exception raised for image-related errors."""
    
    def __init__(self, message: str, image_path: str = None):
        """
        Initialize ImageError.
        
        Args:
            message: Error message
            image_path: Path to the image
        """
        self.image_path = image_path
        super().__init__(message, "IMAGE_ERROR")
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary format."""
        result = super().to_dict()
        if self.image_path:
            result["image_path"] = self.image_path
        return result

