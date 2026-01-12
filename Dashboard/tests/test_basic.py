"""
Basic test suite for Volleyball Analytics Dashboard.

Run with: pytest Dashboard/tests/ -v
"""
import pytest
import sys
from pathlib import Path

# Add Dashboard to path for imports
dashboard_dir = Path(__file__).parent.parent
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))


class TestModuleImports:
    """Test that all core modules can be imported."""
    
    def test_import_utils(self):
        """Test utilities module imports."""
        from utils.helpers import (
            filter_good_receptions, 
            filter_good_digs, 
            filter_block_touches,
            get_player_position
        )
        assert filter_good_receptions is not None
        assert get_player_position is not None
    
    def test_import_formatters(self):
        """Test formatters module imports."""
        from utils.formatters import format_percentage, get_performance_color
        assert format_percentage is not None
        assert get_performance_color is not None
    
    def test_import_components(self):
        """Test UI components imports."""
        from ui.components import get_position_full_name, get_position_emoji
        assert get_position_full_name is not None
        assert get_position_emoji is not None
    
    def test_import_config(self):
        """Test config imports."""
        from config import KPI_TARGETS, CHART_COLORS, VALID_ACTIONS
        assert KPI_TARGETS is not None
        assert CHART_COLORS is not None
        assert VALID_ACTIONS is not None
    
    def test_import_services(self):
        """Test services imports."""
        from services.analytics_service import AnalyticsService
        from services.session_manager import SessionStateManager
        assert AnalyticsService is not None
        assert SessionStateManager is not None
    
    def test_import_charts(self):
        """Test chart utilities imports."""
        from charts.utils import apply_beautiful_theme, plotly_config
        assert apply_beautiful_theme is not None
        assert plotly_config is not None


class TestFormatters:
    """Test formatting utility functions."""
    
    def test_format_percentage_basic(self):
        """Test basic percentage formatting."""
        from utils.formatters import format_percentage
        
        assert format_percentage(0.35) == "35.0%"
        assert format_percentage(0.5) == "50.0%"
        assert format_percentage(0.123) == "12.3%"
        assert format_percentage(0.0) == "0.0%"
    
    def test_format_percentage_edge_cases(self):
        """Test edge cases for percentage formatting."""
        from utils.formatters import format_percentage
        
        assert format_percentage(1.0) == "100.0%"
        assert format_percentage(0.999) == "99.9%"
    
    def test_get_performance_color_above_optimal(self):
        """Test performance color for values above optimal."""
        from utils.formatters import get_performance_color
        
        # Value 0.6 is above optimal 0.5
        result = get_performance_color(0.6, 0.4, 0.8, 0.5)
        assert result == "🟢"
    
    def test_get_performance_color_below_optimal(self):
        """Test performance color for values below optimal."""
        from utils.formatters import get_performance_color
        
        # Value 0.3 is below optimal 0.5
        result = get_performance_color(0.3, 0.4, 0.8, 0.5)
        assert result == "🔴"


class TestPositionHelpers:
    """Test position helper functions."""
    
    def test_get_position_full_name(self):
        """Test position full name mapping."""
        from ui.components import get_position_full_name
        
        assert get_position_full_name("OH1") == "Outside Hitter"
        assert get_position_full_name("OH2") == "Outside Hitter"
        assert get_position_full_name("S") == "Setter"
        assert get_position_full_name("OPP") == "Opposite"
        assert get_position_full_name("MB1") == "Middle Blocker"
        assert get_position_full_name("MB2") == "Middle Blocker"
        assert get_position_full_name("L") == "Libero"
    
    def test_get_position_emoji(self):
        """Test position emoji mapping."""
        from ui.components import get_position_emoji
        
        assert get_position_emoji("S") == "🎯"
        assert get_position_emoji("L") == "🕸️"
        assert get_position_emoji("OPP") == "💥"


class TestFileValidation:
    """Test file validation utilities."""
    
    def test_validate_none_file(self):
        """Test validation of None file."""
        from utils import validate_uploaded_file
        
        is_valid, error = validate_uploaded_file(None)
        assert not is_valid
        assert "No file provided" in error
    
    def test_validate_file_too_large(self):
        """Test validation of oversized file."""
        from utils import validate_uploaded_file
        
        class MockFile:
            def __init__(self, size, name):
                self.size = size
                self.name = name
        
        large_file = MockFile(11 * 1024 * 1024, "large.xlsx")
        is_valid, error = validate_uploaded_file(large_file)
        assert not is_valid
        assert "too large" in error.lower()
    
    def test_validate_invalid_extension(self):
        """Test validation of invalid file extension."""
        from utils import validate_uploaded_file
        
        class MockFile:
            def __init__(self, size, name):
                self.size = size
                self.name = name
        
        invalid_file = MockFile(1000, "file.txt")
        is_valid, error = validate_uploaded_file(invalid_file)
        assert not is_valid
        assert "file type" in error.lower()
    
    def test_validate_valid_file(self):
        """Test validation of valid file."""
        from utils import validate_uploaded_file
        
        class MockFile:
            def __init__(self, size, name):
                self.size = size
                self.name = name
        
        valid_file = MockFile(1000, "match_data.xlsx")
        is_valid, error = validate_uploaded_file(valid_file)
        assert is_valid
        assert error == ""


class TestConfig:
    """Test configuration values."""
    
    def test_kpi_targets_structure(self):
        """Test KPI targets have required structure."""
        from config import KPI_TARGETS
        
        required_kpis = ['attack_efficiency', 'reception_quality', 'serve_efficiency']
        
        for kpi in required_kpis:
            assert kpi in KPI_TARGETS
            assert 'optimal' in KPI_TARGETS[kpi]
            assert 'good' in KPI_TARGETS[kpi]
    
    def test_valid_actions_exist(self):
        """Test that valid actions are defined."""
        from config import VALID_ACTIONS
        
        expected_actions = ['serve', 'attack', 'block', 'reception', 'set', 'dig']
        for action in expected_actions:
            assert action in VALID_ACTIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

