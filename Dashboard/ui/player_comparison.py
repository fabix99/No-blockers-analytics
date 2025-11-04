"""
Player Comparison UI Module
"""
from typing import Dict, Any, Optional, Tuple
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import KPI_TARGETS
from utils.helpers import get_player_position
from ui.components import get_position_full_name
from charts.utils import apply_beautiful_theme, plotly_config


def display_player_comparison(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display player comparison with ratings and KPIs.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for aggregated data
    """
    st.markdown('<h2 class="main-header">🏆 Player Comparison</h2>', unsafe_allow_html=True)
    
    player_stats = analyzer.calculate_player_metrics()
    
    if player_stats is None:
        st.error("No player statistics available")
        return
    
    df = analyzer.match_data
    
    # Create comparison dataframe with new KPIs and ratings
    comparison_data = []
    for player, stats in player_stats.items():
        position = get_player_position(df, player) or 'Unknown'
        is_setter = stats.get('total_sets', 0) > 0 and stats.get('total_sets', 0) >= stats['total_actions'] * 0.2
        
        # Calculate player KPIs (consistent with Team Overview)
        kpis = _calculate_player_kpis_for_comparison(analyzer, player, stats, position, is_setter, loader)
        
        # Calculate position-specific rating
        rating, rating_breakdown = _calculate_player_rating_new(stats, position, is_setter, kpis, loader, player)
        
        # Calculate total actions including all types (from loader aggregated data if available)
        total_actions = stats['total_actions']  # Base count from action rows
        if loader and hasattr(loader, 'player_data_by_set'):
            # Add digs and receptions from aggregated data if not in action rows
            total_digs = 0
            total_receptions = 0
            for set_num in loader.player_data_by_set.keys():
                if player in loader.player_data_by_set[set_num]:
                    stats_agg = loader.player_data_by_set[set_num][player].get('stats', {})
                    total_digs += float(stats_agg.get('Dig_Total', 0) or 0)
                    total_receptions += float(stats_agg.get('Reception_Total', 0) or 0)
            # Only add if not already counted in action rows
            # Check if digs/receptions are in action rows
            player_df = df[df['player'] == player]
            if len(player_df[player_df['action'] == 'dig']) == 0:
                total_actions += int(total_digs)
            if len(player_df[player_df['action'] == 'receive']) < total_receptions:
                total_actions += int(total_receptions - len(player_df[player_df['action'] == 'receive']))
        
        comparison_data.append({
            'Player': player,
            'Position': get_position_full_name(position),
            'Rating': rating,
            'Attack Rating': rating_breakdown.get('attack', 0),
            'Reception Rating': rating_breakdown.get('reception', 0),
            'Serve Rating': rating_breakdown.get('serve', 0),
            'Block Rating': rating_breakdown.get('block', 0),
            'Defense Rating': rating_breakdown.get('defense', 0),
            'Setting Rating': rating_breakdown.get('setting', 0),
            # New KPIs
            'Attack Kill %': kpis.get('attack_kill_pct', 0),
            'Serve In-Rate': kpis.get('serve_in_rate', 0),
            'Reception Quality': kpis.get('reception_quality', 0),
            'Block Kill %': kpis.get('block_kill_pct', 0),
            'Dig Rate': kpis.get('dig_rate', 0),
            'Setting Quality': kpis.get('setting_quality', 0),
            # Volume metrics
            'Attack Attempts': stats.get('attack_attempts', 0),
            'Attack Kills': stats.get('attack_kills', 0),
            'Attack Good': kpis.get('attack_good', 0),  # For weighted scoring
            'Service Attempts': stats.get('service_attempts', 0),
            'Block Attempts': stats.get('block_attempts', 0),
            'Block Kills': stats.get('block_kills', 0),
            'Block Touches': kpis.get('block_touches', 0),  # For weighted scoring
            'Reception Attempts': stats.get('total_receives', 0),
            'Total Sets': stats.get('total_sets', 0),
            'Total Actions': total_actions
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Display top performers
    _display_top_performers(comparison_df)
    
    # Display ratings
    # HIDDEN: Ratings section temporarily hidden - uncomment to re-enable
    # _display_ratings(comparison_df)


def _calculate_player_kpis_for_comparison(analyzer: MatchAnalyzer, player_name: str, 
                                          player_data: Dict[str, Any], position: Optional[str],
                                          is_setter: bool, loader=None) -> Dict[str, float]:
    """Calculate player KPIs consistent with Team Overview metrics."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    metrics = {}
    
    # Attack Kill % (consistent with Team Overview)
    # Calculate for all players - will be used if they have attempts
    attack_attempts = player_data.get('attack_attempts', 0)
    if attack_attempts > 0:
        metrics['attack_kill_pct'] = player_data['attack_kills'] / attack_attempts
        # Also get attack good for weighted scoring
        attacks = player_df[player_df['action'] == 'attack']
        metrics['attack_good'] = len(attacks[attacks['outcome'] == 'good'])
    else:
        metrics['attack_kill_pct'] = 0.0
        metrics['attack_good'] = 0
    
    # Serve In-Rate (consistent with Team Overview)
    # Liberos don't serve - exclude for position 'L'
    if position == 'L':
        metrics['serve_in_rate'] = 0.0
    else:
        service_attempts = player_data.get('service_attempts', 0)
        if service_attempts > 0:
            service_aces = player_data.get('service_aces', 0)
            serves = player_df[player_df['action'] == 'serve']
            service_good = len(serves[serves['outcome'] == 'good'])
            metrics['serve_in_rate'] = (service_aces + service_good) / service_attempts
        else:
            metrics['serve_in_rate'] = 0.0
    
    # Reception Quality (consistent with Team Overview)
    if loader and hasattr(loader, 'player_data_by_set'):
        total_rec_good = 0.0
        total_rec_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                total_rec_good += float(stats.get('Reception_Good', 0) or 0)
                total_rec_total += float(stats.get('Reception_Total', 0) or 0)
        if total_rec_total > 0:
            metrics['reception_quality'] = total_rec_good / total_rec_total
        else:
            receives = player_df[player_df['action'] == 'receive']
            total_receives = len(receives)
            if total_receives > 0:
                good_receives = len(receives[receives['outcome'] == 'good'])
                metrics['reception_quality'] = good_receives / total_receives
            else:
                metrics['reception_quality'] = 0.0
    else:
        receives = player_df[player_df['action'] == 'receive']
        total_receives = len(receives)
        if total_receives > 0:
            good_receives = len(receives[receives['outcome'] == 'good'])
            metrics['reception_quality'] = good_receives / total_receives
        else:
            metrics['reception_quality'] = 0.0
    
    # Dig Rate (consistent with Team Overview)
    if loader and hasattr(loader, 'player_data_by_set'):
        total_dig_good = 0.0
        total_dig_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                total_dig_good += float(stats.get('Dig_Good', 0) or 0)
                total_dig_total += float(stats.get('Dig_Total', 0) or 0)
        if total_dig_total > 0:
            metrics['dig_rate'] = total_dig_good / total_dig_total
        else:
            metrics['dig_rate'] = 0.0
    else:
        metrics['dig_rate'] = 0.0
    
    # Block Kill % (consistent with Team Overview)
    # Calculate for all players - will be used if they have attempts
    block_attempts = player_data.get('block_attempts', 0)
    if block_attempts > 0:
        metrics['block_kill_pct'] = player_data['block_kills'] / block_attempts
        # Also get block touches for weighted scoring
        blocks = player_df[player_df['action'] == 'block']
        metrics['block_touches'] = len(blocks[blocks['outcome'] == 'good'])
    else:
        metrics['block_kill_pct'] = 0.0
        metrics['block_touches'] = 0
    
    # Setting Quality - check from action rows first (more accurate for all players)
    # Calculate for all players - will be used as bonus if they set well
    sets = player_df[player_df['action'] == 'set']
    total_sets_count = len(sets)
    if total_sets_count > 0:
        good_sets_count = len(sets[sets['outcome'] == 'good'])
        metrics['setting_quality'] = good_sets_count / total_sets_count
    else:
        # Fallback to player_data if available
        total_sets = player_data.get('total_sets', 0)
        if total_sets > 0:
            good_sets = player_data.get('good_sets', 0)
            metrics['setting_quality'] = good_sets / total_sets
        else:
            metrics['setting_quality'] = 0.0
    
    return metrics


def _normalize_kpi_to_rating(value: float, target_min: float, target_optimal: float, 
                             target_max: float) -> float:
    """
    Normalize a KPI value to a rating on a 6=average scale (more generous).
    - 6.0 = at target_min (average performance)
    - 7.0 = at target_optimal (good performance)
    - 8.0 = at target_max (great performance)
    - 9-10 = exceptional (above target_max)
    - 5.5+ = below target_min but still decent (more generous floor)
    - 5.0-5.5 = below average
    """
    if value >= target_max * 1.12:  # 12% above max = exceptional (slightly more generous)
        return 10.0
    elif value >= target_max * 1.06:  # 6% above max = outstanding
        return 9.0
    elif value >= target_max:
        # Great to Outstanding: 8.0 to 9.0 scale
        return min(9.0, 8.0 + ((value - target_max) / (target_max * 0.06)) * 1.0)
    elif value >= target_optimal:
        # Good to Great: 7.0 to 8.0 scale
        return 7.0 + ((value - target_optimal) / (target_max - target_optimal)) * 1.0
    elif value >= target_min:
        # Average to Good: 6.0 to 7.0 scale
        return 6.0 + ((value - target_min) / (target_optimal - target_min)) * 1.0
    elif value > target_min * 0.7:  # More generous: 70% of target_min still gets 5.5+
        # Below Average but decent: 5.5 to 6.0 scale
        return max(5.5, 5.5 + ((value - target_min * 0.7) / (target_min * 0.3)) * 0.5)
    elif value > 0:
        # Below Average: 5.0 to 5.5 scale
        return max(5.0, 5.0 + (value / (target_min * 0.7)) * 0.5)
    else:
        # Poor: 5.0 (more generous floor, no data or zero performance)
        return 5.0


def _calculate_player_rating_new(player_data: Dict[str, Any], position: Optional[str],
                                 is_setter: bool, kpis: Dict[str, float], 
                                 loader=None, player_name: str = "") -> Tuple[float, Dict[str, float]]:
    """
    Calculate position-specific rating on normalized 6=average scale.
    Uses expected actions (90% weight) + bonus actions (up to 10%).
    Expected actions have consistent weights across positions for fairness.
    Returns: (overall_rating, breakdown_dict)
    """
    breakdown = {}
    
    # Standard weights for expected actions (same across all positions)
    WEIGHT_ATTACK = 0.30  # 30%
    WEIGHT_BLOCK = 0.25   # 25%
    WEIGHT_RECEPTION = 0.25  # 25%
    WEIGHT_SERVE = 0.15   # 15%
    WEIGHT_DIG = 0.20     # 20%
    WEIGHT_SETTING = 0.40  # 40% (for setters)
    
    # Bonus threshold: only add bonus if rating ≥ 7.0 (good performance)
    BONUS_THRESHOLD = 7.0
    MAX_BONUS = 0.10  # Maximum 10% bonus
    
    # Check position first (liberos can set but are still liberos)
    if position == 'L':
        # LIBERO: Expected = Reception (45%) + Dig (45%) = 90%
        # Bonus: Setting (up to 10%)
        # Liberos CANNOT serve (hard rule) - no attack, block, serve
        reception_q = kpis.get('reception_quality', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                         KPI_TARGETS['reception_quality']['min'],
                                                         KPI_TARGETS['reception_quality']['optimal'],
                                                         KPI_TARGETS['reception_quality']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Liberos don't serve, attack, or block - set to 0
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['reception'] * 0.45 + 
                      breakdown['defense'] * 0.45)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.10  # 10% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
        # Ensure liberos never have serve, attack, or block ratings (double-check)
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
    
    elif is_setter or position == 'S':
        # SETTER: Expected = Setting (40%) + Attack (30%) + Serve (15%) + Block (5%) = 90%
        # Bonus: Dig, Reception (up to 10%)
        setting_q = kpis.get('setting_quality', 0)
        attack_kill = kpis.get('attack_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        
        targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
        breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                         targets_setting['optimal'], targets_setting['max'])
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max']) if (attack_kill > 0 or player_data.get('attack_attempts', 0) > 0) else 6.0
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in, 
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max']) if (block_kill > 0 or player_data.get('block_attempts', 0) > 0) else 6.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['setting'] * WEIGHT_SETTING + 
                      breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['block'] * 0.05)  # 5% for block
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if dig_rate > 0 or (loader and hasattr(loader, 'player_data_by_set')):
            has_digs = False
            if loader and hasattr(loader, 'player_data_by_set'):
                for set_num in loader.player_data_by_set.keys():
                    if player_name in loader.player_data_by_set[set_num]:
                        stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                        if float(stats.get('Dig_Total', 0) or 0) > 0:
                            has_digs = True
                            break
            if has_digs or dig_rate > 0:
                breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                                KPI_TARGETS['dig_rate']['min'],
                                                                KPI_TARGETS['dig_rate']['optimal'],
                                                                KPI_TARGETS['dig_rate']['max'])
                if breakdown['defense'] >= BONUS_THRESHOLD:
                    bonus += 0.05  # 5% bonus
            else:
                breakdown['defense'] = 0.0
        else:
            breakdown['defense'] = 0.0
        
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position and position.startswith('OH'):
        # OUTSIDE HITTER: Expected = Attack (30%) + Reception (25%) + Block (25%) + Serve (10%) = 90%
        # Bonus: Dig, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        reception_q = kpis.get('reception_quality', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max'])
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                          KPI_TARGETS['reception_quality']['min'],
                                                          KPI_TARGETS['reception_quality']['optimal'],
                                                          KPI_TARGETS['reception_quality']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['reception'] * WEIGHT_RECEPTION + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * 0.10)  # 10% for serve (not 15%)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if dig_rate > 0 or (loader and hasattr(loader, 'player_data_by_set')):
            has_digs = any(player_name in loader.player_data_by_set.get(set_num, {}) and 
                          float(loader.player_data_by_set[set_num][player_name].get('stats', {}).get('Dig_Total', 0) or 0) > 0
                          for set_num in loader.player_data_by_set.keys()) if loader and hasattr(loader, 'player_data_by_set') else False
            if has_digs or dig_rate > 0:
                breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                                KPI_TARGETS['dig_rate']['min'],
                                                                KPI_TARGETS['dig_rate']['optimal'],
                                                                KPI_TARGETS['dig_rate']['max'])
                if breakdown['defense'] >= BONUS_THRESHOLD:
                    bonus += 0.05  # 5% bonus
            else:
                breakdown['defense'] = 0.0
        else:
            breakdown['defense'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position and position.startswith('MB'):
        # MIDDLE BLOCKER: Expected = Attack (30%) + Block (25%) + Serve (15%) + Dig (20%) = 90%
        # Bonus: Reception, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                      KPI_TARGETS['kill_percentage']['min'],
                                                      KPI_TARGETS['kill_percentage']['optimal'],
                                                      KPI_TARGETS['kill_percentage']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['defense'] * WEIGHT_DIG)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position == 'OPP':
        # OPPOSITE: Expected = Attack (30%) + Block (25%) + Serve (15%) + Dig (20%) = 90%
        # Bonus: Reception, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                       KPI_TARGETS['block_kill_percentage']['min'],
                                                       KPI_TARGETS['block_kill_percentage']['optimal'],
                                                       KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['defense'] * WEIGHT_DIG)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position == 'L':
        # LIBERO: Expected = Reception (45%) + Dig (45%) = 90%
        # Bonus: Setting (up to 10%)
        # Liberos CANNOT serve (hard rule) - no attack, block, serve
        reception_q = kpis.get('reception_quality', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                         KPI_TARGETS['reception_quality']['min'],
                                                         KPI_TARGETS['reception_quality']['optimal'],
                                                         KPI_TARGETS['reception_quality']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Liberos don't serve, attack, or block - set to 0
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['reception'] * 0.45 + 
                      breakdown['defense'] * 0.45)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.10  # 10% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
        # Ensure liberos never have serve, attack, or block ratings (double-check)
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
    else:
        # Unknown/Other: General rating
        attack_kill = kpis.get('attack_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max']) if attack_kill > 0 else 6.0
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max']) if serve_in > 0 else 6.0
        
        rating = (breakdown['attack'] * 0.5 + breakdown['serve'] * 0.5) if (attack_kill > 0 or serve_in > 0) else 6.0
    
    # Round to 1 decimal place
    rating = round(rating, 1)
    for key in breakdown:
        breakdown[key] = round(breakdown[key], 1)
    
    return rating, breakdown


def _display_top_performers(comparison_df: pd.DataFrame) -> None:
    """Display top performers by category with horizontal bar charts."""
    st.markdown("### 🏆 Top Performers by Category")
    
    # Top Attackers
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Top Attackers (Weighted: Kills 3x + Good)")
        # Calculate weighted score: kills * 3 + good attacks
        attackers_df = comparison_df[comparison_df['Attack Attempts'] > 0].copy()
        if len(attackers_df) > 0:
            attackers_df['Attack Score'] = (attackers_df['Attack Kills'] * 3 + attackers_df['Attack Good']) / attackers_df['Attack Attempts']
            attackers_df = attackers_df.nlargest(5, 'Attack Score').sort_values('Attack Score', ascending=False)  # Sort descending: largest first = top
            
            fig_attack = go.Figure(data=go.Bar(
                x=attackers_df['Attack Score'],
                y=attackers_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.2f}" for x in attackers_df['Attack Score']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_attack.update_layout(
                xaxis_title="Attack Score (Kills×3 + Good) / Attempts",
                yaxis_title="Player",
                xaxis=dict(tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_attack = apply_beautiful_theme(fig_attack, "")
            fig_attack.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_attack, use_container_width=True, config=plotly_config)
        else:
            st.info("No attack data available")
    
    with col2:
        st.markdown("#### 🎾 Top Servers (Serve In-Rate)")
        servers_df = comparison_df[comparison_df['Service Attempts'] > 0].nlargest(5, 'Serve In-Rate').sort_values('Serve In-Rate', ascending=False)  # Sort descending: largest first = top
        if len(servers_df) > 0:
            fig_serve = go.Figure(data=go.Bar(
                x=servers_df['Serve In-Rate'],
                y=servers_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.1%}" for x in servers_df['Serve In-Rate']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_serve.update_layout(
                xaxis_title="Serve In-Rate",
                yaxis_title="Player",
                xaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_serve = apply_beautiful_theme(fig_serve, "")
            fig_serve.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_serve, use_container_width=True, config=plotly_config)
        else:
            st.info("No service data available")
    
    # Second row
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("#### 🛡️ Top Blockers (Weighted: Kills + Touches)")
        # Calculate weighted score: kills + touches
        blockers_df = comparison_df[comparison_df['Block Attempts'] > 0].copy()
        if len(blockers_df) > 0:
            blockers_df['Block Score'] = (blockers_df['Block Kills'] + blockers_df['Block Touches']) / blockers_df['Block Attempts']
            blockers_df = blockers_df.nlargest(5, 'Block Score').sort_values('Block Score', ascending=False)  # Sort descending: largest first = top
            
            fig_block = go.Figure(data=go.Bar(
                x=blockers_df['Block Score'],
                y=blockers_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.2f}" for x in blockers_df['Block Score']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_block.update_layout(
                xaxis_title="Block Score (Kills + Touches) / Attempts",
                yaxis_title="Player",
                xaxis=dict(tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_block = apply_beautiful_theme(fig_block, "")
            fig_block.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_block, use_container_width=True, config=plotly_config)
        else:
            st.info("No block data available")
    
    with col4:
        st.markdown("#### ✋ Top Receivers (Reception Quality)")
        receivers_df = comparison_df[comparison_df['Reception Attempts'] > 0].nlargest(5, 'Reception Quality').sort_values('Reception Quality', ascending=False)  # Sort descending: largest first = top
        if len(receivers_df) > 0:
            fig_rec = go.Figure(data=go.Bar(
                x=receivers_df['Reception Quality'],
                y=receivers_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.1%}" for x in receivers_df['Reception Quality']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_rec.update_layout(
                xaxis_title="Reception Quality",
                yaxis_title="Player",
                xaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_rec = apply_beautiful_theme(fig_rec, "")
            fig_rec.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_rec, use_container_width=True, config=plotly_config)
        else:
            st.info("No reception data available")
    
    # Third row
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("#### 🏐 Top Diggers (Dig Rate)")
        diggers_df = comparison_df[comparison_df['Dig Rate'] > 0].nlargest(5, 'Dig Rate').sort_values('Dig Rate', ascending=False)  # Sort descending: largest first = top
        if len(diggers_df) > 0:
            fig_dig = go.Figure(data=go.Bar(
                x=diggers_df['Dig Rate'],
                y=diggers_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.1%}" for x in diggers_df['Dig Rate']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_dig.update_layout(
                xaxis_title="Dig Rate",
                yaxis_title="Player",
                xaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_dig = apply_beautiful_theme(fig_dig, "")
            fig_dig.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_dig, use_container_width=True, config=plotly_config)
        else:
            st.info("No dig data available")
    
    with col6:
        st.markdown("#### 🎯 Top Setters (Setting Quality)")
        # Check for setters - use Total Sets > 0 OR check if Setting Quality is calculated
        setters_df = comparison_df[(comparison_df['Total Sets'] > 0) | (comparison_df['Setting Quality'] > 0)].nlargest(5, 'Setting Quality').sort_values('Setting Quality', ascending=False)  # Sort descending: largest first = top
        if len(setters_df) > 0:
            fig_set = go.Figure(data=go.Bar(
                x=setters_df['Setting Quality'],
                y=setters_df['Player'],
                orientation='h',
                marker_color='#B8D4E6',  # Soft blue
                text=[f"{x:.1%}" for x in setters_df['Setting Quality']],
                textposition='outside',
                textfont=dict(size=11, color='#040C7B')
            ))
            fig_set.update_layout(
                xaxis_title="Setting Quality",
                yaxis_title="Player",
                xaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
                yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
                height=200,
                showlegend=False
            )
            fig_set = apply_beautiful_theme(fig_set, "")
            fig_set.update_traces(marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)))
            st.plotly_chart(fig_set, use_container_width=True, config=plotly_config)
        else:
            st.info("No setting data available")


def _display_ratings(comparison_df: pd.DataFrame) -> None:
    """Display overall player ratings with skill breakdowns."""
    st.markdown("## ⭐ Overall Player Ratings (Out of 10)")
    
    # Sort by rating
    sorted_df = comparison_df.sort_values('Rating', ascending=False)
    
    # Create horizontal bar chart with color coding: green from 7+, red only below 5
    # Define colors based on rating
    def get_rating_color(rating):
        if rating >= 7.0:
            return '#90EE90'  # Soft green
        elif rating >= 5.0:
            return '#FFE4B5'  # Soft yellow/cream
        else:
            return '#FFB6C1'  # Soft pink/red
    
    colors = [get_rating_color(r) for r in sorted_df['Rating']]
    
    fig_rating = go.Figure(data=go.Bar(
        x=sorted_df['Rating'],
        y=sorted_df['Player'],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.8)', width=1)
        ),
        text=[f"{x:.1f}" for x in sorted_df['Rating']],
        textposition='outside',
        textfont=dict(size=11, color='#040C7B')
    ))
    fig_rating.update_layout(
        title="Player Ratings Comparison (Out of 10)",
        xaxis_title="Rating",
        yaxis_title="Player",
        xaxis=dict(range=[0, 10], tickfont=dict(color='#040C7B'), dtick=1),
        yaxis=dict(tickfont=dict(color='#040C7B'), autorange='reversed'),
        height=max(400, len(sorted_df) * 40),
        showlegend=False
    )
    fig_rating = apply_beautiful_theme(fig_rating, "Player Ratings Comparison (Out of 10)")
    st.plotly_chart(fig_rating, use_container_width=True, config=plotly_config)
    
    # Display ratings table with skill breakdowns
    ratings_display_df = sorted_df[['Player', 'Position', 'Rating', 
                                   'Attack Rating', 'Reception Rating', 'Serve Rating',
                                   'Block Rating', 'Defense Rating', 'Setting Rating',
                                   'Total Actions']].copy()
    
    # Format ratings to 1 decimal place, only show relevant ratings for each position
    rating_cols = ['Rating', 'Attack Rating', 'Reception Rating', 'Serve Rating',
                   'Block Rating', 'Defense Rating', 'Setting Rating']
    for col in rating_cols:
        if col in ratings_display_df.columns:
            ratings_display_df[col] = ratings_display_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) and x > 0 else "-")
    
    # Hide irrelevant ratings based on position
    # Libero: no Attack Rating or Block Rating or Setting Rating
    for idx, row in ratings_display_df.iterrows():
        position = row['Position']
        if 'Libero' in position:
            # Libero: no attack, block, or setting
            if 'Attack Rating' in ratings_display_df.columns:
                ratings_display_df.at[idx, 'Attack Rating'] = "-"
            if 'Block Rating' in ratings_display_df.columns:
                ratings_display_df.at[idx, 'Block Rating'] = "-"
            if 'Setting Rating' in ratings_display_df.columns:
                ratings_display_df.at[idx, 'Setting Rating'] = "-"
    
    st.dataframe(
        ratings_display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Add explanation


