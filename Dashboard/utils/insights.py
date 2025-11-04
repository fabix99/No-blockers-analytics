"""
Insights and recommendations generation
"""
from typing import Dict, Any, List, Tuple
import pandas as pd
from match_analyzer import MatchAnalyzer


def generate_insights(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                     targets: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate actionable insights and recommendations from match data.
    
    Args:
        analyzer: MatchAnalyzer instance
        team_stats: Dictionary of team statistics
        targets: Dictionary of target values for KPIs
        
    Returns:
        Dictionary with 'high_priority', 'medium_priority', 'low_priority' lists
    """
    insights: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    
    df = analyzer.match_data
    player_stats = analyzer.calculate_player_metrics()
    
    # Import the full function from main file for now
    # This will be fully extracted later
    from streamlit_dashboard import generate_insights as _generate_insights_full
    return _generate_insights_full(analyzer, team_stats, targets)

