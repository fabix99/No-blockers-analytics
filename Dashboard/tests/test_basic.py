"""
Test framework setup and basic tests
"""
import pytest
import sys
from pathlib import Path

# Add Dashboard to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_modules():
    """Test that all modules can be imported."""
    from Dashboard.utils import validate_uploaded_file, save_uploaded_file_securely
    from Dashboard.utils.formatters import format_percentage, get_performance_color
    from Dashboard.ui.components import display_match_banner, get_position_full_name
    from Dashboard.config import KPI_TARGETS, CHART_COLORS
    
    assert validate_uploaded_file is not None
    assert format_percentage is not None
    assert KPI_TARGETS is not None


def test_format_percentage():
    """Test percentage formatting."""
    from Dashboard.utils.formatters import format_percentage
    
    assert format_percentage(0.35) == "35.0%"
    assert format_percentage(0.5) == "50.0%"
    assert format_percentage(0.123) == "12.3%"
    assert format_percentage(0.0) == "0.0%"


def test_get_performance_color():
    """Test performance color calculation."""
    from Dashboard.utils.formatters import get_performance_color
    
    # Above optimal
    assert get_performance_color(0.6, 0.4, 0.8, 0.5) == "🟢"
    # Below optimal
    assert get_performance_color(0.3, 0.4, 0.8, 0.5) == "🔴"


def test_validate_uploaded_file():
    """Test file validation."""
    from Dashboard.utils import validate_uploaded_file
    
    # Test None file
    is_valid, error = validate_uploaded_file(None)
    assert not is_valid
    assert "No file provided" in error
    
    # Test file size limit
    class MockFile:
        def __init__(self, size, name):
            self.size = size
            self.name = name
    
    large_file = MockFile(11 * 1024 * 1024, "large.xlsx")
    is_valid, error = validate_uploaded_file(large_file)
    assert not is_valid
    assert "too large" in error.lower()
    
    # Test invalid extension
    invalid_file = MockFile(1000, "file.txt")
    is_valid, error = validate_uploaded_file(invalid_file)
    assert not is_valid
    assert "file type" in error.lower()


def test_position_helpers():
    """Test position helper functions."""
    from Dashboard.ui.components import get_position_full_name, get_position_emoji
    
    assert get_position_full_name("OH1") == "Outside Hitter"
    assert get_position_full_name("S") == "Setter"
    assert get_position_emoji("S") == "🎯"
    assert get_position_emoji("L") == "🕸️"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

