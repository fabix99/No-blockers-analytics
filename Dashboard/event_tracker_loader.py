"""
Event Tracker Data Loader for Volleyball Match Data
Handles event-by-event tracking format with individual events and team stats tables
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List, Tuple

from config import (
    VALID_ACTIONS, VALID_OUTCOMES, VALID_ATTACK_TYPES, ACTION_OUTCOME_MAP,
    MAX_FILE_SIZE
)

logger = logging.getLogger(__name__)


class EventTrackerLoader:
    """Load and process match data from event-by-event tracking format"""
    
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.individual_events = None
        self.team_events = None
        self.player_data_by_set = {}
        self.team_data_by_set = {}
        self.team_data_by_rotation = {}  # Added for rotation-level team stats
        self.reception_data_by_rotation = {}
        self.sets = []
        self.validation_errors = []
        self.validation_warnings = []
        self.data_completeness = {
            'individual_events': {'total': 0, 'valid': 0, 'invalid': 0},
            'team_events': {'total': 0, 'valid': 0, 'invalid': 0, 'missing_point_won': 0, 'invalid_point_won': 0}
        }
        
        self.load_data()
    
    def load_data(self):
        """Load all data from Excel file"""
        try:
            # Read the two main sheets
            xl_file = pd.ExcelFile(self.excel_file)
            sheet_names = xl_file.sheet_names
            
            # Check for required sheets
            if 'Individual Events' not in sheet_names:
                raise ValueError("Required sheet 'Individual Events' not found in Excel file")
            if 'Team Events' not in sheet_names:
                raise ValueError("Required sheet 'Team Events' not found in Excel file")
            
            # Load individual events
            self.individual_events = pd.read_excel(self.excel_file, sheet_name='Individual Events')
            # Normalize column names (strip whitespace, handle case)
            self.individual_events.columns = self.individual_events.columns.str.strip()
            
            # Load team events
            self.team_events = pd.read_excel(self.excel_file, sheet_name='Team Events')
            # Normalize column names
            self.team_events.columns = self.team_events.columns.str.strip()
            
            # Validate and process data
            self._validate_individual_events()
            self._process_individual_events()
            self._process_team_events()
            
            logger.info(f"Loaded {len(self.individual_events)} individual events and {len(self.team_events)} team events")
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}", exc_info=True)
            raise Exception(f"Error loading Excel file: {e}")
    
    def _validate_individual_events(self):
        """Validate individual events data structure and values"""
        # Normalize column names for case-insensitive matching
        column_map = {col: col for col in self.individual_events.columns}
        # Create case-insensitive lookup
        col_lower_map = {col.lower(): col for col in self.individual_events.columns}
        
        required_columns = ['Set', 'Point', 'Rotation', 'Player', 'Position', 'Action', 'Outcome']
        missing_columns = []
        for req_col in required_columns:
            if req_col not in self.individual_events.columns:
                # Try case-insensitive match
                if req_col.lower() in col_lower_map:
                    # Rename to standard case
                    actual_col = col_lower_map[req_col.lower()]
                    self.individual_events.rename(columns={actual_col: req_col}, inplace=True)
                else:
                    missing_columns.append(req_col)
        
        if missing_columns:
            self.validation_errors.append(
                f"Missing required columns in Individual Events: {', '.join(missing_columns)}"
            )
            return
        
        # Check for Attack_Type column (required for attacks) - case insensitive
        attack_type_col = None
        for col in self.individual_events.columns:
            if col.lower() == 'attack_type':
                attack_type_col = col
                break
        
        if attack_type_col and attack_type_col != 'Attack_Type':
            self.individual_events.rename(columns={attack_type_col: 'Attack_Type'}, inplace=True)
        
        if 'Attack_Type' not in self.individual_events.columns:
            self.validation_warnings.append(
                "Attack_Type column not found. Attack type will be set to 'normal' for all attacks."
            )
            self.individual_events['Attack_Type'] = None
        
        # Validate actions
        invalid_actions = self.individual_events[
            ~self.individual_events['Action'].isin(VALID_ACTIONS)
        ]
        if len(invalid_actions) > 0:
            unique_invalid = invalid_actions['Action'].unique()
            self.validation_errors.append(
                f"Invalid action values found: {', '.join(unique_invalid)}. "
                f"Valid actions: {', '.join(VALID_ACTIONS)}"
            )
        
        # Validate outcomes based on action
        for action in VALID_ACTIONS:
            if action not in ACTION_OUTCOME_MAP:
                continue
            
            action_events = self.individual_events[self.individual_events['Action'] == action]
            if len(action_events) == 0:
                continue
            
            valid_outcomes = ACTION_OUTCOME_MAP[action]
            invalid_outcomes = action_events[~action_events['Outcome'].isin(valid_outcomes)]
            
            if len(invalid_outcomes) > 0:
                unique_invalid = invalid_outcomes['Outcome'].unique()
                self.validation_errors.append(
                    f"Invalid outcome '{', '.join(unique_invalid)}' for action '{action}'. "
                    f"Valid outcomes: {', '.join(valid_outcomes)}"
                )
        
        # Validate attack type requirement
        attack_events = self.individual_events[self.individual_events['Action'] == 'attack']
        if len(attack_events) > 0:
            missing_attack_type = attack_events[
                (attack_events['Attack_Type'].isna()) | 
                (attack_events['Attack_Type'] == '') |
                (~attack_events['Attack_Type'].isin(VALID_ATTACK_TYPES))
            ]
            
            if len(missing_attack_type) > 0:
                if len(missing_attack_type[missing_attack_type['Attack_Type'].isna()]) > 0:
                    self.validation_errors.append(
                        f"Attack_Type is required for all attacks. Found {len(missing_attack_type)} attacks without valid attack type."
                    )
                else:
                    unique_invalid = missing_attack_type['Attack_Type'].unique()
                    self.validation_errors.append(
                        f"Invalid attack types: {', '.join(unique_invalid)}. "
                        f"Valid attack types: {', '.join(VALID_ATTACK_TYPES)}"
                    )
        
        # Validate numeric columns
        numeric_columns = ['Set', 'Point', 'Rotation']
        for col in numeric_columns:
            if col in self.individual_events.columns:
                non_numeric = pd.to_numeric(self.individual_events[col], errors='coerce').isna()
                if non_numeric.sum() > 0:
                    self.validation_errors.append(
                        f"Column '{col}' contains non-numeric values"
                    )
        
        # Validate rotation range (1-6)
        if 'Rotation' in self.individual_events.columns:
            invalid_rotations = self.individual_events[
                (~self.individual_events['Rotation'].between(1, 6)) &
                (self.individual_events['Rotation'].notna())
            ]
            if len(invalid_rotations) > 0:
                self.validation_errors.append(
                    f"Invalid rotation values found. Rotations must be between 1 and 6."
                )
    
    def _process_individual_events(self):
        """Process individual events into internal data structures"""
        if self.validation_errors:
            logger.warning("Skipping processing due to validation errors")
            return
        
        # Clean and normalize data
        df = self.individual_events.copy()
        
        # Fill missing attack types with 'normal' (default)
        if 'Attack_Type' in df.columns:
            df['Attack_Type'] = df['Attack_Type'].fillna('normal')
            # Replace invalid attack types with 'normal'
            df.loc[~df['Attack_Type'].isin(VALID_ATTACK_TYPES), 'Attack_Type'] = 'normal'
        
        # Extract unique sets
        self.sets = sorted(df['Set'].dropna().unique().tolist())
        
        # Group by set and player to build player_data_by_set
        for set_num in self.sets:
            set_df = df[df['Set'] == set_num]
            self.player_data_by_set[set_num] = {}
            
            # Initialize reception data by rotation
            if set_num not in self.reception_data_by_rotation:
                self.reception_data_by_rotation[set_num] = {}
            
            for _, row in set_df.iterrows():
                player = str(row['Player']).strip()
                position = str(row['Position']).strip()
                action = str(row['Action']).strip().lower()
                outcome = str(row['Outcome']).strip().lower()
                rotation = int(row['Rotation']) if pd.notna(row['Rotation']) else 1
                
                # Initialize player if not exists
                if player not in self.player_data_by_set[set_num]:
                    self.player_data_by_set[set_num][player] = {
                        'position': position,
                        'stats': {},
                        'rotations': []
                    }
                
                # Initialize rotation-level reception data
                if rotation not in self.reception_data_by_rotation[set_num]:
                    self.reception_data_by_rotation[set_num][rotation] = {
                        'good': 0.0,
                        'total': 0.0
                    }
                
                # Aggregate stats based on action and outcome
                self._aggregate_player_stat(set_num, player, action, outcome, rotation)
    
    def _aggregate_player_stat(self, set_num: int, player: str, action: str, outcome: str, rotation: int):
        """Aggregate a single player stat"""
        stats = self.player_data_by_set[set_num][player]['stats']
        
        # Map outcomes to stat keys based on action
        if action == 'attack':
            if outcome == 'kill':
                stats['Attack_Kills'] = stats.get('Attack_Kills', 0) + 1
            elif outcome in ['out', 'net']:
                stats['Attack_Errors'] = stats.get('Attack_Errors', 0) + 1
            elif outcome == 'blocked':
                stats['Attack_Errors'] = stats.get('Attack_Errors', 0) + 1  # Blocked is an error
            elif outcome == 'defended':
                stats['Attack_Good'] = stats.get('Attack_Good', 0) + 1
            # Note: 'error' removed from attack outcomes - all errors covered by 'out', 'net', 'blocked'
            stats['Attack_Total'] = stats.get('Attack_Total', 0) + 1
        
        elif action == 'serve':
            if outcome == 'ace':
                stats['Service_Aces'] = stats.get('Service_Aces', 0) + 1
            elif outcome == 'error':
                stats['Service_Errors'] = stats.get('Service_Errors', 0) + 1
            elif outcome == 'good':
                stats['Service_Good'] = stats.get('Service_Good', 0) + 1
            stats['Service_Total'] = stats.get('Service_Total', 0) + 1
        
        elif action == 'block':
            if outcome == 'kill':
                stats['Block_Kills'] = stats.get('Block_Kills', 0) + 1
            elif outcome == 'touch':
                stats['Block_Touches'] = stats.get('Block_Touches', 0) + 1
            elif outcome == 'block_no_kill':
                stats['Block_Touches'] = stats.get('Block_Touches', 0) + 1  # Count as touch (ball was touched)
            elif outcome == 'no_touch':
                # Block attempted but didn't touch ball - doesn't count as error, just no touch
                pass  # Don't increment any stat, but still count in total
            elif outcome == 'error':
                stats['Block_Errors'] = stats.get('Block_Errors', 0) + 1
            stats['Block_Total'] = stats.get('Block_Total', 0) + 1
        
        elif action == 'receive':
            # Reception quality mapping
            if outcome == 'perfect':
                stats['Reception_Good'] = stats.get('Reception_Good', 0) + 1
                self.reception_data_by_rotation[set_num][rotation]['good'] += 1
            elif outcome == 'good':
                stats['Reception_Good'] = stats.get('Reception_Good', 0) + 1
                self.reception_data_by_rotation[set_num][rotation]['good'] += 1
            elif outcome == 'poor':
                # Poor is still playable, but not "good"
                stats['Reception_Good'] = stats.get('Reception_Good', 0) + 0.5  # Partial credit
                self.reception_data_by_rotation[set_num][rotation]['good'] += 0.5
            elif outcome == 'error':
                stats['Reception_Errors'] = stats.get('Reception_Errors', 0) + 1
            stats['Reception_Total'] = stats.get('Reception_Total', 0) + 1
            self.reception_data_by_rotation[set_num][rotation]['total'] += 1
        
        elif action == 'set':
            if outcome == 'exceptional':
                stats['Sets_Exceptional'] = stats.get('Sets_Exceptional', 0) + 1
            elif outcome == 'good':
                stats['Sets_Good'] = stats.get('Sets_Good', 0) + 1
            elif outcome == 'poor':
                stats['Sets_Errors'] = stats.get('Sets_Errors', 0) + 1  # Poor set is an error
            elif outcome == 'error':
                stats['Sets_Errors'] = stats.get('Sets_Errors', 0) + 1
            stats['Sets_Total'] = stats.get('Sets_Total', 0) + 1
        
        elif action == 'dig':
            # Dig quality mapping (similar to reception)
            if outcome == 'perfect':
                stats['Dig_Good'] = stats.get('Dig_Good', 0) + 1
            elif outcome == 'good':
                stats['Dig_Good'] = stats.get('Dig_Good', 0) + 1
            elif outcome == 'poor':
                stats['Dig_Good'] = stats.get('Dig_Good', 0) + 0.5  # Partial credit
            elif outcome == 'error':
                stats['Dig_Errors'] = stats.get('Dig_Errors', 0) + 1
            stats['Dig_Total'] = stats.get('Dig_Total', 0) + 1
    
    def _process_team_events(self):
        """Process team events into internal data structures"""
        if self.team_events is None or len(self.team_events) == 0:
            logger.warning("No team events data found")
            return
        
        # Normalize column names for case-insensitive matching
        col_lower_map = {col.lower(): col for col in self.team_events.columns}
        
        # Check for both old and new column names for backward compatibility
        required_columns = ['Set', 'Point', 'Rotation', 'Point_Type']
        point_won_col = None
        if 'Point Won' in self.team_events.columns:
            point_won_col = 'Point Won'
        elif 'Point_Winner' in self.team_events.columns:
            point_won_col = 'Point_Winner'
        elif 'point won' in col_lower_map:
            point_won_col = col_lower_map['point won']
        elif 'point_winner' in col_lower_map:
            point_won_col = col_lower_map['point_winner']
            # Rename to new standard
            self.team_events.rename(columns={point_won_col: 'Point Won'}, inplace=True)
            point_won_col = 'Point Won'
        
        missing_columns = []
        for req_col in required_columns:
            if req_col not in self.team_events.columns:
                # Try case-insensitive match
                if req_col.lower() in col_lower_map:
                    # Rename to standard case
                    actual_col = col_lower_map[req_col.lower()]
                    self.team_events.rename(columns={actual_col: req_col}, inplace=True)
                else:
                    missing_columns.append(req_col)
        
        if missing_columns or point_won_col is None:
            missing = missing_columns + ([] if point_won_col else ['Point Won'])
            self.validation_warnings.append(
                f"Missing columns in Team Events: {', '.join(missing)}. "
                "Team statistics may be incomplete."
            )
            return
        
        # Process each team event
        self.data_completeness['team_events']['total'] = len(self.team_events)
        for _, row in self.team_events.iterrows():
            set_num = int(row['Set']) if pd.notna(row['Set']) else None
            point_type = str(row['Point_Type']).strip().lower() if pd.notna(row['Point_Type']) else None
            point_won_value = str(row[point_won_col]).strip().lower() if pd.notna(row[point_won_col]) else None
            rotation = int(row['Rotation']) if pd.notna(row['Rotation']) else 1
            
            # Track data completeness
            if point_won_value is None or pd.isna(row[point_won_col]):
                self.data_completeness['team_events']['missing_point_won'] += 1
                self.data_completeness['team_events']['invalid'] += 1
                continue
            
            if set_num is None or point_type is None:
                self.data_completeness['team_events']['invalid'] += 1
                continue
            
            # Convert point won value to boolean
            # Accept: 'yes', 'y', '1', 'true', 'us' (backward compatibility) → True
            # Accept: 'no', 'n', '0', 'false', 'them' (backward compatibility) → False
            point_won = False
            if point_won_value in ['yes', 'y', '1', 'true', 'us']:
                point_won = True
            elif point_won_value in ['no', 'n', '0', 'false', 'them']:
                point_won = False
            else:
                # Invalid value, skip this row
                self.data_completeness['team_events']['invalid_point_won'] += 1
                self.data_completeness['team_events']['invalid'] += 1
                continue
            
            # Track valid row
            self.data_completeness['team_events']['valid'] += 1
            
            # Initialize set data structures
            if set_num not in self.team_data_by_set:
                self.team_data_by_set[set_num] = {
                    'serving_rallies': 0,
                    'serving_points_won': 0,
                    'serving_points_lost': 0,
                    'receiving_rallies': 0,
                    'receiving_points_won': 0,
                    'receiving_points_lost': 0
                }
            
            # Initialize rotation-level team data
            if set_num not in self.team_data_by_rotation:
                self.team_data_by_rotation[set_num] = {}
            if rotation not in self.team_data_by_rotation[set_num]:
                self.team_data_by_rotation[set_num][rotation] = {
                    'serving_rallies': 0,
                    'serving_points_won': 0,
                    'receiving_rallies': 0,
                    'receiving_points_won': 0
                }
            
            # Update team statistics (both set-level and rotation-level)
            if point_type == 'serving':
                self.team_data_by_set[set_num]['serving_rallies'] += 1
                self.team_data_by_rotation[set_num][rotation]['serving_rallies'] += 1
                if point_won:
                    self.team_data_by_set[set_num]['serving_points_won'] += 1
                    self.team_data_by_rotation[set_num][rotation]['serving_points_won'] += 1
                else:
                    self.team_data_by_set[set_num]['serving_points_lost'] += 1
            elif point_type == 'receiving':
                self.team_data_by_set[set_num]['receiving_rallies'] += 1
                self.team_data_by_rotation[set_num][rotation]['receiving_rallies'] += 1
                if point_won:
                    self.team_data_by_set[set_num]['receiving_points_won'] += 1
                    self.team_data_by_rotation[set_num][rotation]['receiving_points_won'] += 1
                else:
                    self.team_data_by_set[set_num]['receiving_points_lost'] += 1
    
    def get_match_dataframe(self) -> pd.DataFrame:
        """Convert loaded data to format compatible with MatchAnalyzer"""
        if self.validation_errors:
            raise ValueError(f"Cannot create match dataframe due to validation errors: {self.validation_errors}")
        
        data = []
        
        # Process individual events directly into dataframe format
        for _, row in self.individual_events.iterrows():
            set_num = int(row['Set']) if pd.notna(row['Set']) else 1
            point = int(row['Point']) if pd.notna(row['Point']) else 1
            rotation = int(row['Rotation']) if pd.notna(row['Rotation']) else 1
            player = str(row['Player']).strip()
            position = str(row['Position']).strip()
            action = str(row['Action']).strip().lower()
            outcome = str(row['Outcome']).strip().lower()
            
            # Create point_id for tracking
            point_id = f"Set{set_num}_Point{point}"
            
            event_data = {
                'timestamp': datetime.now(),  # Could use actual timestamp if available
                'point_id': point_id,
                'set_number': set_num,
                'rotation': rotation,
                'player': player,
                'action': action,
                'outcome': outcome,
                'position': position
            }
            
            # Add attack type if available
            if action == 'attack' and 'Attack_Type' in row and pd.notna(row['Attack_Type']):
                event_data['attack_type'] = str(row['Attack_Type']).strip().lower()
            
            data.append(event_data)
        
        return pd.DataFrame(data)
    
    def get_player_data(self) -> Dict[int, Dict[str, Any]]:
        """Get player data by set (for compatibility with existing code)"""
        return self.player_data_by_set
    
    @property
    def player_data(self) -> Dict[str, Any]:
        """Get aggregated player data across all sets (for compatibility)"""
        aggregated = {}
        for set_num, set_data in self.player_data_by_set.items():
            for player, info in set_data.items():
                if player not in aggregated:
                    aggregated[player] = {
                        'position': info.get('position', ''),
                        'stats': {}
                    }
                # Aggregate stats
                for stat_key, stat_value in info.get('stats', {}).items():
                    if stat_key not in aggregated[player]['stats']:
                        aggregated[player]['stats'][stat_key] = 0
                    aggregated[player]['stats'][stat_key] += stat_value
        return aggregated
    
    def get_team_data(self) -> Dict[int, Dict[str, Any]]:
        """Get team data by set"""
        return self.team_data_by_set
    
    @property
    def team_data(self) -> Dict[int, Dict[str, Any]]:
        """Get team data (alias for team_data_by_set for compatibility)"""
        return self.team_data_by_set
    
    def get_reception_data_by_rotation(self) -> Dict[int, Dict[int, Dict[str, float]]]:
        """Get reception data by set and rotation"""
        return self.reception_data_by_rotation
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.validation_errors
    
    def get_validation_warnings(self) -> List[str]:
        """Get list of validation warnings"""
        return self.validation_warnings


