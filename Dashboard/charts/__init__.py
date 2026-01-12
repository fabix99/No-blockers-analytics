"""
Chart generation modules for the dashboard.

This package provides modular chart generation for different skill areas:
- team_charts: Main coordinator and match flow charts
- attack_charts: Attack type and quality distribution
- serving_charts: Serve performance analysis
- blocking_charts: Block performance analysis
- reception_charts: Reception quality analysis
- player_charts: Individual player performance
- utils: Shared chart utilities and theming
"""
from charts.team_charts import (
    get_played_sets,
    create_match_flow_charts,
    create_skill_performance_charts,
)
from charts.attack_charts import create_attacking_performance_charts
from charts.serving_charts import create_serving_performance_charts
from charts.blocking_charts import create_blocking_performance_charts
from charts.reception_charts import create_reception_performance_charts
from charts.player_charts import create_player_charts
from charts.utils import apply_beautiful_theme, plotly_config

__all__ = [
    'get_played_sets',
    'create_match_flow_charts',
    'create_skill_performance_charts',
    'create_attacking_performance_charts',
    'create_serving_performance_charts',
    'create_blocking_performance_charts',
    'create_reception_performance_charts',
    'create_player_charts',
    'apply_beautiful_theme',
    'plotly_config',
]
