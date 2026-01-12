"""
KPI Configuration package for the volleyball analytics dashboard.

Contains:
- kpi_definitions: KPI definitions, help text, and targets
"""
from kpi_config.kpi_definitions import (
    KPI_DEFINITIONS,
    get_kpi_help_text,
    get_kpi_tooltip,
    get_kpi_category
)

__all__ = [
    'KPI_DEFINITIONS',
    'get_kpi_help_text',
    'get_kpi_tooltip',
    'get_kpi_category'
]

