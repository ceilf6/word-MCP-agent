"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def sample_image(test_data_dir):
    """Path to sample test image (if it exists)."""
    img_path = test_data_dir / "sample.png"
    if img_path.exists():
        return img_path
    return None

