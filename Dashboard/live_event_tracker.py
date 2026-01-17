"""
Live Event Tracker - Real-time event tracking interface for volleyball matches

Production-quality refactored version with:
- Modular component architecture
- Comprehensive type hints
- Constants extraction
- Reduced code duplication
- Better separation of concerns
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Optional, Tuple, Set, Callable
from datetime import datetime, date
from io import BytesIO
import sys
from pathlib import Path
import os
import logging

# Add the Dashboard directory to the path for imports
dashboard_dir = Path(__file__).parent
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))

from config import VALID_ACTIONS, ACTION_OUTCOME_MAP, VALID_ATTACK_TYPES, get_outcome_label

# ============================================================================
# CONSTANTS
# ============================================================================

POSITIONS: List[str] = ['S', 'OPP', 'MB1', 'MB2', 'OH1', 'OH2', 'L']

# Rotation to court position mapping
# Court positions (viewed from above, our side):
#   4   3   2
#   5   6   1
ROTATION_TO_COURT_POSITION: Dict[int, Dict[str, float]] = {
    1: {'x': 85, 'y': 75, 'label': '1'},  # Back right (server)
    2: {'x': 85, 'y': 25, 'label': '2'},  # Front right
    3: {'x': 50, 'y': 25, 'label': '3'},  # Front center
    4: {'x': 15, 'y': 25, 'label': '4'},  # Front left
    5: {'x': 15, 'y': 75, 'label': '5'},  # Back left
    6: {'x': 50, 'y': 75, 'label': '6'},  # Back center
}

# Position labels for court display
COURT_POSITION_LABELS: Dict[int, str] = {
    1: 'Back Right',
    2: 'Front Right',
    3: 'Front Center',
    4: 'Front Left',
    5: 'Back Left',
    6: 'Back Center',
}

# Game rules constants
SET_WIN_SCORE: int = 25
SET_WIN_MARGIN: int = 2
MATCH_WIN_SETS: int = 3
ROTATION_SEQUENCE: List[int] = [1, 6, 5, 4, 3, 2]

# Libero restrictions
LIBERO_RESTRICTED_ACTIONS: Set[str] = {'serve', 'attack', 'block'}

# Point type constants
POINT_TYPE_SERVING: str = 'serving'
POINT_TYPE_RECEIVING: str = 'receiving'

# Event keys
OPPONENT_PLAYER: str = 'OPPONENT'
OPPONENT_POSITION: str = 'OPPONENT'

# ============================================================================
# DATA IMPORT
# ============================================================================

def import_existing_match(uploaded_file) -> Optional[Dict[str, any]]:
    """
    Import existing match data from Excel file and determine current state.
    
    Returns:
        Dictionary with match state information or None if import fails
    """
    try:
        # Read Excel file
        xl_file = pd.ExcelFile(uploaded_file)
        
        if 'Individual Events' not in xl_file.sheet_names or 'Team Events' not in xl_file.sheet_names:
            st.error("❌ Excel file must contain 'Individual Events' and 'Team Events' sheets.")
            return None
        
        df_individual = pd.read_excel(uploaded_file, sheet_name='Individual Events')
        df_team = pd.read_excel(uploaded_file, sheet_name='Team Events')
        
        # Normalize column names
        df_individual.columns = df_individual.columns.str.strip()
        df_team.columns = df_team.columns.str.strip()
        
        if df_individual.empty or df_team.empty:
            st.error("❌ Excel file appears to be empty.")
            return None
        
        # Determine current set (highest set number)
        current_set = int(df_team['Set'].max()) if 'Set' in df_team.columns else 1
        
        # Get last team event to determine current state
        last_team_event = df_team.iloc[-1]
        our_score = int(last_team_event.get('Our_Score', 0))
        opponent_score = int(last_team_event.get('Opponent_Score', 0))
        current_rotation = int(last_team_event.get('Rotation', 1))
        
        # Determine if last point ended and who won
        point_won = last_team_event.get('Point Won', False)
        point_won_bool = point_won is not False and str(point_won).lower() in ['yes', 'true', '1']
        
        # Determine current point (next point after last recorded)
        last_point = int(last_team_event.get('Point', 0))
        if point_won_bool:
            # Last point ended, start next point
            current_point = last_point + 1
        else:
            # Last point didn't end yet, continue with same point
            current_point = last_point
        
        # Determine point type for NEXT point based on who won the last point
        # If we won the last point → we serve next
        # If we lost the last point → we receive next
        if point_won_bool:
            # We won the last point, so next point is serving
            point_type = POINT_TYPE_SERVING
            # If we won while receiving, rotation should have changed for the next point
            # Check the point type of the last event to see if we were receiving
            last_point_type_str = str(last_team_event.get('Point_Type', 'serving')).lower()
            if 'receiving' in last_point_type_str:
                # We won while receiving, so rotation should have changed counter-clockwise
                # The rotation in the last event is the rotation DURING that point
                # After winning, rotation changes for the NEXT point
                current_rotation = rotate_setter(current_rotation)
        else:
            # We lost the last point, so next point is receiving
            point_type = POINT_TYPE_RECEIVING
            # Rotation stays the same when we lose
        
        # Determine sets won
        sets_won = 0
        opponent_sets_won = 0
        
        # Count sets won by checking final scores of each set
        for set_num in df_team['Set'].unique():
            set_events = df_team[df_team['Set'] == set_num]
            if not set_events.empty:
                final_set_event = set_events.iloc[-1]
                set_our_score = int(final_set_event.get('Our_Score', 0))
                set_opp_score = int(final_set_event.get('Opponent_Score', 0))
                point_won = final_set_event.get('Point Won', False)
                
                # Determine set winner (team that reached 25+ with 2 point lead, or won the last point)
                if set_our_score >= 25 and set_our_score >= set_opp_score + 2:
                    sets_won += 1
                elif set_opp_score >= 25 and set_opp_score >= set_our_score + 2:
                    opponent_sets_won += 1
                elif point_won:
                    sets_won += 1
                else:
                    opponent_sets_won += 1
        
        # Determine players and positions from individual events
        # Get most recent events for each position to infer current lineup
        players = {pos: '' for pos in POSITIONS}
        
        # Get events from current set (or last set if current set has no events)
        current_set_events = df_individual[df_individual['Set'] == current_set]
        if current_set_events.empty:
            current_set_events = df_individual[df_individual['Set'] == df_individual['Set'].max()]
        
        # Strategy: Get all unique player-position pairs
        # Prioritize more recent events, but collect from entire set to ensure completeness
        # If current set doesn't have enough data, also check previous sets
        
        if not current_set_events.empty:
            # First, try to get from most recent point (most likely to have current lineup)
            latest_point = current_set_events['Point'].max()
            latest_point_events = current_set_events[current_set_events['Point'] == latest_point]
            
            for _, event in latest_point_events.iterrows():
                position = str(event.get('Position', '')).strip().upper()
                player = str(event.get('Player', '')).strip()
                
                if position and player and player.upper() != 'OPPONENT':
                    # Map position codes to our internal format
                    mapped_pos = POSITION_MAP.get(position, None)
                    if mapped_pos and mapped_pos in players:
                        # Only set if not already set (prioritize latest point)
                        if not players[mapped_pos]:
                            players[mapped_pos] = player
            
            # Fill in missing positions from all events in current set
            # This ensures we get all players even if they didn't play in the latest point
            if any(not players[pos] for pos in POSITIONS):
                # Get all unique player-position pairs from current set, sorted by point (most recent first)
                all_set_events = current_set_events.sort_values('Point', ascending=False)
                
                for _, event in all_set_events.iterrows():
                    position = str(event.get('Position', '')).strip().upper()
                    player = str(event.get('Player', '')).strip()
                    
                    if position and player and player.upper() != 'OPPONENT':
                        mapped_pos = POSITION_MAP.get(position, None)
                        if mapped_pos and mapped_pos in players and not players[mapped_pos]:
                            players[mapped_pos] = player
        
        # If still missing positions, check previous sets (starting from most recent)
        # This handles cases where a new set just started and not all players have participated yet
        if any(not players[pos] for pos in POSITIONS):
            all_sets = sorted(df_individual['Set'].unique(), reverse=True)
            
            for set_num in all_sets:
                if set_num == current_set:
                    continue  # Already checked current set
                
                set_events = df_individual[df_individual['Set'] == set_num]
                if set_events.empty:
                    continue
                
                # Start from most recent points in this set and work backwards
                set_points = sorted(set_events['Point'].unique(), reverse=True)
                
                for point_num in set_points:
                    point_events = set_events[set_events['Point'] == point_num]
                    
                    for _, event in point_events.iterrows():
                        position = str(event.get('Position', '')).strip().upper()
                        player = str(event.get('Player', '')).strip()
                        
                        if position and player and player.upper() != 'OPPONENT':
                            mapped_pos = POSITION_MAP.get(position, None)
                            if mapped_pos and mapped_pos in players and not players[mapped_pos]:
                                players[mapped_pos] = player
                    
                    # Stop if we've filled all positions
                    if all(players[pos] for pos in POSITIONS):
                        break
                
                # Stop if we've filled all positions
                if all(players[pos] for pos in POSITIONS):
                    break
        
        # Determine setter start rotation (from first event of first set)
        first_set_events = df_team[df_team['Set'] == 1]
        setter_start_rotation = 1
        if not first_set_events.empty:
            first_rotation = int(first_set_events.iloc[0].get('Rotation', 1))
            setter_start_rotation = first_rotation
        
        # Determine original serve start (from first point of first set)
        first_set_first_point = first_set_events[first_set_events['Point'] == 1]
        original_serve_start = True
        if not first_set_first_point.empty:
            first_point_type = str(first_set_first_point.iloc[0].get('Point_Type', 'serving')).lower()
            original_serve_start = 'serving' in first_point_type
        
        # Extract opponent name and date from filename if possible
        filename = uploaded_file.name if hasattr(uploaded_file, 'name') else 'Match'
        opponent_name = ''
        match_date = datetime.now().date()
        
        # Try to parse filename - handle multiple formats:
        # Format 1: YYYY-MM-DD_OpponentName_event_tracker.xlsx
        # Format 2: OpponentName_YYYY-MM-DD_live.xlsx
        # Format 3: OpponentName_YYYY-MM-DD_event_tracker.xlsx
        import re
        
        # Extract date (YYYY-MM-DD pattern)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            try:
                match_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                pass
        
        # Extract opponent name - try Format 1 first (date at start)
        opponent_match = re.search(r'\d{4}-\d{2}-\d{2}_([^_]+)_(?:event_tracker|live)', filename)
        if opponent_match:
            opponent_name = opponent_match.group(1).replace('_', ' ')
        else:
            # Try Format 2/3 (date in middle or end)
            # Pattern: OpponentName_YYYY-MM-DD_live or OpponentName_YYYY-MM-DD_event_tracker
            opponent_match = re.search(r'^([^_]+(?:_[^_]+)*)_\d{4}-\d{2}-\d{2}_(?:live|event_tracker)', filename)
            if opponent_match:
                opponent_name = opponent_match.group(1).replace('_', ' ')
            else:
                # Fallback: try to extract anything before the date
                opponent_match = re.search(r'^([^_]+(?:_[^_]+)*)_\d{4}-\d{2}-\d{2}', filename)
                if opponent_match:
                    opponent_name = opponent_match.group(1).replace('_', ' ')
        
        return {
            'individual_events': df_individual.to_dict('records'),
            'team_events': df_team.to_dict('records'),
            'current_set': current_set,
            'current_point': current_point,
            'our_score': our_score,
            'opponent_score': opponent_score,
            'current_rotation': current_rotation,
            'point_type': point_type,
            'players': players,
            'setter_start_rotation': setter_start_rotation,
            'original_serve_start': original_serve_start,
            'sets_won': sets_won,
            'opponent_sets_won': opponent_sets_won,
            'opponent_name': opponent_name,
            'match_date': match_date
        }
    
    except Exception as e:
        st.error(f"❌ Error importing match data: {str(e)}")
        return None

# Position mapping for import (handle variations)
POSITION_MAP: Dict[str, str] = {
    'S': 'S',
    'SETTER': 'S',
    'OPP': 'OPP',
    'OPPOSITE': 'OPP',
    'MB1': 'MB1',
    'MB2': 'MB2',
    'MB': 'MB1',  # Default to MB1 if just MB
    'MIDDLE': 'MB1',
    'OH1': 'OH1',
    'OH2': 'OH2',
    'OH': 'OH1',  # Default to OH1 if just OH
    'OUTSIDE': 'OH1',
    'L': 'L',
    'LIBERO': 'L',
    'LIB': 'L'
}

# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def initialize_session_state() -> None:
    """Initialize all session state variables with default values."""
    defaults = {
        'individual_events': [],
        'team_events': [],
        'current_set': 1,
        'current_point': 1,
        'current_rotation': 1,
        'point_type': POINT_TYPE_SERVING,
        'our_score': 0,
        'opponent_score': 0,
        'current_rally_events': [],
        'rally_started': False,
        'players': {pos: '' for pos in POSITIONS},
        'setter_start_rotation': 1,
        'serve_start': True,
        'sets_won': 0,
        'opponent_sets_won': 0,
        'opponent_name': '',
        'match_date': datetime.now().date(),
        '_last_counted_set': 0,  # Track which set was last counted to prevent double-counting
        # Form state variables
        'selected_player': None,
        'selected_player_pos': None,
        'selected_player_name': None,
        'selected_action': None,
        'selected_outcome': None,
        'selected_attack_type': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def has_libero() -> bool:
    """Return True if a libero name has been configured."""
    players = st.session_state.get('players', {})
    libero_name = players.get('L', '')
    if libero_name is None:
        return False
    return bool(str(libero_name).strip())

def can_add_event() -> bool:
    """Check if events can be added (match not complete, no pending confirmations)."""
    return not (
        st.session_state.get('match_complete', False) or
        st.session_state.get('show_set_confirmation', False)
    )

# ============================================================================
# GAME LOGIC FUNCTIONS
# ============================================================================

POSITION_LABELS: Dict[str, str] = {
    'S': 'Setter',
    'OPP': 'Opposite',
    'MB1': 'Middle Blocker 1',
    'MB2': 'Middle Blocker 2',
    'OH1': 'Outside 1',
    'OH2': 'Outside 2',
    'L': 'Libero'
}

# Rotation to court position mapping
# Court positions (viewed from above, our side):
#   4   3   2
#   5   6   1
ROTATION_TO_COURT_POSITION: Dict[int, Dict[str, float]] = {
    1: {'x': 85, 'y': 75, 'label': '1'},  # Back right (server)
    2: {'x': 85, 'y': 25, 'label': '2'},  # Front right
    3: {'x': 50, 'y': 25, 'label': '3'},  # Front center
    4: {'x': 15, 'y': 25, 'label': '4'},  # Front left
    5: {'x': 15, 'y': 75, 'label': '5'},  # Back left
    6: {'x': 50, 'y': 75, 'label': '6'},  # Back center
}

def get_rotation_sequence(start_rotation: int) -> List[int]:
    """Get rotation sequence counter-clockwise: 1-6-5-4-3-2."""
    start_idx = ROTATION_SEQUENCE.index(start_rotation)
    return ROTATION_SEQUENCE[start_idx:] + ROTATION_SEQUENCE[:start_idx]

def rotate_setter(current_rotation: int) -> int:
    """Rotate setter counter-clockwise: 1->6->5->4->3->2->1."""
    rotation_map = {1: 6, 6: 5, 5: 4, 4: 3, 3: 2, 2: 1}
    return rotation_map.get(current_rotation, current_rotation)

def reverse_rotation(current_rotation: int) -> int:
    """Reverse rotation for undo: 6->1, 5->6, 4->5, 3->4, 2->3, 1->2."""
    reverse_map = {6: 1, 5: 6, 4: 5, 3: 4, 2: 3, 1: 2}
    return reverse_map.get(current_rotation, current_rotation)

def check_if_point_ended(action: str, outcome: str) -> Tuple[bool, bool]:
    """
    Check if the action/outcome combination ends the point.
    
    Returns:
        Tuple[bool, bool]: (point_ended, point_won)
    """
    outcome_lower = outcome.lower()
    action_lower = action.lower()
    
    # Point-winning outcomes (we win)
    if outcome_lower == 'kill':
        return True, True
    if outcome_lower == 'ace':
        return True, True
    if action_lower == 'block' and outcome_lower == 'kill':
        return True, True
    
    # Point-losing outcomes (we lose)
    if outcome_lower == 'error':
        return True, False
    if action_lower == 'attack' and outcome_lower in ['out', 'net', 'blocked']:
        return True, False
    
    return False, False

def check_set_win(our_score: int, opp_score: int) -> Tuple[bool, bool]:
    """
    Check if set is won based on scores.
    
    Returns:
        Tuple[bool, bool]: (set_won_by_us, set_won_by_opponent)
    """
    if our_score >= SET_WIN_SCORE and our_score - opp_score >= SET_WIN_MARGIN:
        return True, False
    if opp_score >= SET_WIN_SCORE and opp_score - our_score >= SET_WIN_MARGIN:
        return False, True
    return False, False

# ============================================================================
# EVENT MANAGEMENT
# ============================================================================

def create_event(player: str, position: str, action: str, outcome: str, attack_type: str = '') -> Dict:
    """Create a standardized event dictionary."""
    return {
        'Player': player,
        'Position': position,
        'Action': action,
        'Outcome': outcome,
        'Attack_Type': attack_type if action == 'attack' else ''
    }

def add_event_to_rally(player: str, position: str, action: str, outcome: str, attack_type: str = '') -> None:
    """Add an event to the current rally and auto-detect point end."""
    if not can_add_event():
        st.warning("⚠️ Cannot add events right now. Match complete or set confirmation pending.")
        return
    
    event = create_event(player, position, action, outcome, attack_type)
    st.session_state.current_rally_events.append(event)
    
    point_ended, point_won = check_if_point_ended(action, outcome)
    if point_ended:
        auto_end_point(point_won)

def add_opponent_lost_point() -> None:
    """Record opponent lost point - automatically ends point with us winning."""
    if not can_add_event():
        st.warning("⚠️ Cannot add events right now. Match complete or set confirmation pending.")
        return
    
    # Use 'free_ball' action with 'error' outcome to match validation requirements
    event = create_event(OPPONENT_PLAYER, OPPONENT_POSITION, 'free_ball', 'error')
    st.session_state.current_rally_events.append(event)
    auto_end_point(point_won=True)

def add_our_team_lost_point() -> None:
    """Record our team lost point - automatically ends point with us losing."""
    if not can_add_event():
        st.warning("⚠️ Cannot add events right now. Match complete or set confirmation pending.")
        return
    
    # Use 'free_ball' action with 'error' outcome to match validation requirements
    # This represents a team error where no individual player is at fault
    event = create_event('OUR_TEAM', 'TEAM', 'free_ball', 'error')
    st.session_state.current_rally_events.append(event)
    auto_end_point(point_won=False)

def auto_end_point(point_won: bool) -> None:
    """Automatically end point without confirmation."""
    if not can_add_event() or not st.session_state.current_rally_events:
        return
    
    rally_events = st.session_state.current_rally_events.copy()
    
    # Save individual events with metadata
    for event in rally_events:
        event['Set'] = st.session_state.current_set
        event['Point'] = st.session_state.current_point
        event['Rotation'] = st.session_state.current_rotation
        st.session_state.individual_events.append(event.copy())
    
    # Create and save team event
    team_event = {
        'Set': st.session_state.current_set,
        'Point': st.session_state.current_point,
        'Rotation': st.session_state.current_rotation,
        'Point_Type': st.session_state.point_type,
        'Point Won': 'yes' if point_won else 'no',
        'Our_Score': st.session_state.our_score + (1 if point_won else 0),
        'Opponent_Score': st.session_state.opponent_score + (0 if point_won else 1),
        'Rally_Length': len(rally_events)
    }
    st.session_state.team_events.append(team_event)
    
    # Update scores
    st.session_state.our_score += (1 if point_won else 0)
    st.session_state.opponent_score += (0 if point_won else 1)
    
    # Update rotation (only if we won while receiving)
    if point_won and st.session_state.point_type == POINT_TYPE_RECEIVING:
        st.session_state.current_rotation = rotate_setter(st.session_state.current_rotation)
    
    # Update point type for next point
    st.session_state.point_type = POINT_TYPE_SERVING if point_won else POINT_TYPE_RECEIVING
    
    # Check for set win (only if not already confirmed for this set)
    # Prevent double-counting by checking if set confirmation is already showing
    # and by tracking which set was last counted
    last_counted_set = st.session_state.get('_last_counted_set', 0)
    if not st.session_state.get('show_set_confirmation', False) and last_counted_set < st.session_state.current_set:
        set_won_by_us, set_won_by_opponent = check_set_win(
            st.session_state.our_score,
            st.session_state.opponent_score
        )
        
        if set_won_by_us:
            st.session_state.sets_won += 1
            # Mark this set as counted
            st.session_state['_last_counted_set'] = st.session_state.current_set
            # Only mark match complete if we've won 3 sets
            if st.session_state.sets_won >= MATCH_WIN_SETS:
                st.session_state.match_complete = True
            else:
                st.session_state.show_set_confirmation = True
                st.session_state.set_winner = "Your Team"
        elif set_won_by_opponent:
            st.session_state.opponent_sets_won += 1
            # Mark this set as counted
            st.session_state['_last_counted_set'] = st.session_state.current_set
            # Only mark match complete if opponent has won 3 sets
            if st.session_state.opponent_sets_won >= MATCH_WIN_SETS:
                st.session_state.match_complete = True
            else:
                st.session_state.show_set_confirmation = True
                st.session_state.set_winner = "Opponent"
    
    # Reset rally state
    st.session_state.current_rally_events = []
    st.session_state.rally_started = False
    st.session_state.current_point += 1
    
    # Live export: Export to file path if configured
    live_export_path = st.session_state.get('live_export_path', '')
    if live_export_path and live_export_path.strip():
        try:
            export_success = export_to_file_path(live_export_path.strip())
            if export_success:
                # Store last export time for status display
                st.session_state['last_live_export_time'] = datetime.now()
                # Set flag to show success notification
                st.session_state['show_live_export_notification'] = True
                # Clear any previous errors
                if 'live_export_error' in st.session_state:
                    del st.session_state['live_export_error']
            else:
                # Export failed - error is stored in session state
                pass
        except Exception as e:
            # Store error for display in UI
            st.session_state['live_export_error'] = str(e)
            logger = logging.getLogger(__name__)
            logger.error(f"Error in live export: {e}", exc_info=True)

def undo_last_event() -> None:
    """Undo the last event added, and if it ended a point, undo the point too."""
    if not st.session_state.individual_events:
        st.warning("No events to undo")
        return
    
    last_event = st.session_state.individual_events[-1]
    last_set = last_event.get('Set')
    last_point = last_event.get('Point')
    
    # Determine if this event ended a point
    action = last_event.get('Action', '')
    outcome = last_event.get('Outcome', '')
    is_opponent_lost_point = last_event.get('Player') == OPPONENT_PLAYER and action == 'free_ball' and outcome == 'error'
    is_our_team_lost_point = last_event.get('Player') == 'OUR_TEAM' and action == 'free_ball' and outcome == 'error'
    
    if is_opponent_lost_point:
        point_ended, point_won = True, True
    elif is_our_team_lost_point:
        point_ended, point_won = True, False
    else:
        point_ended, point_won = check_if_point_ended(action, outcome)
    
    # Remove last individual event
    st.session_state.individual_events.pop()
    
    # If this event ended a point, revert point changes
    if point_ended and st.session_state.team_events:
        team_event_to_remove, team_event_index = _find_team_event(last_set, last_point)
        
        if team_event_to_remove:
            _revert_point_changes(team_event_to_remove, point_won)
            st.session_state.team_events.pop(team_event_index)
            _restore_rally_events(last_set, last_point)
    else:
        # Remove from current rally if it exists
        _remove_from_current_rally(last_event)

def _find_team_event(set_num: int, point_num: int) -> Tuple[Optional[Dict], int]:
    """Find team event for given set and point."""
    for i in range(len(st.session_state.team_events) - 1, -1, -1):
        te = st.session_state.team_events[i]
        if te.get('Set') == set_num and te.get('Point') == point_num:
            return te, i
    return None, -1

def _revert_point_changes(team_event: Dict, point_won: bool) -> None:
    """Revert score, rotation, and set changes from a point."""
    # Check if we're at point 1 and need to go back to previous set
    going_back_to_prev_set = (st.session_state.current_point == 1 and 
                               st.session_state.current_set > 1)
    
    if going_back_to_prev_set:
        # Going back to previous set - restore everything from last point of previous set
        st.session_state.current_set -= 1
        
        # Find the last point of the previous set
        last_point_prev_set = 0
        last_team_event_prev_set = None
        for te in reversed(st.session_state.team_events):
            if te.get('Set') == st.session_state.current_set:
                last_point_prev_set = te.get('Point', 0)
                last_team_event_prev_set = te
                break
        
        st.session_state.current_point = last_point_prev_set
        
        # Restore scores and state from the last point of the previous set
        if last_team_event_prev_set:
            st.session_state.our_score = last_team_event_prev_set.get('Our_Score', 0)
            st.session_state.opponent_score = last_team_event_prev_set.get('Opponent_Score', 0)
            st.session_state.current_rotation = last_team_event_prev_set.get('Rotation', st.session_state.setter_start_rotation)
            st.session_state.point_type = last_team_event_prev_set.get('Point_Type', POINT_TYPE_SERVING)
        else:
            # No previous set events, reset to defaults
            st.session_state.our_score = 0
            st.session_state.opponent_score = 0
            st.session_state.current_rotation = st.session_state.setter_start_rotation
            st.session_state.point_type = POINT_TYPE_SERVING
    else:
        # Normal case: just revert the current point
        # Revert scores
        if point_won:
            st.session_state.our_score -= 1
        else:
            st.session_state.opponent_score -= 1
        
        # Revert rotation if needed
        if point_won and team_event.get('Point_Type') == POINT_TYPE_RECEIVING:
            st.session_state.current_rotation = reverse_rotation(st.session_state.current_rotation)
        
        # Revert point type
        st.session_state.point_type = team_event.get('Point_Type', POINT_TYPE_SERVING)
        
        # Revert point number
        if st.session_state.current_point > 1:
            st.session_state.current_point -= 1
    
    # Revert set wins
    if team_event.get('Point Won') == 'yes':
        if st.session_state.sets_won > 0:
            st.session_state.sets_won -= 1
    else:
        if st.session_state.opponent_sets_won > 0:
            st.session_state.opponent_sets_won -= 1
    
    st.session_state.show_set_confirmation = False

def _restore_rally_events(set_num: int, point_num: int) -> None:
    """Restore all events from a point back to current rally."""
    point_events = []
    for event in reversed(st.session_state.individual_events):
        if event.get('Set') == set_num and event.get('Point') == point_num:
            point_events.insert(0, {
                'Player': event.get('Player'),
                'Position': event.get('Position'),
                'Action': event.get('Action'),
                'Outcome': event.get('Outcome'),
                'Attack_Type': event.get('Attack_Type', '')
            })
        else:
            break
    
    st.session_state.current_rally_events = point_events
    st.session_state.rally_started = len(point_events) > 0

def _remove_from_current_rally(event: Dict) -> None:
    """Remove matching event from current rally."""
    if not st.session_state.current_rally_events:
        return
    
    for i in range(len(st.session_state.current_rally_events) - 1, -1, -1):
        e = st.session_state.current_rally_events[i]
        if (e.get('Player') == event.get('Player') and
            e.get('Action') == event.get('Action') and
            e.get('Outcome') == event.get('Outcome')):
            st.session_state.current_rally_events.pop(i)
            break

# ============================================================================
# SET MANAGEMENT
# ============================================================================

def confirm_set_end() -> None:
    """Confirm set end and move to next set."""
    st.session_state.current_set += 1
    st.session_state.current_point = 1
    st.session_state.our_score = 0
    st.session_state.opponent_score = 0
    
    # Use internal rotation value if set, otherwise use setter_start_rotation
    new_rotation = st.session_state.get('_setter_start_rotation_value', st.session_state.setter_start_rotation)
    st.session_state.current_rotation = new_rotation
    
    # Also update setter_start_rotation for the new set (but don't modify widget key directly)
    # We'll use _setter_start_rotation_value to track it
    
    # Alternate serve start between sets
    # Use _serve_start_value to avoid widget conflict (widget uses key="serve_start")
    # Get original_serve_start (what was selected for Set 1)
    original_serve_start = st.session_state.get('original_serve_start')
    if original_serve_start is None:
        # Fallback: use _serve_start_value if original_serve_start wasn't set
        original_serve_start = st.session_state.get('_serve_start_value', True)
        st.session_state.original_serve_start = original_serve_start
    
    if st.session_state.current_set % 2 == 0:
        # Even sets (2, 4, 6...): alternate (opposite of Set 1)
        st.session_state['_serve_start_value'] = not original_serve_start
    else:
        # Odd sets (1, 3, 5...): same as Set 1
        st.session_state['_serve_start_value'] = original_serve_start
    
    # Update point_type based on the new serve_start value
    new_serve_start = st.session_state.get('_serve_start_value', original_serve_start)
    st.session_state.point_type = POINT_TYPE_SERVING if new_serve_start else POINT_TYPE_RECEIVING
    st.session_state.show_score_confirmation = False
    st.session_state.show_set_confirmation = False

# ============================================================================
# DATA EXPORT
# ============================================================================

def export_to_excel() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Export data to Excel matching event tracker template format."""
    if not st.session_state.individual_events:
        st.warning("⚠️ No events to export.")
        return None, None
    
    # Filter out opponent lost point and our team lost point events (keep them in session state but exclude from export)
    filtered_events = [
        event for event in st.session_state.individual_events
        if not (event.get('Player') == OPPONENT_PLAYER and 
                event.get('Action') == 'free_ball' and 
                event.get('Outcome') == 'error' and
                (event.get('Player') == OPPONENT_PLAYER or event.get('Player') == 'OUR_TEAM'))
    ]
    
    if not filtered_events:
        st.warning("⚠️ No events to export (all events were opponent/team lost points).")
        return None, None
    
    df_individual = pd.DataFrame(filtered_events)
    df_individual = df_individual.reindex(columns=[
        'Set', 'Point', 'Rotation', 'Player', 'Position', 
        'Action', 'Outcome', 'Attack_Type', 'Notes'
    ], fill_value='')
    df_individual['Notes'] = ''
    
    df_team = pd.DataFrame(st.session_state.team_events)
    df_team = df_team.reindex(columns=[
        'Set', 'Point', 'Rotation', 'Point_Type', 'Point Won',
        'Our_Score', 'Opponent_Score', 'Rally_Length'
    ])
    
    return df_individual, df_team

def get_export_filename() -> str:
    """Generate export filename from opponent name and date."""
    opponent = st.session_state.opponent_name.strip() if st.session_state.opponent_name else "Match"
    
    date_value = st.session_state.match_date
    if isinstance(date_value, date):
        date_str = date_value.strftime("%Y-%m-%d")
    else:
        date_str = str(date_value)
    
    opponent_clean = "".join(c for c in opponent if c.isalnum() or c in (' ', '-', '_')).strip()
    opponent_clean = opponent_clean.replace(' ', '_')
    return f"{date_str}_{opponent_clean}_event_tracker"

def get_live_export_filename() -> str:
    """Generate live export filename: opponentname_date_live."""
    opponent = st.session_state.opponent_name.strip() if st.session_state.opponent_name else "Match"
    
    date_value = st.session_state.match_date
    if isinstance(date_value, date):
        date_str = date_value.strftime("%Y-%m-%d")
    else:
        date_str = str(date_value)
    
    opponent_clean = "".join(c for c in opponent if c.isalnum() or c in (' ', '-', '_')).strip()
    opponent_clean = opponent_clean.replace(' ', '_')
    return f"{opponent_clean}_{date_str}_live"

def export_to_file_path(file_path: str) -> bool:
    """
    Export data to Excel file at specified path.
    
    Args:
        file_path: Directory path where the file should be saved
        
    Returns:
        True if successful, False otherwise
    """
    if not st.session_state.individual_events:
        return False
    
    try:
        # Get the DataFrames
        df_individual, df_team = export_to_excel()
        
        if df_individual is None or df_team is None:
            return False
        
        # Generate filename
        filename = get_live_export_filename()
        full_path = os.path.join(file_path, f"{filename}.xlsx")
        
        # Ensure directory exists
        os.makedirs(file_path, exist_ok=True)
        
        # Write to file (will overwrite if exists)
        # The context manager automatically saves and closes the file
        with pd.ExcelWriter(full_path, engine='openpyxl', mode='w') as writer:
            df_individual.to_excel(writer, sheet_name='Individual Events', index=False)
            df_team.to_excel(writer, sheet_name='Team Events', index=False)
        
        # Force flush to disk
        import time
        time.sleep(0.1)  # Small delay to ensure file is written
        
        # Verify file was created and has content
        if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
            return True
        else:
            st.session_state['live_export_error'] = f"File was not created or is empty at {full_path}"
            return False
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error exporting to file path: {e}", exc_info=True)
        # Also show error to user in session state for debugging
        st.session_state['live_export_error'] = str(e)
        return False

# ============================================================================
# UI COMPONENT FUNCTIONS
# ============================================================================

def render_css() -> None:
    """Render custom CSS for the application with brand colors."""
    st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #050d76;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .status-card {
        background: linear-gradient(135deg, #050d76 0%, #1a2d8f 100%);
        color: #FFFFFF;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .score-card {
        background: linear-gradient(135deg, #050d76 0%, #1a2d8f 100%);
        color: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .score-card-opponent {
        background: linear-gradient(135deg, #e21b39 0%, #c4162f 100%);
        color: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.8);
        margin-bottom: 0.3rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin-top: 0.3rem;
    }
    .score-value {
        font-size: 3.5rem;
        font-weight: bold;
        line-height: 1;
    }
    .rally-event-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        background: #ffffff;
        border-radius: 5px;
        border-left: 4px solid #050d76;
    }
    .stButton>button {
        font-size: 0.95rem;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
        white-space: normal;
        word-wrap: break-word;
        min-height: 3rem;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    button[kind="primary"] {
        background-color: #050d76 !important;
        border: 2px solid #050d76 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 4px rgba(5,13,118,0.3) !important;
    }
    button[kind="primary"]:hover {
        background-color: #1a2d8f !important;
        border-color: #1a2d8f !important;
    }
    .stSelectbox>div>div, .stTextInput>div>div>input {
        font-size: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def render_match_complete_screen() -> None:
    """Render match complete screen."""
    st.success("🎉 Match Complete!")
    winner = "Our Team" if st.session_state.sets_won >= MATCH_WIN_SETS else "Opponent"
    st.write(f"**Winner:** {winner} ({max(st.session_state.sets_won, st.session_state.opponent_sets_won)} sets)")
    
    # Final score
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Final Score", f"{st.session_state.our_score} - {st.session_state.opponent_score}")
    with col2:
        st.metric("Sets Won", f"{st.session_state.sets_won} - {st.session_state.opponent_sets_won}")
    
    # Auto-export if live export is configured
    if st.session_state.get('live_export_path') and not st.session_state.get('match_complete_exported', False):
        try:
            export_success = export_to_file_path(st.session_state['live_export_path'])
            if export_success:
                st.success("✅ **Final match data automatically exported!**")
                st.session_state['match_complete_exported'] = True
                st.session_state['show_live_export_notification'] = True
        except Exception as e:
            st.warning(f"⚠️ Auto-export failed: {str(e)}")
    
    st.markdown("---")
    
    if st.button("🔄 Start New Match", type="primary", use_container_width=True):
        initialize_session_state()
        st.session_state.match_complete = False
        st.session_state['match_complete_exported'] = False
        st.rerun()

def render_status_cards() -> None:
    """Render match status cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">Current Set</div>
            <div class="metric-value">{st.session_state.current_set}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        point_type_display = "Serving" if st.session_state.point_type == POINT_TYPE_SERVING else "Receiving"
        point_type_icon = "🎯" if st.session_state.point_type == POINT_TYPE_SERVING else "🛡️"
        st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">Point Type</div>
            <div class="metric-value">{point_type_icon} {point_type_display}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">Rotation</div>
            <div class="metric-value">{st.session_state.current_rotation}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">Point #{st.session_state.current_point}</div>
            <div class="metric-value">Set {st.session_state.current_set}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

def render_score_display() -> None:
    """Render score display."""
    col1, col2, col3 = st.columns([2.5, 1, 2.5])
    
    with col1:
        st.markdown(f"""
        <div class="score-card">
            <div style="font-size: 1rem; margin-bottom: 0.3rem; opacity: 0.9;">OUR TEAM</div>
            <div class="score-value">{st.session_state.our_score}</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.8;">
                Sets: {st.session_state.sets_won}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 0.5rem;">
            <div style="font-size: 1.2rem; font-weight: bold; color: #050d76;">VS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="score-card-opponent">
            <div style="font-size: 1rem; margin-bottom: 0.3rem; opacity: 0.9;">OPPONENT</div>
            <div class="score-value">{st.session_state.opponent_score}</div>
            <div style="font-size: 0.85rem; margin-top: 0.5rem; opacity: 0.8;">
                Sets: {st.session_state.opponent_sets_won}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

def get_player_at_rotation(rotation: int) -> Optional[str]:
    """
    Get the player name at a specific rotation position based on current rotation.
    
    Rotation mapping (serving rotation 1):
    - Position 1: Setter
    - Position 2: Outside Hitter 1
    - Position 3: Middle Blocker 1
    - Position 4: Opposite
    - Position 5: Outside Hitter 2
    - Position 6: Middle Blocker 2
    
    When receiving (rotation 2), everyone shifts one position counter-clockwise.
    """
    # Base rotation mapping for serving rotation 1
    rotation_1_mapping = {
        1: 'S',    # Setter
        2: 'OH1',  # Outside Hitter 1
        3: 'MB1',  # Middle Blocker 1
        4: 'OPP',  # Opposite
        5: 'OH2',  # Outside Hitter 2
        6: 'MB2',  # Middle Blocker 2
    }
    
    # Get current rotation (rotation number = setter's position)
    current_rotation = st.session_state.current_rotation
    
    # Rotation number IS the setter's position
    # Rotation 1: Setter at Pos 1
    # Rotation 6: Setter at Pos 6 (one CCW from Rot 1)
    # Rotation 5: Setter at Pos 5 (two CCW from Rot 1)
    # Rotation 4: Setter at Pos 4 (three CCW from Rot 1)
    # Rotation 3: Setter at Pos 3 (four CCW from Rot 1)
    # Rotation 2: Setter at Pos 2 (five CCW from Rot 1)
    
    # Calculate offset: how many positions CCW from Rotation 1
    # Rotation 1: offset = 0
    # Rotation 6: offset = 5 (one CCW)
    # Rotation 5: offset = 4 (two CCW)
    # etc.
    offset = (current_rotation - 1) % 6
    
    # Map court position to base position with counter-clockwise shift
    # Formula: base_pos = ((pos - 1 - offset + 6) % 6) + 1
    # Simplified: base_pos = ((pos - current_rotation + 6) % 6) + 1
    base_position = ((rotation - current_rotation + 6) % 6) + 1
    
    # Get the position code for this base position
    position_code = rotation_1_mapping.get(base_position)
    
    if not position_code:
        return None
    
    # Check for Libero substitution
    player_name = st.session_state.players.get(position_code)
    libero_active = has_libero()
    
    # Libero substitution logic
    if position_code in ['MB1', 'MB2']:
        libero_name = st.session_state.players.get('L')
        if libero_active and libero_name and player_name:
            # Check if this MB is in back row (positions 1, 5, or 6)
            is_back_row = rotation in [1, 5, 6]
            is_serving = st.session_state.point_type == POINT_TYPE_SERVING
            is_server_position = rotation == 1  # Position 1 is the server position
            
            # Libero enters when:
            # 1. MB is in back row and receiving (not serving)
            # 2. MB is in back row and serving, BUT not at server position (Pos 1)
            #    (i.e., MB at Pos 5 or 6 when serving)
            if is_back_row:
                if not is_serving:
                    # Receiving: Libero replaces MB in back row
                    return libero_name
                elif is_serving and not is_server_position:
                    # Serving: Libero replaces MB in back row (Pos 5 or 6), but not if MB is serving (Pos 1)
                    return libero_name
            
            # Libero exits when MB rotates to front row (Pos 2, 3, or 4)
            # Or when MB is serving (at Pos 1)
            return player_name  # Show MB in front row or when MB is serving
    
    return player_name

def get_player_name_by_position(position_code: str) -> Optional[str]:
    """Get player name by position code."""
    return st.session_state.players.get(position_code, '')

def get_players_on_court() -> Set[str]:
    """
    Get set of position codes for players currently on the court.
    Excludes players replaced by Libero.
    """
    players_on_court = set()
    
    # Check each position (1-6) to see which player is there
    for rotation_pos in range(1, 7):
        player_name = get_player_at_rotation(rotation_pos)
        if player_name:
            # Find which position code this player corresponds to
            for pos_code, name in st.session_state.players.items():
                if name == player_name:
                    players_on_court.add(pos_code)
                    break
    
    # Always include Libero if they're on court (they replace MB)
    # Check if Libero is actually on court by checking if any MB is replaced
    libero_name = st.session_state.players.get('L')
    if has_libero() and libero_name:
        # Check if Libero is on court (replacing MB in back row)
        for rotation_pos in range(1, 7):
            player_name = get_player_at_rotation(rotation_pos)
            if player_name == libero_name:
                players_on_court.add('L')
                break
    
    return players_on_court

def render_volleyball_court() -> None:
    """Render a professional volleyball court visualization with trapezoidal shape using Plotly."""
    
    # Get current rotation
    current_rotation = st.session_state.current_rotation
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Court dimensions for trapezoid (half court view from behind)
    # Top line (net) is shorter, bottom line (back line) is wider
    court_top_width = 9  # Width at net (shorter)
    court_bottom_width = 12  # Width at back line (wider)
    court_depth = 9  # Depth of court
    
    # Center coordinates
    center_x = 0
    court_top_y = court_depth  # Top of court (net line)
    court_bottom_y = 0  # Bottom of court (back line)
    
    # Trapezoid vertices (counter-clockwise from top-left)
    trapezoid_x = [
        center_x - court_top_width / 2,  # Top left
        center_x + court_top_width / 2,  # Top right
        center_x + court_bottom_width / 2,  # Bottom right
        center_x - court_bottom_width / 2,  # Bottom left
        center_x - court_top_width / 2  # Close the shape
    ]
    trapezoid_y = [
        court_top_y,  # Top left
        court_top_y,  # Top right
        court_bottom_y,  # Bottom right
        court_bottom_y,  # Bottom left
        court_top_y  # Close the shape
    ]
    
    # Draw trapezoid court background
    fig.add_trace(go.Scatter(
        x=trapezoid_x,
        y=trapezoid_y,
        fill='toself',
        fillcolor='rgba(219, 231, 255, 0.5)',  # Light blue background
        line=dict(color='#050d76', width=2),
        mode='lines',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Net line at top
    fig.add_shape(
        type="line",
        x0=center_x - court_top_width / 2,
        y0=court_top_y,
        x1=center_x + court_top_width / 2,
        y1=court_top_y,
        line=dict(color='#050d76', width=2, dash="dash"),
        layer="below"
    )
    
    # Position coordinates on trapezoidal court
    # Positions arranged: 4-3-2 (front), 5-6-1 (back)
    position_coords = {
        1: {'x': center_x + court_bottom_width / 2 - 1.2, 'y': court_bottom_y + 1.2, 'label': '1'},  # Back right
        2: {'x': center_x + court_top_width / 2 - 1.2, 'y': court_top_y - 1.2, 'label': '2'},  # Front right
        3: {'x': center_x, 'y': court_top_y - 1.2, 'label': '3'},  # Front center
        4: {'x': center_x - court_top_width / 2 + 1.2, 'y': court_top_y - 1.2, 'label': '4'},  # Front left
        5: {'x': center_x - court_bottom_width / 2 + 1.2, 'y': court_bottom_y + 1.2, 'label': '5'},  # Back left
        6: {'x': center_x, 'y': court_bottom_y + 1.2, 'label': '6'},  # Back center
    }
    
    # Add position circles
    for rotation in range(1, 7):
        pos_data = position_coords[rotation]
        x = pos_data['x']
        y = pos_data['y']
        
        # Check if this is the setter position
        is_setter = rotation == current_rotation
        
        # Get player name for this rotation
        player_name = get_player_at_rotation(rotation)
        display_name = player_name if player_name else f"Pos {rotation}"
        if len(display_name) > 12:
            display_name = display_name[:10] + ".."
        
        # Color and size based on setter position
        if is_setter:
            circle_color = "#e21b39"  # Brand red for setter
            circle_size = 50
            hover_text = f"Position {rotation}<br>Setter<br>{display_name}"
        else:
            circle_color = "#050d76"  # Brand dark blue for other players
            circle_size = 45
            hover_text = f"Position {rotation}<br>{display_name}"
        
        # Add circle
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers+text',
            marker=dict(
                size=circle_size,
                color=circle_color,
                line=dict(width=3, color='white'),
                opacity=0.9
            ),
            text=[pos_data['label']],
            textposition="middle center",
            textfont=dict(size=16, color='white', family='Arial Black'),
            name=f"Position {rotation}",
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
        
        # Add player name below position number
        fig.add_annotation(
            x=x,
            y=y - 0.8,
            text=display_name,
            showarrow=False,
            font=dict(size=10, color='white', family='Arial'),
            bgcolor=circle_color,
            bordercolor='white',
            borderwidth=1,
            borderpad=3,
            xref="x",
            yref="y"
        )
        
        # Highlight setter position with ring
        if is_setter:
            # Add gold ring annotation
            fig.add_shape(
                type="circle",
                xref="x",
                yref="y",
                x0=x - 0.6,
                y0=y - 0.6,
                x1=x + 0.6,
                y1=y + 0.6,
                line=dict(color="#dbe7ff", width=3, dash="dash"),  # Light blue ring
                layer="above"
            )
            fig.add_annotation(
                x=x,
                y=y - 1.5,
                text="⭐ SETTER",
                showarrow=False,
                font=dict(size=10, color='#e21b39', family='Arial Black'),  # Brand red
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="#dbe7ff",  # Light blue border
                borderwidth=2,
                borderpad=3
            )
    
    # Removed white box labels - only showing player names in colored bubbles
    
    # Update layout
    fig.update_layout(
        title=dict(
            text="",
            font=dict(size=18, color='#050d76', family='Arial'),  # Brand dark blue
            x=0.5
        ),
        xaxis=dict(
            range=[center_x - court_bottom_width * 0.65, center_x + court_bottom_width * 0.65],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title=""
        ),
        yaxis=dict(
            range=[court_bottom_y - court_depth * 0.2, court_top_y + court_depth * 0.2],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            scaleanchor="x",
            scaleratio=1
        ),
        height=500,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Info caption only (no legend)
    st.caption(f"Rotation: {current_rotation} | Set: {st.session_state.current_set} | Point: {st.session_state.current_point}")

def render_match_setup() -> None:
    with st.expander("⚙️ Match Setup & Configuration", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 👥 Player Positions")
            st.markdown("Enter player names for each position:")
            
            # Order matches Rotation 1: S, OH1, MB1, OPP, OH2, MB2, L
            positions_col1 = ['S', 'OH1', 'MB1', 'OPP']
            positions_col2 = ['OH2', 'MB2', 'L']
            
            col1a, col1b = st.columns(2)
            for col, positions in [(col1a, positions_col1), (col1b, positions_col2)]:
                with col:
                    for pos in positions:
                        label = POSITION_LABELS[pos]
                        st.text_input(
                            label,
                            value=st.session_state.players[pos],
                            key=f"player_{pos}",
                            help=f"Enter name for {label}"
                        )
                        if f"player_{pos}" in st.session_state:
                            st.session_state.players[pos] = st.session_state[f"player_{pos}"]
        
        with col2:
            st.markdown("### 🎮 Match Configuration")
            
            # Opponent name input
            opponent_name = st.text_input(
                "Opponent Team Name",
                value=st.session_state.get('opponent_name', ''),
                key='opponent_name_input',
                help="Enter the name of the opposing team"
            )
            if 'opponent_name_input' in st.session_state:
                st.session_state.opponent_name = st.session_state['opponent_name_input']
            
            # Match date input
            match_date = st.date_input(
                "Match Date",
                value=st.session_state.get('match_date', datetime.now().date()),
                key='match_date_input',
                help="Select the date of the match"
            )
            if 'match_date_input' in st.session_state:
                st.session_state.match_date = st.session_state['match_date_input']
            
            st.markdown("---")
            
            # Get current setter start rotation - use internal value if set, otherwise use widget value
            current_rotation_value = st.session_state.get('_setter_start_rotation_value', st.session_state.get('setter_start_rotation', 1))
            st.selectbox(
                "Setter Start Rotation",
                options=list(range(1, 7)),
                index=current_rotation_value - 1,
                key="setter_start_rotation",
                help="Starting rotation position for the setter (1-6)"
            )
            
            # Update internal rotation value when widget changes (only in setup phase)
            if st.session_state.current_set == 1 and st.session_state.current_point == 1:
                if "setter_start_rotation" in st.session_state:
                    st.session_state['_setter_start_rotation_value'] = st.session_state.setter_start_rotation
            
            serve_start = st.selectbox(
                "Serve Start (Set 1)",
                options=[True, False],
                format_func=lambda x: "Yes (We Serve First)" if x else "No (We Receive First)",
                index=0 if st.session_state.get('_serve_start_value', st.session_state.get('serve_start', True)) else 1,
                key="serve_start",
                help="Which team starts serving in the first set (will alternate automatically)"
            )
            
            # Update _serve_start_value when widget changes (only in setup phase)
            if st.session_state.current_set == 1 and st.session_state.current_point == 1:
                st.session_state['_serve_start_value'] = serve_start
            
            if 'original_serve_start' not in st.session_state:
                st.session_state.original_serve_start = serve_start
            elif st.session_state.current_set == 1:
                st.session_state.original_serve_start = serve_start
            
            # Use _setter_start_rotation_value if available, otherwise use widget value
            final_rotation = st.session_state.get('_setter_start_rotation_value', st.session_state.get('setter_start_rotation', 1))
            # Use _serve_start_value if available (from set alternation), otherwise use widget value
            final_serve_start = st.session_state.get('_serve_start_value', serve_start)
            if st.session_state.current_point == 1 and st.session_state.current_set == 1:
                st.session_state.point_type = POINT_TYPE_SERVING if final_serve_start else POINT_TYPE_RECEIVING
                st.session_state.current_rotation = final_rotation
            
            st.info("💡 **Tip:** Setup only needs to be done once at the start. Serve/receive alternates automatically between sets.")
        
        st.markdown("---")
        st.markdown("### 📤 Live Export Configuration")
        st.markdown("Configure automatic export to a file path. The file will be updated every time a point ends.")
        
        live_export_path = st.text_input(
            "Live Export Path",
            value=st.session_state.get('live_export_path', ''),
            key='live_export_path_input',
            help="Enter the directory path where the live export file should be saved (e.g., /path/to/exports). File will be named: opponentname_date_live.xlsx"
        )
        
        if live_export_path:
            st.session_state['live_export_path'] = live_export_path
            
            # Show status
            if st.session_state.get('last_live_export_time'):
                last_export = st.session_state['last_live_export_time']
                if isinstance(last_export, datetime):
                    export_time_str = last_export.strftime('%H:%M:%S')
                else:
                    export_time_str = str(last_export)
                filename = get_live_export_filename()
                st.success(f"✅ Live export active • Last exported at {export_time_str} • File: `{filename}.xlsx`")
            else:
                filename = get_live_export_filename()
                st.info(f"🔄 Live export configured • File will be saved as: `{filename}.xlsx`")
            
            # Show error if export failed
            if st.session_state.get('live_export_error'):
                st.error(f"❌ Export error: {st.session_state['live_export_error']}")
                # Clear error after showing
                del st.session_state['live_export_error']
            
            # Show test export button
            if st.button("🧪 Test Export Now", use_container_width=True, help="Test the export function manually"):
                if st.session_state.individual_events:
                    export_success = export_to_file_path(live_export_path)
                    if export_success:
                        st.success(f"✅ Test export successful! File saved to: `{os.path.join(live_export_path, get_live_export_filename() + '.xlsx')}`")
                        st.session_state['last_live_export_time'] = datetime.now()
                        st.session_state['show_live_export_notification'] = True
                    else:
                        st.error("❌ Test export failed. Check the error message above.")
                else:
                    st.warning("⚠️ No events to export yet. Add some events first.")
        else:
            st.session_state['live_export_path'] = ''
            st.info("💡 Leave empty to disable live export. Use the export button at the bottom for manual exports.")

def render_set_confirmation() -> None:
    """Render set win confirmation dialog with lineup confirmation."""
    if not st.session_state.get('show_set_confirmation', False):
        return
    
    st.markdown("---")
    winner = st.session_state.get('set_winner', 'Unknown')
    current_set = st.session_state.current_set
    
    st.success(f"### 🏆 Set {current_set} Won by {winner}!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Set Score", f"{st.session_state.our_score} - {st.session_state.opponent_score}")
    with col2:
        st.metric("Match", f"{st.session_state.sets_won} - {st.session_state.opponent_sets_won} sets")
    
    st.markdown("---")
    st.markdown("### 📋 Lineup & Rotation for Next Set")
    
    # Ask if user wants to change lineup
    change_lineup = st.checkbox(
        "Change lineup for next set?",
        value=False,
        key="change_lineup_checkbox",
        help="Check this if you want to modify player positions for the next set"
    )
    
    if change_lineup:
        st.markdown("#### 👥 Update Player Positions")
        col1, col2 = st.columns(2)
        
        positions_col1 = ['S', 'OH1', 'MB1', 'OPP']
        positions_col2 = ['OH2', 'MB2', 'L']
        
        with col1:
            for pos in positions_col1:
                label = POSITION_LABELS[pos]
                new_value = st.text_input(
                    label,
                    value=st.session_state.players[pos],
                    key=f"new_player_{pos}_set_{current_set}",
                    help=f"Enter name for {label}"
                )
                # Update players dict directly (don't modify widget keys)
                if f"new_player_{pos}_set_{current_set}" in st.session_state:
                    st.session_state.players[pos] = st.session_state[f"new_player_{pos}_set_{current_set}"]
        
        with col2:
            for pos in positions_col2:
                label = POSITION_LABELS[pos]
                new_value = st.text_input(
                    label,
                    value=st.session_state.players[pos],
                    key=f"new_player_{pos}_set_{current_set}_2",
                    help=f"Enter name for {label}"
                )
                # Update players dict directly (don't modify widget keys)
                if f"new_player_{pos}_set_{current_set}_2" in st.session_state:
                    st.session_state.players[pos] = st.session_state[f"new_player_{pos}_set_{current_set}_2"]
    
    # Confirm starting rotation for next set
    st.markdown("#### 🎯 Starting Rotation for Next Set")
    # Use internal key to avoid widget conflict
    current_rotation_value = st.session_state.get('_setter_start_rotation_value', st.session_state.get('setter_start_rotation', 1))
    next_set_rotation = st.selectbox(
        "Setter Start Rotation",
        options=list(range(1, 7)),
        index=current_rotation_value - 1,
        key=f"next_set_rotation_{current_set}",
        help="Starting rotation position for the setter in the next set (1-6)"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ NEXT SET", type="primary", use_container_width=True):
            # Update internal rotation value to avoid widget conflict
            st.session_state['_setter_start_rotation_value'] = next_set_rotation
            
            # Update player positions if lineup was changed
            # Only update st.session_state.players, not widget keys
            if change_lineup:
                for pos in POSITIONS:
                    # Get the new value from the input widgets
                    new_value = None
                    if f"new_player_{pos}_set_{current_set}" in st.session_state:
                        new_value = st.session_state[f"new_player_{pos}_set_{current_set}"]
                    elif f"new_player_{pos}_set_{current_set}_2" in st.session_state:
                        new_value = st.session_state[f"new_player_{pos}_set_{current_set}_2"]
                    
                    # Update only the players dict (not widget keys)
                    if new_value is not None:
                        st.session_state.players[pos] = new_value
            
            confirm_set_end()
            st.rerun()
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            if winner == "Your Team":
                st.session_state.sets_won -= 1
            else:
                st.session_state.opponent_sets_won -= 1
            st.session_state.show_set_confirmation = False
            st.rerun()
    
    st.markdown("---")

def render_rally_events() -> None:
    """Render current rally events display."""
    if st.session_state.current_rally_events:
        st.markdown("**📋 Current Rally Events:**")
        recent_events = st.session_state.current_rally_events[-3:]
        
        for i, event in enumerate(recent_events, 1):
            event_num = len(st.session_state.current_rally_events) - len(recent_events) + i
            attack_type_str = f" [{event['Attack_Type']}]" if event.get('Attack_Type') else ""
            st.markdown(f"""
            <div class="rally-event-item">
                <strong>#{event_num}</strong> {event['Player']} ({event['Position']}) - 
                {event['Action'].upper()}: {event['Outcome']}{attack_type_str}
            </div>
            """, unsafe_allow_html=True)
        
        if len(st.session_state.current_rally_events) > 3:
            with st.expander(f"View all {len(st.session_state.current_rally_events)} events"):
                rally_df = pd.DataFrame(st.session_state.current_rally_events)
                rally_df_display = rally_df.copy()
                rally_df_display.insert(0, '#', range(1, len(rally_df_display) + 1))
                st.dataframe(
                    rally_df_display[['#', 'Player', 'Position', 'Action', 'Outcome', 'Attack_Type']],
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.info("📝 Ready to log events - Select player and action below")

def render_button_grid(items: List[str], selected: Optional[str], key_prefix: str, 
                       on_select: Callable[[str], None], max_cols: int = 7) -> None:
    """Render a grid of selectable buttons."""
    cols = st.columns(min(len(items), max_cols))
    for idx, item in enumerate(items):
        with cols[idx % len(cols)]:
            is_selected = selected == item
            if st.button(
                item.upper(),
                key=f"{key_prefix}_{item}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                on_select(item)

def get_available_actions(selected_position: Optional[str] = None) -> List[str]:
    """
    Get available actions based on:
    1. Player position (Libero restrictions)
    2. Point type (serving/receiving)
    3. Already recorded actions in current rally
    """
    available = VALID_ACTIONS.copy()
    
    # 1. Libero restrictions
    if selected_position == 'L' and has_libero():
        available = [a for a in available if a not in LIBERO_RESTRICTED_ACTIONS]
    
    # 2. Point type restrictions
    point_type = st.session_state.point_type
    if point_type == POINT_TYPE_RECEIVING:
        # When receiving, cannot serve
        available = [a for a in available if a != 'serve']
    elif point_type == POINT_TYPE_SERVING:
        # When serving, cannot receive
        available = [a for a in available if a != 'receive']
    
    # 3. Check already recorded actions in current rally
    rally_events = st.session_state.current_rally_events
    if rally_events:
        # Get list of actions already recorded in this rally
        recorded_actions = [event.get('Action', '').lower() for event in rally_events]
        
        # Cannot serve twice in same point
        if 'serve' in recorded_actions:
            available = [a for a in available if a != 'serve']
        
        # Cannot receive twice in same point
        if 'receive' in recorded_actions:
            available = [a for a in available if a != 'receive']
        
        # Note: Removed constraint preventing consecutive digs - liberos can dig multiple times in a row
    
    return available

def render_event_entry_form() -> None:
    """Render the event entry form with player/action/outcome selection."""
    # Get players on court (excludes those replaced by Libero)
    players_on_court = get_players_on_court()
    available_players = {
        pos: name for pos, name in st.session_state.players.items() 
        if name and pos in players_on_court
    }
    
    if not available_players:
        st.warning("⚠️ Enter player names in Match Setup first")
        return
    
    # Initialize form state
    form_state_keys = ['selected_player', 'selected_action', 'selected_outcome', 'selected_attack_type']
    for key in form_state_keys:
        if key not in st.session_state:
            st.session_state[key] = None
    
    # Player Selection
    st.markdown("**👤 Select Player:**")
    player_cols = st.columns(min(len(available_players), 7))
    for idx, (pos, name) in enumerate(available_players.items()):
        with player_cols[idx % len(player_cols)]:
            label = f"{POSITION_LABELS[pos]}\n{name}"
            is_selected = st.session_state.selected_player == f"{pos}_{name}"
            if st.button(
                label,
                key=f"player_btn_{pos}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_player = f"{pos}_{name}"
                st.session_state.selected_player_pos = pos
                st.session_state.selected_player_name = name
                # Reset restricted actions if Libero selected
                if pos == 'L' and st.session_state.selected_action in LIBERO_RESTRICTED_ACTIONS:
                    st.session_state.selected_action = None
                    st.session_state.selected_outcome = None
                    st.session_state.selected_attack_type = None
                st.rerun()
    
    if st.session_state.selected_player:
        st.success(f"✓ Selected: {st.session_state.selected_player_name} ({POSITION_LABELS[st.session_state.selected_player_pos]})")
    
    # Action Selection
    available_actions = get_available_actions(st.session_state.selected_player_pos if st.session_state.selected_player else None)
    
    if not st.session_state.current_rally_events and st.session_state.point_type == POINT_TYPE_SERVING:
        st.markdown("**⚡ Select Action:** (First action must be SERVE)")
        if 'serve' in available_actions:
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            with col1:
                is_selected = st.session_state.selected_action == 'serve'
                if st.button(
                    "SERVE",
                    key="action_btn_serve_first",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_action = 'serve'
                    st.session_state.selected_outcome = None
                    st.rerun()
            for i in range(2, 8):
                with [col2, col3, col4, col5, col6, col7][i-2]:
                    st.empty()
        else:
            if has_libero():
                st.warning("⚠️ Libero cannot serve. Please select a different player.")
    else:
        st.markdown("**⚡ Select Action:**")
        if st.session_state.selected_player_pos == 'L' and has_libero():
            st.info("ℹ️ Libero cannot serve, attack, or block")
        render_button_grid(
            available_actions,
            st.session_state.selected_action,
            "action_btn",
            lambda action: _handle_action_selection(action)
        )
    
    if st.session_state.selected_action:
        st.success(f"✓ Selected: {st.session_state.selected_action}")
    
    # Outcome Selection
    if st.session_state.selected_action:
        valid_outcomes = ACTION_OUTCOME_MAP.get(st.session_state.selected_action, [])
        st.markdown("**📊 Select Outcome:**")
        num_cols = min(len(valid_outcomes), 6)
        outcome_cols = st.columns(num_cols)
        for idx, outcome in enumerate(valid_outcomes):
            with outcome_cols[idx % num_cols]:
                is_selected = st.session_state.selected_outcome == outcome
                outcome_label = get_outcome_label(outcome).upper()
                if st.button(
                    outcome_label,
                    key=f"outcome_btn_{outcome}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_outcome = outcome
                    # Auto-add event if form is complete (unless it's an attack that needs attack type)
                    if st.session_state.selected_action != 'attack':
                        if _validate_event_form():
                            _add_event_from_form()
                    st.rerun()
        
        if st.session_state.selected_outcome:
            st.success(f"✓ Selected: {st.session_state.selected_outcome}")
    
    # Attack Type Selection
    if st.session_state.selected_action == 'attack':
        st.markdown("**🎯 Select Attack Type:**")
        render_button_grid(
            VALID_ATTACK_TYPES,
            st.session_state.selected_attack_type,
            "attack_type_btn",
            lambda attack_type: _handle_attack_type_selection(attack_type)
        )
        
        if st.session_state.selected_attack_type:
            st.success(f"✓ Selected: {st.session_state.selected_attack_type}")
    
    # Show status if form is incomplete (for attack actions that need attack type)
    if st.session_state.selected_action == 'attack' and st.session_state.selected_outcome and not st.session_state.selected_attack_type:
        st.info("ℹ️ Select Attack Type to complete the event")
    
    # Opponent Lost Point Button
    can_record_opponent_lost_point = not (
        st.session_state.point_type == POINT_TYPE_SERVING and 
        not st.session_state.current_rally_events
    )
    
    # Our Team Lost Point Button
    can_record_our_team_lost_point = not (
        st.session_state.point_type == POINT_TYPE_RECEIVING and 
        not st.session_state.current_rally_events
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if can_record_opponent_lost_point:
            if st.button("❌ OPPONENT LOST POINT (We Win)", type="primary", use_container_width=True,
                        help="Record opponent lost point - automatically ends point with us winning"):
                add_opponent_lost_point()
                st.rerun()
        else:
            st.info("ℹ️ Record your serve first")
    
    with col3:
        if can_record_our_team_lost_point:
            if st.button("❌ OUR TEAM LOST POINT (We Lose)", type="primary", use_container_width=True,
                        help="Record our team lost point - automatically ends point with us losing"):
                add_our_team_lost_point()
                st.rerun()
        else:
            st.info("ℹ️ Record opponent serve first")
    
    # Undo Button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("↶ UNDO LAST EVENT", type="secondary", use_container_width=True,
                    help="Remove the last event added (and point if it ended one)"):
            undo_last_event()
            st.rerun()

def _handle_action_selection(action: str) -> None:
    """Handle action selection."""
    st.session_state.selected_action = action
    st.session_state.selected_outcome = None
    st.rerun()

def _handle_attack_type_selection(attack_type: str) -> None:
    """Handle attack type selection."""
    st.session_state.selected_attack_type = attack_type
    # Auto-add event if form is now complete
    if _validate_event_form():
        _add_event_from_form()
    st.rerun()

def _validate_event_form() -> bool:
    """Validate event form and return True if all required fields are filled."""
    if not st.session_state.selected_player:
        return False
    if not st.session_state.selected_action:
        return False
    if not st.session_state.selected_outcome:
        return False
    if st.session_state.selected_action == 'attack' and not st.session_state.selected_attack_type:
        return False
    
    # Libero restrictions
    if st.session_state.selected_player_pos == 'L' and has_libero():
        if st.session_state.selected_action in LIBERO_RESTRICTED_ACTIONS:
            st.warning("⚠️ Libero cannot serve, attack, or block")
            return False
    
    # First action must be serve when serving
    if not st.session_state.current_rally_events and st.session_state.point_type == POINT_TYPE_SERVING:
        if st.session_state.selected_action != 'serve':
            st.warning("⚠️ First action must be SERVE when we're serving")
            return False
        if st.session_state.selected_player_pos == 'L' and has_libero():
            st.warning("⚠️ Libero cannot serve. Please select a different player.")
            return False
    
    return True

def _get_missing_fields() -> List[str]:
    """Get list of missing required fields."""
    missing = []
    if not st.session_state.selected_player:
        missing.append("Player")
    if not st.session_state.selected_action:
        missing.append("Action")
    if not st.session_state.selected_outcome:
        missing.append("Outcome")
    if st.session_state.selected_action == 'attack' and not st.session_state.selected_attack_type:
        missing.append("Attack Type")
    return missing

def _add_event_from_form() -> None:
    """Add event from form selections."""
    pos = st.session_state.selected_player_pos
    name = st.session_state.selected_player_name
    action = st.session_state.selected_action
    outcome = st.session_state.selected_outcome
    attack_type = st.session_state.selected_attack_type if action == 'attack' else ''
    
    add_event_to_rally(name, pos, action, outcome, attack_type)
    
    # Reset selections
    st.session_state.selected_player = None
    st.session_state.selected_action = None
    st.session_state.selected_outcome = None
    st.session_state.selected_attack_type = None
    
    if not st.session_state.rally_started:
        st.session_state.rally_started = True

def render_live_events_tables() -> None:
    """Render live events tables."""
    st.markdown("### 📊 Live Events Tables")
    
    tab1, tab2 = st.tabs(["📋 Individual Events", "👥 Team Events"])
    
    with tab1:
        if st.session_state.individual_events:
            df_individual = pd.DataFrame(st.session_state.individual_events)
            if 'Notes' not in df_individual.columns:
                df_individual['Notes'] = ''
            df_individual = df_individual.reindex(columns=[
                'Set', 'Point', 'Rotation', 'Player', 'Position', 
                'Action', 'Outcome', 'Attack_Type', 'Notes'
            ], fill_value='')
            st.dataframe(df_individual, use_container_width=True, hide_index=True)
            st.caption(f"Total: {len(df_individual)} individual events")
        else:
            st.info("📝 No individual events recorded yet. Start tracking points to see events here.")
    
    with tab2:
        if st.session_state.team_events:
            df_team = pd.DataFrame(st.session_state.team_events)
            df_team = df_team.reindex(columns=[
                'Set', 'Point', 'Rotation', 'Point_Type', 'Point Won',
                'Our_Score', 'Opponent_Score', 'Rally_Length'
            ])
            st.dataframe(df_team, use_container_width=True, hide_index=True)
            st.caption(f"Total: {len(df_team)} team events (points)")
        else:
            st.info("📝 No team events recorded yet. Start tracking points to see events here.")

def render_export_section() -> None:
    """Render data export section."""
    if not st.session_state.individual_events:
        st.info("📝 No events recorded yet. Start tracking points to see export options here.")
        return
    
    st.markdown("### 📥 Export Data")
    st.markdown("Export your match data to Excel format matching the event tracker template.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Preview Data", use_container_width=True, help="Preview the data before exporting"):
            st.session_state.show_preview = True
    
    with col2:
        if st.button("💾 Export to Excel", use_container_width=True, help="Download data as Excel file"):
            df_individual, df_team = export_to_excel()
            if df_individual is not None:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_individual.to_excel(writer, sheet_name='Individual Events', index=False)
                    df_team.to_excel(writer, sheet_name='Team Events', index=False)
                
                output.seek(0)
                filename = get_export_filename()
                st.download_button(
                    label="⬇️ Download Excel File",
                    data=output.getvalue(),
                    file_name=f"{filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    if st.session_state.get('show_preview', False):
        st.markdown("#### Individual Events Preview")
        # Filter out opponent lost point and our team lost point events from preview (same as export)
        filtered_events = [
            event for event in st.session_state.individual_events
            if not (event.get('Action') == 'free_ball' and 
                    event.get('Outcome') == 'error' and
                    (event.get('Player') == OPPONENT_PLAYER or event.get('Player') == 'OUR_TEAM'))
        ]
        df_individual = pd.DataFrame(filtered_events)
        st.dataframe(df_individual, use_container_width=True)
        
        st.markdown("#### Team Events Preview")
        df_team = pd.DataFrame(st.session_state.team_events)
        st.dataframe(df_team, use_container_width=True)

def render_import_section() -> None:
    """Render data import section at the top."""
    if st.session_state.get('match_started', False) and st.session_state.individual_events:
        # Don't show import if match already has data
        return
    
    with st.expander("📥 Import Existing Match Data", expanded=False):
        st.markdown("Load an existing match file to resume tracking from where you left off.")
        
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx'],
            help="Upload an event tracker Excel file to resume a match"
        )
        
        if uploaded_file is not None:
            if st.button("📂 Import Match Data", type="primary", use_container_width=True):
                with st.spinner("Importing match data..."):
                    match_data = import_existing_match(uploaded_file)
                    
                    if match_data:
                        # Load data into session state
                        st.session_state.individual_events = match_data['individual_events']
                        st.session_state.team_events = match_data['team_events']
                        st.session_state.current_set = match_data['current_set']
                        st.session_state.current_point = match_data['current_point']
                        st.session_state.our_score = match_data['our_score']
                        st.session_state.opponent_score = match_data['opponent_score']
                        st.session_state.current_rotation = match_data['current_rotation']
                        st.session_state.point_type = match_data['point_type']
                        st.session_state.players = match_data['players']
                        st.session_state.setter_start_rotation = match_data['setter_start_rotation']
                        st.session_state.original_serve_start = match_data['original_serve_start']
                        st.session_state['_serve_start_value'] = match_data['original_serve_start']
                        st.session_state.sets_won = match_data['sets_won']
                        st.session_state.opponent_sets_won = match_data['opponent_sets_won']
                        st.session_state.opponent_name = match_data['opponent_name']
                        st.session_state.match_date = match_data['match_date']
                        st.session_state.match_started = True
                        st.session_state.current_rally_events = []
                        st.session_state.rally_started = False
                        
                        # Update widget keys for Match Setup section to autofill
                        for pos in POSITIONS:
                            if match_data['players'].get(pos):
                                st.session_state[f"player_{pos}"] = match_data['players'][pos]
                        
                        # Update serve_start widget key
                        st.session_state['serve_start'] = match_data['original_serve_start']
                        
                        # Update opponent_name and match_date widget keys if they exist
                        if match_data['opponent_name']:
                            st.session_state['opponent_name'] = match_data['opponent_name']
                        if match_data['match_date']:
                            st.session_state['match_date'] = match_data['match_date']
                        
                        st.success(f"✅ Match data imported successfully! Resuming from Set {match_data['current_set']}, Point {match_data['current_point']}")
                        st.rerun()

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main() -> None:
    """Main Live Event Tracker interface."""
    st.set_page_config(
        page_title="Live Event Tracker",
        page_icon="🏐",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    render_css()
    st.markdown('<h1 class="main-header">🏐 Live Event Tracker</h1>', unsafe_allow_html=True)
    
    initialize_session_state()
    
    # Display live export notification at the top if export just happened
    if st.session_state.get('show_live_export_notification', False):
        filename = get_live_export_filename()
        live_export_path = st.session_state.get('live_export_path', '')
        current_score = f"{st.session_state.our_score}-{st.session_state.opponent_score}"
        
        if live_export_path:
            full_path = os.path.join(live_export_path, f"{filename}.xlsx")
            st.success(f"✅ **Live Data Exported!** File saved: `{full_path}` • Score: {current_score}")
        else:
            st.success(f"✅ **Live Data Exported!** File: `{filename}.xlsx` • Score: {current_score}")
        # Clear the notification flag after showing
        st.session_state['show_live_export_notification'] = False
    
    # Import section at the top (only if match not started)
    render_import_section()
    
    if st.session_state.get('match_complete', False):
        render_match_complete_screen()
        st.markdown("---")
        st.markdown("### 📥 Export Final Match Data")
        st.info("💡 Match is complete! You can still export your data below.")
        render_export_section()
        # Don't stop - let the rest of the UI render (tables, etc.) but disable event entry
        # The can_add_event() function will prevent new events from being added
    
    # Show status cards and other UI elements even when match is complete
    render_status_cards()
    render_score_display()
    
    # Only show setup and event entry if match is not complete
    if not st.session_state.get('match_complete', False):
        render_match_setup()
        render_set_confirmation()
        render_rally_events()
        
        # Two-column layout: Court rotation (25%) and Quick Event Entry (75%)
        col_left, col_right = st.columns([1, 3])
        
        with col_left:
            render_volleyball_court()
        
        with col_right:
            st.markdown("### ⚡ Quick Event Entry")
            render_event_entry_form()
    else:
        # Match complete - show read-only view
        st.info("🏆 Match Complete - Event entry disabled. Use export section above to save your data.")
        render_volleyball_court()
    
    render_live_events_tables()
    
    # Show export section again at bottom if match is not complete (for convenience)
    if not st.session_state.get('match_complete', False):
        render_export_section()

if __name__ == "__main__":
    main()
