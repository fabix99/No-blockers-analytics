import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Track team and player performance over time
    """
    
    def __init__(self, data_directory="data/matches"):
        self.data_directory = data_directory
        self.all_matches = []
        self.performance_history = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(data_directory, exist_ok=True)
    
    def load_all_matches(self):
        """Load all match data from the data directory"""
        if not os.path.exists(self.data_directory):
            return False
        
        match_files = [f for f in os.listdir(self.data_directory) if f.endswith('.xlsx')]
        
        for file in match_files:
            try:
                match_data = pd.read_excel(os.path.join(self.data_directory, file), sheet_name='Raw_Data')
                match_data['match_file'] = file
                match_data['match_date'] = self.extract_date_from_filename(file)
                self.all_matches.append(match_data)
            except Exception as e:
                logger.warning(f"Error loading {file}: {e}")
        
        if self.all_matches:
            self.combined_data = pd.concat(self.all_matches, ignore_index=True)
            return True
        return False
    
    def extract_date_from_filename(self, filename):
        """Extract date from filename (assuming format: match_data_YYYYMMDD_HHMMSS.xlsx)"""
        try:
            # Extract date part from filename
            date_part = filename.split('_')[2]  # Get YYYYMMDD part
            return datetime.strptime(date_part, '%Y%m%d').date()
        except (ValueError, IndexError, AttributeError):
            return datetime.now().date()
    
    def calculate_performance_trends(self):
        """Calculate performance trends over time"""
        if not hasattr(self, 'combined_data'):
            return None
        
        # Group by match date
        daily_stats = self.combined_data.groupby('match_date').agg({
            'action': 'count',
            'outcome': lambda x: (x == 'kill').sum()
        }).rename(columns={'action': 'total_actions', 'outcome': 'kills'})
        
        # Calculate attack efficiency by date
        attack_data = self.combined_data[self.combined_data['action'] == 'attack']
        daily_attacks = attack_data.groupby('match_date').agg({
            'outcome': lambda x: (x == 'kill').sum() - (x == 'error').sum()
        }).rename(columns={'outcome': 'attack_efficiency'})
        
        # Calculate service efficiency by date
        service_data = self.combined_data[self.combined_data['action'] == 'serve']
        daily_services = service_data.groupby('match_date').agg({
            'outcome': lambda x: (x == 'ace').sum() - (x == 'error').sum()
        }).rename(columns={'outcome': 'service_efficiency'})
        
        # Combine all metrics
        trends = pd.concat([daily_stats, daily_attacks, daily_services], axis=1)
        trends = trends.fillna(0)
        
        return trends
    
    def track_player_development(self, player_name):
        """Track individual player development over time"""
        if not hasattr(self, 'combined_data'):
            return None
        
        player_data = self.combined_data[self.combined_data['player'] == player_name]
        
        if player_data.empty:
            return None
        
        # Group by match date
        daily_player_stats = player_data.groupby('match_date').agg({
            'action': 'count',
            'outcome': lambda x: (x == 'kill').sum()
        }).rename(columns={'action': 'total_actions', 'outcome': 'kills'})
        
        # Calculate attack efficiency
        player_attacks = player_data[player_data['action'] == 'attack']
        daily_attack_efficiency = player_attacks.groupby('match_date').agg({
            'outcome': lambda x: (x == 'kill').sum() - (x == 'error').sum()
        }).rename(columns={'outcome': 'attack_efficiency'})
        
        # Calculate service efficiency
        player_services = player_data[player_data['action'] == 'serve']
        daily_service_efficiency = player_services.groupby('match_date').agg({
            'outcome': lambda x: (x == 'ace').sum() - (x == 'error').sum()
        }).rename(columns={'outcome': 'service_efficiency'})
        
        # Combine metrics
        player_trends = pd.concat([daily_player_stats, daily_attack_efficiency, daily_service_efficiency], axis=1)
        player_trends = player_trends.fillna(0)
        
        return player_trends
    
    def identify_improvement_areas(self):
        """Identify areas where the team needs improvement"""
        if not hasattr(self, 'combined_data'):
            return None
        
        # Calculate overall team stats
        total_actions = len(self.combined_data)
        attacks = self.combined_data[self.combined_data['action'] == 'attack']
        services = self.combined_data[self.combined_data['action'] == 'serve']
        blocks = self.combined_data[self.combined_data['action'] == 'block']
        receives = self.combined_data[self.combined_data['action'] == 'receive']
        
        # Calculate efficiency metrics
        attack_efficiency = (len(attacks[attacks['outcome'] == 'kill']) - len(attacks[attacks['outcome'] == 'error'])) / len(attacks) if len(attacks) > 0 else 0
        service_efficiency = (len(services[services['outcome'] == 'ace']) - len(services[services['outcome'] == 'error'])) / len(services) if len(services) > 0 else 0
        block_efficiency = (len(blocks[blocks['outcome'] == 'kill']) - len(blocks[blocks['outcome'] == 'error'])) / len(blocks) if len(blocks) > 0 else 0
        reception_percentage = len(receives[receives['outcome'] == 'good']) / len(receives) if len(receives) > 0 else 0
        
        # Identify weak areas (efficiency < 0.3 or percentage < 0.7)
        improvement_areas = []
        
        if attack_efficiency < 0.3:
            improvement_areas.append({
                'area': 'Attack Efficiency',
                'current_value': attack_efficiency,
                'target_value': 0.3,
                'priority': 'High'
            })
        
        if service_efficiency < 0.2:
            improvement_areas.append({
                'area': 'Service Efficiency',
                'current_value': service_efficiency,
                'target_value': 0.2,
                'priority': 'High'
            })
        
        if block_efficiency < 0.1:
            improvement_areas.append({
                'area': 'Block Efficiency',
                'current_value': block_efficiency,
                'target_value': 0.1,
                'priority': 'Medium'
            })
        
        if reception_percentage < 0.7:
            improvement_areas.append({
                'area': 'Reception Percentage',
                'current_value': reception_percentage,
                'target_value': 0.7,
                'priority': 'High'
            })
        
        return improvement_areas
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        if not self.load_all_matches():
            return "No match data found"
        
        trends = self.calculate_performance_trends()
        improvement_areas = self.identify_improvement_areas()
        
        # Get all players
        all_players = self.combined_data['player'].unique()
        
        # Track each player's development
        player_developments = {}
        for player in all_players:
            player_trends = self.track_player_development(player)
            if player_trends is not None:
                player_developments[player] = player_trends
        
        report = {
            'total_matches': len(self.all_matches),
            'total_actions': len(self.combined_data),
            'date_range': {
                'start': self.combined_data['match_date'].min(),
                'end': self.combined_data['match_date'].max()
            },
            'performance_trends': trends.to_dict() if trends is not None else {},
            'improvement_areas': improvement_areas,
            'player_developments': {k: v.to_dict() for k, v in player_developments.items()},
            'top_performers': self.identify_top_performers(),
            'recommendations': self.generate_recommendations(improvement_areas)
        }
        
        return report
    
    def identify_top_performers(self):
        """Identify top performing players"""
        if not hasattr(self, 'combined_data'):
            return None
        
        player_stats = {}
        
        for player in self.combined_data['player'].unique():
            player_data = self.combined_data[self.combined_data['player'] == player]
            
            # Calculate key metrics
            attacks = player_data[player_data['action'] == 'attack']
            attack_efficiency = (len(attacks[attacks['outcome'] == 'kill']) - len(attacks[attacks['outcome'] == 'error'])) / len(attacks) if len(attacks) > 0 else 0
            
            services = player_data[player_data['action'] == 'serve']
            service_efficiency = (len(services[services['outcome'] == 'ace']) - len(services[services['outcome'] == 'error'])) / len(services) if len(services) > 0 else 0
            
            player_stats[player] = {
                'total_actions': len(player_data),
                'attack_efficiency': attack_efficiency,
                'service_efficiency': service_efficiency,
                'overall_score': attack_efficiency + service_efficiency
            }
        
        # Sort by overall score
        top_performers = sorted(player_stats.items(), key=lambda x: x[1]['overall_score'], reverse=True)
        
        return top_performers[:5]  # Top 5 performers
    
    def generate_recommendations(self, improvement_areas):
        """Generate training recommendations based on improvement areas"""
        recommendations = []
        
        for area in improvement_areas:
            if area['area'] == 'Attack Efficiency':
                recommendations.append({
                    'area': 'Attack Efficiency',
                    'recommendation': 'Focus on attack technique drills, timing, and shot selection',
                    'drills': ['Attack approach drills', 'Shot placement practice', 'Block avoidance training']
                })
            elif area['area'] == 'Service Efficiency':
                recommendations.append({
                    'area': 'Service Efficiency',
                    'recommendation': 'Improve service consistency and power',
                    'drills': ['Service target practice', 'Power service drills', 'Service placement training']
                })
            elif area['area'] == 'Block Efficiency':
                recommendations.append({
                    'area': 'Block Efficiency',
                    'recommendation': 'Enhance blocking timing and positioning',
                    'drills': ['Block timing drills', 'Positioning practice', 'Block reading training']
                })
            elif area['area'] == 'Reception Percentage':
                recommendations.append({
                    'area': 'Reception Percentage',
                    'recommendation': 'Improve serve receive technique and positioning',
                    'drills': ['Serve receive drills', 'Passing accuracy training', 'Movement drills']
                })
        
        return recommendations
    
    def save_performance_report(self, filename=None):
        """Save performance report to Excel file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.xlsx"
        
        report = self.generate_performance_report()
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': ['Total Matches', 'Total Actions', 'Date Range Start', 'Date Range End'],
                'Value': [
                    report['total_matches'],
                    report['total_actions'],
                    report['date_range']['start'],
                    report['date_range']['end']
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Improvement areas sheet
            if report['improvement_areas']:
                improvement_df = pd.DataFrame(report['improvement_areas'])
                improvement_df.to_excel(writer, sheet_name='Improvement_Areas', index=False)
            
            # Top performers sheet
            if report['top_performers']:
                top_performers_data = []
                for player, stats in report['top_performers']:
                    top_performers_data.append({
                        'Player': player,
                        'Total Actions': stats['total_actions'],
                        'Attack Efficiency': stats['attack_efficiency'],
                        'Service Efficiency': stats['service_efficiency'],
                        'Overall Score': stats['overall_score']
                    })
                top_performers_df = pd.DataFrame(top_performers_data)
                top_performers_df.to_excel(writer, sheet_name='Top_Performers', index=False)
            
            # Recommendations sheet
            if report['recommendations']:
                recommendations_df = pd.DataFrame(report['recommendations'])
                recommendations_df.to_excel(writer, sheet_name='Recommendations', index=False)
        
        return filename

# -----------------------------
# New helpers for Team Overview
# -----------------------------
def compute_set_results_from_loader(loader):
    """Return per-set scores using loader.team_data.
    Each item: {set_number, our_points, opp_points, won}
    Only includes sets that have at least one point scored.
    """
    try:
        results = []
        for set_num in sorted(loader.team_data.keys()):
            stats = loader.team_data[set_num]
            # Safely get point values, defaulting to 0
            serving_won = float(stats.get('serving_points_won', 0) or 0)
            receiving_won = float(stats.get('receiving_points_won', 0) or 0)
            serving_lost = float(stats.get('serving_points_lost', 0) or 0)
            receiving_lost = float(stats.get('receiving_points_lost', 0) or 0)
            
            our_points = int(serving_won + receiving_won)
            opp_points = int(serving_lost + receiving_lost)
            
            # Skip sets with no detected points (both scores are 0)
            if our_points == 0 and opp_points == 0:
                continue
            
            results.append({
                'set_number': int(set_num),
                'our_points': our_points,
                'opp_points': opp_points,
                'won': our_points > opp_points
            })
        return results
    except Exception as e:
        # Return empty list on any error
        return []

def get_match_summary(set_results):
    """Summarize match result from per-set results.
    Returns dict: {sets_us, sets_them, outcome, label}
    """
    if not set_results:
        return {'sets_us': 0, 'sets_them': 0, 'outcome': 'N/A', 'label': 'No sets'}
    sets_us = sum(1 for s in set_results if s.get('won'))
    sets_them = len(set_results) - sets_us
    outcome = 'Win' if sets_us > sets_them else ('Loss' if sets_us < sets_them else 'Draw')
    return {
        'sets_us': sets_us,
        'sets_them': sets_them,
        'outcome': outcome,
        'label': f"{outcome} {sets_us}–{sets_them}"
    }

def _aggregate_player_totals(loader):
    """Aggregate totals from loader.player_data (across all sets/players)."""
    totals = {
        'Attack_Kills': 0, 'Attack_Good': 0, 'Attack_Errors': 0, 'Attack_Total': 0,
        'Service_Aces': 0, 'Service_Good': 0, 'Service_Errors': 0, 'Service_Total': 0,
        'Block_Kills': 0, 'Block_Touches': 0, 'Block_Errors': 0, 'Block_Total': 0,
        'Reception_Good': 0, 'Reception_Errors': 0, 'Reception_Total': 0,
        'Dig_Good': 0, 'Dig_Errors': 0, 'Dig_Total': 0,
        'Sets_Exceptional': 0, 'Sets_Good': 0, 'Sets_Errors': 0, 'Sets_Total': 0
    }
    try:
        for player, info in loader.player_data.items():
            stats = info.get('stats', {})
            for key in totals.keys():
                val = stats.get(key, 0) or 0
                try:
                    totals[key] += float(val)
                except (ValueError, TypeError):
                    pass
    except (AttributeError, KeyError):
        pass
    return totals

def compute_team_kpis_from_loader(loader):
    """Compute team KPIs from EventTrackerLoader data.
    Returns a dict with friendly metrics for Team Overview.
    Uses event-based format with aggregated stats.
    """
    totals = _aggregate_player_totals(loader)

    # Attacks - use Attack_Total if available, otherwise calculate from components
    attack_kills = totals.get('Attack_Kills', 0)
    attack_good = totals.get('Attack_Good', 0)
    attack_errors = totals.get('Attack_Errors', 0)
    attack_attempts = totals.get('Attack_Total', 0)
    if attack_attempts == 0:
        # Fallback: calculate from components
        attack_attempts = attack_kills + attack_good + attack_errors
    attack_kill_pct = (attack_kills / attack_attempts) if attack_attempts > 0 else 0.0
    attack_error_pct = (attack_errors / attack_attempts) if attack_attempts > 0 else 0.0

    # Serves - use Service_Total if available, otherwise calculate from components
    service_aces = totals.get('Service_Aces', 0)
    service_good = totals.get('Service_Good', 0)
    service_errors = totals.get('Service_Errors', 0)
    serve_attempts = totals.get('Service_Total', 0)
    if serve_attempts == 0:
        # Fallback: calculate from components
        serve_attempts = service_aces + service_good + service_errors
    serve_in_rate = ((service_aces + service_good) / serve_attempts) if serve_attempts > 0 else 0.0
    ace_pct = (service_aces / serve_attempts) if serve_attempts > 0 else 0.0
    serve_error_pct = (service_errors / serve_attempts) if serve_attempts > 0 else 0.0

    # Blocks - use Block_Total if available, otherwise calculate from components
    block_kills = totals.get('Block_Kills', 0)
    block_touches = totals.get('Block_Touches', 0)
    block_errors = totals.get('Block_Errors', 0)
    block_attempts = totals.get('Block_Total', 0)
    if block_attempts == 0:
        # Fallback: calculate from components
        block_attempts = block_kills + block_touches + block_errors
    block_point_rate = (block_kills / block_attempts) if block_attempts > 0 else 0.0
    block_touch_rate = (block_touches / block_attempts) if block_attempts > 0 else 0.0

    # Team-level side-out and break-point from team sheets
    serving_rallies = 0
    serving_points_won = 0
    receiving_rallies = 0
    receiving_points_won = 0
    try:
        for set_num, stats in loader.team_data.items():
            serving_rallies += int(stats.get('serving_rallies', 0) or 0)
            serving_points_won += int(stats.get('serving_points_won', 0) or 0)
            receiving_rallies += int(stats.get('receiving_rallies', 0) or 0)
            receiving_points_won += int(stats.get('receiving_points_won', 0) or 0)
    except (AttributeError, KeyError, ValueError, TypeError):
        pass

    side_out_eff = (receiving_points_won / receiving_rallies) if receiving_rallies > 0 else 0.0
    break_point_rate = (serving_points_won / serving_rallies) if serving_rallies > 0 else 0.0

    # Reception quality (good / total attempts)
    # Note: Reception_Good includes perfect (1.0), good (1.0), and poor (0.5)
    # Reception_Total includes all attempts (perfect + good + poor + error)
    rec_good = totals.get('Reception_Good', 0)
    rec_total = totals.get('Reception_Total', 0)
    # If Reception_Total not available, calculate from good + errors (fallback)
    if rec_total == 0:
        rec_errors = totals.get('Reception_Errors', 0)
        rec_total = rec_good + rec_errors
    reception_quality = (rec_good / rec_total) if rec_total > 0 else 0.0

    # Dig quality (good digs / total attempts)
    # Note: Dig_Good includes perfect (1.0), good (1.0), and poor (0.5)
    # Dig_Total includes all attempts (perfect + good + poor + error)
    dig_good = totals.get('Dig_Good', 0)
    dig_total = totals.get('Dig_Total', 0)
    # If Dig_Total not available, calculate from good + errors (fallback)
    if dig_total == 0:
        dig_errors = totals.get('Dig_Errors', 0)
        dig_total = dig_good + dig_errors
    dig_rate = (dig_good / dig_total) if dig_total > 0 else 0.0

    # Block Kill Percentage (block kills / total block attempts)
    block_kill_pct = (block_kills / block_attempts) if block_attempts > 0 else 0.0

    # Average Actions per Point
    # Total points = serving_rallies + receiving_rallies (each rally is one point)
    total_points = serving_rallies + receiving_rallies
    # Include all action types in total actions
    sets_attempts = totals.get('Sets_Total', totals.get('Sets_Exceptional', 0) + totals.get('Sets_Good', 0) + totals.get('Sets_Errors', 0))
    rec_attempts = totals.get('Reception_Total', 0)
    if rec_attempts == 0:
        rec_attempts = totals.get('Reception_Good', 0) + totals.get('Reception_Errors', 0)
    dig_attempts = totals.get('Dig_Total', 0)
    if dig_attempts == 0:
        dig_attempts = totals.get('Dig_Good', 0) + totals.get('Dig_Errors', 0)
    total_actions = (
        attack_attempts + serve_attempts + block_attempts + 
        rec_attempts + dig_attempts + sets_attempts
    )
    avg_actions_per_point = (total_actions / total_points) if total_points > 0 else 0.0

    # New enhanced KPIs (MEDIUM PRIORITY 26-28)
    # Attack Efficiency: (Kills - Errors) / Total Attempts
    attack_efficiency = ((attack_kills - attack_errors) / attack_attempts) if attack_attempts > 0 else 0.0
    
    # Ace-to-Error Ratio: Service Aces / Service Errors
    ace_to_error_ratio = (service_aces / service_errors) if service_errors > 0 else (service_aces if service_aces > 0 else 0.0)

    return {
        'attack_kill_pct': attack_kill_pct,
        'attack_error_pct': attack_error_pct,
        'attack_efficiency': attack_efficiency,  # NEW
        'serve_in_rate': serve_in_rate,
        'ace_pct': ace_pct,
        'ace_rate': ace_pct,  # Alias for consistency
        'serve_error_pct': serve_error_pct,
        'ace_to_error_ratio': ace_to_error_ratio,  # NEW
        'block_point_rate': block_point_rate,
        'block_kill_pct': block_kill_pct,
        'block_touch_rate': block_touch_rate,  # NEW
        'side_out_efficiency': side_out_eff,
        'break_point_rate': break_point_rate,
        'reception_quality': reception_quality,
        'dig_rate': dig_rate,
        'avg_actions_per_point': avg_actions_per_point,
        'totals': {
            'attack_attempts': int(attack_attempts),
            'attack_kills': int(attack_kills),
            'attack_errors': int(attack_errors),
            'serve_attempts': int(serve_attempts),
            'service_aces': int(service_aces),
            'service_good': int(service_good),
            'service_errors': int(service_errors),
            'block_attempts': int(block_attempts),
            'block_kills': int(block_kills),
            'block_touches': int(block_touches),
            'block_errors': int(block_errors),
            'block_no_kill': int(block_touches),  # block_no_kill is counted as touches in aggregated data
            'serving_rallies': int(serving_rallies),
            'serving_points_won': int(serving_points_won),
            'receiving_rallies': int(receiving_rallies),
            'receiving_points_won': int(receiving_points_won),
            'reception_total': int(rec_total),
            'reception_good': int(rec_good),
            'reception_errors': int(rec_total - rec_good),  # Add reception_errors to totals
            'dig_total': int(dig_total),
            'dig_good': int(dig_good)
        }
    }

# Example usage
if __name__ == "__main__":
    # Configure logging for CLI usage
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    tracker = PerformanceTracker()
    
    # Generate performance report
    report = tracker.generate_performance_report()
    
    if isinstance(report, str):
        logger.info(report)
    else:
        logger.info("Performance Report Generated:")
        logger.info(f"Total Matches: {report['total_matches']}")
        logger.info(f"Total Actions: {report['total_actions']}")
        logger.info(f"Improvement Areas: {len(report['improvement_areas'])}")
        logger.info(f"Top Performers: {len(report['top_performers'])}")
        
        # Save report
        report_file = tracker.save_performance_report()
        logger.info(f"Performance report saved to: {report_file}")
