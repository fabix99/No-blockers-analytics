import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class MatchAnalyzer:
    """
    Advanced match analysis tools for volleyball team performance
    """
    
    def __init__(self, data_file=None):
        self.data_file = data_file
        self.match_data = None
        self.team_stats = {}
        self.player_stats = {}
        
        if data_file and os.path.exists(data_file):
            self.load_match_data(data_file)
    
    def load_match_data(self, filename):
        """Load match data from Excel file"""
        try:
            self.match_data = pd.read_excel(filename, sheet_name='Raw_Data')
            self.data_file = filename
            print(f"Loaded match data from {filename}")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def calculate_team_metrics(self):
        """Calculate key team performance metrics"""
        if self.match_data is None:
            return None
        
        df = self.match_data
        
        # Basic team stats
        total_actions = len(df)
        sets_played = df['set_number'].nunique()
        
        # Attack efficiency
        attacks = df[df['action'] == 'attack']
        attack_kills = len(attacks[attacks['outcome'] == 'kill'])
        attack_errors = len(attacks[attacks['outcome'] == 'error'])
        attack_attempts = len(attacks)
        attack_efficiency = (attack_kills - attack_errors) / attack_attempts if attack_attempts > 0 else 0
        
        # Service stats
        serves = df[df['action'] == 'serve']
        service_aces = len(serves[serves['outcome'] == 'ace'])
        service_errors = len(serves[serves['outcome'] == 'error'])
        service_attempts = len(serves)
        service_efficiency = (service_aces - service_errors) / service_attempts if service_attempts > 0 else 0
        
        # Blocking stats (including block touches)
        blocks = df[df['action'] == 'block']
        block_kills = len(blocks[blocks['outcome'] == 'kill'])
        block_touches = len(blocks[blocks['outcome'] == 'good'])  # Block touches
        block_errors = len(blocks[blocks['outcome'] == 'error'])
        block_attempts = len(blocks)
        block_efficiency = (block_kills - block_errors) / block_attempts if block_attempts > 0 else 0
        
        # Reception stats (for reception percentage - separate from side-out %)
        receive_actions = df[df['action'] == 'receive']
        good_receives = len(receive_actions[receive_actions['outcome'] == 'good'])
        total_receives = len(receive_actions)
        reception_percentage = good_receives / total_receives if total_receives > 0 else 0
        
        # Pass quality distribution given pass_quality column exists)
        if 'pass_quality' in df.columns:
            pass_qualities = receive_actions[receive_actions['pass_quality'].notna()]
            perfect_passes = len(pass_qualities[pass_qualities['pass_quality'] == 1])
            good_passes = len(pass_qualities[pass_qualities['pass_quality'] == 2])
            poor_passes = len(pass_qualities[pass_qualities['pass_quality'] == 3])
            total_passes_with_quality = len(pass_qualities)
        else:
            perfect_passes = 0
            good_passes = 0
            poor_passes = 0
            total_passes_with_quality = 0
        
        # SIDE-OUT PERCENTAGE (CORRECTED): Points won when receiving serve / Total rallies when receiving
        # This requires point-level data. If point_id exists, use it. Otherwise, estimate from serves.
        if 'point_id' in df.columns and df['point_id'].notna().any():
            # Group by point_id to identify rallies
            points = df[df['point_id'].notna()].groupby('point_id')
            receiving_rallies = 0
            receiving_points_won = 0
            
            for point_id, point_data in points:
                # Determine if we were receiving (opponent served first)
                point_actions = point_data.sort_values('timestamp' if 'timestamp' in point_data.columns else point_data.index)
                
                # Look for our serve first - if we serve first, we're serving, not receiving
                first_serve = point_actions[point_actions['action'] == 'serve']
                if len(first_serve) == 0:
                    continue
                
                # If first action is opponent's serve (indicated by no 'serve' action for our team, 
                # or if there's a receive before our serve), we're receiving
                has_receive_before_serve = False
                has_our_serve = False
                for idx, row in point_actions.iterrows():
                    if row['action'] == 'receive':
                        has_receive_before_serve = True
                    if row['action'] == 'serve' and not has_receive_before_serve:
                        has_our_serve = True
                        break
                    if row['action'] == 'serve' and has_receive_before_serve:
                        break
                
                if has_receive_before_serve or (not has_our_serve and len(point_actions[point_actions['action'] == 'receive']) > 0):
                    receiving_rallies += 1
                    # Check if we won the point (if we have a kill or opponent error, or if point_winner column exists)
                    if 'point_winner' in point_data.columns:
                        point_won = point_data['point_winner'].iloc[0] == 'us'
                    else:
                        # Infer: if we have a kill and they don't serve again, we likely won
                        our_kills = len(point_data[point_data['outcome'] == 'kill'])
                        point_won = our_kills > 0
                    
                    if point_won:
                        receiving_points_won += 1
            
            side_out_percentage = receiving_points_won / receiving_rallies if receiving_rallies > 0 else 0
        else:
            # Fallback: Estimate from serve/receive pattern
            # Count serves as proxy for rallies when we're serving
            # Side-out = points won when receiving / total receiving rallies
            # Estimate: use attack kills after reception as proxy
            receives_with_attacks = 0
            kills_after_receive = 0
            
            # Group by set and rotation to approximate rally grouping
            for set_num in df['set_number'].unique():
                set_df = df[df['set_number'] == set_num]
                for rot in set_df['rotation'].unique():
                    rot_df = set_df[set_df['rotation'] == rot].sort_index()
                    
                    # Look for receive -> attack sequences
                    for i in range(len(rot_df) - 1):
                        if rot_df.iloc[i]['action'] == 'receive' and rot_df.iloc[i+1]['action'] == 'attack':
                            receives_with_attacks += 1
                            if rot_df.iloc[i+1]['outcome'] == 'kill':
                                kills_after_receive += 1
            
            # Rough estimate: side-out % ≈ kills after receive / receives that led to attacks
            # This is an approximation - proper calculation needs point tracking
            side_out_percentage = kills_after_receive / receives_with_attacks if receives_with_attacks > 0 else reception_percentage
        
        # Serve Point Percentage: Points won when serving / Total service rallies
        if 'point_id' in df.columns and df['point_id'].notna().any():
            points = df[df['point_id'].notna()].groupby('point_id')
            serving_rallies = 0
            serving_points_won = 0
            
            for point_id, point_data in points:
                # Determine if we were serving (we serve first)
                point_actions = point_data.sort_index()
                first_serve = point_actions[point_actions['action'] == 'serve']
                if len(first_serve) == 0:
                    continue
                
                # If we serve first (no receive before our first serve), we're serving
                has_our_serve_first = True
                for idx, row in point_actions.iterrows():
                    if row['action'] == 'receive':
                        has_our_serve_first = False
                        break
                    if row['action'] == 'serve':
                        break
                
                if has_our_serve_first:
                    serving_rallies += 1
                    if 'point_winner' in point_data.columns:
                        point_won = point_data['point_winner'].iloc[0] == 'us'
                    else:
                        our_kills = len(point_data[point_data['outcome'] == 'kill'])
                        point_won = our_kills > 0
                    
                    if point_won:
                        serving_points_won += 1
            
            serve_point_percentage = serving_points_won / serving_rallies if serving_rallies > 0 else 0
        else:
            # Fallback: estimate from service aces + kills after serve
            service_points_won_estimate = service_aces  # Aces are immediate points
            # Add kills that might have followed our serves
            serve_point_percentage = service_points_won_estimate / service_attempts if service_attempts > 0 else 0
        
        # First Ball Efficiency: Attack kill % after perfect pass (pass_quality = 1)
        if 'pass_quality' in df.columns:
            perfect_pass_attacks = df[(df['action'] == 'attack') & 
                                     (df['pass_quality'] == 1)]
            if len(perfect_pass_attacks) > 0:
                first_ball_kills = len(perfect_pass_attacks[perfect_pass_attacks['outcome'] == 'kill'])
                first_ball_efficiency = first_ball_kills / len(perfect_pass_attacks)
            else:
                first_ball_efficiency = 0
        else:
            first_ball_efficiency = None
        
        # NEW KPIs
        # Kill Percentage: Kills / Total Attack Attempts (different from efficiency)
        kill_percentage = attack_kills / attack_attempts if attack_attempts > 0 else 0
        
        # Reception Efficiency: (Good Passes - Errors) / Total Reception Attempts
        reception_efficiency = (good_receives - len(receive_actions[receive_actions['outcome'] == 'error'])) / total_receives if total_receives > 0 else 0
        
        # Error Rates (by action type)
        attack_error_rate = attack_errors / attack_attempts if attack_attempts > 0 else 0
        service_error_rate = service_errors / service_attempts if service_attempts > 0 else 0
        block_error_rate = block_errors / block_attempts if block_attempts > 0 else 0
        reception_error_rate = len(receive_actions[receive_actions['outcome'] == 'error']) / total_receives if total_receives > 0 else 0
        total_error_rate = len(df[df['outcome'] == 'error']) / total_actions if total_actions > 0 else 0
        
        # Ace-to-Error Ratio: Service Aces / Service Errors
        ace_to_error_ratio = service_aces / service_errors if service_errors > 0 else (service_aces if service_aces > 0 else 0)
        
        self.team_stats = {
            'total_actions': total_actions,
            'sets_played': sets_played,
            'attack_efficiency': attack_efficiency,
            'attack_kills': attack_kills,
            'attack_errors': attack_errors,
            'attack_attempts': attack_attempts,
            'service_efficiency': service_efficiency,
            'service_aces': service_aces,
            'service_errors': service_errors,
            'service_attempts': service_attempts,
            'serve_point_percentage': serve_point_percentage,
            'block_efficiency': block_efficiency,
            'block_kills': block_kills,
            'block_touches': block_touches,
            'block_errors': block_errors,
            'block_attempts': block_attempts,
            'side_out_percentage': side_out_percentage,  # CORRECTED: Points won when receiving / Receiving rallies
            'reception_percentage': reception_percentage,  # NEW: Good receives / Total receives
            'good_receives': good_receives,
            'total_receives': total_receives,
            'perfect_passes': perfect_passes,
            'good_passes': good_passes,
            'poor_passes': poor_passes,
            'first_ball_efficiency': first_ball_efficiency,
            # New KPIs
            'kill_percentage': kill_percentage,
            'reception_efficiency': reception_efficiency,
            'attack_error_rate': attack_error_rate,
            'service_error_rate': service_error_rate,
            'block_error_rate': block_error_rate,
            'reception_error_rate': reception_error_rate,
            'total_error_rate': total_error_rate,
            'ace_to_error_ratio': ace_to_error_ratio
        }
        
        return self.team_stats
    
    def calculate_player_metrics(self):
        """Calculate individual player performance metrics"""
        if self.match_data is None:
            return None
        
        df = self.match_data
        players = df['player'].unique()
        
        player_metrics = {}
        
        for player in players:
            player_data = df[df['player'] == player]
            
            # Attack stats
            attacks = player_data[player_data['action'] == 'attack']
            attack_kills = len(attacks[attacks['outcome'] == 'kill'])
            attack_errors = len(attacks[attacks['outcome'] == 'error'])
            attack_attempts = len(attacks)
            attack_efficiency = (attack_kills - attack_errors) / attack_attempts if attack_attempts > 0 else 0
            
            # Service stats
            serves = player_data[player_data['action'] == 'serve']
            service_aces = len(serves[serves['outcome'] == 'ace'])
            service_errors = len(serves[serves['outcome'] == 'error'])
            service_attempts = len(serves)
            service_efficiency = (service_aces - service_errors) / service_attempts if service_attempts > 0 else 0
            
            # Blocking stats
            blocks = player_data[player_data['action'] == 'block']
            block_kills = len(blocks[blocks['outcome'] == 'kill'])
            block_errors = len(blocks[blocks['outcome'] == 'error'])
            block_attempts = len(blocks)
            block_efficiency = (block_kills - block_errors) / block_attempts if block_attempts > 0 else 0
            
            # Reception stats
            receives = player_data[player_data['action'] == 'receive']
            good_receives = len(receives[receives['outcome'] == 'good'])
            total_receives = len(receives)
            reception_percentage = good_receives / total_receives if total_receives > 0 else 0
            
            # Setting stats
            sets = player_data[player_data['action'] == 'set']
            good_sets = len(sets[sets['outcome'] == 'good'])
            total_sets = len(sets)
            setting_percentage = good_sets / total_sets if total_sets > 0 else 0
            
            player_metrics[player] = {
                'total_actions': len(player_data),
                'attack_efficiency': attack_efficiency,
                'attack_kills': attack_kills,
                'attack_errors': attack_errors,
                'attack_attempts': attack_attempts,
                'service_efficiency': service_efficiency,
                'service_aces': service_aces,
                'service_errors': service_errors,
                'service_attempts': service_attempts,
                'block_efficiency': block_efficiency,
                'block_kills': block_kills,
                'block_errors': block_errors,
                'block_attempts': block_attempts,
                'reception_percentage': reception_percentage,
                'good_receives': good_receives,
                'total_receives': total_receives,
                'setting_percentage': setting_percentage,
                'good_sets': good_sets,
                'total_sets': total_sets
            }
        
        self.player_stats = player_metrics
        return player_metrics
    
    def analyze_rotation_performance(self):
        """Analyze performance by rotation with enhanced metrics"""
        if self.match_data is None:
            return None
        
        df = self.match_data
        rotations = sorted([r for r in df['rotation'].unique() if pd.notna(r)])
        
        rotation_stats = {}
        
        for rotation in rotations:
            rotation_data = df[df['rotation'] == rotation]
            
            # Calculate metrics for this rotation
            total_actions = len(rotation_data)
            
            # Attack stats
            attacks = rotation_data[rotation_data['action'] == 'attack']
            attack_kills = len(attacks[attacks['outcome'] == 'kill'])
            attack_errors = len(attacks[attacks['outcome'] == 'error'])
            attack_attempts = len(attacks)
            attack_efficiency = (attack_kills - attack_errors) / attack_attempts if attack_attempts > 0 else 0
            
            # Service stats
            serves = rotation_data[rotation_data['action'] == 'serve']
            service_aces = len(serves[serves['outcome'] == 'ace'])
            service_errors = len(serves[serves['outcome'] == 'error'])
            service_attempts = len(serves)
            service_efficiency = (service_aces - service_errors) / service_attempts if service_attempts > 0 else 0
            
            # Reception stats
            receives = rotation_data[rotation_data['action'] == 'receive']
            good_receives = len(receives[receives['outcome'] == 'good'])
            total_receives = len(receives)
            reception_percentage = good_receives / total_receives if total_receives > 0 else 0
            
            # Block stats
            blocks = rotation_data[rotation_data['action'] == 'block']
            block_kills = len(blocks[blocks['outcome'] == 'kill'])
            block_errors = len(blocks[blocks['outcome'] == 'error'])
            block_attempts = len(blocks)
            block_efficiency = (block_kills - block_errors) / block_attempts if block_attempts > 0 else 0
            
            # Pass quality for this rotation
            if 'pass_quality' in df.columns:
                rotation_receives = receives[receives['pass_quality'].notna()]
                perfect_passes = len(rotation_receives[rotation_receives['pass_quality'] == 1])
                good_passes = len(rotation_receives[rotation_receives['pass_quality'] == 2])
                poor_passes = len(rotation_receives[rotation_receives['pass_quality'] == 3])
            else:
                perfect_passes = 0
                good_passes = 0
                poor_passes = 0
            
            rotation_stats[rotation] = {
                'total_actions': total_actions,
                'attack_efficiency': attack_efficiency,
                'attack_kills': attack_kills,
                'attack_errors': attack_errors,
                'attack_attempts': attack_attempts,
                'service_efficiency': service_efficiency,
                'service_aces': service_aces,
                'service_errors': service_errors,
                'service_attempts': service_attempts,
                'reception_percentage': reception_percentage,
                'good_receives': good_receives,
                'total_receives': total_receives,
                'block_efficiency': block_efficiency,
                'block_kills': block_kills,
                'block_errors': block_errors,
                'block_attempts': block_attempts,
                'perfect_passes': perfect_passes,
                'good_passes': good_passes,
                'poor_passes': poor_passes
            }
        
        return rotation_stats
    
    def generate_match_report(self):
        """Generate comprehensive match report"""
        team_stats = self.calculate_team_metrics()
        player_stats = self.calculate_player_metrics()
        rotation_stats = self.analyze_rotation_performance()
        
        report = {
            'match_info': {
                'data_file': self.data_file,
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_actions': team_stats['total_actions'],
                'sets_played': team_stats['sets_played']
            },
            'team_performance': team_stats,
            'player_performance': player_stats,
            'rotation_performance': rotation_stats
        }
        
        return report
    
    def save_analysis_report(self, filename=None):
        """Save analysis report to Excel file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"match_analysis_{timestamp}.xlsx"
        
        report = self.generate_match_report()
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Team stats sheet
            team_df = pd.DataFrame(list(report['team_performance'].items()), 
                                 columns=['Metric', 'Value'])
            team_df.to_excel(writer, sheet_name='Team_Stats', index=False)
            
            # Player stats sheet
            player_df = pd.DataFrame(report['player_performance']).T
            player_df.to_excel(writer, sheet_name='Player_Stats')
            
            # Rotation stats sheet
            rotation_df = pd.DataFrame(report['rotation_performance']).T
            rotation_df.to_excel(writer, sheet_name='Rotation_Stats')
            
            # Summary sheet
            summary_data = {
                'Metric': ['Total Actions', 'Sets Played', 'Attack Efficiency', 
                          'Service Efficiency', 'Block Efficiency', 'Side-out %'],
                'Value': [
                    report['team_performance']['total_actions'],
                    report['team_performance']['sets_played'],
                    f"{report['team_performance']['attack_efficiency']:.3f}",
                    f"{report['team_performance']['service_efficiency']:.3f}",
                    f"{report['team_performance']['block_efficiency']:.3f}",
                    f"{report['team_performance']['side_out_percentage']:.3f}"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return filename

# Example usage
if __name__ == "__main__":
    # Create sample data for testing
    sample_data = {
        'timestamp': [datetime.now()] * 20,
        'set_number': [1] * 10 + [2] * 10,
        'rotation': [1, 1, 1, 2, 2, 2, 3, 3, 3, 4] * 2,
        'player': ['John', 'Jane', 'Mike', 'Sarah', 'Tom'] * 4,
        'action': ['serve', 'receive', 'set', 'attack', 'block'] * 4,
        'outcome': ['good', 'good', 'good', 'kill', 'good'] * 4,
        'position': ['OH1', 'OH2', 'MB1', 'MB2', 'OPP'] * 4,
        'notes': ['Example'] * 20
    }
    
    # Create sample Excel file
    sample_df = pd.DataFrame(sample_data)
    sample_df.to_excel('sample_match_data.xlsx', index=False)
    
    # Analyze the data
    analyzer = MatchAnalyzer('sample_match_data.xlsx')
    
    # Generate report
    report = analyzer.generate_match_report()
    print("Match Analysis Report:")
    print(f"Total Actions: {report['team_performance']['total_actions']}")
    print(f"Attack Efficiency: {report['team_performance']['attack_efficiency']:.3f}")
    print(f"Service Efficiency: {report['team_performance']['service_efficiency']:.3f}")
    
    # Save report
    report_file = analyzer.save_analysis_report()
    print(f"\nAnalysis report saved to: {report_file}")
