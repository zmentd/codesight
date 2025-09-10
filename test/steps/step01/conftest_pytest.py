"""
Test configuration for Step 01 tests.
"""

import sys
from pathlib import Path

# Add the source directory to Python path
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest

# Configure pytest-mock if available
pytest_plugins = ['pytest_mock']

# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Mark tests in test_*_integration.py as integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark tests with "slow" in name as slow
        if "slow" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Mark all other tests as unit tests
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
