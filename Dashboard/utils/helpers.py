"""
Helper utility functions for data processing and player information
"""
from typing import Optional, List
import pandas as pd
import re
from datetime import datetime


def get_player_df(df: pd.DataFrame, player_name: str) -> pd.DataFrame:
    """Get player dataframe with case-insensitive, whitespace-tolerant matching.
    
    Args:
        df: Match dataframe with player column
        player_name: Name of the player to match
        
    Returns:
        DataFrame filtered to player's rows
    """
    if df is None or df.empty or 'player' not in df.columns:
        return pd.DataFrame()
    
    player_name_normalized = player_name.strip().lower()
    # Match case-insensitively and handle whitespace (fillna to handle None/NaN)
    player_col_normalized = df['player'].fillna('').astype(str).str.strip().str.lower()
    return df[player_col_normalized == player_name_normalized]


def get_player_position(df: pd.DataFrame, player_name: str) -> Optional[str]:
    """Get the primary position of a player from the dataframe.
    
    Args:
        df: Match dataframe with player and position columns
        player_name: Name of the player to look up
        
    Returns:
        Primary position string (e.g., 'OH1', 'MB1', 'OPP') or None if not found
    """
    player_data = get_player_df(df, player_name)
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


def _is_good_outcome_base(action: str, outcome: str) -> bool:
    """Base function to check if an outcome is 'good' for a given action.
    
    Args:
        action: Action type (receive, dig, block)
        outcome: Outcome string
        
    Returns:
        True if outcome is considered good for the action
    """
    if action == 'block':
        return outcome == 'touch'
    elif action in ['receive', 'dig']:
        return outcome in ['perfect', 'good']
    return False


def is_good_reception(outcome: str) -> bool:
    """Check if a reception outcome is considered 'good' (perfect or good).
    
    Args:
        outcome: Outcome string
        
    Returns:
        True if outcome is perfect or good
    """
    return _is_good_outcome_base('receive', outcome)


def is_good_dig(outcome: str) -> bool:
    """Check if a dig outcome is considered 'good' (perfect or good).
    
    Args:
        outcome: Outcome string
        
    Returns:
        True if outcome is perfect or good
    """
    return _is_good_outcome_base('dig', outcome)


def is_good_block(outcome: str) -> bool:
    """Check if a block outcome is considered successful (touch).
    
    Args:
        outcome: Outcome string
        
    Returns:
        True if outcome is touch (block touch creates opportunity)
    """
    return _is_good_outcome_base('block', outcome)


def is_good_reception_or_dig(outcome: str) -> bool:
    """Check if a reception or dig outcome is considered 'good'.
    
    DEPRECATED: Use is_good_reception() or is_good_dig() instead.
    Kept for backward compatibility.
    
    Args:
        outcome: Outcome string
        
    Returns:
        True if outcome is perfect or good
    """
    return outcome in ['perfect', 'good']


def get_reception_quality_score(outcome: str) -> float:
    """Get quality score for reception (1.0 = perfect, 0.8 = good, 0.5 = poor, 0.0 = error).
    
    Args:
        outcome: Reception outcome
        
    Returns:
        Quality score (0.0 to 1.0)
    """
    if outcome == 'perfect':
        return 1.0
    elif outcome == 'good':
        return 0.8
    elif outcome == 'poor':
        return 0.5
    elif outcome == 'error':
        return 0.0
    return 0.0


def get_dig_quality_score(outcome: str) -> float:
    """Get quality score for dig (1.0 = perfect, 0.8 = good, 0.5 = poor, 0.0 = error).
    
    Args:
        outcome: Dig outcome
        
    Returns:
        Quality score (0.0 to 1.0)
    """
    if outcome == 'perfect':
        return 1.0
    elif outcome == 'good':
        return 0.8
    elif outcome == 'poor':
        return 0.5
    elif outcome == 'error':
        return 0.0
    return 0.0


def filter_good_receptions(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe to only good receptions (perfect or good).
    
    Args:
        df: Dataframe with 'action' and 'outcome' columns
        
    Returns:
        Filtered dataframe
    """
    if 'action' not in df.columns or 'outcome' not in df.columns:
        return pd.DataFrame()
    receives = df[df['action'] == 'receive']
    return receives[receives['outcome'].isin(['perfect', 'good'])]


def filter_good_digs(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe to only good digs (perfect or good).
    
    Args:
        df: Dataframe with 'action' and 'outcome' columns
        
    Returns:
        Filtered dataframe
    """
    if 'action' not in df.columns or 'outcome' not in df.columns:
        return pd.DataFrame()
    digs = df[df['action'] == 'dig']
    return digs[digs['outcome'].isin(['perfect', 'good'])]


def filter_block_touches(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe to only block touches.
    
    Args:
        df: Dataframe with 'action' and 'outcome' columns
        
    Returns:
        Filtered dataframe
    """
    if 'action' not in df.columns or 'outcome' not in df.columns:
        return pd.DataFrame()
    blocks = df[df['action'] == 'block']
    return blocks[blocks['outcome'] == 'touch']


def count_good_outcomes(df: pd.DataFrame, action: str) -> int:
    """Count good outcomes for a specific action.
    
    Args:
        df: Dataframe with 'action' and 'outcome' columns
        action: Action type (serve, receive, set, attack, block, dig)
        
    Returns:
        Count of good outcomes
    """
    if 'action' not in df.columns or 'outcome' not in df.columns:
        return 0
    
    action_df = df[df['action'] == action]
    
    if action == 'receive':
        return len(action_df[action_df['outcome'].isin(['perfect', 'good'])])
    elif action == 'dig':
        return len(action_df[action_df['outcome'].isin(['perfect', 'good'])])
    elif action == 'block':
        return len(action_df[action_df['outcome'] == 'touch'])
    elif action in ['serve', 'set']:
        return len(action_df[action_df['outcome'] == 'good'])
    elif action == 'attack':
        # For attacks, 'defended' is considered good (kept in play)
        return len(action_df[action_df['outcome'] == 'defended'])
    
    return 0


def extract_date_from_filename(filename: str) -> Optional[datetime.date]:
    """Extract date from filename (expects format with YYYY-MM-DD pattern).
    
    Args:
        filename: Filename string
        
    Returns:
        Date object or None if not found
    """
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
        except (ValueError, AttributeError):
            pass
    return None

