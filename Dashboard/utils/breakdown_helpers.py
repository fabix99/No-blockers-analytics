"""
Helper functions for calculating breakdowns by various dimensions
(attack type, position, player, set, rotation, etc.)
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from utils.helpers import filter_good_receptions, filter_good_digs, filter_block_touches
from services.kpi_calculator import KPICalculator


def get_attack_breakdown_by_type(df: pd.DataFrame, loader=None) -> Dict[str, Dict[str, int]]:
    """Get attack breakdown by attack type (normal, tip).
    
    Returns:
        Dict with keys: 'normal', 'tip'
        Each value is a dict with: 'kills', 'defended', 'blocked', 'out', 'net', 'total'
        Note: 'error' removed from attack outcomes - all errors covered by 'out', 'net', 'blocked'
    """
    attacks = df[df['action'] == 'attack']
    breakdown = {
        'normal': {'kills': 0, 'defended': 0, 'blocked': 0, 'out': 0, 'net': 0, 'total': 0},
        'tip': {'kills': 0, 'defended': 0, 'blocked': 0, 'out': 0, 'net': 0, 'total': 0}
    }
    
    if 'Attack_Type' in attacks.columns:
        for attack_type in ['normal', 'tip']:
            type_attacks = attacks[attacks['Attack_Type'].str.lower().str.strip() == attack_type]
            breakdown[attack_type]['kills'] = len(type_attacks[type_attacks['outcome'] == 'kill'])
            breakdown[attack_type]['defended'] = len(type_attacks[type_attacks['outcome'] == 'defended'])
            breakdown[attack_type]['blocked'] = len(type_attacks[type_attacks['outcome'] == 'blocked'])
            breakdown[attack_type]['out'] = len(type_attacks[type_attacks['outcome'] == 'out'])
            breakdown[attack_type]['net'] = len(type_attacks[type_attacks['outcome'] == 'net'])
            breakdown[attack_type]['total'] = len(type_attacks)
    elif 'attack_type' in attacks.columns:
        # Handle lowercase column name (from match_data processing)
        for attack_type in ['normal', 'tip']:
            type_attacks = attacks[attacks['attack_type'].str.lower().str.strip() == attack_type]
            breakdown[attack_type]['kills'] = len(type_attacks[type_attacks['outcome'] == 'kill'])
            breakdown[attack_type]['defended'] = len(type_attacks[type_attacks['outcome'] == 'defended'])
            breakdown[attack_type]['blocked'] = len(type_attacks[type_attacks['outcome'] == 'blocked'])
            breakdown[attack_type]['out'] = len(type_attacks[type_attacks['outcome'] == 'out'])
            breakdown[attack_type]['net'] = len(type_attacks[type_attacks['outcome'] == 'net'])
            breakdown[attack_type]['total'] = len(type_attacks)
    else:
        # If Attack_Type column doesn't exist, assume all are 'normal'
        breakdown['normal']['kills'] = len(attacks[attacks['outcome'] == 'kill'])
        breakdown['normal']['defended'] = len(attacks[attacks['outcome'] == 'defended'])
        breakdown['normal']['blocked'] = len(attacks[attacks['outcome'] == 'blocked'])
        breakdown['normal']['out'] = len(attacks[attacks['outcome'] == 'out'])
        breakdown['normal']['net'] = len(attacks[attacks['outcome'] == 'net'])
        breakdown['normal']['total'] = len(attacks)
    
    return breakdown


def get_reception_breakdown_by_quality(df: pd.DataFrame, loader=None) -> Dict[str, int]:
    """Get reception breakdown by quality level (perfect, good, poor, error).
    
    Returns:
        Dict with keys: 'perfect', 'good', 'poor', 'error', 'total'
    """
    receives = df[df['action'] == 'receive']
    breakdown = {
        'perfect': len(receives[receives['outcome'] == 'perfect']),
        'good': len(receives[receives['outcome'] == 'good']),
        'poor': len(receives[receives['outcome'] == 'poor']),
        'error': len(receives[receives['outcome'] == 'error']),
        'total': len(receives)
    }
    return breakdown


def get_dig_breakdown_by_quality(df: pd.DataFrame, loader=None) -> Dict[str, int]:
    """Get dig breakdown by quality level (perfect, good, poor, error).
    
    Returns:
        Dict with keys: 'perfect', 'good', 'poor', 'error', 'total'
    """
    digs = df[df['action'] == 'dig']
    breakdown = {
        'perfect': len(digs[digs['outcome'] == 'perfect']),
        'good': len(digs[digs['outcome'] == 'good']),
        'poor': len(digs[digs['outcome'] == 'poor']),
        'error': len(digs[digs['outcome'] == 'error']),
        'total': len(digs)
    }
    return breakdown


def get_block_breakdown_by_outcome(df: pd.DataFrame, loader=None) -> Dict[str, int]:
    """Get block breakdown by outcome (kill, touch, block_no_kill, no_touch, error).
    
    Returns:
        Dict with keys: 'kill', 'touch', 'block_no_kill', 'no_touch', 'error', 'total'
    """
    blocks = df[df['action'] == 'block']
    breakdown = {
        'kill': len(blocks[blocks['outcome'] == 'kill']),
        'touch': len(blocks[blocks['outcome'] == 'touch']),
        'block_no_kill': len(blocks[blocks['outcome'] == 'block_no_kill']),
        'no_touch': len(blocks[blocks['outcome'] == 'no_touch']),
        'error': len(blocks[blocks['outcome'] == 'error']),
        'total': len(blocks)
    }
    return breakdown


def get_serve_breakdown_by_outcome(df: pd.DataFrame, loader=None) -> Dict[str, int]:
    """Get serve breakdown by outcome (ace, good, error).
    
    Returns:
        Dict with keys: 'ace', 'good', 'error', 'total'
    """
    serves = df[df['action'] == 'serve']
    breakdown = {
        'ace': len(serves[serves['outcome'] == 'ace']),
        'good': len(serves[serves['outcome'] == 'good']),
        'error': len(serves[serves['outcome'] == 'error']),
        'total': len(serves)
    }
    return breakdown


def get_kpi_by_player(loader, kpi_name: str, return_totals: bool = False) -> Dict[str, Any]:
    """Get a KPI broken down by player.
    
    Args:
        loader: EventTrackerLoader instance
        kpi_name: Name of KPI ('attack_kill_pct', 'serve_in_rate', etc.)
        return_totals: If True, return dict with 'value', 'numerator', 'denominator' for each player
        
    Returns:
        Dict mapping player names to KPI values (or dicts with value/totals if return_totals=True)
    """
    player_kpis = {}
    
    if not loader or not hasattr(loader, 'player_data_by_set'):
        return player_kpis
    
    for set_num in loader.player_data_by_set.keys():
        for player in loader.player_data_by_set[set_num].keys():
            # Skip OUR_TEAM - it's just for logging mistakes, not a real player
            if str(player).upper() == 'OUR_TEAM':
                continue
            if player not in player_kpis:
                player_kpis[player] = {
                    'attack_kills': 0, 'attack_attempts': 0,
                    'service_aces': 0, 'service_good': 0, 'service_attempts': 0,
                    'block_kills': 0, 'block_attempts': 0,
                    'reception_good': 0, 'reception_total': 0,
                    'dig_good': 0, 'dig_total': 0
                }
            
            stats = loader.player_data_by_set[set_num][player].get('stats', {})
            player_kpis[player]['attack_kills'] += float(stats.get('Attack_Kills', 0) or 0)
            player_kpis[player]['attack_attempts'] += float(stats.get('Attack_Total', 0) or 0)
            player_kpis[player]['service_aces'] += float(stats.get('Service_Aces', 0) or 0)
            player_kpis[player]['service_good'] += float(stats.get('Service_Good', 0) or 0)
            player_kpis[player]['service_attempts'] += float(stats.get('Service_Total', 0) or 0)
            player_kpis[player]['block_kills'] += float(stats.get('Block_Kills', 0) or 0)
            player_kpis[player]['block_attempts'] += float(stats.get('Block_Total', 0) or 0)
            player_kpis[player]['reception_good'] += float(stats.get('Reception_Good', 0) or 0)
            player_kpis[player]['reception_total'] += float(stats.get('Reception_Total', 0) or 0)
            player_kpis[player]['dig_good'] += float(stats.get('Dig_Good', 0) or 0)
            player_kpis[player]['dig_total'] += float(stats.get('Dig_Total', 0) or 0)
    
    # Calculate KPIs
    result = {}
    for player, totals in player_kpis.items():
        if kpi_name == 'attack_kill_pct':
            value = (totals['attack_kills'] / totals['attack_attempts']) if totals['attack_attempts'] > 0 else 0.0
            if return_totals:
                result[player] = {
                    'value': value,
                    'numerator': int(totals['attack_kills']),
                    'denominator': int(totals['attack_attempts'])
                }
            else:
                result[player] = value
        elif kpi_name == 'serve_in_rate':
            value = ((totals['service_aces'] + totals['service_good']) / totals['service_attempts']) if totals['service_attempts'] > 0 else 0.0
            if return_totals:
                result[player] = {
                    'value': value,
                    'numerator': int(totals['service_aces'] + totals['service_good']),
                    'denominator': int(totals['service_attempts'])
                }
            else:
                result[player] = value
        elif kpi_name == 'block_kill_pct':
            value = (totals['block_kills'] / totals['block_attempts']) if totals['block_attempts'] > 0 else 0.0
            if return_totals:
                result[player] = {
                    'value': value,
                    'numerator': int(totals['block_kills']),
                    'denominator': int(totals['block_attempts'])
                }
            else:
                result[player] = value
        elif kpi_name == 'reception_quality':
            value = (totals['reception_good'] / totals['reception_total']) if totals['reception_total'] > 0 else 0.0
            if return_totals:
                result[player] = {
                    'value': value,
                    'numerator': int(totals['reception_good']),
                    'denominator': int(totals['reception_total'])
                }
            else:
                result[player] = value
        elif kpi_name == 'dig_rate':
            value = (totals['dig_good'] / totals['dig_total']) if totals['dig_total'] > 0 else 0.0
            if return_totals:
                result[player] = {
                    'value': value,
                    'numerator': int(totals['dig_good']),
                    'denominator': int(totals['dig_total'])
                }
            else:
                result[player] = value
    
    return result


def get_kpi_by_position(df: pd.DataFrame, loader, kpi_name: str) -> Dict[str, float]:
    """Get a KPI broken down by position (Outside, Middle Blocker, Opposite, Setter, Libero).
    
    Args:
        df: Match dataframe
        loader: EventTrackerLoader instance
        kpi_name: Name of KPI
        
    Returns:
        Dict mapping position groups to KPI values (only includes positions with data)
    """
    from utils.helpers import get_player_position
    
    position_kpis = {
        'Outside': {'kills': 0, 'attempts': 0, 'good': 0, 'total': 0},
        'Middle Blocker': {'kills': 0, 'attempts': 0, 'good': 0, 'total': 0},
        'Opposite': {'kills': 0, 'attempts': 0, 'good': 0, 'total': 0},
        'Setter': {'kills': 0, 'attempts': 0, 'good': 0, 'total': 0},
        'Libero': {'kills': 0, 'attempts': 0, 'good': 0, 'total': 0}
    }
    
    # Map position codes to position groups
    def get_position_group(pos):
        if pd.isna(pos) or pos is None:
            return None
        pos_str = str(pos).upper()
        if pos_str.startswith('OH'):
            return 'Outside'
        elif pos_str.startswith('MB'):
            return 'Middle Blocker'
        elif pos_str == 'OPP':
            return 'Opposite'
        elif pos_str == 'S':
            return 'Setter'
        elif pos_str == 'L':
            return 'Libero'
        return None
    
    if kpi_name == 'attack_kill_pct':
        attacks = df[df['action'] == 'attack']
        for _, row in attacks.iterrows():
            pos_group = get_position_group(row.get('position', None))
            # Filter out Liberos from attack data (they cannot attack)
            if pos_group and pos_group != 'Libero':
                position_kpis[pos_group]['kills'] += 1 if row['outcome'] == 'kill' else 0
                position_kpis[pos_group]['attempts'] += 1
    elif kpi_name == 'reception_quality':
        receives = df[df['action'] == 'receive']
        for _, row in receives.iterrows():
            pos_group = get_position_group(row.get('position', None))
            if pos_group:
                if row['outcome'] in ['perfect', 'good']:
                    position_kpis[pos_group]['good'] += 1
                position_kpis[pos_group]['total'] += 1
    elif kpi_name == 'block_kill_pct':
        blocks = df[df['action'] == 'block']
        for _, row in blocks.iterrows():
            pos_group = get_position_group(row.get('position', None))
            # Filter out Liberos from block data (they cannot block)
            if pos_group and pos_group != 'Libero':
                position_kpis[pos_group]['kills'] += 1 if row['outcome'] == 'kill' else 0
                position_kpis[pos_group]['attempts'] += 1
    
    # Calculate KPIs and filter out positions with no data
    result = {}
    for pos_group, totals in position_kpis.items():
        if kpi_name == 'attack_kill_pct':
            # Only include positions with attack attempts
            if totals['attempts'] > 0:
                result[pos_group] = totals['kills'] / totals['attempts']
        elif kpi_name == 'reception_quality':
            # Only include positions with reception attempts (filter out 0%)
            if totals['total'] > 0:
                result[pos_group] = totals['good'] / totals['total']
        elif kpi_name == 'block_kill_pct':
            # Only include positions with block attempts
            if totals['attempts'] > 0:
                result[pos_group] = totals['kills'] / totals['attempts']
    
    return result


def get_kpi_by_set(loader, kpi_name: str) -> Dict[int, float]:
    """Get a KPI broken down by set.
    
    Args:
        loader: EventTrackerLoader instance
        kpi_name: Name of KPI
        
    Returns:
        Dict mapping set numbers to KPI values
    """
    set_kpis = {}
    
    if not loader or not hasattr(loader, 'player_data_by_set'):
        return set_kpis
    
    for set_num in loader.player_data_by_set.keys():
        set_kpis[set_num] = {
            'attack_kills': 0, 'attack_attempts': 0, 'attack_errors': 0,
            'service_aces': 0, 'service_good': 0, 'service_attempts': 0, 'service_errors': 0,
            'block_kills': 0, 'block_attempts': 0,
            'reception_good': 0, 'reception_total': 0,
            'dig_good': 0, 'dig_total': 0,
            'serving_rallies': 0, 'serving_points_won': 0,
            'receiving_rallies': 0, 'receiving_points_won': 0
        }
        
        for player in loader.player_data_by_set[set_num].keys():
            stats = loader.player_data_by_set[set_num][player].get('stats', {})
            set_kpis[set_num]['attack_kills'] += float(stats.get('Attack_Kills', 0) or 0)
            set_kpis[set_num]['attack_attempts'] += float(stats.get('Attack_Total', 0) or 0)
            set_kpis[set_num]['attack_errors'] += float(stats.get('Attack_Errors', 0) or 0)
            set_kpis[set_num]['service_aces'] += float(stats.get('Service_Aces', 0) or 0)
            set_kpis[set_num]['service_good'] += float(stats.get('Service_Good', 0) or 0)
            set_kpis[set_num]['service_attempts'] += float(stats.get('Service_Total', 0) or 0)
            set_kpis[set_num]['service_errors'] += float(stats.get('Service_Errors', 0) or 0)
            set_kpis[set_num]['block_kills'] += float(stats.get('Block_Kills', 0) or 0)
            set_kpis[set_num]['block_attempts'] += float(stats.get('Block_Total', 0) or 0)
            set_kpis[set_num]['reception_good'] += float(stats.get('Reception_Good', 0) or 0)
            set_kpis[set_num]['reception_total'] += float(stats.get('Reception_Total', 0) or 0)
            set_kpis[set_num]['dig_good'] += float(stats.get('Dig_Good', 0) or 0)
            set_kpis[set_num]['dig_total'] += float(stats.get('Dig_Total', 0) or 0)
        
        # Add team data
        if set_num in loader.team_data_by_set:
            team_stats = loader.team_data_by_set[set_num]
            set_kpis[set_num]['serving_rallies'] = float(team_stats.get('serving_rallies', 0) or 0)
            set_kpis[set_num]['serving_points_won'] = float(team_stats.get('serving_points_won', 0) or 0)
            set_kpis[set_num]['receiving_rallies'] = float(team_stats.get('receiving_rallies', 0) or 0)
            set_kpis[set_num]['receiving_points_won'] = float(team_stats.get('receiving_points_won', 0) or 0)
    
    # Calculate KPIs using centralized calculation methods
    result = {}
    for set_num, totals in set_kpis.items():
        if kpi_name == 'attack_kill_pct':
            result[set_num] = KPICalculator.calculate_attack_kill_pct_from_totals(
                totals['attack_kills'], totals['attack_attempts']
            )
        elif kpi_name == 'attack_error_rate':
            result[set_num] = KPICalculator.calculate_attack_error_rate_from_totals(
                totals['attack_errors'], totals['attack_attempts']
            )
        elif kpi_name == 'serve_in_rate':
            result[set_num] = KPICalculator.calculate_serve_in_rate_from_totals(
                totals['service_aces'], totals['service_good'], totals['service_attempts']
            )
        elif kpi_name == 'serve_error_rate':
            result[set_num] = KPICalculator.calculate_serve_error_rate_from_totals(
                totals['service_errors'], totals['service_attempts']
            )
        elif kpi_name == 'block_kill_pct':
            result[set_num] = KPICalculator.calculate_block_kill_pct_from_totals(
                totals['block_kills'], totals['block_attempts']
            )
        elif kpi_name == 'reception_quality':
            result[set_num] = KPICalculator.calculate_reception_quality_from_totals(
                totals['reception_good'], totals['reception_total']
            )
        elif kpi_name == 'dig_quality':
            result[set_num] = KPICalculator.calculate_dig_rate_from_totals(
                totals['dig_good'], totals['dig_total']
            )
        elif kpi_name == 'break_point_rate':
            result[set_num] = KPICalculator.calculate_break_point_rate_from_totals(
                totals['serving_points_won'], totals['serving_rallies']
            )
        elif kpi_name == 'side_out_efficiency':
            result[set_num] = KPICalculator.calculate_side_out_efficiency_from_totals(
                totals['receiving_points_won'], totals['receiving_rallies']
            )
    
    return result

