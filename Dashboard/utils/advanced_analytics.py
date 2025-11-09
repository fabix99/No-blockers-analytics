"""
Advanced analytics utilities
Predictive analytics, momentum indicators, tactical recommendations
"""
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np


def calculate_win_probability(current_score_us: int, current_score_them: int, 
                             serving_rate: float, receiving_rate: float,
                             set_number: int = 1) -> float:
    """Calculate win probability based on current score and historical rates.
    
    Args:
        current_score_us: Our current score in the set
        current_score_them: Opponent's current score in the set
        serving_rate: Historical serving point rate
        receiving_rate: Historical receiving point rate
        set_number: Current set number
        
    Returns:
        Win probability (0-1)
    """
    # Target score (usually 25, but can be 15 for 5th set)
    target_score = 25 if set_number < 5 else 15
    
    # Points needed to win
    points_needed_us = max(0, target_score - current_score_us)
    points_needed_them = max(0, target_score - current_score_them)
    
    # If we've already won or lost
    if points_needed_us == 0:
        return 1.0
    if points_needed_them == 0:
        return 0.0
    
    # Simple probability model: average of serving and receiving rates
    avg_point_win_rate = (serving_rate + receiving_rate) / 2
    
    # Calculate probability using binomial approximation
    # More sophisticated models could use Markov chains
    if points_needed_us <= points_needed_them:
        # We're ahead or tied - higher probability
        prob = 0.5 + (avg_point_win_rate - 0.5) * 0.3
    else:
        # We're behind - lower probability
        prob = 0.5 - (avg_point_win_rate - 0.5) * 0.3
    
    return max(0.0, min(1.0, prob))


def calculate_momentum_indicators(df: pd.DataFrame, loader=None) -> Dict[str, Any]:
    """Calculate momentum indicators (runs of points, streaks).
    
    Returns:
        Dict with momentum indicators
    """
    momentum = {
        'longest_winning_streak': 0,
        'longest_losing_streak': 0,
        'current_streak': 0,
        'current_streak_type': None,  # 'win' or 'loss'
        'runs_of_3_plus': 0,  # Number of runs of 3+ consecutive points
        'biggest_lead': 0,
        'biggest_deficit': 0
    }
    
    if loader is None or not hasattr(loader, 'team_events'):
        return momentum
    
    try:
        team_events = loader.team_events.sort_values(['Set', 'Point'])
        
        if 'Point Won' not in team_events.columns:
            return momentum
        
        # Determine point outcomes
        point_outcomes = []
        for _, row in team_events.iterrows():
            point_won = str(row.get('Point Won', '')).strip().lower()
            if point_won in ['yes', 'y', '1', 'true', 'us']:
                point_outcomes.append('win')
            elif point_won in ['no', 'n', '0', 'false', 'them']:
                point_outcomes.append('loss')
        
        if not point_outcomes:
            return momentum
        
        # Calculate streaks
        current_streak = 1
        current_type = point_outcomes[0]
        longest_win = 0
        longest_loss = 0
        runs_3_plus = 0
        
        for i in range(1, len(point_outcomes)):
            if point_outcomes[i] == point_outcomes[i-1]:
                current_streak += 1
            else:
                # Streak ended
                if current_type == 'win':
                    longest_win = max(longest_win, current_streak)
                    if current_streak >= 3:
                        runs_3_plus += 1
                else:
                    longest_loss = max(longest_loss, current_streak)
                    if current_streak >= 3:
                        runs_3_plus += 1
                
                current_streak = 1
                current_type = point_outcomes[i]
        
        # Check final streak
        if current_type == 'win':
            longest_win = max(longest_win, current_streak)
            if current_streak >= 3:
                runs_3_plus += 1
        else:
            longest_loss = max(longest_loss, current_streak)
            if current_streak >= 3:
                runs_3_plus += 1
        
        momentum['longest_winning_streak'] = longest_win
        momentum['longest_losing_streak'] = longest_loss
        momentum['current_streak'] = current_streak
        momentum['current_streak_type'] = current_type
        momentum['runs_of_3_plus'] = runs_3_plus
        
    except Exception as e:
        pass
    
    return momentum


def generate_tactical_recommendations(analyzer, kpis: Dict[str, Any], 
                                     loader=None) -> List[Dict[str, str]]:
    """Generate tactical recommendations based on current performance.
    
    Returns:
        List of recommendation dicts with 'type', 'title', 'message', 'priority'
    """
    recommendations = []
    
    # Check serving performance
    if kpis.get('break_point_rate', 0) < 0.50:
        recommendations.append({
            'type': 'serving',
            'title': 'Improve Serving Pressure',
            'message': f"Serving point rate is {kpis.get('break_point_rate', 0):.1%}, below target. Focus on aggressive serving and placement.",
            'priority': 'high'
        })
    
    # Check reception quality
    if kpis.get('reception_quality', 0) < 0.70:
        recommendations.append({
            'type': 'reception',
            'title': 'Enhance Reception Quality',
            'message': f"Reception quality is {kpis.get('reception_quality', 0):.1%}. Work on first contact and positioning.",
            'priority': 'high'
        })
    
    # Check attack efficiency
    if kpis.get('attack_efficiency', 0) < 0.25:
        recommendations.append({
            'type': 'attack',
            'title': 'Improve Attack Efficiency',
            'message': f"Attack efficiency is {kpis.get('attack_efficiency', 0):.1%}. Focus on shot selection and error reduction.",
            'priority': 'medium'
        })
    
    # Check block touch rate
    if kpis.get('block_touch_rate', 0) < 0.15:
        recommendations.append({
            'type': 'block',
            'title': 'Increase Block Presence',
            'message': f"Block touch rate is {kpis.get('block_touch_rate', 0):.1%}. Work on timing and positioning at the net.",
            'priority': 'medium'
        })
    
    # Check ace-to-error ratio
    ace_error_ratio = kpis.get('ace_to_error_ratio', 0)
    if ace_error_ratio < 0.5:
        recommendations.append({
            'type': 'serving',
            'title': 'Balance Serve Aggressiveness',
            'message': f"Ace-to-error ratio is {ace_error_ratio:.2f}. Consider more conservative serving to reduce errors.",
            'priority': 'low'
        })
    
    return recommendations


def analyze_timeout_effectiveness(loader=None) -> Dict[str, Any]:
    """Analyze timeout effectiveness (if timeout data is available).
    
    Returns:
        Dict with timeout analysis
    """
    # This would require timeout data in the event tracker
    # For now, return placeholder structure
    return {
        'timeouts_taken': 0,
        'points_won_after_timeout': 0,
        'points_lost_after_timeout': 0,
        'effectiveness_rate': 0.0,
        'message': 'Timeout data not available in current format'
    }


def analyze_substitution_impact(loader=None) -> Dict[str, Any]:
    """Analyze substitution impact (if substitution data is available).
    
    Returns:
        Dict with substitution analysis
    """
    # This would require substitution tracking in the event tracker
    # For now, return placeholder structure
    return {
        'substitutions_made': 0,
        'improvement_rate': 0.0,
        'message': 'Substitution data not available in current format'
    }


def analyze_player_complementarity(comparison_df, loader=None) -> Dict[str, Any]:
    """HIGH PRIORITY 5: Analyze player complementarity for optimal pairings.
    
    Args:
        comparison_df: DataFrame with player comparison data
        loader: Optional EventTrackerLoader for rotation data
        
    Returns:
        Dict with complementarity analysis including recommended pairings
    """
    complementarity_results = {
        'recommended_pairings': [],
        'avoid_pairings': [],
        'position_complementarity': {},
        'overall_score': 0.0
    }
    
    if loader is None or not hasattr(loader, 'team_data_by_rotation'):
        return complementarity_results
    
    # Analyze position combinations
    positions = comparison_df['Position'].unique()
    
    for i, pos1 in enumerate(positions):
        for pos2 in positions[i+1:]:
            players_pos1 = comparison_df[comparison_df['Position'] == pos1]
            players_pos2 = comparison_df[comparison_df['Position'] == pos2]
            
            if len(players_pos1) == 0 or len(players_pos2) == 0:
                continue
            
            # Calculate average ratings
            avg_rating_pos1 = players_pos1['Rating'].mean()
            avg_rating_pos2 = players_pos2['Rating'].mean()
            
            # Complementarity score (based on balanced performance)
            rating_diff = abs(avg_rating_pos1 - avg_rating_pos2)
            complementarity_score = 1.0 - (rating_diff / 10.0)  # Normalize by max rating
            
            # Also consider if positions have complementary strengths
            # (e.g., strong attacker + strong receiver)
            if complementarity_score > 0.7:
                complementarity_results['recommended_pairings'].append({
                    'position_1': pos1,
                    'position_2': pos2,
                    'score': complementarity_score,
                    'reason': f'Balanced performance (ratings: {avg_rating_pos1:.1f} vs {avg_rating_pos2:.1f})'
                })
            elif complementarity_score < 0.5:
                complementarity_results['avoid_pairings'].append({
                    'position_1': pos1,
                    'position_2': pos2,
                    'score': complementarity_score,
                    'reason': f'Performance imbalance (ratings: {avg_rating_pos1:.1f} vs {avg_rating_pos2:.1f})'
                })
    
    # Sort by score
    complementarity_results['recommended_pairings'].sort(key=lambda x: x['score'], reverse=True)
    complementarity_results['avoid_pairings'].sort(key=lambda x: x['score'])
    
    return complementarity_results

