"""
Helper utility functions for data processing and player information
"""
from typing import Optional
import pandas as pd


def get_player_position(df: pd.DataFrame, player_name: str) -> Optional[str]:
    """Get the primary position of a player from the dataframe.
    
    Args:
        df: Match dataframe with player and position columns
        player_name: Name of the player to look up
        
    Returns:
        Primary position string (e.g., 'OH1', 'MB1', 'OPP') or None if not found
    """
    player_data = df[df['player'] == player_name]
    if 'position' in player_data.columns and len(player_data) > 0:
        # Get the most common position for this player
        position_counts = player_data['position'].value_counts()
        if len(position_counts) > 0:
            return position_counts.index[0]
    return None


def calculate_total_points_from_loader(loader) -> float:
    """Calculate total points from loader team_data.
    
    Args:
        loader: ExcelMatchLoader instance with team_data attribute
        
    Returns:
        Total points (serving_points_won + receiving_points_won) across all sets
    """
    if loader is None or not hasattr(loader, 'team_data') or not loader.team_data:
        return 0.0
    
    total_points = 0.0
    for set_num in loader.team_data.keys():
        serving_points = float(loader.team_data[set_num].get('serving_points_won', 0) or 0)
        receiving_points = float(loader.team_data[set_num].get('receiving_points_won', 0) or 0)
        total_points += (serving_points + receiving_points)
    
    return total_points

