"""
Helper functions for generating insights from match data.
Extracted from generate_insights() for better organization.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from match_analyzer import MatchAnalyzer
from utils.helpers import filter_block_touches


def get_player_position(df: pd.DataFrame, player: str) -> Optional[str]:
    """Get player position from dataframe.
    
    Args:
        df: Match data DataFrame
        player: Player name
        
    Returns:
        Position code or None
    """
    player_data = df[df['player'] == player]
    if len(player_data) > 0 and 'position' in player_data.columns:
        return player_data['position'].iloc[0]
    return None


def _generate_attack_efficiency_insights(
    team_stats: Dict[str, Any],
    targets: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about attack efficiency.
    
    Args:
        team_stats: Team statistics dictionary
        targets: KPI targets dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    attack_eff = team_stats['attack_efficiency']
    
    if attack_eff < targets['attack_efficiency']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'Attack Efficiency Below Target',
            'message': f"Attack efficiency ({attack_eff:.1%}) is below target ({targets['attack_efficiency']['min']:.1%}). Team has {team_stats['attack_errors']} attack errors vs {team_stats['attack_kills']} kills.",
            'recommendation': 'Focus on attack precision and decision-making. Consider reducing high-risk attacks when ahead.'
        })
    
    # Attack Error Analysis
    attack_errors = team_stats['attack_errors']
    attack_kills = team_stats['attack_kills']
    if attack_errors > attack_kills * 0.5:  # More than half as many errors as kills
        error_rate = attack_errors / team_stats['attack_attempts'] if team_stats['attack_attempts'] > 0 else 0
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'High Attack Error Rate',
            'message': f"Attack errors ({attack_errors}) are {error_rate:.1%} of all attack attempts. Error-to-kill ratio: {attack_errors/attack_kills:.2f}:1",
            'recommendation': 'Focus on shot selection and placement. Work on hitting angles, reducing out-of-bounds attacks. Consider lowering attack tempo when ahead to reduce errors. Practice attacking under pressure.'
        })
    
    return insights


def _generate_set_by_set_insights(
    df: pd.DataFrame,
    set_stats: pd.DataFrame
) -> List[Dict[str, Any]]:
    """Generate insights about set-by-set performance trends.
    
    Args:
        df: Match data DataFrame
        set_stats: Set statistics DataFrame
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    if len(set_stats) <= 1:
        return insights
    
    # Calculate attack efficiency by set
    set_attack_eff = []
    for set_num in set_stats.index:
        set_df = df[df['set_number'] == set_num]
        attacks = set_df[set_df['action'] == 'attack']
        if len(attacks) > 0:
            kills = len(attacks[attacks['outcome'] == 'kill'])
            errors = len(attacks[attacks['outcome'] == 'error'])
            eff = (kills - errors) / len(attacks)
            set_attack_eff.append({'set': set_num, 'efficiency': eff})
    
    if len(set_attack_eff) >= 2:
        first_set_eff = set_attack_eff[0]['efficiency']
        last_set_eff = set_attack_eff[-1]['efficiency']
        change = last_set_eff - first_set_eff
        
        if change < -0.10:  # Drop of 10% or more
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Performance Decline in Later Sets',
                'message': f"Attack efficiency drops from {first_set_eff:.1%} in Set {set_attack_eff[0]['set']} to {last_set_eff:.1%} in Set {set_attack_eff[-1]['set']} ({change:.1%} decrease).",
                'recommendation': 'Consider strategic substitutions or timeout management to maintain performance. May indicate fatigue or loss of focus.'
            })
        elif change > 0.10:
            insights.append({
                'type': 'success',
                'priority': 'medium',
                'title': 'Improving Performance',
                'message': f"Attack efficiency improves from {first_set_eff:.1%} to {last_set_eff:.1%} (+{change:.1%}).",
                'recommendation': 'Team is adapting well. Maintain this momentum.'
            })
    
    # Error Distribution by Set
    set_errors = []
    for set_num in set_stats.index:
        set_df = df[df['set_number'] == set_num]
        errors = len(set_df[set_df['outcome'] == 'error'])
        set_errors.append({'set': set_num, 'errors': errors})
    
    if len(set_errors) >= 2:
        max_errors_set = max(set_errors, key=lambda x: x['errors'])
        min_errors_set = min(set_errors, key=lambda x: x['errors'])
        
        if max_errors_set['errors'] > min_errors_set['errors'] * 1.5:
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': f'Error Concentration in Set {max_errors_set["set"]}',
                'message': f"Set {max_errors_set['set']} has {max_errors_set['errors']} errors vs {min_errors_set['errors']} in Set {min_errors_set['set']}.",
                'recommendation': f'Review what happened in Set {max_errors_set["set"]}. Identify error patterns and address root causes.'
            })
    
    # Set-by-Set Service Analysis
    set_service_stats = []
    for set_num in set_stats.index:
        set_df = df[df['set_number'] == set_num]
        serves = set_df[set_df['action'] == 'serve']
        if len(serves) > 0:
            aces = len(serves[serves['outcome'] == 'ace'])
            serv_errors = len(serves[serves['outcome'] == 'error'])
            set_service_stats.append({
                'set': set_num,
                'aces': aces,
                'errors': serv_errors,
                'net': aces - serv_errors
            })
    
    if len(set_service_stats) >= 2:
        worst_service_set = max(set_service_stats, key=lambda x: x['errors'])
        if worst_service_set['errors'] > 5:
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': f'Service Errors Peak in Set {worst_service_set["set"]}',
                'message': f"Set {worst_service_set['set']} has {worst_service_set['errors']} service errors, highest of all sets.",
                'recommendation': f'Review service strategy for Set {worst_service_set["set"]}. Consider switching to safer serves when errors accumulate. May indicate fatigue or pressure affecting service consistency.'
            })
    
    # Set-by-Set Error Trend
    error_trend = []
    for set_num in sorted(set_stats.index):
        set_df = df[df['set_number'] == set_num]
        errors = len(set_df[set_df['outcome'] == 'error'])
        error_trend.append({'set': set_num, 'errors': errors})
    
    if len(error_trend) >= 2:
        increasing_errors = all(error_trend[i]['errors'] < error_trend[i+1]['errors'] for i in range(len(error_trend)-1))
        if increasing_errors and error_trend[-1]['errors'] > error_trend[0]['errors'] * 1.3:
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Increasing Error Trend Across Sets',
                'message': f"Errors increase from Set {error_trend[0]['set']} ({error_trend[0]['errors']} errors) to Set {error_trend[-1]['set']} ({error_trend[-1]['errors']} errors).",
                'recommendation': 'Errors are increasing across sets - may indicate fatigue, loss of focus, or mounting pressure. Consider strategic timeouts, substitutions, or mental reset strategies. Work on maintaining consistency under pressure.'
            })
    
    return insights


def _generate_rotation_insights(
    df: pd.DataFrame,
    rotation_stats: Dict[int, float]
) -> List[Dict[str, Any]]:
    """Generate insights about rotation performance.
    
    Args:
        df: Match data DataFrame
        rotation_stats: Dictionary mapping rotation number to efficiency
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    if not rotation_stats:
        return insights
    
    avg_rotation_eff = sum(rotation_stats.values()) / len(rotation_stats)
    weakest_rotation = min(rotation_stats.items(), key=lambda x: x[1])
    strongest_rotation = max(rotation_stats.items(), key=lambda x: x[1])
    
    if weakest_rotation[1] < avg_rotation_eff - 0.10:  # 10% below average
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': f'Weak Rotation Identified',
            'message': f"Rotation {weakest_rotation[0]} has attack efficiency {weakest_rotation[1]:.1%}, which is {avg_rotation_eff - weakest_rotation[1]:.1%} below team average ({avg_rotation_eff:.1%}).",
            'recommendation': f'Focus practice on Rotation {weakest_rotation[0]} combinations. Review positioning and communication in this rotation.'
        })
    
    if strongest_rotation[1] > avg_rotation_eff + 0.10:  # 10% above average
        insights.append({
            'type': 'success',
            'priority': 'low',
            'title': f'Strong Rotation',
            'message': f"Rotation {strongest_rotation[0]} performs well with {strongest_rotation[1]:.1%} attack efficiency.",
            'recommendation': f'Use Rotation {strongest_rotation[0]} strategically when you need points. Consider this as your "go-to" rotation.'
        })
    
    # Rotation-Specific Detailed Analysis
    for rot, eff in rotation_stats.items():
        rot_df = df[df['rotation'] == rot]
        rot_errors = len(rot_df[rot_df['outcome'] == 'error'])
        rot_total = len(rot_df)
        
        if rot_total > 10:  # Only analyze rotations with significant data
            error_rate = rot_errors / rot_total
            if error_rate > 0.20:  # More than 20% errors in rotation
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': f'Rotation {rot} - High Error Rate',
                    'message': f"Rotation {rot} has {error_rate:.1%} error rate ({rot_errors}/{rot_total} errors).",
                    'recommendation': f'Review Rotation {rot} lineup and positioning. Identify which players in this rotation struggle. Consider lineup adjustments or focused practice for this rotation combination. Work on communication and coordination in this rotation.'
                })
    
    return insights


def _generate_service_insights(
    team_stats: Dict[str, Any],
    targets: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about service performance.
    
    Args:
        team_stats: Team statistics dictionary
        targets: KPI targets dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    service_eff = team_stats['service_efficiency']
    service_errors = team_stats['service_errors']
    service_aces = team_stats['service_aces']
    
    # Service Error Analysis
    if service_errors > service_aces * 2:  # More than 2x errors vs aces
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'High Service Error Rate',
            'message': f"Service errors ({service_errors}) significantly outnumber aces ({service_aces}). Net service impact: {service_aces - service_errors} points.",
            'recommendation': 'Focus on service consistency over power. Consider safer serves when ahead in score.'
        })
    
    # Service Pressure Analysis
    if service_aces > service_errors * 1.5:  # More aces than errors
        insights.append({
            'type': 'success',
            'priority': 'medium',
            'title': 'Effective Service Pressure',
            'message': f"Service aces ({service_aces}) significantly exceed errors ({service_errors}). Good service pressure.",
            'recommendation': 'Continue aggressive serving. Your service game is putting pressure on opponents. Maintain consistency while keeping aggressive approach.'
        })
    
    return insights


def _generate_block_insights(
    team_stats: Dict[str, Any],
    df: pd.DataFrame,
    targets: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about blocking performance.
    
    Args:
        team_stats: Team statistics dictionary
        df: Match data DataFrame
        targets: KPI targets dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    block_eff = team_stats['block_efficiency']
    if block_eff < targets['block_efficiency']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'medium',
            'title': 'Low Block Efficiency',
            'message': f"Block efficiency ({block_eff:.1%}) is below target. Only {team_stats['block_kills']} block kills.",
            'recommendation': 'Work on timing and positioning. Consider blocking assignments and communication.'
        })
    
    # Block Coverage Analysis
    block_attempts = team_stats['block_attempts']
    block_kills = team_stats['block_kills']
    if block_attempts > 0:
        block_kill_rate = block_kills / block_attempts
        if block_kill_rate < 0.05:  # Less than 5% kill rate
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': 'Low Block Kill Rate',
                'message': f"Only {block_kill_rate:.1%} of block attempts result in kills. {block_kills} kills from {block_attempts} attempts.",
                'recommendation': 'Focus on blocking timing and hand positioning. Work on reading attacker approach and timing jump. Practice middle blockers on quick tempo blocks. Improve blocking unit coordination.'
            })
    
    # Block Touch vs Kill Analysis
    blocks = df[df['action'] == 'block']
    if len(blocks) > 0:
        block_touches = len(filter_block_touches(blocks))
        block_kills_total = len(blocks[blocks['outcome'] == 'kill'])
        if block_touches > block_kills_total * 5:  # More touches than kills
            insights.append({
                'type': 'info',
                'priority': 'medium',
                'title': 'Blocks Creating Opportunities',
                'message': f"Many block touches ({block_touches}) creating follow-up opportunities. {block_kills_total} direct block kills.",
                'recommendation': 'Blocks are creating opportunities. Work on converting block touches into points through better defense coverage and transition attacks.'
            })
    
    return insights


def _generate_reception_insights(
    team_stats: Dict[str, Any],
    targets: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about reception performance.
    
    Args:
        team_stats: Team statistics dictionary
        targets: KPI targets dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    # Side-out Percentage
    side_out = team_stats['side_out_percentage']
    if side_out < targets['side_out_percentage']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'Low Side-out Percentage',
            'message': f"Side-out percentage ({side_out:.1%}) is below target. Only {team_stats['good_receives']} good receives out of {team_stats['total_receives']} attempts.",
            'recommendation': 'Focus on reception quality. Good reception is the foundation of effective offense. Practice serve receive drills with OH and Libero players. Work on reading serve trajectory and positioning.'
        })
    elif side_out >= targets['side_out_percentage']['max']:
        insights.append({
            'type': 'success',
            'priority': 'low',
            'title': 'Excellent Side-out Performance',
            'message': f"Side-out percentage ({side_out:.1%}) exceeds target. Strong reception foundation.",
            'recommendation': 'Maintain this reception quality. This strong foundation allows for more aggressive offensive plays.'
        })
    
    # Reception Quality Distribution
    total_receives = team_stats['total_receives']
    if total_receives > 0:
        reception_error_rate = (team_stats['total_receives'] - team_stats['good_receives']) / total_receives
        if reception_error_rate > 0.25:  # More than 25% reception errors
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Reception Error Rate Too High',
                'message': f"Reception error rate is {reception_error_rate:.1%}. {team_stats['total_receives'] - team_stats['good_receives']} reception errors.",
                'recommendation': 'Focus on reception fundamentals: body positioning, platform angle, reading serve trajectory. Practice with different serve types and speeds. Work on libero and outside hitter reception skills specifically.'
            })
    
    return insights


def _generate_position_specific_insights(
    df: pd.DataFrame,
    player_stats: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate insights about position-specific performance.
    
    Args:
        df: Match data DataFrame
        player_stats: Dictionary of player statistics
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    if not player_stats:
        return insights
    
    # Outside Hitter Analysis
    oh_players = []
    for player, stats in player_stats.items():
        pos = get_player_position(df, player)
        if pos and pos.startswith('OH'):
            oh_players.append({'player': player, 'position': pos, 'stats': stats})
    
    if oh_players:
        oh_attack_eff = [p['stats']['attack_efficiency'] for p in oh_players if p['stats']['attack_attempts'] > 5]
        oh_reception = [p['stats'].get('reception_percentage', 0) for p in oh_players if p['stats'].get('total_receives', 0) > 0]
        
        if oh_attack_eff:
            avg_oh_attack = sum(oh_attack_eff) / len(oh_attack_eff)
            if avg_oh_attack < 0.20:
                weak_oh = [p for p in oh_players if p['stats']['attack_efficiency'] < 0.20 and p['stats']['attack_attempts'] > 5]
                if weak_oh:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': 'Outside Hitter Attack Efficiency Low',
                        'message': f"Average OH attack efficiency: {avg_oh_attack:.1%}. {', '.join([p['player'] for p in weak_oh[:2]])} performing below target.",
                        'recommendation': 'Focus on OH attack technique: hitting angles, power control, off-speed shots. Work on attacking from various sets. Practice back-row attacks. Improve attacking against double blocks.'
                    })
        
        if oh_reception:
            avg_oh_reception = sum(oh_reception) / len(oh_reception)
            if avg_oh_reception < 0.70:
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'Outside Hitter Reception Quality Needs Improvement',
                    'message': f"Average OH reception percentage: {avg_oh_reception:.1%}, below target 70%.",
                    'recommendation': 'Focus OH reception training: platform work, body positioning, reading serve. Practice with different serve types. Work on movement to ball and proper platform angle.'
                })
    
    # Middle Blocker Analysis
    mb_players = []
    for player, stats in player_stats.items():
        pos = get_player_position(df, player)
        if pos and pos.startswith('MB'):
            mb_players.append({'player': player, 'position': pos, 'stats': stats})
    
    if mb_players:
        mb_block_eff = [p['stats']['block_efficiency'] for p in mb_players if p['stats']['block_attempts'] > 0]
        mb_attack_eff = [p['stats']['attack_efficiency'] for p in mb_players if p['stats']['attack_attempts'] > 0]
        
        if mb_block_eff:
            avg_mb_block = sum(mb_block_eff) / len(mb_block_eff)
            if avg_mb_block < 0.05:
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'Middle Blocker Blocking Performance Low',
                    'message': f"Average MB block efficiency: {avg_mb_block:.1%}. Middle blockers not generating enough block kills.",
                    'recommendation': 'Focus MB blocking: timing, penetration, hand positioning. Work on reading setter and hitter. Practice quick tempo blocks. Improve coordination between MBs. Focus on blocking assignments and communication.'
                })
        
        if mb_attack_eff:
            avg_mb_attack = sum(mb_attack_eff) / len(mb_attack_eff)
            if avg_mb_attack < 0.30:
                insights.append({
                    'type': 'warning',
                    'priority': 'medium',
                    'title': 'Middle Blocker Attack Efficiency Below Target',
                    'message': f"Average MB attack efficiency: {avg_mb_attack:.1%}. Middle blockers should have high efficiency.",
                    'recommendation': 'MBs need to capitalize on quick sets. Work on quick attack timing, hitting angles, and variety. Practice 1st tempo attacks. Improve connection with setter on quick sets.'
                })
    
    # Setter Analysis
    setter_players = []
    for player, stats in player_stats.items():
        pos = get_player_position(df, player)
        if pos == 'S':
            setter_players.append({'player': player, 'stats': stats})
        elif stats.get('total_sets', 0) > 20:  # Has many sets even if not marked as S
            setter_players.append({'player': player, 'stats': stats})
    
    if setter_players:
        for setter in setter_players:
            sets_total = setter['stats'].get('total_sets', 0)
            good_sets = setter['stats'].get('good_sets', 0)
            if sets_total > 0:
                set_quality = good_sets / sets_total
                if set_quality < 0.80:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': f'Setter {setter["player"]} - Setting Quality Below Target',
                        'message': f"Setting quality: {set_quality:.1%} ({good_sets}/{sets_total} good sets). Target: 80%+.",
                        'recommendation': f'Focus on setting consistency for {setter["player"]}. Work on hand position, footwork, and reading blockers. Practice setting accuracy to different positions. Improve decision-making on distribution. Setter should prioritize consistency over spectacular sets.'
                    })
    
    # Opposite Hitter Analysis
    opp_players = []
    for player, stats in player_stats.items():
        pos = get_player_position(df, player)
        if pos == 'OPP':
            opp_players.append({'player': player, 'stats': stats})
    
    if opp_players:
        opp_attack_eff = [p['stats']['attack_efficiency'] for p in opp_players if p['stats']['attack_attempts'] > 5]
        if opp_attack_eff:
            avg_opp_attack = sum(opp_attack_eff) / len(opp_attack_eff)
            if avg_opp_attack < 0.25:
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'Opposite Hitter Attack Efficiency Low',
                    'message': f"Average OPP attack efficiency: {avg_opp_attack:.1%}. Opposite hitters are key offensive weapons.",
                    'recommendation': 'OPP needs improvement on right-side attacks. Work on attacking angles, avoiding opponent blocks, back-row attacks. Practice attacking from the right side with various sets. Focus on power and placement. Work on hitting around blocks and using the antenna effectively.'
                })
    
    # Libero Analysis
    libero_players = []
    for player, stats in player_stats.items():
        pos = get_player_position(df, player)
        if pos == 'L':
            libero_players.append({'player': player, 'stats': stats})
    
    if libero_players:
        for libero in libero_players:
            reception = libero['stats'].get('reception_percentage', 0)
            total_rec = libero['stats'].get('total_receives', 0)
            if total_rec > 10 and reception < 0.75:
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': f'Libero {libero["player"]} - Reception Below Standard',
                    'message': f"Reception percentage: {reception:.1%} ({libero['stats'].get('good_receives', 0)}/{total_rec} good). Libero target: 75%+.",
                    'recommendation': f'Focus on reception fundamentals for {libero["player"]}. Libero is primary reception specialist. Work on platform work, reading serves, and positioning. Practice with various serve speeds and types. Improve movement to ball and first contact quality. Focus on consistency and minimizing reception errors.'
                })
    
    return insights


def _generate_action_distribution_insights(
    df: pd.DataFrame,
    team_stats: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about action and outcome distribution.
    
    Args:
        df: Match data DataFrame
        team_stats: Team statistics dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    # Action Distribution Analysis
    action_counts = df['action'].value_counts()
    total_actions = len(df)
    if total_actions > 0:
        attack_pct = action_counts.get('attack', 0) / total_actions
        if attack_pct < 0.20:  # Less than 20% attacks
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': 'Low Attack Percentage',
                'message': f"Only {attack_pct:.1%} of actions are attacks. Team may be too passive.",
                'recommendation': 'Increase attack frequency. Good reception should lead to attacks. Work on transition offense. Improve attack opportunities from good receptions.'
            })
        elif attack_pct > 0.35:  # More than 35% attacks
            insights.append({
                'type': 'info',
                'priority': 'low',
                'title': 'High Attack Percentage',
                'message': f"{attack_pct:.1%} of actions are attacks. Team is aggressive offensively.",
                'recommendation': 'Maintain offensive pressure. Ensure high attack efficiency accompanies high frequency.'
            })
    
    # Outcome Distribution Analysis
    outcome_counts = df['outcome'].value_counts()
    total_outcomes = len(df)
    if total_outcomes > 0:
        good_pct = outcome_counts.get('good', 0) / total_outcomes
        kill_pct = outcome_counts.get('kill', 0) / total_outcomes
        error_pct = outcome_counts.get('error', 0) / total_outcomes
        
        if error_pct > 0.15:  # More than 15% errors
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'High Error Rate Across All Actions',
                'message': f"Errors represent {error_pct:.1%} of all actions ({outcome_counts.get('error', 0)} total errors).",
                'recommendation': 'Focus on reducing unforced errors across all skills. Work on consistency and decision-making. Practice under pressure situations. Review error types and address root causes.'
            })
        
        if kill_pct < 0.08:  # Less than 8% kills
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Low Scoring Rate',
                'message': f"Kills represent only {kill_pct:.1%} of all actions. Low scoring efficiency.",
                'recommendation': 'Increase kill rate. Focus on attack placement, power, and decision-making. Work on finishing rallies. Improve attacking against blocks.'
            })
    
    # Attack Distribution - Are we balanced?
    if 'player_stats' in team_stats or hasattr(df, 'player'):
        # This would need player_stats passed separately
        pass
    
    return insights


def _generate_service_reception_battle_insights(
    team_stats: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate insights about service vs reception battle.
    
    Args:
        team_stats: Team statistics dictionary
        
    Returns:
        List of insight dictionaries
    """
    insights = []
    
    total_receives = team_stats['total_receives']
    service_aces = team_stats['service_aces']
    service_errors = team_stats['service_errors']
    
    if total_receives > 0 and service_aces + service_errors > 0:
        service_pressure = service_aces / (service_aces + service_errors) if (service_aces + service_errors) > 0 else 0
        reception_success = team_stats['good_receives'] / total_receives
        
        if service_pressure < 0.15 and reception_success < 0.70:
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Service-Reception Battle Not Favorable',
                'message': f"Low service pressure ({service_pressure:.1%}) and low reception success ({reception_success:.1%}).",
                'recommendation': 'Improve both serving and receiving. Work on service consistency and power. Simultaneously improve reception quality through focused drills. Both skills need attention for competitive play.'
            })
    
    return insights

