"""
Configuration constants for the volleyball analytics dashboard
"""
from typing import Dict, List

# No Blockers Brand Color Palette - Deep Blue & White
CHART_COLORS: Dict[str, str] = {
    'primary': '#040C7B',      # No Blockers Deep Blue
    'secondary': '#FFFFFF',    # White
    'success': '#00FF00',      # Green (for success metrics)
    'warning': '#FFD700',      # Gold (for warnings)
    'danger': '#FF4500',       # Orange-red (for errors)
    'info': '#040C7B',         # Blue (for info)
    'light': '#F5F5F5',        # Light gray
    'dark': '#040C7B',         # Deep blue
}

CHART_COLOR_GRADIENTS: Dict[str, List[str]] = {
    'gradient': ['#040C7B', '#050C8C', '#060D9E', '#0A11B0', '#1A22C2', '#2A33D4'],
    'blue_variations': ['#040C7B', '#050C8C', '#060D9E', '#0A11B0', '#1A22C2'],
    'blue_white': ['#040C7B', '#1A1F9E', '#3333C1', '#6666D4', '#9999E7', '#FFFFFF']
}

# Performance thresholds and constants
SETTER_THRESHOLD: float = 0.2  # Setter if sets >= 20% of total actions

# KPI Target Ranges - Updated for new metrics
KPI_TARGETS: Dict[str, Dict[str, float]] = {
    'break_point_rate': {'min': 0.50, 'max': 0.60, 'optimal': 0.55},
    'side_out_percentage': {'min': 0.65, 'max': 0.75, 'optimal': 0.70},
    'kill_percentage': {'min': 0.35, 'max': 0.50, 'optimal': 0.42},
    'block_kill_percentage': {'min': 0.05, 'max': 0.15, 'optimal': 0.10},
    'reception_quality': {'min': 0.70, 'max': 0.85, 'optimal': 0.75},
    'serve_in_rate': {'min': 0.85, 'max': 0.95, 'optimal': 0.90},
    'dig_rate': {'min': 0.65, 'max': 0.80, 'optimal': 0.70},
    # Legacy metrics (kept for compatibility)
    'attack_efficiency': {'min': 0.25, 'max': 0.35, 'optimal': 0.30},
    'service_efficiency': {'min': 0.10, 'max': 0.20, 'optimal': 0.15},
    'block_efficiency': {'min': 0.05, 'max': 0.15, 'optimal': 0.10},
    'reception_percentage': {'min': 0.60, 'max': 0.80, 'optimal': 0.75},
    'ace_to_error_ratio': {'min': 0.5, 'max': 1.5, 'optimal': 1.0}
}

# Valid volleyball action and outcome values
VALID_ACTIONS: List[str] = ['serve', 'receive', 'set', 'attack', 'block', 'dig', 'free_ball']
VALID_OUTCOMES: List[str] = ['kill', 'error', 'good', 'ace', 'blocked', 'out', 'net']

# File upload limits
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS: List[str] = ['.xlsx', '.xls']

# Paths
DEFAULT_TEMPLATE_PATH: str = "../templates/Match_Template.xlsx"
DEFAULT_IMAGES_DIR: str = "assets/images/team"

