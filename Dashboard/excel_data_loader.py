"""
Excel Data Loader for Volleyball Match Data
Handles the new Excel format with rotation sheets and team points sheets
"""
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExcelMatchLoader:
    """Load and process match data from new Excel format"""
    
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.player_data = {}
        self.team_data = {}  # Set-level aggregated data
        self.team_data_by_rotation = {}  # Rotation-level data: {set_num: {rotation: {...}}}
        self.reception_data_by_rotation = {}  # Rotation-level reception data: {set_num: {rotation: {'good': X, 'total': Y}}}
        self.sets = []
        
        self.load_data()
    
    def load_data(self):
        """Load all data from Excel file"""
        try:
            # Get all sheet names
            xl_file = pd.ExcelFile(self.excel_file)
            sheet_names = xl_file.sheet_names
            
            # Identify sets and rotations
            rotation_sheets = [s for s in sheet_names if s.startswith("Set") and "Rot" in s]
            team_sheets = [s for s in sheet_names if s.startswith("Set") and "Team Points" in s]
            
            # Extract set numbers
            sets_found = set()
            for sheet in rotation_sheets:
                # Extract set number from sheet name like "Set1-Rot1 (...)"
                try:
                    set_num = int(sheet.split("Set")[1].split("-")[0])
                    sets_found.add(set_num)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not extract set number from sheet name '{sheet}': {e}")
                    continue
            
            self.sets = sorted(list(sets_found))
            
            # Load player data from rotation sheets - preserve set information
            self.player_data_by_set = {}  # Store data per set
            
            for sheet_name in rotation_sheets:
                try:
                    df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                    
                    # Extract set and rotation from sheet name
                    parts = sheet_name.split("-")
                    set_num = int(parts[0].replace("Set", ""))
                    rot_num = int(parts[1].replace("Rot", "").split(" ")[0])
                    
                    if set_num not in self.player_data_by_set:
                        self.player_data_by_set[set_num] = {}
                    
                    # Initialize rotation-level reception data storage
                    if set_num not in self.reception_data_by_rotation:
                        self.reception_data_by_rotation[set_num] = {}
                    if rot_num not in self.reception_data_by_rotation[set_num]:
                        self.reception_data_by_rotation[set_num][rot_num] = {'good': 0.0, 'total': 0.0}
                    
                    # Process each player row
                    for _, row in df.iterrows():
                        if pd.notna(row.get('Player')) and pd.notna(row.get('Position')):
                            player = str(row['Player']).strip()
                            position = str(row['Position']).strip()
                            
                            if player == '' or player.startswith('Player_'):
                                continue  # Skip placeholder rows
                            
                            if player not in self.player_data_by_set[set_num]:
                                self.player_data_by_set[set_num][player] = {
                                    'position': position,
                                    'stats': {},
                                    'rotations': []
                                }
                            
                            # Store stats for this set
                            player_stats = {}
                            for col in df.columns:
                                if col not in ['Player', 'Position']:
                                    value = row.get(col, 0)
                                    if pd.notna(value):
                                        try:
                                            player_stats[col] = float(value)
                                            if col not in self.player_data_by_set[set_num][player]['stats']:
                                                self.player_data_by_set[set_num][player]['stats'][col] = 0
                                            self.player_data_by_set[set_num][player]['stats'][col] += float(value)
                                            
                                            # Store rotation-level reception data
                                            if col == 'Reception_Good':
                                                self.reception_data_by_rotation[set_num][rot_num]['good'] += float(value)
                                            elif col == 'Reception_Total':
                                                self.reception_data_by_rotation[set_num][rot_num]['total'] += float(value)
                                        except (ValueError, TypeError) as e:
                                            logger.debug(f"Could not convert value '{value}' to float for column '{col}' in sheet '{sheet_name}': {e}")
                                            continue
                            
                            # Also aggregate for total player_data (for compatibility)
                            if player not in self.player_data:
                                self.player_data[player] = {
                                    'position': position,
                                    'stats': {}
                                }
                            
                            for col, value in player_stats.items():
                                if col not in self.player_data[player]['stats']:
                                    self.player_data[player]['stats'][col] = 0
                                self.player_data[player]['stats'][col] += value
                except Exception as e:
                    logger.error(f"Error loading sheet {sheet_name}: {e}", exc_info=True)
                    continue
            
            # Load team data from team points sheets
            for sheet_name in team_sheets:
                try:
                    df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                    
                    # Extract set number
                    set_num = int(sheet_name.split("Set")[1].split("-")[0])
                    
                    # Initialize set-level and rotation-level data structures
                    if set_num not in self.team_data:
                        self.team_data[set_num] = {
                            'serving_rallies': 0,
                            'serving_points_won': 0,
                            'serving_points_lost': 0,
                            'receiving_rallies': 0,
                            'receiving_points_won': 0,
                            'receiving_points_lost': 0
                        }
                    if set_num not in self.team_data_by_rotation:
                        self.team_data_by_rotation[set_num] = {}
                    
                    # Process each row (each row represents a rotation)
                    for idx, row in df.iterrows():
                        # Try to identify rotation number - check for Rotation column or use row index + 1
                        rotation = None
                        if 'Rotation' in df.columns and pd.notna(row.get('Rotation')):
                            rotation_val = row.get('Rotation')
                            try:
                                # Try direct integer conversion first
                                rotation = int(rotation_val)
                            except (ValueError, TypeError):
                                # Try to extract number from string like "Rotation 1" or "Rotation 1 (Setter Front)"
                                import re
                                rotation_str = str(rotation_val)
                                match = re.search(r'Rotation\s+(\d+)', rotation_str, re.IGNORECASE)
                                if match:
                                    rotation = int(match.group(1))
                                else:
                                    rotation = idx + 1  # Fallback to row index
                        else:
                            rotation = idx + 1  # Default: row 0 = Rotation 1, row 1 = Rotation 2, etc.
                        
                        # Initialize rotation data if needed
                        if rotation not in self.team_data_by_rotation[set_num]:
                            self.team_data_by_rotation[set_num][rotation] = {
                                'serving_rallies': 0,
                                'serving_points_won': 0,
                                'serving_points_lost': 0,
                                'receiving_rallies': 0,
                                'receiving_points_won': 0,
                                'receiving_points_lost': 0
                            }
                        
                        # Store rotation-level data
                        for col in ['Serving_Rallies', 'Serving_Points_Won', 'Serving_Points_Lost',
                                   'Receiving_Rallies', 'Receiving_Points_Won', 'Receiving_Points_Lost']:
                            if col in row and pd.notna(row[col]):
                                key = col.lower()
                                try:
                                    value = float(row[col])
                                    # Store rotation-level
                                    self.team_data_by_rotation[set_num][rotation][key] += value
                                    # Also aggregate to set-level (for backward compatibility)
                                    self.team_data[set_num][key] += value
                                except (ValueError, TypeError, KeyError) as e:
                                    logger.warning(f"Could not process team stat '{col}' in sheet '{sheet_name}', row {idx}: {e}")
                                    continue
                except Exception as e:
                    logger.error(f"Error loading team sheet {sheet_name}: {e}", exc_info=True)
                    continue
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}", exc_info=True)
            raise Exception(f"Error loading Excel file: {e}")
    
    def get_match_dataframe(self):
        """Convert loaded data to format compatible with MatchAnalyzer"""
        # Create a dataframe similar to the old format for compatibility
        data = []
        
        # Process each set separately to preserve set numbers
        for set_num in sorted(self.player_data_by_set.keys()):
            for player, info in self.player_data_by_set[set_num].items():
                stats = info['stats']
                position = info['position']
                
                # Attack data
                attack_kills = int(stats.get('Attack_Kills', 0) or 0)
                attack_good = int(stats.get('Attack_Good', 0) or 0)
                attack_errors = int(stats.get('Attack_Errors', 0) or 0)
                
                # Distribute actions across rotations 1-6
                # NOTE: This is an ESTIMATION when actual rotation data isn't available.
                # Actions are distributed evenly across rotations using modulo operation.
                # For accurate rotation analysis, actual rotation data should be provided
                # in the source Excel file. This distribution ensures each rotation gets
                # approximately equal representation for statistical purposes.
                # Generate point_ids for tracking rallies
                point_counter = 1
                for i, _ in enumerate(range(attack_kills)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    point_id = f"Set{set_num}_Point{point_counter}"
                    point_counter += 1
                    data.append({
                        'timestamp': datetime.now(),
                        'point_id': point_id,
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'attack',
                        'outcome': 'kill',
                        'position': position
                    })
            
                for i, _ in enumerate(range(attack_good)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'attack',
                        'outcome': 'good',
                        'position': position
                    })
            
                for i, _ in enumerate(range(attack_errors)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'attack',
                        'outcome': 'error',
                        'position': position
                    })
            
                # Service data - distribute across rotations
                service_aces = int(stats.get('Service_Aces', 0) or 0)
                service_good = int(stats.get('Service_Good', 0) or 0)
                service_errors = int(stats.get('Service_Errors', 0) or 0)
                
                for i, _ in enumerate(range(service_aces)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'serve',
                        'outcome': 'ace',
                        'position': position
                    })
                
                for i, _ in enumerate(range(service_good)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'serve',
                        'outcome': 'good',
                        'position': position
                    })
                
                for i, _ in enumerate(range(service_errors)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'serve',
                        'outcome': 'error',
                        'position': position
                    })
                
                # Block data - distribute across rotations
                block_kills = int(stats.get('Block_Kills', 0) or 0)
                block_touches = int(stats.get('Block_Touches', 0) or 0)
                block_errors = int(stats.get('Block_Errors', 0) or 0)
                
                for i, _ in enumerate(range(block_kills)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'block',
                        'outcome': 'kill',
                        'position': position
                    })
                
                for i, _ in enumerate(range(block_touches)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'block',
                        'outcome': 'good',
                        'position': position
                    })
                
                for i, _ in enumerate(range(block_errors)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'block',
                        'outcome': 'error',
                        'position': position
                    })
                
                # Reception data
                reception_good = int(stats.get('Reception_Good', 0) or 0)
                reception_errors = int(stats.get('Reception_Errors', 0) or 0)
                good_attack_after = int(stats.get('Good_Attack_After_Reception', 0) or 0)
                
                # Distribute receptions across rotations
                for i, _ in enumerate(range(reception_good + good_attack_after)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'receive',
                        'outcome': 'good',
                        'position': position
                    })
                
                for i, _ in enumerate(range(reception_errors)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'receive',
                        'outcome': 'error',
                        'position': position
                    })
                
                # Setting data - distribute across rotations
                sets_exceptional = int(stats.get('Sets_Exceptional', 0) or 0)
                sets_good = int(stats.get('Sets_Good', 0) or 0)
                sets_errors = int(stats.get('Sets_Errors', 0) or 0)
                
                for i, _ in enumerate(range(sets_exceptional + sets_good)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'set',
                        'outcome': 'good',
                        'position': position
                    })
                
                for i, _ in enumerate(range(sets_errors)):
                    rotation = (i % 6) + 1  # Distribute evenly across rotations 1-6
                    data.append({
                        'set_number': set_num,
                        'rotation': rotation,
                        'player': player,
                        'action': 'set',
                        'outcome': 'error',
                        'position': position
                    })
        
        return pd.DataFrame(data)
    
    def get_team_stats(self):
        """Get aggregated team statistics"""
        total_stats = {
            'serving_rallies': 0,
            'serving_points_won': 0,
            'serving_points_lost': 0,
            'receiving_rallies': 0,
            'receiving_points_won': 0,
            'receiving_points_lost': 0
        }
        
        for set_num, stats in self.team_data.items():
            for key in total_stats:
                total_stats[key] += stats[key]
        
        return total_stats
