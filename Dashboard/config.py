"""
Configuration constants for the volleyball analytics dashboard
"""
from typing import Dict, List

# No Blockers Brand Color Palette - Updated to match brand colors
CHART_COLORS: Dict[str, str] = {
    'primary': '#050d76',      # No Blockers Dark Blue
    'secondary': '#FFFFFF',    # White
    'success': '#00FF00',      # Green (for success metrics)
    'warning': '#FFD700',      # Gold (for warnings)
    'danger': '#FF4500',       # Orange-red (for errors)
    'info': '#050d76',         # Blue (for info)
    'light': '#F5F5F5',        # Light gray
    'dark': '#050d76',         # Dark blue
}

CHART_COLOR_GRADIENTS: Dict[str, List[str]] = {
    'gradient': ['#050d76', '#1a2a8a', '#2f479e', '#4464b2', '#5981c6', '#6e9eda'],
    'blue_variations': ['#050d76', '#1a2a8a', '#2f479e', '#4464b2', '#5981c6'],
    'blue_white': ['#050d76', '#1a2a8a', '#2f479e', '#4464b2', '#5981c6', '#dbe7ff', '#FFFFFF']
}

# Standardized outcome colors for consistent visualization across all views
OUTCOME_COLORS: Dict[str, str] = {
    # Positive outcomes (green shades)
    'kill': '#28A745',           # Success green
    'ace': '#28A745',            # Success green (same as kill)
    'perfect': '#28A745',        # Success green
    'good': '#6CBF47',           # Light green
    'defended': '#B0E0E6',       # Light blue (good attack but defended)
    
    # Neutral/Moderate outcomes (yellow/gold)
    'poor': '#FFC107',           # Warning yellow
    'touch': '#FFC107',          # Warning yellow (block touch)
    'block_no_kill': '#FF9800',  # Orange (block touched, went back but didn't finish point)
    'no_touch': '#999999',       # Gray (block attempted but didn't touch ball)
    
    # Negative outcomes (red shades)
    'error': '#DC3545',          # Danger red
    'blocked': '#DC3545',        # Danger red
    'out': '#DC3545',            # Danger red
    'net': '#DC3545',            # Danger red
    'pass': '#9E9E9E',           # Gray (free ball stayed on our side)
    
    # Metric-specific colors (for line charts, bar charts)
    'serving_rate': '#4A90E2',   # Blue
    'receiving_rate': '#7ED321', # Green
    'attack_kill': '#F5A623',    # Orange
    'serve_in': '#BD10E0',       # Purple
    'reception': '#50E3C2',      # Teal
    'block_kill': '#B8E986',     # Light green
}

# Standardized action colors for consistent visualization
ACTION_COLORS: Dict[str, str] = {
    'serve': '#4A90E2',          # Blue
    'receive': '#50E3C2',        # Teal
    'set': '#6CBF47',            # Light green
    'attack': '#F5A623',         # Orange
    'block': '#B8E986',          # Light green
    'dig': '#BD10E0',            # Purple
    'free_ball': '#9E9E9E',      # Gray
}

# Standardized attack type colors for consistent visualization
ATTACK_TYPE_COLORS: Dict[str, str] = {
    'normal': '#4A90E2',         # Blue
    'tip': '#F5A623',            # Orange
}

# Standard chart dimensions
CHART_HEIGHTS: Dict[str, int] = {
    'small': 300,      # For small breakdown charts
    'medium': 400,     # For standard charts
    'large': 500,      # For detailed charts
    'line': 400,       # For line/trend charts
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
    # New enhanced metrics (MEDIUM PRIORITY 26-28)
    'attack_efficiency': {'min': 0.25, 'max': 0.35, 'optimal': 0.30},
    'block_touch_rate': {'min': 0.15, 'max': 0.30, 'optimal': 0.20},
    'ace_rate': {'min': 0.05, 'max': 0.15, 'optimal': 0.10},
    'ace_to_error_ratio': {'min': 0.5, 'max': 1.5, 'optimal': 1.0},
    'avg_actions_per_point': {'min': 2.5, 'max': 3.5, 'optimal': 3.0},
    # Legacy metrics (kept for compatibility)
    'service_efficiency': {'min': 0.10, 'max': 0.20, 'optimal': 0.15},
    'block_efficiency': {'min': 0.05, 'max': 0.15, 'optimal': 0.10},
    'reception_percentage': {'min': 0.60, 'max': 0.80, 'optimal': 0.75}
}

# Valid volleyball action and outcome values
VALID_ACTIONS: List[str] = ['serve', 'receive', 'set', 'attack', 'block', 'dig', 'free_ball']

# Complete list of valid outcomes (context-dependent by action)
VALID_OUTCOMES: List[str] = [
    # Universal outcomes
    'kill',        # Point scored (attack, block)
    'error',       # General error (any action)
    
    # Attack-specific
    'blocked',     # Attack blocked by opponent
    'out',         # Attack out of bounds
    'net',         # Attack into net
    'defended',    # Good attack but kept in play
    
    # Service-specific
    'ace',         # Service ace (point)
    'good',        # Good service (in play) - ONLY for service
    
    # Reception-specific (distance-based)
    'perfect',     # Perfect reception (within 1m of setter)
    'poor',        # Poor reception (beyond 3m, playable)
    # Note: 'good' is also used for reception (within 3m) - context distinguishes from service/set
    
    # Block-specific
    'touch',       # Block touch (creates opportunity)
    'no_touch',    # Block attempted but didn't touch ball (replaces 'missed')
    'block_no_kill', # Block touched ball, went back to opponent but didn't finish point
    
    # Free ball-specific
    'pass',        # Free ball stayed on our side
    
    # Set-specific (three tiers)
    'exceptional', # Exceptional set (full attack options)
    # Note: 'good' and 'poor' are also used for sets - context distinguishes from reception/dig
]

# Attack types (required when action = 'attack')
VALID_ATTACK_TYPES: List[str] = ['normal', 'tip']

# Action-specific outcome mappings for validation
ACTION_OUTCOME_MAP: Dict[str, List[str]] = {
    'attack': ['kill', 'blocked', 'out', 'net', 'defended'],  # Removed 'error' - all errors covered
    'serve': ['ace', 'good', 'error'],
    'receive': ['perfect', 'good', 'poor', 'error'],
    'block': ['kill', 'block_no_kill', 'touch', 'no_touch', 'error'],  # Ordered: Kill, Block No Kill, Touch, No Touch, Error
    'set': ['exceptional', 'good', 'poor', 'error'],
    'dig': ['perfect', 'good', 'poor', 'error'],
    'free_ball': ['good', 'pass', 'error']  # Added 'pass' for free ball stayed on our side
}

# Human-readable labels for outcomes (for UI display)
OUTCOME_LABELS: Dict[str, str] = {
    # Block outcomes
    'kill': 'Kill',
    'block_no_kill': 'Block No Kill',
    'touch': 'Touch',
    'no_touch': 'No Touch',
    'error': 'Error',
    # Attack outcomes
    'blocked': 'Blocked',
    'out': 'Out',
    'net': 'Net',
    'defended': 'Defended',
    # Service outcomes
    'ace': 'Ace',
    'good': 'Good',
    # Reception/Dig/Set outcomes
    'perfect': 'Perfect',
    'poor': 'Poor',
    # Set outcomes
    'exceptional': 'Exceptional',
    # Free ball outcomes
    'pass': 'Pass',
}

def get_outcome_label(outcome: str) -> str:
    """Get human-readable label for an outcome value."""
    return OUTCOME_LABELS.get(outcome, outcome.replace('_', ' ').title())

# File upload limits
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS: List[str] = ['.xlsx', '.xls']

# Paths
DEFAULT_TEMPLATE_PATH: str = "../templates/Match_Template.xlsx"
DEFAULT_IMAGES_DIR: str = "assets/images/team"

