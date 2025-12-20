# Word MCP Server Tests

## Running Tests

### Install test dependencies

```bash
pip install pytest pytest-cov
```

### Run all tests

```bash
# From the wordMCP directory
pytest tests/

# With coverage report
pytest tests/ --cov=core --cov=tools --cov-report=html

# Verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_document.py

# Run specific test
pytest tests/test_document.py::TestDocumentManager::test_create_document
```

## Test Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Pytest configuration and shared fixtures
├── README.md             # This file
├── test_document.py      # Tests for core document operations
├── test_path_utils.py    # Tests for path utilities
└── test_data/            # Test data files (images, sample docs, etc.)
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from core.document import DocumentManager

class TestMyFeature:
    @pytest.fixture
    def setup(self):
        # Setup code
        pass
    
    def test_something(self, setup):
        # Test code
        assert True
```

### Using Fixtures

```python
def test_with_temp_dir(tmp_path):
    # tmp_path is a built-in pytest fixture
    file_path = tmp_path / "test.docx"
    # ... test code
```

## Test Coverage

Run with coverage to see which code is tested:

```bash
pytest tests/ --cov=core --cov=tools --cov-report=term-missing
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Make sure to:
1. Install dependencies before running tests
2. Set appropriate environment variables if needed
3. Use pytest exit codes to determine pass/fail

